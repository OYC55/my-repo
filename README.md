# 재무분석기

[OpenDART](https://opendart.fss.or.kr) API를 이용해 국내 기업 최대 3곳의 최근 3개년 재무제표를 비교하는 도구. CLI와 웹(Vercel 배포) 두 가지 방식으로 쓸 수 있다.

- 회사명으로 검색 (영문 대소문자 구분 없음)
- 매출액, 영업이익, 당기순이익, 자산총계, 부채총계, 자본총계 비교
- 영업이익률, 순이익률, ROE, ROA, 부채비율 자동 계산
- 결과를 엑셀(.xlsx)로 다운로드/저장

## 데모

배포된 웹 버전: https://my-repo-chi-roan.vercel.app

## 사전 준비

1. Python 3.11+
2. OpenDART API 키 발급: https://opendart.fss.or.kr → 오픈API 이용신청
3. 의존성 설치

```bash
pip install -r requirements.txt
```

4. 프로젝트 루트에 `.env` 생성

```
OPENDART_API=발급받은_키
```

## CLI로 사용하기

```bash
python main.py "삼성전자" "SK하이닉스" "LG전자" --years 2022 2023 2024
```

- 인자 없이 실행하면 회사명을 대화식으로 입력받는다 (연도 기본값: 최근 3년)
- 동명이인 기업이 여러 개 검색되면 번호로 선택
- 결과는 `재무비교.xlsx`로 저장 (`--output`으로 파일명 변경 가능)

## 웹으로 로컬 실행하기

`vercel dev` 없이 배포 환경(정적 페이지 + Flask API)을 근사해서 로컬에서 확인할 수 있다.

```bash
python scripts/dev_server.py
```

브라우저에서 http://localhost:5055 접속.

## Vercel 배포

1. GitHub 저장소를 Vercel 프로젝트로 Import
2. 프로젝트 Settings → Environment Variables에 `OPENDART_API` 등록
3. `main` 브랜치에 push하면 자동 배포됨

## 프로젝트 구조

```
dart_client.py      # OpenDART API 통신 (회사 검색, 재무제표 조회, 계정 매칭)
analysis.py          # 재무비율 계산, 회사x연도 병렬 조회
excel_builder.py      # 비교 결과를 엑셀 Workbook으로 생성
main.py                # CLI 진입점
api/index.py            # 웹용 Flask 진입점 (GET /api/search, POST /api/compare)
public/index.html        # 웹 프런트엔드 (자동완성 검색 + 다운로드)
data/corp_codes.json      # 전체 기업 코드 캐시 (배포 번들에 포함)
scripts/refresh_corp_codes.py  # corp_codes.json 수동 갱신
scripts/dev_server.py           # 로컬에서 웹 버전 실행용
```

## 기업 코드 캐시 갱신

새로 상장/등록된 기업이 검색되지 않으면 캐시를 갱신한다.

```bash
python scripts/refresh_corp_codes.py
```

갱신된 `data/corp_codes.json`을 커밋하고 push하면 배포에 반영된다.

## 계정 매칭 방식

재무제표 항목은 회사·연도마다 한글 표기가 달라(예: "매출액" vs "영업수익") 텍스트로 매칭하면 값이 누락될 수 있다. 대신 표준 XBRL 계정ID(`ifrs-full_Revenue`, `ifrs-full_ProfitLoss` 등)와 재무제표구분(`sj_div`: BS/IS/CIS)으로 매칭해 회사와 무관하게 안정적으로 값을 찾는다. 자세한 매핑은 [dart_client.py](dart_client.py)의 `ACCOUNT_ID_MAP` 참고.

## 제한 사항

- 최대 3개 기업, 연간 재무제표(사업보고서)만 지원
- 비상장사 등 표준계정을 제출하지 않는 일부 기업은 값이 비어 있을 수 있음
- `/api/search`, `/api/compare`는 인증 없이 공개되어 있음 (남용 시 OpenDART 일일 호출 한도 소진 가능)
