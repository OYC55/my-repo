from concurrent.futures import ThreadPoolExecutor, as_completed

from dart_client import extract_main_accounts, get_financial_statement

RATIO_LABELS = ["영업이익률(%)", "순이익률(%)", "ROE(%)", "ROA(%)", "부채비율(%)"]


def compute_ratios(accounts):
    revenue = accounts.get("매출액")
    op_income = accounts.get("영업이익")
    net_income = accounts.get("당기순이익")
    assets = accounts.get("자산총계")
    liabilities = accounts.get("부채총계")
    equity = accounts.get("자본총계")

    def pct(numer, denom):
        if numer is None or denom in (None, 0):
            return None
        return round(numer / denom * 100, 2)

    return {
        "영업이익률(%)": pct(op_income, revenue),
        "순이익률(%)": pct(net_income, revenue),
        "ROE(%)": pct(net_income, equity),
        "ROA(%)": pct(net_income, assets),
        "부채비율(%)": pct(liabilities, equity),
    }


def _fetch_one(company, year, on_progress):
    if on_progress:
        on_progress(company["corp_name"], year)
    statements = get_financial_statement(company["corp_code"], year)
    accounts = extract_main_accounts(statements)
    ratios = compute_ratios(accounts)
    return company["corp_name"], year, {**accounts, **ratios}


def fetch_data(companies, years, on_progress=None):
    """{company_name: {year: {account: value, ...ratios}}}

    회사x연도 조합마다 순차 호출하면 (회사수 x 연도수)만큼 DART API를 왕복해야 해서
    Vercel 함수 제한 시간을 넘기기 쉽다. 서로 독립적인 호출이므로 스레드풀로 병렬 실행한다.
    on_progress(company_name, year)가 주어지면 각 조회 시작 시 호출한다 (순서 보장 안 됨).
    """
    data = {company["corp_name"]: {} for company in companies}
    tasks = [(company, year) for company in companies for year in years]

    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        futures = [executor.submit(_fetch_one, company, year, on_progress) for company, year in tasks]
        for future in as_completed(futures):
            name, year, result = future.result()
            data[name][year] = result

    return data
