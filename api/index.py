import base64
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, request

from analysis import RATIO_LABELS, fetch_data
from dart_client import MAIN_ACCOUNTS, get_company_by_code, load_corp_codes, search_companies
from excel_builder import build_workbook

app = Flask(__name__)


@app.errorhandler(Exception)
def handle_exception(e):
    """예상치 못한 서버 오류도 HTML이 아닌 JSON으로 반환해 원인을 바로 알 수 있게 한다."""
    return jsonify({"error": str(e)}), 500


_corp_codes_cache = None


def _corp_codes():
    global _corp_codes_cache
    if _corp_codes_cache is None:
        _corp_codes_cache = load_corp_codes()
    return _corp_codes_cache


@app.route("/api/search")
def search():
    query = request.args.get("q", "")
    results = search_companies(query, corp_codes=_corp_codes())
    return jsonify(results)


@app.route("/api/compare", methods=["POST"])
def compare():
    body = request.get_json(silent=True) or {}
    companies_in = body.get("companies")
    years_in = body.get("years")

    if not isinstance(companies_in, list) or len(companies_in) != 3:
        return jsonify({"error": "companies는 정확히 3개여야 합니다."}), 400
    if not isinstance(years_in, list) or len(years_in) != 3:
        return jsonify({"error": "years는 정확히 3개여야 합니다."}), 400

    corp_codes = _corp_codes()
    companies = []
    for item in companies_in:
        corp_code = (item or {}).get("corp_code") if isinstance(item, dict) else None
        company = get_company_by_code(corp_code, corp_codes=corp_codes) if corp_code else None
        if not company:
            return jsonify({"error": f"알 수 없는 회사코드: {corp_code}"}), 400
        companies.append(company)

    try:
        years = sorted(int(y) for y in years_in)
    except (TypeError, ValueError):
        return jsonify({"error": "years는 숫자여야 합니다."}), 400

    data = fetch_data(companies, years)
    wb = build_workbook(data, companies, years)

    buf = BytesIO()
    wb.save(buf)

    return jsonify({
        "companies": companies,
        "years": years,
        "rows": list(MAIN_ACCOUNTS) + RATIO_LABELS,
        "ratio_rows": RATIO_LABELS,
        "data": data,
        "xlsx_base64": base64.b64encode(buf.getvalue()).decode("ascii"),
    })
