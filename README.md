# 反向隧道管理器 (Reverse Tunnel Manager)

> 把本机端口（例如 Clash 代理 `127.0.0.1:7890`）**反向穿透**给任意多台远程服务器使用：
> 可视化配置、断线自动重连、独立于终端 / IDE 的 SSH 会话。
> Ubuntu 22.04+ 与 Windows 10/11 开箱即用，零第三方依赖。

[![Release](https://img.shields.io/github/v/release/wuxinxin27/reverse-tunnel-manager?label=release)](https://github.com/wuxinxin27/reverse-tunnel-manager/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Ubuntu%2022.04%2B%20%7C%20Windows%2010%2B-blue)](#下载安装)

[![主界面](https://cdn.statically.io/gh/wuxinxin27/reverse-tunnel-manager/main/docs/screenshot.png)](https://github.com/wuxinxin27/reverse-tunnel-manager/tree/main/docs)

[![可视化配置](https://cdn.statically.io/gh/wuxinxin27/reverse-tunnel-manager/main/docs/screenshot-editor.png)](https://github.com/wuxinxin27/reverse-tunnel-manager/tree/main/docs)

## 特性

- 🖥 **可视化配置**：独立原生窗口（Linux GTK/WebKit2、Windows WebView2），增删改查、启停隧道、查看实时日志
- 📌 **最小化到状态栏**：关闭窗口自动隐藏到系统托盘（Ubuntu 顶栏 / Windows 任务栏），隧道继续在后台运行；托盘菜单可显示界面 / 全部启停 / 退出
- 📊 **流量统计**：每条隧道实时上下行速率 + 累计流量（跨重连保持），可一键清零
- 🔁 **断线自动重连**：每条隧道独立进程守护，重连间隔可调
- 🧩 **多服务器 × 多端口**：同一本机端口（如 7890）可同时反向穿透给任意多台服务器
- 🔒 **独立于 SSH 通道**：与 VS Code / 终端里的 SSH 会话互不影响，关掉 IDE 隧道照常工作
- 🧪 **连接测试**：内置测试功能，检查认证、网络以及远端端口是否被占用
- 🪄 **聪明的小细节**：粘贴平台给的 `ssh` 命令自动解析；支持 `~/.ssh/config` 别名（自动忽略别名自带的 RemoteForward，避免重复绑定）
- 📄 日志落盘、配置导入导出、开机自启（可选）
- 📦 **核心零第三方依赖**：Python 标准库 + 系统 `ssh`；提供 .deb / Windows 安装包（Windows 原生窗口基于系统 WebView2）

## 下载安装

### Ubuntu 22.04+ / Debian

从 [Releases](https://github.com/wuxinxin27/reverse-tunnel-manager/releases) 下载 `.deb` 安装包：

```bash
sudo apt install ./reverse-tunnel-manager_1.0.0_all.deb
```

然后在应用菜单里打开「反向隧道管理器」。（也提供免安装的 `.tar.gz`）

### Windows 10/11

从 [Releases](https://github.com/wuxinxin27/reverse-tunnel-manager/releases) 下载
`ReverseTunnelManager-1.0.0-setup.exe` 双击安装，可选桌面图标与开机自启。
界面是独立原生窗口（使用系统自带的 WebView2/Edge 运行时）；若系统缺少 WebView2（极少见），会自动退化为 Edge/Chrome 应用窗口。

> 需要 `ssh.exe`：Windows 10 1809+ 默认包含；如缺失，在「设置 → 应用 → 可选功能」安装 OpenSSH 客户端。

### 源码运行

```bash
git clone https://github.com/wuxinxin27/reverse-tunnel-manager
cd reverse-tunnel-manager

python3 desktop.py        # 打开窗口（Linux 原生窗口；Windows Edge/Chrome 应用窗口）
python3 app.py            # 纯服务模式：自动打开浏览器 http://127.0.0.1:8787
```

要求 Python 3.10+；Linux 桌面窗口需要 `python3-gi` 与 WebKit2（Ubuntu 桌面通常已自带），
Windows 源码运行原生窗口需 `pip install pywebview`；以上缺失时会自动退化为浏览器应用窗口，功能不受影响。

## 快速上手

以「让远程服务器通过你本机的 Clash 上外网」为例：

1. 打开软件，点右上角「＋ 新建隧道」
2. 填连接信息：
   - **自定义主机**：把平台给的 `ssh -p 2222 user@1.2.3.4` 粘进「从 SSH 命令解析」，一键填充；
   - 或 **使用别名**：直接选 `~/.ssh/config` 里的主机别名
3. 「转发规则」填 `7890 → 127.0.0.1:7890`（远端 7890 指回本机 Clash）
4. 点「测试连接」确认认证与端口都 OK，然后保存并「▶ 启动」
5. 到服务器上即可使用：`export https_proxy=http://127.0.0.1:7890`

## 原理与限制

- 每条隧道 = 一个独立的 `ssh -N -R 远端端口:本机目标` 进程；断线由工具自动重连。
- **同一台服务器上同一个远端端口只能被一条连接占用**；同一台服务器多个端口、多台服务器
  共用你本机的同一个 7890，都没有冲突。
- 远端监听默认绑定 `127.0.0.1`（仅服务器本机可用）。若想开放给局域网，需要服务器 sshd
  开启 `GatewayPorts clientspecified`，并在规则中填写「远端绑定地址」（如 `0.0.0.0`）。
- 带宽由本机代理出口共享，多台服务器同时使用没有问题。

## 常见问题

| 现象 | 处理 |
|---|---|
| `远端端口 X 已被占用` | 服务器上已有其他隧道/会话占用；换端口，或先停掉占用者。同一规则不要新旧脚本同时跑 |
| `本机目标 127.0.0.1:7890 没有服务` | 隧道正常，但你本机代理没开；启动 Clash 等代理即可 |
| 认证失败 | 检查用户名/私钥；云平台通常需要先在平台上导入你的公钥 |
| Windows 找不到 ssh | 「设置 → 应用 → 可选功能」安装 OpenSSH 客户端 |
| Windows 界面变成浏览器窗口 | 系统缺少 WebView2/Edge 运行时；安装 Edge 即可恢复原生窗口（功能不受影响） |
| 关闭窗口后程序「不见了」 | Linux 上已最小化到顶栏状态栏（托盘），隧道继续运行；点顶栏图标重新打开，彻底退出用托盘菜单「退出」 |
| 顶栏没有托盘图标 | 缺少 AppIndicator 组件：`sudo apt install gir1.2-ayatanaappindicator3-0.1` 后重启工具 |
| 编辑后不生效 | 运行中的隧道需要点「⟳ 重启」 |
| 端口 8787 被占用 | 在设置里改「Web 界面端口」后重启工具 |

## 项目结构

```
app.py                    后端：隧道进程管理 + 本地 Web 服务（核心，跨平台）
desktop.py                桌面入口：Linux GTK/WebKit2、Windows WebView2 原生窗口，浏览器兜底
static/                   Web 界面（HTML/CSS/JS，零框架）
assets/                   图标（SVG/PNG/ICO）
tools/gen_icons.py        从 icon.svg 生成 png 与 ico
packaging/linux/build.sh  构建 .deb 与 .tar.gz
packaging/windows/        PyInstaller + Inno Setup 打包脚本
.github/workflows/        CI：推 v* 标签自动构建双平台安装包并发布 Release
```

## 开发与发布

```bash
# Ubuntu 安装包
bash packaging/linux/build.sh 1.0.0 https://github.com/wuxinxin27/reverse-tunnel-manager

# Windows 安装包：见 packaging/windows/README.md

# 发布：推 tag 后 CI 自动构建并挂到 Release
git tag v1.0.0 && git push origin v1.0.0
```

## 数据位置

| 内容 | Linux | Windows |
|---|---|---|
| 配置 | `~/.config/reverse-tunnel-manager/config.json` | `%APPDATA%\ReverseTunnelManager\config.json` |
| 日志 | `~/.local/share/reverse-tunnel-manager/logs/` | `%LOCALAPPDATA%\ReverseTunnelManager\logs\` |

## License

[MIT](LICENSE)
