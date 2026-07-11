from __future__ import annotations

import http.server
import json
import socketserver
from pathlib import Path
from urllib.parse import urlparse

from ashare_replay.config import PROJECT_ROOT, load_settings
from ashare_replay.services.health import health_status


def _latest_html() -> Path | None:
    report_root = PROJECT_ROOT / "outputs" / "reports"
    files = sorted(report_root.glob("*/POST_CLOSE_FINAL/report.html"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/report"}:
            latest = _latest_html()
            if latest is None:
                self.send_response(404)
                self.end_headers()
                self.wfile.write("还没有生成报告，请先运行 generate-all。".encode())
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(latest.read_bytes())
            return
        if parsed.path == "/health":
            payload = json.dumps(health_status(load_settings()), ensure_ascii=False, indent=2)
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(payload.encode("utf-8"))
            return
        return super().do_GET()


def main() -> None:
    settings = load_settings()
    port = settings.streamlit_port
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"本地预览服务已启动：http://127.0.0.1:{port}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
