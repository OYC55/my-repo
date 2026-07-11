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


def fetch_data(companies, years, on_progress=None):
    """{company_name: {year: {account: value, ...ratios}}}

    on_progress(company_name, year)가 주어지면 각 조회 직전에 호출한다.
    """
    data = {}
    for company in companies:
        data[company["corp_name"]] = {}
        for year in years:
            if on_progress:
                on_progress(company["corp_name"], year)
            statements = get_financial_statement(company["corp_code"], year)
            accounts = extract_main_accounts(statements)
            ratios = compute_ratios(accounts)
            data[company["corp_name"]][year] = {**accounts, **ratios}
    return data
