#!/usr/bin/env python3
"""CI 冒烟测试用：模拟 GitHub releases/latest 接口。

用法：python3 mock_release_api.py --port 8902 [--tag v9.9.9]
      [--asset https://github.com/wuxinxin27/reverse-tunnel-manager/releases/download/v1.1.4/ReverseTunnelManager-1.1.4-setup.exe]
"""
import argparse
import http.server
import json


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--tag", default="v9.9.9")
    ap.add_argument("--asset", default="")
    ap.add_argument("--asset-name", default="")
    args = ap.parse_args()

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = {
                "tag_name": args.tag,
                "html_url": "https://github.com/wuxinxin27/reverse-tunnel-manager/releases",
                "assets": [],
            }
            if args.asset:
                body["assets"] = [{
                    "name": args.asset_name or args.asset.rsplit("/", 1)[-1],
                    "size": 1,
                    "browser_download_url": args.asset,
                }]
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    http.server.HTTPServer(("127.0.0.1", args.port), H).serve_forever()


if __name__ == "__main__":
    main()
