#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反向隧道管理器 —— 桌面窗口版
=============================
用 GTK + WebKit2 把管理界面装进一个原生窗口，像普通桌面软件一样使用：
在“显示应用程序”里点图标，或双击本目录的 reverse-tunnel-manager.desktop 打开。

- 后端与 app.py 完全相同（多服务器 SSH 反向隧道、自动重连、独立于其他 SSH 会话）
- 关闭窗口 = 停止全部隧道并退出（带确认框）
- 如果系统缺少 WebKit2，会自动退回“浏览器应用窗口 / 默认浏览器”方案

用法：
    ./desktop.py                # 打开窗口
    ./desktop.py --port 8787
    ./desktop.py --background   # 后台服务（无窗口），供开机自启
    ./desktop.py --smoke-test   # 自检（无界面）
"""

from __future__ import annotations

import argparse
import functools
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

if getattr(sys, "frozen", False):  # PyInstaller 打包运行时，资源在解包目录
    APP_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    APP_DIR = Path(__file__).resolve().parent
ICON = APP_DIR / "assets" / "icon.svg"

sys.path.insert(0, str(APP_DIR))


# ---------------------------------------------------------------- 基础组件

def load_gtk():
    """加载 Gtk3 + WebKit2（Ubuntu 24.04 是 4.1，22.04 是 4.0），失败抛异常"""
    import gi
    gi.require_version("Gtk", "3.0")
    last_err = None
    for ver in ("4.1", "4.0"):
        try:
            gi.require_version("WebKit2", ver)
            break
        except ValueError as e:
            last_err = e
    else:
        raise ImportError(f"系统缺少 WebKit2（{last_err}）")
    from gi.repository import GLib, Gtk, WebKit2
    return Gtk, WebKit2, GLib


def api_responding(port: int, timeout: float = 3.0) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/state", timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def start_backend(port: int, core):
    """启动核心服务，返回 (manager, httpd)"""
    manager = core.Manager()
    handler = core.make_handler(manager, None)
    httpd = core.ThreadingHTTPServer(("127.0.0.1", port), handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 0.5}, daemon=True).start()
    return manager, httpd


def find_browser() -> str | None:
    """找一个 Chromium 内核浏览器（用于 --app 应用窗口模式）"""
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
            Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe",
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                 "microsoft-edge", "msedge", "brave-browser"):
        path = shutil.which(name)
        if path:
            return path
    return None


# ---------------------------------------------------------------- 入口

def main() -> int:
    parser = argparse.ArgumentParser(description="反向隧道管理器（桌面窗口版）")
    parser.add_argument("--port", type=int, default=None, help="Web 服务端口（默认取配置文件）")
    parser.add_argument("--smoke-test", action="store_true", help="无界面自检")
    parser.add_argument("--background", action="store_true", help="后台服务模式：不开窗口，供开机自启使用")
    args = parser.parse_args()

    import app as core  # 复用 app.py 的核心逻辑

    try:
        cfg_port = int(core.load_config()["settings"].get("ui_port", 8787))
    except Exception:
        cfg_port = 8787
    port = args.port or cfg_port
    url = f"http://127.0.0.1:{port}"

    # 如果已有实例在运行，则只开一个新窗口连到它（不再启动第二份服务）
    owns = not api_responding(port)

    manager = httpd = None
    if owns:
        try:
            manager, httpd = start_backend(port, core)
        except OSError as e:
            print(f"[错误] 无法监听 127.0.0.1:{port}：{e}")
            return 1

    # ---- 无界面自检 ----
    if args.smoke_test:
        ok = api_responding(port)
        print("SMOKE:", "OK" if ok else "FAIL")
        if owns:
            manager.stop_all()
            httpd.shutdown()
        return 0 if ok else 1

    # ---- 后台服务模式（无窗口；供开机自启使用）----
    if args.background:
        if not owns:
            print("已有实例在运行，无需重复启动。")
            return 0
        stop_event = threading.Event()
        # 注意：不能用 lambda —— 类属性上的普通函数会被绑定成实例方法（多传一个 self）
        httpd.RequestHandlerClass.shutdown_cb = functools.partial(stop_event.set)
        for sig_name in ("SIGINT", "SIGTERM"):
            try:
                signal.signal(getattr(signal, sig_name), lambda *_: stop_event.set())
            except (ValueError, AttributeError, OSError):
                pass
        print(f"反向隧道管理器已在后台运行：{url}")
        print("（在 Web 界面点「退出工具」，或按 Ctrl+C / 关掉进程来停止）")
        if manager.config["settings"].get("auto_start", True):
            manager.start_enabled()
        try:
            while not stop_event.wait(1):
                pass
        except KeyboardInterrupt:
            pass
        manager.stop_all()
        httpd.shutdown()
        return 0

    # ---- 加载 GTK / WebKit2（Linux 原生窗口）----
    try:
        Gtk, WebKit2, GLib = load_gtk()
    except Exception as e:
        # 没有 WebKit2：退回“浏览器应用窗口”方案（Windows 上走这里，用 Edge/Chrome）
        print(f"[提示] 未使用 GTK/WebKit2（{e}），改用浏览器应用窗口。")
        browser = find_browser()
        stop_event = threading.Event()
        if owns:
            httpd.RequestHandlerClass.shutdown_cb = functools.partial(stop_event.set)

        if browser:
            # 用独立 profile，保证窗口关闭时浏览器进程真正退出（不会被已有浏览器实例接管）
            profile = str(core.DATA_DIR / "browser-profile")
            proc = subprocess.Popen(
                [browser, f"--app={url}", f"--user-data-dir={profile}",
                 "--class=reverse-tunnel-manager", "--no-first-run", "--no-default-browser-check"],
            )
            try:
                while proc.poll() is None and not stop_event.is_set():
                    time.sleep(0.4)
                if owns and stop_event.is_set() and proc.poll() is None:
                    proc.terminate()
            except KeyboardInterrupt:
                try:
                    proc.terminate()
                except OSError:
                    pass
        else:
            webbrowser.open(url)
            if owns:
                print("已用默认浏览器打开界面；在网页里点「退出工具」或按 Ctrl+C 结束。")
                try:
                    while not stop_event.wait(1):
                        pass
                except KeyboardInterrupt:
                    pass
        if owns:
            manager.stop_all()
            httpd.shutdown()
        return 0

    try:
        Gtk.init(None)
    except Exception:
        pass

    state = {"quitting": False}
    win = Gtk.Window(title="反向隧道管理器")
    win.set_default_size(1180, 800)
    win.set_position(Gtk.WindowPosition.CENTER)
    try:
        win.set_wmclass("reverse-tunnel-manager", "reverse-tunnel-manager")
    except Exception:
        pass
    if ICON.exists():
        try:
            win.set_icon_from_file(str(ICON))
        except Exception:
            pass

    view = WebKit2.WebView()
    view.load_uri(url)
    win.add(view)

    def quit_all(*_):
        """停止全部隧道并退出（幂等）"""
        if state["quitting"]:
            return False
        state["quitting"] = True
        try:
            win.set_sensitive(False)
        except Exception:
            pass

        def work():
            try:
                if owns:
                    manager.stop_all()
            finally:
                if owns:
                    try:
                        httpd.shutdown()
                    except Exception:
                        pass
                GLib.idle_add(Gtk.main_quit)

        threading.Thread(target=work, daemon=True).start()
        return False

    def on_delete(*_):
        if state["quitting"]:
            return True
        if not owns:
            return False  # 连的是别的实例：直接关窗口，不退出对方
        dialog = Gtk.MessageDialog(
            transient_for=win, modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="关闭窗口将停止全部隧道并退出工具。",
        )
        dialog.format_secondary_text("确定要退出吗？")
        resp = dialog.run()
        dialog.destroy()
        if resp == Gtk.ResponseType.OK:
            quit_all()
        return True

    win.connect("delete-event", on_delete)

    if owns:
        # Web 界面里的“退出工具”按钮也走同一套退出逻辑
        httpd.RequestHandlerClass.shutdown_cb = functools.partial(GLib.idle_add, quit_all)
        if hasattr(GLib, "unix_signal_add"):
            try:
                GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, quit_all)
                GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_all)
            except Exception:
                pass
        if manager.config["settings"].get("auto_start", True):
            threading.Thread(target=manager.start_enabled, daemon=True).start()

    win.show_all()
    Gtk.main()

    if owns:
        manager.stop_all()
        try:
            httpd.server_close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
