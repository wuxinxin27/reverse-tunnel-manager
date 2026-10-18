#!/usr/bin/env python3
"""Windows 诊断实验：进程 I/O 计数（GetProcessIoCounters）是否包含套接字流量。

背景：v1.1.5 在 Windows 上流量统计恒 0。现有实现 app.read_process_io 使用
GetProcessIoCounters 的 ReadTransferCount/WriteTransferCount。
本实验起一个子进程向本地回环发送 ~10MB，取传输前后的计数差分：
- delta_write ≈ 10MB → 含套接字流量（问题在读取实现/权限）
- delta_write ≈ 0    → 不含套接字流量（需要换计数机制）
同时对照“显式 argtypes/restype 的规范写法”，排除句柄截断类隐患。
"""
import ctypes
import os
import socket
import subprocess
import sys
import time

if os.name != "nt":
    print("SKIP: 本实验只针对 Windows")
    sys.exit(0)

sys.path.insert(0, ".")
import app  # noqa: E402  仓库中的现有实现

CHILD = r"""
import socket
s = socket.create_connection(("127.0.0.1", 18973), timeout=15)
s.recv(1)  # 等待“go”
blk = b"x" * 65536
for _ in range(160):
    s.sendall(blk)
s.shutdown(socket.SHUT_WR)
try:
    s.recv(4096)
except Exception:
    pass
"""


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [("ReadOperationCount", ctypes.c_ulonglong),
                ("WriteOperationCount", ctypes.c_ulonglong),
                ("OtherOperationCount", ctypes.c_ulonglong),
                ("ReadTransferCount", ctypes.c_ulonglong),
                ("WriteTransferCount", ctypes.c_ulonglong),
                ("OtherTransferCount", ctypes.c_ulonglong)]


def io_fixed(pid):
    """显式 argtypes/restype 的规范写法（排除句柄截断等隐患）。"""
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.GetProcessIoCounters.argtypes = [ctypes.c_void_p, ctypes.POINTER(IO_COUNTERS)]
    k32.GetProcessIoCounters.restype = ctypes.c_int
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    h = k32.OpenProcess(0x1000, 0, pid)
    if not h:
        return None
    try:
        c = IO_COUNTERS()
        if not k32.GetProcessIoCounters(h, ctypes.byref(c)):
            return None
        return (int(c.ReadTransferCount), int(c.WriteTransferCount))
    finally:
        k32.CloseHandle(h)


def main():
    server = socket.socket()
    server.bind(("127.0.0.1", 18973))
    server.listen(1)
    p = subprocess.Popen([sys.executable, "-c", CHILD])
    conn, _ = server.accept()
    conn.settimeout(20)
    time.sleep(0.3)
    base = app.read_process_io(p.pid)
    base2 = io_fixed(p.pid)
    conn.sendall(b"g")
    total = 0
    while True:
        b = conn.recv(262144)
        if not b:
            break
        total += len(b)
    conn.close()
    p.wait(timeout=20)
    fin = app.read_process_io(p.pid)
    fin2 = io_fixed(p.pid)
    print("loopback 收到:", total)
    print("app 实现      : base =", base, " final =", fin)
    print("显式 argtypes : base =", base2, " final =", fin2)

    def verdict(tag, a, b):
        if not a or not b:
            print(f"VERDICT[{tag}]: 读取失败（None）")
            return
        dw = b[1] - a[1]
        dr = b[0] - a[0]
        ok = "OK 含套接字" if dw >= total * 0.8 else "NOT-INCLUDED 不含套接字"
        print(f"VERDICT[{tag}]: delta_read={dr} delta_write={dw} -> {ok}")

    verdict("app", base, fin)
    verdict("fixed", base2, fin2)


if __name__ == "__main__":
    main()
