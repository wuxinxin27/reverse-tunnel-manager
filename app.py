#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
反向隧道管理器 (Reverse Tunnel Manager)
=======================================
零第三方依赖（Python 标准库 + 系统 ssh 命令）的多服务器 SSH 反向隧道管理器。

功能：
  - 管理多台服务器的 SSH 反向转发（远端端口 -> 本机端口，例如 127.0.0.1:7890）
  - 每台服务器一个独立的 ssh 进程，断线自动重连；与 IDE / 终端里的 SSH 会话完全无关
  - 本地 Web 界面（默认 http://127.0.0.1:8787），浏览器中可视化增删改查 / 启停 / 查看日志
  - 支持 ~/.ssh/config 别名 或 自定义 主机/端口/用户名/私钥
  - 支持同一条隧道配置多条转发规则（多个远端端口 -> 本机目标）
  - 支持从 "ssh user@host -p 22" 形式的命令自动解析连接参数
  - 隧道连通性测试（检查认证、网络、远端端口是否被占用）
  - 日志持久化、配置导入导出、开机自启动（可选）

配置文件： ~/.config/reverse-tunnel-manager/config.json
日志目录： ~/.local/share/reverse-tunnel-manager/logs/
"""

import argparse
import atexit
import collections
import json
import os
import queue
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import uuid
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# ---------------------------------------------------------------- 路径与默认值

if getattr(sys, "frozen", False):  # PyInstaller 打包运行时，资源在解包目录
    APP_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
ICON_FILE = APP_DIR / "assets" / "icon.svg"
VERSION = "1.1.1"


def _base_dir(kind: str) -> Path:
    """配置/数据目录：Windows 用 %APPDATA%/%LOCALAPPDATA%，Linux 遵循 XDG 规范"""
    env_key = "RTM_CONFIG_DIR" if kind == "config" else "RTM_DATA_DIR"
    v = os.environ.get(env_key)
    if v:
        return Path(v)
    if os.name == "nt":
        env = "APPDATA" if kind == "config" else "LOCALAPPDATA"
        base = os.environ.get(env)
        if not base:
            base = str(Path.home() / "AppData" / ("Roaming" if kind == "config" else "Local"))
        return Path(base) / "ReverseTunnelManager"
    xdg = os.environ.get("XDG_CONFIG_HOME" if kind == "config" else "XDG_DATA_HOME")
    if xdg:
        return Path(xdg) / "reverse-tunnel-manager"
    fallback = ".config" if kind == "config" else ".local/share"
    return Path.home() / fallback / "reverse-tunnel-manager"


CONFIG_DIR = _base_dir("config")
CONFIG_FILE = CONFIG_DIR / "config.json"
DATA_DIR = _base_dir("data")
LOG_DIR = DATA_DIR / "logs"
# 故意留空的 ssh 配置文件：命令用 -F 指向它可完全忽略用户 ~/.ssh/config，
# 跨平台路径比 /dev/null 更可靠（Windows 上是 NUL 的坑）。
NO_SSH_CONFIG = DATA_DIR / "empty_ssh_config"

DEFAULT_SETTINGS = {
    "retry_seconds": 5,      # 断线后重连间隔（智能重连的基准值，失败后指数退避）
    "auto_start": True,      # 工具启动时，自动启动勾选了“随工具启动”的隧道
    "ui_port": 8787,         # 本地 Web 界面端口
    "extra_ssh_args": "",    # 追加到所有 ssh 命令的额外参数
    "notify": True,          # 断开 / 重连成功等事件发系统通知
    "theme": "auto",         # 界面主题：auto / dark / light
    "language": "auto",      # 界面语言：auto / zh / en
    "update_check": True,    # 启动时检查 GitHub 是否有新版本
    "proxy_check": True,     # 定期探测本机目标端口（代理）是否在监听
}

SSH_BASE_OPTS_COMMON = [
    ("ExitOnForwardFailure", "yes"),   # 远端端口绑定失败立即退出，交给重建逻辑明确报错
    ("BatchMode", "yes"),              # 完全非交互，绝不提示输入
    ("ConnectTimeout", "15"),
    ("ServerAliveInterval", "15"),     # 保活：网络中断约 45 秒内判定断线
    ("ServerAliveCountMax", "3"),
    ("TCPKeepAlive", "yes"),
]

# 错误行 => (中文解释, 是否致命)
_ERROR_RULES = [
    (re.compile(r"remote port forwarding failed for listen port (\d+)"),
     lambda m: f"远端端口 {m.group(1)} 已被占用（可能有其他隧道/会话在用，或上次连接还没释放）", True),
    (re.compile(r"connect_to (\S+) port (\d+): failed"),
     lambda m: f"隧道正常，但本机目标 {m.group(1)}:{m.group(2)} 没有服务（请检查本机代理是否在运行）", False),
    (re.compile(r"Permission denied"),
     lambda m: "认证失败：请检查用户名 / 私钥 / 免密公钥是否配置正确", True),
    (re.compile(r"Connection refused"),
     lambda m: "连接被拒绝：请检查主机地址、SSH 端口是否正确", True),
    (re.compile(r"Connection timed out|Operation timed out|Connection timeout"),
     lambda m: "连接超时：网络不通或防火墙拦截", True),
    (re.compile(r"Host key verification failed"),
     lambda m: "主机密钥校验失败：请清理对应的 known_hosts 记录", True),
    (re.compile(r"Could not resolve hostname"),
     lambda m: "无法解析主机名：请检查地址拼写和网络", True),
    (re.compile(r"Too many authentication failures"),
     lambda m: "认证失败次数过多：服务器上可能装了太多私钥，建议在配置中明确指定私钥文件", True),
    (re.compile(r"Network is unreachable"),
     lambda m: "网络不可达：请检查本机网络", True),
    (re.compile(r"kex_exchange_identification"),
     lambda m: "SSH 握手被中断：服务器可能限流，或端口不是 SSH 服务", True),
    (re.compile(r"Timeout, server .* not responding|Broken pipe"),
     lambda m: "连接中断：远端无响应", True),
]


def analyze_ssh_line(line: str):
    """返回 (中文解释, 是否致命) 或 None"""
    for rx, handler, fatal in _ERROR_RULES:
        m = rx.search(line)
        if m:
            return handler(m), fatal
    return None


def read_process_io(pid: int) -> tuple[int, int] | None:
    """读取进程累计 I/O 计数，返回 (接收字节, 发送字节)；失败返回 None。
    Linux: /proc/<pid>/io 的 rchar/wchar；Windows: GetProcessIoCounters。
    对 ssh 进程来说，这基本就是该隧道的上下行流量。"""
    if os.name == "nt":
        try:
            import ctypes

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("ReadOperationCount", ctypes.c_ulonglong),
                    ("WriteOperationCount", ctypes.c_ulonglong),
                    ("OtherOperationCount", ctypes.c_ulonglong),
                    ("ReadTransferCount", ctypes.c_ulonglong),
                    ("WriteTransferCount", ctypes.c_ulonglong),
                    ("OtherTransferCount", ctypes.c_ulonglong),
                ]

            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if not h:
                return None
            try:
                counters = IO_COUNTERS()
                if not k32.GetProcessIoCounters(h, ctypes.byref(counters)):
                    return None
                return int(counters.ReadTransferCount), int(counters.WriteTransferCount)
            finally:
                k32.CloseHandle(h)
        except Exception:
            return None
    try:
        vals: dict[str, int] = {}
        with open(f"/proc/{pid}/io", "r", encoding="ascii") as f:
            for line in f:
                key, _, value = line.partition(":")
                vals[key.strip()] = int(value.strip() or 0)
        return vals.get("rchar", 0), vals.get("wchar", 0)
    except (OSError, ValueError):
        return None


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def safe_filename(name: str) -> str:
    s = re.sub(r"[^\w\-.]+", "_", name or "", flags=re.UNICODE).strip("._")
    return (s[:48] or "tunnel")


# ---------------------------------------------------------------- 配置读写

def _sanitize_rule(rule: dict) -> dict:
    rp = int(str(rule.get("remote_port", "")).strip() or 0)
    if not (1 <= rp <= 65535):
        raise ValueError(f"远端端口不合法：{rule.get('remote_port')!r}")
    lt = str(rule.get("local_target", "")).strip()
    if not lt:
        lt = "127.0.0.1:7890"
    if not re.match(r"^\S+:\d{1,5}$", lt):
        raise ValueError(f"本机目标格式应为 host:port，例如 127.0.0.1:7890（当前：{lt!r}）")
    lport = int(lt.rsplit(":", 1)[1])
    if not (1 <= lport <= 65535):
        raise ValueError(f"本机目标端口不合法：{lt!r}")
    bind = str(rule.get("bind", "")).strip()
    return {
        "id": str(rule.get("id") or new_id()),
        "bind": bind,
        "remote_port": rp,
        "local_target": lt,
    }


def sanitize_tunnel(data: dict, existing: dict | None = None) -> dict:
    t = dict(existing) if existing else {}
    for key in ("id", "name", "enabled", "auto_reconnect", "mode", "alias", "host", "port",
                "user", "identity", "extra_args", "note", "rules", "hostkey_policy"):
        if key in data:
            t[key] = data[key]

    t["id"] = str(t.get("id") or new_id())
    t["name"] = str(t.get("name") or "").strip() or "未命名隧道"
    t["mode"] = "alias" if str(t.get("mode", "custom")).lower() == "alias" else "custom"
    t["alias"] = str(t.get("alias") or "").strip()
    t["host"] = str(t.get("host") or "").strip()
    try:
        t["port"] = int(t.get("port") or 22)
    except (TypeError, ValueError):
        t["port"] = 22
    if not (1 <= t["port"] <= 65535):
        t["port"] = 22
    t["user"] = str(t.get("user") or "").strip()
    t["identity"] = str(t.get("identity") or "").strip()
    t["extra_args"] = str(t.get("extra_args") or "").strip()
    t["note"] = str(t.get("note") or "").strip()
    t["enabled"] = bool(t.get("enabled", True))
    t["auto_reconnect"] = bool(t.get("auto_reconnect", True))
    policy = str(t.get("hostkey_policy") or "accept-new").strip().lower()
    t["hostkey_policy"] = policy if policy in ("accept-new", "no", "yes") else "accept-new"

    if t["mode"] == "alias":
        if not t["alias"]:
            raise ValueError("请选择或填写 ~/.ssh/config 中的别名")
    else:
        if not t["host"]:
            raise ValueError("请填写服务器地址（主机名或 IP）")

    rules = t.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("至少需要一条转发规则")
    t["rules"] = [_sanitize_rule(r if isinstance(r, dict) else {}) for r in rules]
    return t


def load_config() -> dict:
    data = {"settings": dict(DEFAULT_SETTINGS), "tunnels": []}
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            if isinstance(raw.get("settings"), dict):
                data["settings"].update({k: v for k, v in raw["settings"].items() if k in DEFAULT_SETTINGS})
            for item in raw.get("tunnels", []):
                try:
                    data["tunnels"].append(sanitize_tunnel(item))
                except ValueError as e:
                    print(f"[警告] 跳过损坏的隧道配置: {e}")
            # 去重 ID，避免导入/手改配置造成冲突
            seen: set[str] = set()
            for t in data["tunnels"]:
                if t["id"] in seen:
                    t["id"] = new_id()
                seen.add(t["id"])
        except Exception as e:
            print(f"[警告] 配置文件损坏（{e}），已备份为 config.json.bak 并重新生成")
            try:
                shutil.copy2(CONFIG_FILE, CONFIG_FILE.with_suffix(".json.bak"))
            except OSError:
                pass
    return data


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CONFIG_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, CONFIG_FILE)


# ---------------------------------------------------------------- SSH 命令构建

def _no_window_run_kwargs() -> dict:
    """Windows 下让一次性子进程（如 ssh -G 解析别名）不弹出黑色控制台窗口。"""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {}


def resolve_alias(alias: str) -> dict:
    """通过 `ssh -G 别名` 解析出最终连接参数（不发起真实连接）"""
    try:
        proc = subprocess.run(["ssh", "-G", alias], capture_output=True, text=True, timeout=15,
                              **_no_window_run_kwargs())
    except FileNotFoundError:
        raise RuntimeError("系统中找不到 ssh 命令")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"解析 SSH 别名 “{alias}” 超时")
    if proc.returncode != 0:
        raise RuntimeError(f"无法解析 SSH 别名 “{alias}”")

    vals: dict[str, str] = {}
    identities: list[str] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        key, _, value = line.partition(" ")
        key, value = key.lower(), value.strip()
        if key == "identityfile":
            identities.append(value)
        else:
            vals[key] = value

    hostname = vals.get("hostname", "").strip()
    if not hostname:
        raise RuntimeError(f"SSH 别名 “{alias}” 解析不到服务器地址")
    try:
        port = int(vals.get("port", "22") or 22)
    except ValueError:
        port = 22
    return {
        "hostname": hostname,
        "port": port,
        "user": vals.get("user", ""),
        "identityfile": identities,
        "proxyjump": vals.get("proxyjump", "none"),
        "proxycommand": vals.get("proxycommand", "none"),
        "stricthostkeychecking": vals.get("stricthostkeychecking", "ask"),
        "userknownhostsfile": vals.get("userknownhostsfile", ""),
    }


def build_ssh_command(tunnel: dict, extra_args: list[str] | None = None,
                      for_probe: bool = False, probe_ports: list[int] | None = None) -> list[str]:
    """构建 ssh 命令行。for_probe=True 时不建立转发，而是执行远端探测脚本。"""
    mode = tunnel.get("mode", "custom")
    args = ["ssh"]

    if mode == "alias":
        info = resolve_alias(tunnel["alias"])
        args += ["-F", str(NO_SSH_CONFIG), "-p", str(info["port"])]
        target = (info["user"] + "@" + info["hostname"]) if info["user"] else info["hostname"]
        for ident in info["identityfile"]:
            p = Path(os.path.expanduser(ident))
            if p.exists():
                args += ["-i", str(p)]
        if info["proxyjump"] and info["proxyjump"] != "none":
            args += ["-o", f"ProxyJump={info['proxyjump']}"]
        if info["proxycommand"] and info["proxycommand"] != "none":
            args += ["-o", f"ProxyCommand={info['proxycommand']}"]
        shk = (info["stricthostkeychecking"] or "").strip().lower()
        if shk in ("false", "no", "off"):
            args += ["-o", "StrictHostKeyChecking=no"]
        elif shk in ("true", "yes", "on"):
            args += ["-o", "StrictHostKeyChecking=yes"]
        elif shk and shk != "ask":
            args += ["-o", f"StrictHostKeyChecking={shk}"]
        uhf = info["userknownhostsfile"].strip()
        if uhf and uhf.lower() != "none":
            parts = [str(Path(os.path.expanduser(p))) for p in uhf.split()]
            args += ["-o", "UserKnownHostsFile=" + " ".join(parts)]
    else:
        host = tunnel["host"]
        user = tunnel.get("user", "")
        target = f"{user}@{host}" if user else host
        args += ["-F", str(NO_SSH_CONFIG), "-p", str(tunnel.get("port") or 22)]
        ident = tunnel.get("identity", "")
        if ident:
            ip = Path(os.path.expanduser(ident))
            if not ip.exists():
                raise RuntimeError(f"私钥文件不存在：{ip}")
            args += ["-i", str(ip)]
        policy = str(tunnel.get("hostkey_policy") or "accept-new").lower()
        if policy not in ("accept-new", "no", "yes"):
            policy = "accept-new"
        # 使用工具自己的 known_hosts，避免与你全局 ~/.ssh/known_hosts 里的其它记录互相干扰
        args += ["-o", f"StrictHostKeyChecking={policy}",
                 "-o", f"UserKnownHostsFile={DATA_DIR / 'known_hosts'}"]

    # 公共选项（探测模式用更短的连接超时）
    for key, value in SSH_BASE_OPTS_COMMON:
        if for_probe and key == "ConnectTimeout":
            value = "8"
        args += ["-o", f"{key}={value}"]

    for chunk in (extra_args or []):
        args += chunk

    if not for_probe:
        specs = []
        for rule in tunnel.get("rules") or []:
            rp = int(rule["remote_port"])
            lt = rule["local_target"]
            bind = (rule.get("bind") or "").strip()
            specs.append(f"{bind}:{rp}:{lt}" if bind else f"{rp}:{lt}")
        if not specs:
            raise RuntimeError("没有可用的转发规则")
        for spec in specs:
            args += ["-R", spec]
        args += ["-N"]

    args += [target]

    if for_probe:
        ports = " ".join(str(p) for p in (probe_ports or []))
        script = "echo __OK__"
        if ports:
            script += (
                f"; for p in {ports}; do "
                "if (ss -ltn 2>/dev/null || netstat -tln 2>/dev/null) | grep -q \":$p \"; "
                "then echo \"__PORT_BUSY__ $p\"; else echo \"__PORT_FREE__ $p\"; fi; done"
            )
        args += [script]
    return args


def probe_tunnel(tunnel: dict, extra_args: list[str]) -> dict:
    """测试连接：返回 {ok, auth_ok, ports: {port: 'free'|'busy'}, error, output}"""
    ports = [int(r["remote_port"]) for r in tunnel.get("rules") or []]
    try:
        cmd = build_ssh_command(tunnel, extra_args=extra_args, for_probe=True, probe_ports=ports)
    except RuntimeError as e:
        return {"ok": False, "error": str(e), "output": ""}

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45,
                              **_no_window_run_kwargs())
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "测试超时（45 秒）", "output": ""}

    output = (proc.stdout or "") + (proc.stderr or "")
    result = {"ok": False, "auth_ok": False, "ports": {}, "error": "", "output": output.strip()}

    for line in output.splitlines():
        s = line.strip()
        if s == "__OK__":
            result["auth_ok"] = True
        elif s.startswith("__PORT_BUSY__"):
            result["ports"][s.split()[-1]] = "busy"
        elif s.startswith("__PORT_FREE__"):
            result["ports"][s.split()[-1]] = "free"

    if result["auth_ok"]:
        result["ok"] = True
        return result

    # 没拿到 __OK__，从输出里找原因
    reason = "连接失败（无详细信息）"
    for line in output.splitlines():
        hit = analyze_ssh_line(line)
        if hit:
            reason = hit[0]
            break
    result["error"] = reason
    return result


# ---------------------------------------------------------------- 隧道运行时

STATE_LABELS = {
    "stopped": "已停止",
    "starting": "连接中",
    "running": "运行中",
    "retry": "重连中",
    "error": "错误",
}


class TunnelRuntime:
    """单条隧道（一台服务器）的后台进程管理"""

    START_GRACE = 3.0  # 进程存活超过该秒数即视为连接成功

    def __init__(self, tunnel: dict, manager: "Manager"):
        self.tunnel = tunnel
        self.manager = manager
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.proc: subprocess.Popen | None = None
        self.state = "stopped"
        self.detail = ""
        self.last_error = ""
        self.warning = ""
        self.retries = 0
        self.run_since: float | None = None
        self.log_lines: collections.deque = collections.deque(maxlen=2000)
        self.log_total = 0
        self.log_path = LOG_DIR / f"{safe_filename(tunnel.get('name', ''))}-{tunnel['id'][:8]}.log"
        self.traffic = 0           # 累计总流量（上下行合计，含历次重连）
        self.rate = 0.0            # 最近一次采样的总速率（字节/秒）
        self.traffic_history: collections.deque = collections.deque(maxlen=320)  # 每 ~2 秒一个采样点 (时间, 字节)
        self._io_last: tuple[int, int] | None = None
        self._io_time = 0.0
        # 本机目标端口（代理）健康状态
        self.target_ok: bool | None = None
        self.target_info = ""
        # 持久化流量（跨重启，按天存档 + 总计）
        today = datetime.now().strftime("%Y-%m-%d")
        stored = (manager.traffic_store.get(tunnel["id"]) or {}) if manager else {}
        days = stored.get("days") if isinstance(stored.get("days"), dict) else {}
        self.persist_days: dict[str, int] = {str(k): int(v or 0) for k, v in days.items()}
        self.persist_date = today
        self.persist_today = int(self.persist_days.get(today, 0))
        self.persist_total = int(stored.get("total") or 0)
        self._persist_dirty = False
        self._last_notify = 0.0

    # ---- 状态与日志 ----

    def _set(self, **kw):
        with self.lock:
            for k, v in kw.items():
                setattr(self, k, v)

    def _log(self, line: str):
        stamp_short = datetime.now().strftime("%H:%M:%S")
        stamp_full = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.lock:
            self.log_lines.append(f"[{stamp_short}] {line}")
            self.log_total += 1
            try:
                with open(self.log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{stamp_full}] {line}\n")
            except OSError:
                pass

    def _analyze(self, line: str):
        hit = analyze_ssh_line(line)
        if not hit:
            return
        msg, fatal = hit
        if fatal:
            self._set(last_error=msg, detail=msg)
            if "已被占用" in msg:
                self._notify_throttled(f"远端端口被占用：{self.tunnel['name']}", msg, min_interval=3600)
        else:
            self._set(warning=msg)
            with self.lock:
                if self.state == "running":
                    self.detail = msg

    def _notify_throttled(self, title: str, body: str, min_interval: float = 10.0) -> None:
        now = time.time()
        with self.lock:
            if now - self._last_notify < min_interval:
                return
            self._last_notify = now
        self.manager.notify(title, body)

    def get_lines_since(self, since: int) -> tuple[list[str], int]:
        with self.lock:
            base = self.log_total - len(self.log_lines)
            since = max(since, base)
            lines = list(self.log_lines)[since - base:]
            return lines, self.log_total

    # ---- 流量统计 ----

    def _add_persist_locked(self, delta: int) -> None:
        """按天累计持久化流量（需持有 self.lock）"""
        today = datetime.now().strftime("%Y-%m-%d")
        if self.persist_date != today:
            self.persist_date = today
            self.persist_today = 0
        self.persist_today += delta
        self.persist_total += delta
        self.persist_days[today] = self.persist_today
        self._persist_dirty = True

    def _sample_traffic(self, proc) -> None:
        now = time.time()
        io = read_process_io(proc.pid)
        if io is None:
            self._io_last = None
            self._io_time = now
            return
        if self._io_last is not None:
            dt = max(0.5, now - self._io_time)
            drx = max(0, io[0] - self._io_last[0])
            dtx = max(0, io[1] - self._io_last[1])
            # ssh 是转发进程：每个字节都会被“读一次、写一次”，
            # 因此 (rchar + wchar) / 2 ≈ 该隧道的双向总流量
            delta = (drx + dtx) // 2
            with self.lock:
                self.traffic += delta
                self.rate = delta / dt
                self.traffic_history.append((round(now, 1), delta))
                self._add_persist_locked(delta)
        self._io_last = io
        self._io_time = now

    def reset_traffic(self) -> None:
        with self.lock:
            self.traffic = 0
            self.rate = 0.0
            self.traffic_history.clear()
            today = datetime.now().strftime("%Y-%m-%d")
            self.persist_date = today
            self.persist_today = 0
            self.persist_total = 0
            self.persist_days = {today: 0}
            self._persist_dirty = True

    # ---- 进程控制 ----

    def _terminate_proc(self):
        proc = self.proc
        if not proc:
            return
        if proc.poll() is None:
            if os.name == "nt":
                try:
                    proc.terminate()
                except OSError:
                    pass
            else:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                except (ProcessLookupError, PermissionError, OSError):
                    try:
                        proc.terminate()
                    except OSError:
                        pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    try:
                        proc.kill()
                    except OSError:
                        pass
                else:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except (ProcessLookupError, PermissionError, OSError):
                        try:
                            proc.kill()
                        except OSError:
                            pass
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
        try:
            if proc.stdout:
                proc.stdout.close()
        except OSError:
            pass
        self.proc = None

    def start(self) -> str:
        with self.lock:
            if self.thread and self.thread.is_alive():
                return "该隧道已在运行或重连中"
            self.stop_event = threading.Event()
            self.last_error = ""
            self.warning = ""
            self.retries = 0
            self.thread = threading.Thread(target=self._worker, name=f"tunnel-{self.tunnel['id']}", daemon=True)
            self.thread.start()
            return ""

    def stop(self) -> str:
        with self.lock:
            thread = self.thread
            self.stop_event.set()
        if self.proc:
            self._terminate_proc()
        if thread and thread.is_alive():
            thread.join(timeout=7)
        with self.lock:
            self.thread = None
            if self.state in ("starting", "running", "retry"):
                self.state = "stopped"
                self.detail = ""
            self.run_since = None
        return ""

    def restart(self) -> str:
        self.stop()
        return self.start()

    def is_active(self) -> bool:
        with self.lock:
            return self.state in ("starting", "running", "retry")

    # ---- 工作线程 ----

    def _worker(self):
        while not self.stop_event.is_set():
            self._set(state="starting", detail="正在建立 SSH 连接…", run_since=None)
            self._log(f"===== 启动隧道 “{self.tunnel['name']}” =====")
            try:
                cmd = build_ssh_command(self.tunnel, extra_args=self.manager.extra_ssh_args())
            except RuntimeError as e:
                self._set(state="error", detail=str(e))
                self._log(f"[错误] {e}")
                return
            self._log("$ " + shlex.join(cmd))
            popen_kwargs = {
                "stdin": subprocess.DEVNULL,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "bufsize": 1,
            }
            if os.name == "nt":
                # 独立进程组 + 不弹黑色控制台窗口（打包成无控制台程序时很重要）
                popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs["start_new_session"] = True
            try:
                proc = subprocess.Popen(cmd, **popen_kwargs)
            except FileNotFoundError:
                msg = ("系统中找不到 ssh 命令（Windows：请在「设置 → 应用 → 可选功能」中安装 OpenSSH 客户端；"
                       "Linux：安装 openssh-client）")
                self._set(state="error", detail=msg)
                self._log(f"[错误] {msg}")
                return
            except OSError as e:
                self._set(state="error", detail=f"无法启动 ssh：{e}")
                self._log(f"[错误] 无法启动 ssh：{e}")
                return

            self.proc = proc
            line_q: queue.Queue = queue.Queue()

            def _reader(p=proc, q=line_q):
                try:
                    for ln in p.stdout:  # type: ignore[union-attr]
                        q.put(ln)
                except (OSError, ValueError):
                    pass

            threading.Thread(target=_reader, daemon=True).start()

            t0 = time.time()
            announced = False
            while True:
                if self.stop_event.is_set():
                    break
                try:
                    line = line_q.get(timeout=0.25)
                except queue.Empty:
                    if proc.poll() is not None:
                        break
                    if not announced and time.time() - t0 >= self.START_GRACE:
                        announced = True
                        was_retries = self.retries
                        self._set(state="running", detail=self.warning, run_since=time.time(), retries=0)
                        self._io_last = read_process_io(proc.pid)
                        self._io_time = time.time()
                        self._log("===== 隧道已建立 =====")
                        if was_retries >= 2:
                            self._notify_throttled(f"隧道已重连：{self.tunnel['name']}",
                                                   f"经 {was_retries} 次重试后恢复连接", min_interval=5)
                    if announced and time.time() - self._io_time >= 2.0:
                        self._sample_traffic(proc)
                    continue
                line = line.rstrip("\r\n")
                if line:
                    self._log(line)
                    self._analyze(line)

            code = proc.poll()
            self._terminate_proc()
            self._set(rate=0.0)

            # 排空剩余输出，抓到最后的报错
            time.sleep(0.15)
            while True:
                try:
                    line = line_q.get_nowait().rstrip("\r\n")
                except queue.Empty:
                    break
                if line:
                    self._log(line)
                    self._analyze(line)

            if self.stop_event.is_set():
                self._log("===== 隧道已停止 =====")
                self._set(state="stopped", detail="", run_since=None)
                return

            self.retries += 1
            self._log(f"===== 隧道断开（ssh 退出码 {code}）=====")

            if not self.tunnel.get("auto_reconnect", True):
                self._set(state="error", detail=self.last_error or f"连接断开（退出码 {code}）", run_since=None)
                self._log("未启用自动重连，不再重试")
                self._notify_throttled(f"隧道断开：{self.tunnel['name']}",
                                       self.last_error or f"连接断开（退出码 {code}）")
                return

            reason = self.last_error or f"连接断开（退出码 {code}）"
            with self.lock:
                uptime = (time.time() - self.run_since) if self.run_since else 0.0
            if uptime >= 60:  # 只对稳定运行后的断线发通知，避免服务器抖动刷屏
                self._notify_throttled(f"隧道断开：{self.tunnel['name']}", reason, min_interval=30)

            # 智能重连：指数退避（基准 ×2，封顶 60 秒）；网络恢复后立即重连
            base = max(1, int(self.manager.retry_seconds()))
            delay = min(60, base * (2 ** min(self.retries - 1, 3)))
            self._set(state="retry",
                      detail=f"{reason}，{delay} 秒后重试（已重试 {self.retries} 次）…",
                      run_since=None)
            self._wait_retry_or_network(delay)

        self._set(state="stopped", detail="", run_since=None)

    def _ssh_endpoint(self) -> tuple[str, int] | None:
        """解析该隧道对应的 SSH 服务器地址（用于网络恢复探测）"""
        try:
            if self.tunnel.get("mode") == "alias":
                info = resolve_alias(self.tunnel["alias"])
                return info["hostname"], int(info["port"])
            return self.tunnel["host"], int(self.tunnel.get("port") or 22)
        except Exception:
            return None

    def _wait_retry_or_network(self, delay: float) -> None:
        """等待重试间隔；每 2 秒探测一次 SSH 端口，网络/服务器一恢复就立即重连"""
        end = time.time() + delay
        endpoint = self._ssh_endpoint()
        next_probe = time.time() + 2.0
        while not self.stop_event.is_set():
            now = time.time()
            if now >= end:
                break
            if endpoint and now >= next_probe:
                next_probe = now + 2.0
                host, port = endpoint
                try:
                    with socket.create_connection((host, port), timeout=1.5):
                        pass
                    self._log("===== 网络已恢复，立即重连 =====")
                    break
                except OSError:
                    pass
            self.stop_event.wait(0.25)

    # ---- 快照 ----

    def snapshot(self) -> dict:
        with self.lock:
            t = self.tunnel
            return {
                "id": t["id"],
                "name": t.get("name", ""),
                "enabled": bool(t.get("enabled", True)),
                "auto_reconnect": bool(t.get("auto_reconnect", True)),
                "mode": t.get("mode", "custom"),
                "alias": t.get("alias", ""),
                "host": t.get("host", ""),
                "port": t.get("port", 22),
                "user": t.get("user", ""),
                "identity": t.get("identity", ""),
                "extra_args": t.get("extra_args", ""),
                "note": t.get("note", ""),
                "hostkey_policy": t.get("hostkey_policy", "accept-new"),
                "rules": json.loads(json.dumps(t.get("rules", []))),
                "state": self.state,
                "detail": self.detail,
                "last_error": self.last_error,
                "warning": self.warning,
                "retries": self.retries,
                "uptime": int(time.time() - self.run_since) if (self.run_since and self.state == "running") else 0,
                "traffic": self.traffic,
                "rate": round(self.rate, 1),
                "traffic_today": self.persist_today,
                "traffic_total": self.persist_total,
                "target_ok": self.target_ok,
                "target_info": self.target_info,
                "history": list(self.traffic_history),
                "pid": self.proc.pid if self.proc else None,
                "log_file": str(self.log_path),
            }


# ---------------------------------------------------------------- 管理器

class Manager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if not NO_SSH_CONFIG.exists():
                NO_SSH_CONFIG.write_text(
                    "# 该文件故意留空：隧道命令用 -F 指向它，从而忽略用户 ~/.ssh/config\n",
                    encoding="utf-8",
                )
        except OSError:
            pass
        self.lock = threading.RLock()
        self.config = load_config()
        self.traffic_store = load_traffic_store()
        self.runtimes: dict[str, TunnelRuntime] = {}
        for t in self.config["tunnels"]:
            self.runtimes[t["id"]] = TunnelRuntime(t, self)
        save_config(self.config)
        # Windows：旧版 .cmd 自启会闪黑窗，启动时自动迁移为无窗口的 .vbs
        if os.name == "nt":
            try:
                legacy = _windows_legacy_startup_file()
                if legacy and legacy.exists():
                    set_autostart(True)
            except Exception:
                pass
        self.notifier = None          # 桌面层可覆盖（Windows 托盘通知等）
        self.update_info: dict | None = None
        threading.Thread(target=self._background_loop, daemon=True).start()
        if self.config["settings"].get("update_check", True):
            threading.Thread(target=self._refresh_update_info, daemon=True).start()

    # ---- 通知 / 后台巡检 / 流量持久化 ----

    def notify(self, title: str, body: str) -> None:
        if not self.config["settings"].get("notify", True):
            return
        fn = self.notifier or default_notify
        try:
            fn(title, body)
        except Exception:
            pass

    def set_notifier(self, fn) -> None:
        """桌面层注入通知实现（如 Windows 托盘气泡）"""
        self.notifier = fn

    def _refresh_update_info(self) -> None:
        try:
            self.update_info = check_update(force=False)
        except Exception:
            self.update_info = None

    def _background_loop(self) -> None:
        """每 5 秒：本机目标端口健康检查；每 30 秒：流量落盘"""
        last_flush = 0.0
        while True:
            time.sleep(5)
            try:
                if self.config["settings"].get("proxy_check", True):
                    self._check_targets()
                if time.time() - last_flush >= 30:
                    self.flush_traffic()
                    last_flush = time.time()
            except Exception:
                pass

    def _check_targets(self) -> None:
        for rt in list(self.runtimes.values()):
            if rt.state != "running":
                with rt.lock:
                    rt.target_ok = None
                continue
            ok = True
            info = ""
            seen = set()
            for rule in rt.tunnel.get("rules") or []:
                target = str(rule.get("local_target") or "").strip()
                if not target or target in seen:
                    continue
                seen.add(target)
                host, _, port = target.rpartition(":")
                host = host.strip("[]") or "127.0.0.1"
                try:
                    port_i = int(port)
                except ValueError:
                    continue
                info = f"{host}:{port_i}"
                try:
                    with socket.create_connection((host, port_i), timeout=1.0):
                        pass
                except OSError:
                    ok = False
                    break
            with rt.lock:
                was = rt.target_ok
                rt.target_ok = ok if seen else None
                rt.target_info = info
                if was is False and rt.target_ok is True:
                    rt.detail = "" if (rt.detail and "没有服务" in rt.detail) else rt.detail
            if was is False and rt.target_ok is True:
                rt._log(f"===== 本机代理已恢复（{info}）=====")

    def flush_traffic(self) -> None:
        store: dict = {}
        any_dirty = False
        for tid, rt in list(self.runtimes.items()):
            with rt.lock:
                if rt._persist_dirty:
                    rt._persist_dirty = False
                    any_dirty = True
                days = dict(sorted(rt.persist_days.items())[-30:])
                store[tid] = {"total": rt.persist_total, "days": days}
        if any_dirty:
            self.traffic_store = store
            save_traffic_store(store)

    # ---- 辅助 ----

    def extra_ssh_args(self) -> list[str]:
        raw = str(self.config["settings"].get("extra_ssh_args", "")).strip()
        return shlex.split(raw) if raw else []

    def retry_seconds(self) -> int:
        try:
            return int(self.config["settings"].get("retry_seconds", 5))
        except (TypeError, ValueError):
            return 5

    def _find(self, tid: str) -> TunnelRuntime:
        rt = self.runtimes.get(tid)
        if not rt:
            raise KeyError(tid)
        return rt

    # ---- 查询 ----

    def state(self) -> dict:
        with self.lock:
            return {
                "version": VERSION,
                "settings": dict(self.config["settings"]),
                "tunnels": [rt.snapshot() for rt in self.runtimes.values()],
                "update": self.update_info,
            }

    def logs(self, tid: str, since: int) -> dict:
        rt = self._find(tid)
        lines, total = rt.get_lines_since(since)
        return {"lines": lines, "total": total}

    # ---- 增删改 ----

    def create(self, data: dict) -> dict:
        t = sanitize_tunnel(data)
        with self.lock:
            if t["id"] in self.runtimes:
                t["id"] = new_id()
            self.config["tunnels"].append(t)
            self.runtimes[t["id"]] = TunnelRuntime(t, self)
            save_config(self.config)
        return self.runtimes[t["id"]].snapshot()

    def update(self, tid: str, data: dict) -> dict:
        with self.lock:
            rt = self._find(tid)
            t = sanitize_tunnel(data, existing=rt.tunnel)
            t["id"] = tid  # ID 不可改
            idx = self.config["tunnels"].index(rt.tunnel)
            self.config["tunnels"][idx] = t
            rt.tunnel = t
            save_config(self.config)
            return rt.snapshot()

    def delete(self, tid: str) -> None:
        with self.lock:
            rt = self._find(tid)
            rt.stop()
            self.config["tunnels"].remove(rt.tunnel)
            del self.runtimes[tid]
            save_config(self.config)
        self.flush_traffic()

    def duplicate(self, tid: str) -> dict:
        with self.lock:
            rt = self._find(tid)
            copy = json.loads(json.dumps(rt.tunnel))
            copy["id"] = new_id()
            copy["name"] = copy["name"] + " 副本"
            copy["enabled"] = False
            for r in copy.get("rules", []):
                r["id"] = new_id()
            t = sanitize_tunnel(copy)
            idx = self.config["tunnels"].index(rt.tunnel)
            self.config["tunnels"].insert(idx + 1, t)
            self.runtimes[t["id"]] = TunnelRuntime(t, self)
            save_config(self.config)
            return self.runtimes[t["id"]].snapshot()

    # ---- 启停 ----

    def start(self, tid: str) -> dict:
        rt = self._find(tid)
        err = rt.start()
        if err:
            raise RuntimeError(err)
        return rt.snapshot()

    def stop(self, tid: str) -> dict:
        rt = self._find(tid)
        rt.stop()
        return rt.snapshot()

    def reset_traffic(self, tid: str) -> None:
        self._find(tid).reset_traffic()

    def restart(self, tid: str) -> dict:
        rt = self._find(tid)
        err = rt.restart()
        if err:
            raise RuntimeError(err)
        return rt.snapshot()

    def start_all(self) -> None:
        with self.lock:
            for rt in list(self.runtimes.values()):
                rt.start()

    def stop_all(self) -> None:
        with self.lock:
            for rt in list(self.runtimes.values()):
                rt.stop()
        self.flush_traffic()

    def start_enabled(self) -> None:
        with self.lock:
            for rt in list(self.runtimes.values()):
                if rt.tunnel.get("enabled", True):
                    rt.start()

    # ---- 设置与工具 ----

    def update_settings(self, data: dict) -> dict:
        with self.lock:
            for key in DEFAULT_SETTINGS:
                if key not in data:
                    continue
                if key == "retry_seconds":
                    self.config["settings"][key] = max(1, min(3600, int(data[key])))
                elif key == "auto_start":
                    self.config["settings"][key] = bool(data[key])
                elif key == "extra_ssh_args":
                    self.config["settings"][key] = str(data[key]).strip()
                elif key == "ui_port":
                    self.config["settings"][key] = max(1, min(65535, int(data[key])))
                elif key in ("notify", "update_check", "proxy_check"):
                    self.config["settings"][key] = bool(data[key])
                elif key == "theme":
                    v = str(data[key])
                    self.config["settings"][key] = v if v in ("auto", "dark", "light") else "auto"
                elif key == "language":
                    v = str(data[key])
                    self.config["settings"][key] = v if v in ("auto", "zh", "en") else "auto"
            save_config(self.config)
            return dict(self.config["settings"])

    def test(self, data: dict) -> dict:
        t = sanitize_tunnel(data)
        return probe_tunnel(t, self.extra_ssh_args())

    def export_config(self) -> str:
        with self.lock:
            return json.dumps(self.config, ensure_ascii=False, indent=2)

    def import_config(self, raw: str) -> None:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败：{e}")
        tunnels = data.get("tunnels")
        if not isinstance(tunnels, list):
            raise ValueError("配置文件中缺少 tunnels 列表")
        new = {"settings": dict(DEFAULT_SETTINGS), "tunnels": []}
        if isinstance(data.get("settings"), dict):
            new["settings"].update({k: v for k, v in data["settings"].items() if k in DEFAULT_SETTINGS})
        for item in tunnels:
            try:
                t = sanitize_tunnel(item)
            except ValueError as e:
                raise ValueError(f"隧道配置不合法：{e}")
            new["tunnels"].append(t)
        # 去重 ID
        seen: set[str] = set()
        for t in new["tunnels"]:
            if t["id"] in seen:
                t["id"] = new_id()
            seen.add(t["id"])
        with self.lock:
            self.stop_all()
            self.config = new
            self.runtimes = {t["id"]: TunnelRuntime(t, self) for t in new["tunnels"]}
            save_config(self.config)


def ssh_host_aliases() -> list[str]:
    cfg = Path.home() / ".ssh" / "config"
    aliases: list[str] = []
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*Host\s+(.+?)\s*(?:#.*)?$", line, re.IGNORECASE)
            if not m:
                continue
            for token in m.group(1).split():
                if any(ch in token for ch in "*?!") or token in aliases:
                    continue
                aliases.append(token)
    return aliases


def _linux_autostart_file() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "autostart" / "reverse-tunnel-manager.desktop"


def _windows_startup_file() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    # 用 VBScript 无窗口方式启动，避免登录时闪黑色控制台窗口
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "ReverseTunnelManager.vbs"


def _windows_legacy_startup_file() -> Path | None:
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "ReverseTunnelManager.cmd"


def autostart_file() -> Path | None:
    return _windows_startup_file() if os.name == "nt" else _linux_autostart_file()


def autostart_enabled() -> bool:
    f = autostart_file()
    if f and f.exists():
        return True
    if os.name == "nt":
        legacy = _windows_legacy_startup_file()
        return bool(legacy and legacy.exists())
    return False


def _windows_autostart_content() -> str:
    """生成无窗口启动的 VBScript（避免登录时闪黑色控制台窗口）"""
    if getattr(sys, "frozen", False):
        runline = f'"""{Path(sys.executable)}"" --background"'
    else:
        pyw = Path(sys.executable).with_name("pythonw.exe")
        runner = pyw if pyw.exists() else Path(sys.executable)
        runline = f'"""{runner}"" ""{APP_DIR / "desktop.py"}"" --background"'
    return 'Set ws = CreateObject("WScript.Shell")\r\n' + f'ws.Run {runline}, 0, False\r\n'


def set_autostart(enabled: bool) -> bool:
    f = autostart_file()
    if not f:
        return False
    if enabled:
        f.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            f.write_text(_windows_autostart_content(), encoding="utf-8")
            # 清理旧版 .cmd 自启文件（会闪窗）
            legacy = _windows_legacy_startup_file()
            if legacy:
                try:
                    legacy.unlink()
                except FileNotFoundError:
                    pass
        else:
            desktop_py = APP_DIR / "desktop.py"
            app_py = APP_DIR / "app.py"
            target, extra = (desktop_py, "--background") if desktop_py.exists() else (app_py, "--no-browser")
            f.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=反向隧道管理器\n"
                "Comment=多服务器 SSH 反向隧道管理（后台运行）\n"
                f"Exec=/usr/bin/env python3 {shlex.quote(str(target))} {extra}\n"
                f"Icon={ICON_FILE}\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n",
                encoding="utf-8",
            )
    else:
        candidates = [f]
        if os.name == "nt":
            legacy = _windows_legacy_startup_file()
            if legacy:
                candidates.append(legacy)
        for path in candidates:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
    return autostart_enabled()


# ---------------------------------------------------------------- 通知 / 流量持久化 / 更新检查

TRAFFIC_FILE = DATA_DIR / "traffic.json"
UPDATE_CACHE_FILE = DATA_DIR / "update_check.json"
UPDATE_API = "https://api.github.com/repos/wuxinxin27/reverse-tunnel-manager/releases/latest"


def default_notify(title: str, body: str) -> None:
    """默认系统通知（Linux: notify-send；macOS: osascript；Windows 由桌面层接管）"""
    try:
        if os.name == "nt":
            return
        if sys.platform == "darwin":
            script = (f'display notification {json.dumps(body, ensure_ascii=False)} '
                      f'with title {json.dumps(title, ensure_ascii=False)}')
            subprocess.Popen(["osascript", "-e", script],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        subprocess.Popen(["notify-send", "-a", "反向隧道管理器", title, body],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3]) or (0,)
    except Exception:
        return (0,)


def check_update(force: bool = False) -> dict:
    """检查 GitHub 最新 Release；结果缓存 6 小时，网络失败时退回缓存。"""
    now = time.time()
    cached = None
    try:
        if UPDATE_CACHE_FILE.exists():
            cached = json.loads(UPDATE_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        cached = None
    if not force and cached and now - float(cached.get("checked_at") or 0) < 6 * 3600:
        return cached
    try:
        req = urllib.request.Request(UPDATE_API, headers={
            "User-Agent": "reverse-tunnel-manager",
            "Accept": "application/vnd.github+json",
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        latest = str(data.get("tag_name", "")).lstrip("v")
        want_ext = ".exe" if os.name == "nt" else (".dmg" if sys.platform == "darwin" else ".deb")
        asset_url = ""
        for a in data.get("assets", []) or []:
            if str(a.get("name", "")).endswith(want_ext):
                asset_url = a.get("browser_download_url", "")
                break
        info = {
            "checked_at": now,
            "current": VERSION,
            "latest": latest,
            "has_update": bool(latest) and _version_tuple(latest) > _version_tuple(VERSION),
            "url": data.get("html_url", ""),
            "asset_url": asset_url,
            "error": "",
        }
    except Exception as e:
        if cached:
            cached = dict(cached)
            cached["error"] = f"检查失败：{e}"
            return cached
        return {"checked_at": now, "current": VERSION, "latest": "",
                "has_update": False, "url": "", "asset_url": "", "error": str(e)}
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        UPDATE_CACHE_FILE.write_text(json.dumps(info, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return info


def load_traffic_store() -> dict:
    try:
        if TRAFFIC_FILE.exists():
            data = json.loads(TRAFFIC_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_traffic_store(data: dict) -> None:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = TRAFFIC_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, TRAFFIC_FILE)
    except OSError:
        pass


# ---------------------------------------------------------------- HTTP 服务

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = f"RTM/{VERSION}"
    manager: Manager  # 由 make_handler 注入
    shutdown_cb = None

    def log_message(self, fmt, *args):  # 静音访问日志
        pass

    # ---- 基础工具 ----

    def _send(self, code: int, body: bytes, content_type: str, extra: dict | None = None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _json(self, obj, code: int = 200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _error(self, msg: str, code: int = 400):
        self._json({"error": msg}, code)

    def _read_json(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        return json.loads(raw.decode("utf-8"))

    # ---- 路由 ----

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        try:
            if path == "/" or path == "/index.html":
                return self._serve_static("index.html")
            if path == "/favicon.ico":
                return self._send(204, b"", "image/x-icon")
            if path.startswith("/static/"):
                return self._serve_static(path[len("/static/"):])
            if path == "/api/state":
                return self._json(self.manager.state())
            if path == "/api/ssh_hosts":
                return self._json({"hosts": ssh_host_aliases()})
            if path == "/api/autostart":
                return self._json({"enabled": autostart_enabled()})
            if path == "/api/export":
                data = self.manager.export_config().encode("utf-8")
                return self._send(200, data, "application/json; charset=utf-8",
                                  {"Content-Disposition": 'attachment; filename="reverse-tunnel-config.json"'})
            m = re.fullmatch(r"/api/logs/([0-9a-f]+)", path)
            if m:
                since = 0
                m_since = re.search(r"[?&]since=(\d+)", self.path)
                if m_since:
                    since = int(m_since.group(1))
                return self._json(self.manager.logs(m.group(1), since))
            return self._error("未知路径", 404)
        except KeyError:
            return self._error("隧道不存在", 404)
        except Exception as e:
            return self._error(f"服务器内部错误：{e}", 500)

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        try:
            data = self._read_json()
        except Exception as e:
            return self._error(f"请求体不是合法 JSON：{e}")

        try:
            if path == "/api/tunnels":
                return self._json(self.manager.create(data), 201)
            if path == "/api/start_all":
                self.manager.start_all()
                return self._json({"ok": True})
            if path == "/api/stop_all":
                self.manager.stop_all()
                return self._json({"ok": True})
            if path == "/api/settings":
                return self._json(self.manager.update_settings(data))
            if path == "/api/test":
                return self._json(self.manager.test(data))
            if path == "/api/import":
                self.manager.import_config(str(data.get("config", "")))
                return self._json({"ok": True})
            if path == "/api/autostart":
                return self._json({"enabled": set_autostart(bool(data.get("enabled")))})
            if path == "/api/update_check":
                info = check_update(force=bool(data.get("force", True)))
                self.manager.update_info = info
                return self._json(info)
            if path == "/api/quit":
                self.manager.stop_all()
                if callable(self.shutdown_cb):
                    threading.Timer(0.3, self.shutdown_cb).start()
                return self._json({"ok": True})

            m = re.fullmatch(r"/api/tunnels/([0-9a-f]+)/(start|stop|restart|duplicate|traffic_reset)", path)
            if m:
                tid, action = m.group(1), m.group(2)
                if action == "start":
                    return self._json(self.manager.start(tid))
                if action == "stop":
                    return self._json(self.manager.stop(tid))
                if action == "restart":
                    return self._json(self.manager.restart(tid))
                if action == "duplicate":
                    return self._json(self.manager.duplicate(tid), 201)
                if action == "traffic_reset":
                    self.manager.reset_traffic(tid)
                    return self._json({"ok": True})
            return self._error("未知路径", 404)
        except KeyError:
            return self._error("隧道不存在", 404)
        except ValueError as e:
            return self._error(str(e), 400)
        except RuntimeError as e:
            return self._error(str(e), 409)
        except Exception as e:
            return self._error(f"服务器内部错误：{e}", 500)

    def do_PUT(self):
        m = re.fullmatch(r"/api/tunnels/([0-9a-f]+)", self.path.split("?", 1)[0])
        if not m:
            return self._error("未知路径", 404)
        try:
            data = self._read_json()
        except Exception as e:
            return self._error(f"请求体不是合法 JSON：{e}")
        try:
            return self._json(self.manager.update(m.group(1), data))
        except KeyError:
            return self._error("隧道不存在", 404)
        except ValueError as e:
            return self._error(str(e), 400)
        except Exception as e:
            return self._error(f"服务器内部错误：{e}", 500)

    def do_DELETE(self):
        m = re.fullmatch(r"/api/tunnels/([0-9a-f]+)", self.path.split("?", 1)[0])
        if not m:
            return self._error("未知路径", 404)
        try:
            self.manager.delete(m.group(1))
            return self._json({"ok": True})
        except KeyError:
            return self._error("隧道不存在", 404)
        except Exception as e:
            return self._error(f"服务器内部错误：{e}", 500)

    # ---- 静态文件 ----

    def _serve_static(self, rel: str):
        rel = rel.replace("\\", "/")
        target = (STATIC_DIR / rel).resolve()
        if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
            return self._error("文件不存在", 404)
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
        }.get(target.suffix, "application/octet-stream")
        self._send(200, target.read_bytes(), ctype)


def make_handler(manager: Manager, shutdown_cb):
    class _Handler(Handler):
        pass
    _Handler.manager = manager
    _Handler.shutdown_cb = shutdown_cb
    return _Handler


# ---------------------------------------------------------------- 入口

def main():
    try:  # Windows 控制台 / 重定向时避免中文编码异常
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    parser = argparse.ArgumentParser(description="反向隧道管理器")
    parser.add_argument("--port", type=int, default=None, help="Web 界面端口（默认取配置文件中的 ui_port，初始 8787）")
    parser.add_argument("--no-browser", action="store_true", help="启动时不自动打开浏览器")
    args = parser.parse_args()

    manager = Manager()
    port = args.port or int(manager.config["settings"].get("ui_port", 8787))

    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(manager, None))
    except OSError as e:
        print(f"[错误] 无法监听 127.0.0.1:{port}（{e}）。可能已在运行；如需换端口请修改配置文件。")
        sys.exit(1)

    handler_cls = httpd.RequestHandlerClass
    handler_cls.shutdown_cb = httpd.shutdown
    httpd.daemon_threads = True

    atexit.register(manager.stop_all)
    atexit.register(manager.flush_traffic)

    def _on_signal(signum, frame):
        manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, _on_signal)
    try:
        signal.signal(signal.SIGTERM, _on_signal)
    except (ValueError, AttributeError, OSError):
        pass

    if manager.config["settings"].get("auto_start", True):
        manager.start_enabled()

    url = f"http://127.0.0.1:{port}"
    print(f"反向隧道管理器 v{VERSION} 已启动：{url}")
    print(f"配置文件：{CONFIG_FILE}")
    print(f"日志目录：{LOG_DIR}")
    print("按 Ctrl+C 停止（会同时停止所有隧道）")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever(poll_interval=0.5)
    except SystemExit:
        raise
    finally:
        manager.stop_all()
        httpd.server_close()
        print("已退出")


if __name__ == "__main__":
    main()
