import argparse
import datetime
import sys

from analysis import fetch_data
from dart_client import find_company, load_corp_codes
from excel_builder import build_workbook


def resolve_company(name, corp_codes):
    company, candidates = find_company(name, corp_codes)
    if company:
        return company

    if not candidates:
        print(f"'{name}'에 해당하는 회사를 찾을 수 없습니다.")
        sys.exit(1)

    print(f"\n'{name}'에 대해 여러 회사가 검색되었습니다. 번호를 선택하세요:")
    for i, c in enumerate(candidates, 1):
        stock = f" ({c['stock_code']})" if c["stock_code"] else ""
        print(f"  {i}. {c['corp_name']}{stock}")
    choice = input("선택 (숫자): ").strip()
    try:
        idx = int(choice) - 1
        return candidates[idx]
    except (ValueError, IndexError):
        print("잘못된 선택입니다.")
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="OpenDART 기반 재무제표 비교 분석기")
    parser.add_argument("companies", nargs="*", help="비교할 회사명 (최대 3개)")
    parser.add_argument("--years", nargs="+", type=int, help="조회 연도 (예: 2023 2024 2025)")
    parser.add_argument("--output", default="재무비교.xlsx", help="출력 엑셀 파일명")
    return parser.parse_args()


def main():
    args = parse_args()

    companies_input = args.companies
    while len(companies_input) < 3:
        name = input(f"비교할 회사명 {len(companies_input) + 1}/3: ").strip()
        if name:
            companies_input.append(name)
    companies_input = companies_input[:3]

    if args.years:
        years = sorted(args.years)
    else:
        current_year = datetime.date.today().year
        years = [current_year - 3, current_year - 2, current_year - 1]

    print("기업 코드 목록 로딩 중...")
    corp_codes = load_corp_codes()

    companies = [resolve_company(name, corp_codes) for name in companies_input]

    def on_progress(company_name, year):
        print(f"조회 중: {company_name} {year}년...")

    data = fetch_data(companies, years, on_progress=on_progress)
    wb = build_workbook(data, companies, years)
    wb.save(args.output)
    print(f"\n엑셀 저장 완료: {args.output}")


if __name__ == "__main__":
    main()
