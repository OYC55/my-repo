"""data/corp_codes.json을 OpenDART에서 최신 기업코드 목록으로 갱신한다.
회사 목록이 오래됐다고 판단될 때 로컬에서 수동 실행 후 결과를 커밋한다.

사용법: python scripts/refresh_corp_codes.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dart_client import CORP_CODE_CACHE, load_corp_codes


def main():
    corps = load_corp_codes(force_refresh=True)
    print(f"{len(corps)}개 기업 코드 갱신 완료: {CORP_CODE_CACHE}")


if __name__ == "__main__":
    main()
