"""로컬 개발/검증용 서버.
Vercel의 실제 배포 동작(정적 public/ + api/index.py Flask 함수)을 근사해서
`vercel` CLI 없이도 브라우저에서 전체 흐름을 확인할 수 있게 한다.
배포에는 포함되지 않는다 (public/, api/만 Vercel이 사용).

사용법: python scripts/dev_server.py
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from api.index import app  # noqa: E402

app.static_folder = str(REPO_ROOT / "public")
app.static_url_path = ""


@app.route("/")
def _index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5055)
