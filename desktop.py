#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反向隧道管理器 —— 桌面窗口版
=============================
把管理界面装进独立的应用窗口，像普通桌面软件一样使用：

- Linux  : GTK + WebKit2 原生窗口
- Windows: 系统自带 Edge WebView2 原生窗口（pywebview；打包版已内置）
- 兜底   : Edge/Chrome 的 --app 应用窗口 → 默认浏览器

后端与 app.py 完全相同；关闭窗口 = 停止全部隧道并退出（带确认框）。

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
import traceback
import webbrowser
from pathlib import Path

if getattr(sys, "frozen", False):  # PyInstaller 打包运行时，资源在解包目录
    APP_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    APP_DIR = Path(__file__).resolve().parent
ICON = APP_DIR / "assets" / "icon.svg"

sys.path.insert(0, str(APP_DIR))


# ---------------------------------------------------------------- 公共辅助

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


def start_enabled_async(manager) -> None:
    if manager.config["settings"].get("auto_start", True):
        threading.Thread(target=manager.start_enabled, daemon=True).start()


def find_browser() -> str | None:
    """找一个 Chromium 内核浏览器（用于 --app 应用窗口兜底）"""
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


def _load_appindicator():
    """加载可用的 AppIndicator 模块（优先 Ayatana，兼容旧版 libappindicator3）"""
    try:
        import gi
    except Exception:
        return None
    for name in ("AyatanaAppIndicator3", "AppIndicator3"):
        try:
            gi.require_version(name, "0.1")
            return __import__(f"gi.repository.{name}", fromlist=[name])
        except Exception:
            continue
    return None


def _notify_tray_hint():
    """首次最小化到托盘时给一条系统通知"""
    try:
        icon_png = ICON.parent / "icon.png"
        cmd = ["notify-send", "反向隧道管理器",
               "已最小化到状态栏，隧道继续在后台运行。点击顶部栏图标可重新打开界面。"]
        cmd += ["-i", str(icon_png) if icon_png.exists() else "network-vpn"]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _tray_icon_file() -> str:
    """给 AppIndicator 使用的图标路径：优先复制到纯 ASCII 的运行时目录。
    （部分扩展对含中文等非 ASCII 字符的路径加载失败，会显示成占位符）"""
    src = ICON.parent / "icon.png"
    if not src.exists():
        src = ICON
    try:
        import gi
        from gi.repository import GLib
        runtime = GLib.get_user_runtime_dir()  # 如 /run/user/1000，纯 ASCII
        if runtime:
            dst = Path(runtime) / "reverse-tunnel-manager-tray.png"
            if not dst.exists():
                shutil.copyfile(src, dst)
            return str(dst)
    except Exception:
        pass
    return str(src)


def _setup_logging(core) -> None:
    """桌面版（无控制台）：把 stdout/stderr 写入日志文件，失败信息可追踪。"""
    try:
        if sys.stdout is not None and sys.stderr is not None and not getattr(sys, "frozen", False):
            if os.name != "nt" and sys.platform != "darwin":
                return
        log_dir = core.DATA_DIR / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "desktop.log"
        try:
            if log_file.exists() and log_file.stat().st_size > 2 * 1024 * 1024:
                log_file.replace(log_file.with_suffix(".log.1"))
        except OSError:
            pass
        stream = open(log_file, "a", encoding="utf-8", buffering=1)
        sys.stdout = stream
        sys.stderr = stream
        print()
        print(f"===== {time.strftime('%Y-%m-%d %H:%M:%S')} desktop 启动 =====")
        print(f"platform={sys.platform} frozen={getattr(sys, 'frozen', False)} args={sys.argv[1:]}")
    except Exception:
        pass


def _fmt_bytes(n) -> str:
    try:
        v = float(n)
    except (TypeError, ValueError):
        v = 0.0
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    return (f"{v:.0f}" if i == 0 else f"{v:.1f}") + " " + units[i]


_TRAY_LABELS = {
    "zh": {"title": "反向隧道管理器", "show": "显示主界面", "start_all": "全部启动",
           "stop_all": "全部停止", "quit": "退出（停止全部隧道）", "running": "条运行中"},
    "en": {"title": "Reverse Tunnel Manager", "show": "Show window", "start_all": "Start all",
           "stop_all": "Stop all", "quit": "Quit (stop all tunnels)", "running": "running"},
}


def _tray_lang(manager) -> str:
    try:
        lang = str(manager.config["settings"].get("language", "auto"))
    except Exception:
        lang = "auto"
    if lang in ("zh", "en"):
        return lang
    return "zh" if str(os.environ.get("LANG", "")).lower().startswith("zh") else "en"


def _create_tray_win32(window, manager, quit_cb):
    """Windows 系统托盘（pystray；打包版已内置）。不可用时返回 None。"""
    try:
        import pystray
        from PIL import Image
    except Exception:
        traceback.print_exc()
        print("[tray] 无法导入 pystray / Pillow，系统托盘不可用")
        return None
    icon_png = ICON.parent / "icon.png"
    try:
        image = Image.open(str(icon_png if icon_png.exists() else ICON))
        image.load()
    except Exception:
        traceback.print_exc()
        print("[tray] 无法加载托盘图标文件")
        return None

    L = _TRAY_LABELS[_tray_lang(manager)]

    def on_show(icon, item):
        try:
            window.show()
            window.restore()
        except Exception:
            pass

    def on_start_all(icon, item):
        threading.Thread(target=manager.start_all, daemon=True).start()

    def on_stop_all(icon, item):
        threading.Thread(target=manager.stop_all, daemon=True).start()

    def on_quit(icon, item):
        quit_cb()

    def build_menu(*_args):
        items = []
        try:
            snaps = manager.state()["tunnels"]
        except Exception:
            snaps = []
        for snap in snaps:
            running = snap["state"] == "running"
            label = ("● " if running else "○ ") + str(snap.get("name") or "")
            tid = snap["id"]

            def _toggle(icon, item, _tid=tid, _run=running):
                try:
                    if _run:
                        manager.stop(_tid)
                    else:
                        manager.start(_tid)
                except Exception:
                    pass

            items.append(pystray.MenuItem(label, _toggle))
        if items:
            items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(L["show"], on_show, default=True))
        items.append(pystray.MenuItem(L["start_all"], on_start_all))
        items.append(pystray.MenuItem(L["stop_all"], on_stop_all))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(L["quit"], on_quit))
        return items

    try:
        menu = pystray.Menu(build_menu)
        icon = pystray.Icon("reverse-tunnel-manager", image, L["title"], menu)
        threading.Thread(target=icon.run, daemon=True).start()
    except Exception:
        traceback.print_exc()
        print("[tray] pystray 初始化失败")
        return None

    def _title_loop():
        while True:
            try:
                snaps = manager.state()["tunnels"]
                rate = sum(int(x.get("rate") or 0) for x in snaps)
                running = sum(1 for x in snaps if x["state"] == "running")
                icon.title = f'{L["title"]} — ⇅ {_fmt_bytes(rate)}/s · {running} {L["running"]}'
            except Exception:
                pass
            time.sleep(3)

    threading.Thread(target=_title_loop, daemon=True).start()
    return icon


# ---------------------------------------------------------------- Linux：GTK + WebKit2

def run_gtk_window(url, owns, manager, httpd, core) -> int | None:
    """Linux 原生窗口。GTK/WebKit2 不可用时返回 None。"""
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        last_err = None
        for ver in ("4.1", "4.0"):  # Ubuntu 24.04 是 4.1，22.04 是 4.0
            try:
                gi.require_version("WebKit2", ver)
                break
            except ValueError as e:
                last_err = e
        else:
            raise ImportError(f"系统缺少 WebKit2（{last_err}）")
        from gi.repository import GLib, Gtk, WebKit2
    except Exception as e:
        print(f"[提示] GTK/WebKit2 不可用（{e}），尝试其他窗口方案。")
        return None

    # Wayland 下 set_wmclass 无效，靠 prgname 设置应用 ID，才能与 .desktop 关联（收藏栏图标/合并）
    try:
        GLib.set_prgname("reverse-tunnel-manager")
        GLib.set_application_name("反向隧道管理器")
    except Exception:
        pass

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
    icon_png = ICON.parent / "icon.png"
    for cand in (icon_png, ICON):
        if cand.exists():
            try:
                win.set_icon_from_file(str(cand))
                break
            except Exception:
                continue

    view = WebKit2.WebView()
    view.load_uri(url)
    win.add(view)

    # ---- 系统托盘（Ubuntu 顶栏 AppIndicator）----
    AppIndicator = _load_appindicator() if owns else None
    indicator = None
    tray_available = False
    if owns:
        if AppIndicator is None:
            print("[提示] 未检测到 AppIndicator，无法最小化到状态栏"
                  "（可安装 gir1.2-ayatanaappindicator3-0.1 或 gir1.2-appindicator3-0.1 后重启）")
        else:
            try:
                L = _TRAY_LABELS[_tray_lang(manager)]
                indicator = AppIndicator.Indicator.new(
                    "reverse-tunnel-manager",
                    _tray_icon_file(),
                    AppIndicator.IndicatorCategory.APPLICATION_STATUS,
                )
                indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
                indicator.set_title(L["title"])

                def _menu_item(label, cb):
                    item = Gtk.MenuItem(label=label)
                    item.connect("activate", lambda *_: cb())
                    return item

                def _show_window():
                    win.show_all()
                    win.present()

                def _run_bg(fn, *args):
                    threading.Thread(target=fn, args=args, daemon=True).start()

                sig = {"last": None}

                def _rebuild_menu():
                    try:
                        snaps = manager.state()["tunnels"]
                    except Exception:
                        snaps = []
                    m = Gtk.Menu()
                    for snap in snaps:
                        running = snap["state"] == "running"
                        label = ("● " if running else "○ ") + str(snap.get("name") or "")
                        tid = snap["id"]
                        if running:
                            m.append(_menu_item(label, lambda _t=tid: _run_bg(manager.stop, _t)))
                        else:
                            m.append(_menu_item(label, lambda _t=tid: _run_bg(manager.start, _t)))
                    if snaps:
                        m.append(Gtk.SeparatorMenuItem())
                    m.append(_menu_item(L["show"], _show_window))
                    m.append(_menu_item(L["start_all"], lambda: _run_bg(manager.start_all)))
                    m.append(_menu_item(L["stop_all"], lambda: _run_bg(manager.stop_all)))
                    m.append(Gtk.SeparatorMenuItem())
                    m.append(_menu_item(L["quit"], lambda: quit_all()))
                    m.show_all()
                    indicator.set_menu(m)

                def _tick():
                    try:
                        snaps = manager.state()["tunnels"]
                        running = sum(1 for s in snaps if s["state"] == "running")
                        rate = sum(int(s.get("rate") or 0) for s in snaps)
                        indicator.set_title(f'{L["title"]} — ⇅ {_fmt_bytes(rate)}/s · {running} {L["running"]}')
                        state_sig = "|".join(f'{s["id"]}:{s["state"]}:{s["name"]}' for s in snaps)
                        if state_sig != sig["last"]:
                            sig["last"] = state_sig
                            _rebuild_menu()
                    except Exception:
                        pass
                    return True

                _rebuild_menu()
                GLib.timeout_add_seconds(3, _tick)
                tray_available = True
                print("系统托盘已启用（动态隧道菜单 + 速率显示）")
            except Exception as e:
                traceback.print_exc()
                print(f"[提示] 系统托盘初始化失败（{e}）")
                indicator = None
                tray_available = False
        manager.tray_available = tray_available

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
                    if indicator is not None:
                        try:
                            indicator.set_status(AppIndicator.IndicatorStatus.PASSIVE)
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
        if tray_available:
            # 最小化到状态栏：隐藏窗口，隧道继续运行
            win.hide()
            if not state.get("tray_hint_shown"):
                state["tray_hint_shown"] = True
                _notify_tray_hint()
            return True
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

    if owns and tray_available:
        try:
            from gi.repository import Gdk

            def _on_window_state(_w, event):
                if event.new_window_state & Gdk.WindowState.ICONIFIED:
                    _w.hide()
                    if not state.get("tray_hint_shown"):
                        state["tray_hint_shown"] = True
                        _notify_tray_hint()
                    return True
                return False

            win.connect("window-state-event", _on_window_state)
        except Exception:
            traceback.print_exc()

    if owns:
        # 注意：类属性不能用 lambda（会被绑定成实例方法），用 partial
        httpd.RequestHandlerClass.shutdown_cb = functools.partial(GLib.idle_add, quit_all)
        if hasattr(GLib, "unix_signal_add"):
            try:
                GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, quit_all)
                GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, quit_all)
            except Exception:
                pass
        start_enabled_async(manager)

    win.show_all()
    Gtk.main()

    if owns:
        manager.stop_all()
        try:
            httpd.server_close()
        except Exception:
            pass
    return 0


# ---------------------------------------------------------------- Windows：WebView2（pywebview）

def run_webview_window(url, owns, manager, httpd, core) -> int | None:
    """Windows 原生窗口（系统自带 Edge WebView2 内核）。不可用时返回 None。"""
    try:
        import webview  # pywebview：打包版已内置；源码运行需 pip install pywebview
    except Exception:
        return None
    try:
        window = webview.create_window(
            "反向隧道管理器", url, width=1180, height=800, min_size=(760, 520),
        )
        state = {"quitting": False}
        tray_icon = None

        def quit_all(*_):
            if state["quitting"]:
                return
            state["quitting"] = True
            if tray_icon is not None:
                try:
                    tray_icon.stop()
                except Exception:
                    pass
            try:
                window.destroy()
            except Exception:
                pass

        if owns and sys.platform != "darwin":
            tray_icon = _create_tray_win32(window, manager, lambda: quit_all())
            if tray_icon is not None:
                manager.tray_available = True
                try:
                    manager.set_notifier(lambda title, body, _i=tray_icon: _i.notify(body, title))
                except Exception:
                    traceback.print_exc()
                print("[tray] 系统托盘已启用")
            else:
                manager.tray_available = False
                print("[tray] 系统托盘不可用：关闭/最小化窗口将退出。"
                      "（详见本日志；打包版请确认包含 pystray/Pillow）")
        elif owns:
            manager.tray_available = False
            print("[提示] macOS 上暂不支持系统托盘；关闭窗口将退出工具。")

        def _hide_window() -> bool:
            try:
                if hasattr(window, "hide"):
                    window.hide()
                else:
                    window.minimize()
                return True
            except Exception:
                traceback.print_exc()
                return False

        def _show_tray_hint():
            if state.get("tray_hint_shown"):
                return
            state["tray_hint_shown"] = True
            try:
                tray_icon.notify(
                    "已收缩到右下角状态栏，隧道继续在后台运行。双击/右键托盘图标可重新打开。",
                    "反向隧道管理器")
            except Exception:
                traceback.print_exc()

        def on_closing():
            if state["quitting"] or not owns:
                return True
            if tray_icon is not None:
                if _hide_window():
                    _show_tray_hint()
                    return False  # 取消关闭，隐藏到托盘
            try:
                return bool(window.create_confirmation_dialog(
                    "反向隧道管理器", "关闭窗口将停止全部隧道并退出工具。\n确定要退出吗？"))
            except Exception:
                traceback.print_exc()
                return True

        def on_minimized(*_):
            """点最小化按钮 → 收缩到托盘"""
            if state["quitting"] or not owns or tray_icon is None:
                return
            if _hide_window():
                _show_tray_hint()

        window.events.closing += on_closing
        try:
            window.events.minimized += on_minimized
        except Exception:
            traceback.print_exc()  # 该 pywebview 版本不支持 minimized 事件时忽略
        if owns:
            httpd.RequestHandlerClass.shutdown_cb = functools.partial(quit_all)
            start_enabled_async(manager)

        webview.start()  # 阻塞直到窗口关闭（主线程）

        if tray_icon is not None:
            try:
                tray_icon.stop()
            except Exception:
                pass
        if owns:
            manager.stop_all()
            try:
                httpd.shutdown()
            except Exception:
                pass
        return 0
    except Exception as e:
        print(f"[提示] WebView2 窗口启动失败（{e}），尝试其他窗口方案。")
        return None


# ---------------------------------------------------------------- 兜底：Edge/Chrome 应用窗口

def run_browser_window(url, owns, manager, httpd, core) -> int:
    manager.tray_available = False
    browser = find_browser()
    stop_event = threading.Event()
    if owns:
        httpd.RequestHandlerClass.shutdown_cb = functools.partial(stop_event.set)

    if browser:
        # 独立 profile，保证窗口关闭时浏览器进程真正退出（不会被已有浏览器实例接管）
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


# ---------------------------------------------------------------- 入口

def main() -> int:
    if sys.stdout is None:  # PyInstaller --noconsole 时没有标准输出
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="反向隧道管理器（桌面窗口版）")
    parser.add_argument("--port", type=int, default=None, help="Web 服务端口（默认取配置文件）")
    parser.add_argument("--smoke-test", action="store_true", help="无界面自检")
    parser.add_argument("--background", action="store_true", help="后台服务模式：不开窗口，供开机自启使用")
    args = parser.parse_args()

    import app as core  # 复用 app.py 的核心逻辑

    _setup_logging(core)

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
        httpd.RequestHandlerClass.shutdown_cb = functools.partial(stop_event.set)
        for sig_name in ("SIGINT", "SIGTERM"):
            try:
                signal.signal(getattr(signal, sig_name), lambda *_: stop_event.set())
            except (ValueError, AttributeError, OSError):
                pass
        print(f"反向隧道管理器已在后台运行：{url}")
        print("（在 Web 界面点「退出工具」，或按 Ctrl+C / 关掉进程来停止）")
        start_enabled_async(manager)
        try:
            while not stop_event.wait(1):
                pass
        except KeyboardInterrupt:
            pass
        manager.stop_all()
        httpd.shutdown()
        return 0

    # ---- 窗口模式：GTK 原生 → WebView2 原生 → 浏览器应用窗口 ----
    for runner in (run_gtk_window, run_webview_window):
        rc = runner(url, owns, manager, httpd, core)
        if rc is not None:
            return rc
    return run_browser_window(url, owns, manager, httpd, core)


if __name__ == "__main__":
    sys.exit(main())
