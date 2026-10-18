# Windows 打包说明

## CI 自动构建

推 `v*` 标签后，[.github/workflows/release.yml](../../.github/workflows/release.yml) 会在
windows-latest 上自动完成：

1. PyInstaller 打包 `dist/ReverseTunnelManager/`（目录版/onedir，无控制台）
2. Inno Setup 编译出安装包 `dist/ReverseTunnelManager-<版本>-setup.exe`
3. 与 Ubuntu 的 `.deb` 一起附到 GitHub Release 上

> 为什么用目录版而不是单文件：单文件模式每次启动都要把 `python312.dll` 等解压到
> `%TEMP%\_MEIxxxx`，企业电脑上的杀毒软件 / ASR 策略 / 清理工具可能把它删掉或拦截，
> 导致 `Failed to load Python DLL ... 找不到指定的模块` 崩溃。目录版直接从安装目录加载，
> 启动更快也更稳。

## 本地构建

```powershell
pip install pyinstaller pywebview pystray pillow

pyinstaller --noconfirm --clean --onedir --noconsole `
  --name ReverseTunnelManager `
  --icon assets/icon.ico `
  --add-data "static;static" `
  --add-data "assets;assets" `
  --collect-all webview `
  --collect-all clr_loader `
  --hidden-import clr `
  --hidden-import pystray._win32 `
  desktop.py
```

然后安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)，在仓库根目录执行：

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DMyAppVersion=1.1.6 packaging\windows\installer.iss
```

产物：

- `dist\ReverseTunnelManager\` —— 绿色目录版（整个目录一起拷走即可用）
- `dist\ReverseTunnelManager-1.1.6-setup.exe` —— 安装包（开始菜单、可选桌面图标、可选开机自启）

## 说明

- 程序依赖系统自带的 `ssh.exe`（Windows 10 1809+ 默认包含 OpenSSH 客户端）。
- 界面为独立的 WebView2 原生窗口（使用系统自带的 Edge 运行时），不是浏览器标签页；
  系统缺少 WebView2 时自动退回 Edge/Chrome 应用窗口，再退回默认浏览器。
- 关闭窗口自动最小化到系统托盘（任务栏右下角，内置 pystray），隧道继续后台运行。
- 数据目录：配置在 `%APPDATA%\ReverseTunnelManager\`，日志在 `%LOCALAPPDATA%\ReverseTunnelManager\logs\`。
