#!/usr/bin/env python3
"""CI 冒烟测试用：模拟 GitHub releases/latest 接口，并可选托管一个安装包文件。

用法：python3 mock_release_api.py --port 8902 [--tag v9.9.9]
      [--asset http://127.0.0.1:8902/setup.exe] [--serve-file dist/xxx-setup.exe]
"""
import argparse
import http.server
import json
import pathlib


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, required=True)
    ap.add_argument("--tag", default="v9.9.9")
    ap.add_argument("--asset", default="")
    ap.add_argument("--asset-name", default="")
    ap.add_argument("--serve-file", default="")
    args = ap.parse_args()
    serve_file = pathlib.Path(args.serve_file) if args.serve_file else None

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if serve_file and self.path in ("/setup.exe", "/" + serve_file.name):
                data = serve_file.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
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
