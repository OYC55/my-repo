import io
import json
import os
import zipfile
from pathlib import Path

import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://opendart.fss.or.kr/api"
CORP_CODE_CACHE = Path(__file__).parent / "data" / "corp_codes.json"

MAIN_ACCOUNTS = [
    "매출액",
    "영업이익",
    "당기순이익",
    "자산총계",
    "부채총계",
    "자본총계",
]

# 표준 XBRL 계정ID + 재무제표구분(sj_div)으로 매칭한다.
# account_nm(한글 계정명)은 기업/연도별로 "매출액" vs "영업수익" 등으로 표기가 달라
# 텍스트 매칭으로는 누락이 발생하므로 사용하지 않는다.
ACCOUNT_ID_MAP = {
    "매출액": ("ifrs-full_Revenue", ("IS", "CIS")),
    "영업이익": ("dart_OperatingIncomeLoss", ("IS", "CIS")),
    "당기순이익": ("ifrs-full_ProfitLoss", ("IS", "CIS")),
    "자산총계": ("ifrs-full_Assets", ("BS",)),
    "부채총계": ("ifrs-full_Liabilities", ("BS",)),
    "자본총계": ("ifrs-full_Equity", ("BS",)),
}


def _get_api_key():
    key = os.getenv("OPENDART_API")
    if not key:
        raise RuntimeError(".env에 OPENDART_API 키가 설정되어 있지 않습니다.")
    return key


def _download_corp_codes():
    resp = requests.get(BASE_URL + "/corpCode.xml", params={"crtfc_key": _get_api_key()}, timeout=30)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        xml_bytes = zf.read("CORPCODE.xml")

    root = ET.fromstring(xml_bytes)
    corps = []
    for node in root.findall("list"):
        corp_code = node.findtext("corp_code")
        corp_name = node.findtext("corp_name")
        stock_code = (node.findtext("stock_code") or "").strip()
        corps.append({"corp_code": corp_code, "corp_name": corp_name, "stock_code": stock_code})

    CORP_CODE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    CORP_CODE_CACHE.write_text(json.dumps(corps, ensure_ascii=False), encoding="utf-8")
    return corps


def load_corp_codes(force_refresh=False):
    if not force_refresh and CORP_CODE_CACHE.exists():
        return json.loads(CORP_CODE_CACHE.read_text(encoding="utf-8"))
    return _download_corp_codes()


def find_company(name, corp_codes=None):
    """회사명으로 검색(영문 대소문자 구분 안 함). 정확히 일치하는 상장사를 우선 반환하고,
    없으면 후보 목록(부분일치)을 반환한다."""
    corp_codes = corp_codes if corp_codes is not None else load_corp_codes()
    name_cf = name.casefold()

    exact = [c for c in corp_codes if c["corp_name"].casefold() == name_cf]
    if len(exact) == 1:
        return exact[0], []
    if len(exact) > 1:
        listed = [c for c in exact if c["stock_code"]]
        if len(listed) == 1:
            return listed[0], []
        return None, listed or exact

    partial = [c for c in corp_codes if name_cf in c["corp_name"].casefold()]
    listed_partial = [c for c in partial if c["stock_code"]]
    candidates = listed_partial or partial
    if len(candidates) == 1:
        return candidates[0], []
    return None, candidates[:20]


def search_companies(query, corp_codes=None, limit=20):
    """자동완성 검색용(영문 대소문자 구분 안 함). 정확일치 > 접두어일치 > 포함일치 순으로 묶고,
    각 묶음 안에서는 상장사 우선, 이름이 짧은(더 관련도 높은) 순으로 정렬한다."""
    query = (query or "").strip()
    if not query:
        return []
    corp_codes = corp_codes if corp_codes is not None else load_corp_codes()
    query_cf = query.casefold()

    matches = [c for c in corp_codes if query_cf in c["corp_name"].casefold()]

    def rank(c):
        name_cf = c["corp_name"].casefold()
        if name_cf == query_cf:
            group = 0
        elif name_cf.startswith(query_cf):
            group = 1
        else:
            group = 2
        return (group, 0 if c["stock_code"] else 1, len(c["corp_name"]), name_cf)

    matches.sort(key=rank)
    return matches[:limit]


def get_company_by_code(corp_code, corp_codes=None):
    """corp_code로 회사 정보 조회 (클라이언트가 보낸 corp_code 검증용)."""
    corp_codes = corp_codes if corp_codes is not None else load_corp_codes()
    for c in corp_codes:
        if c["corp_code"] == corp_code:
            return c
    return None


def get_financial_statement(corp_code, year, reprt_code="11011", fs_div="CFS"):
    """단일회사 주요계정 조회. CFS(연결) 없으면 OFS(별도)로 재시도."""
    for div in ([fs_div, "OFS"] if fs_div == "CFS" else [fs_div]):
        resp = requests.get(
            BASE_URL + "/fnlttSinglAcntAll.json",
            params={
                "crtfc_key": _get_api_key(),
                "corp_code": corp_code,
                "bsns_year": year,
                "reprt_code": reprt_code,
                "fs_div": div,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "000":
            return data.get("list", [])
    return []


def _to_int(amount):
    try:
        return int(str(amount).replace(",", ""))
    except (ValueError, TypeError):
        return None


def extract_main_accounts(statement_list):
    """주요 계정만 뽑아 {계정명: 금액} 형태로 정리.
    표준 계정ID(account_id) + 재무제표구분(sj_div)으로 매칭한다."""
    result = {acc: None for acc in MAIN_ACCOUNTS}
    for label, (account_id, sj_divs) in ACCOUNT_ID_MAP.items():
        candidates = [
            item for item in statement_list
            if item.get("account_id") == account_id and item.get("sj_div") in sj_divs
        ]
        for preferred_div in sj_divs:
            match = next((c for c in candidates if c.get("sj_div") == preferred_div), None)
            if match:
                result[label] = _to_int(match.get("thstrm_amount"))
                break
    return result
