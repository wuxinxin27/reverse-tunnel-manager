# Windows 打包说明

## CI 自动构建

推 `v*` 标签后，[.github/workflows/release.yml](../../.github/workflows/release.yml) 会在
windows-latest 上自动完成：

1. PyInstaller 打包 `dist/ReverseTunnelManager.exe`（单文件、无控制台）
2. Inno Setup 编译出安装包 `dist/ReverseTunnelManager-<版本>-setup.exe`
3. 与 Ubuntu 的 `.deb` 一起附到 GitHub Release 上

## 本地构建

```powershell
pip install pyinstaller pywebview

pyinstaller --noconfirm --clean --onefile --noconsole `
  --name ReverseTunnelManager `
  --icon assets/icon.ico `
  --add-data "static;static" `
  --add-data "assets;assets" `
  --collect-all webview `
  --collect-all clr_loader `
  --hidden-import clr `
  desktop.py
```

然后安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)，在仓库根目录执行：

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DMyAppVersion=1.0.0 packaging\windows\installer.iss
```

产物：

- `dist\ReverseTunnelManager.exe` —— 绿色单文件
- `dist\ReverseTunnelManager-1.0.0-setup.exe` —— 安装包（开始菜单、可选桌面图标、可选开机自启）

## 说明

- 程序依赖系统自带的 `ssh.exe`（Windows 10 1809+ 默认包含 OpenSSH 客户端）。
- 界面为独立的 WebView2 原生窗口（使用系统自带的 Edge 运行时），不是浏览器标签页；
  系统缺少 WebView2 时自动退回 Edge/Chrome 应用窗口，再退回默认浏览器。
- 数据目录：配置在 `%APPDATA%\ReverseTunnelManager\`，日志在 `%LOCALAPPDATA%\ReverseTunnelManager\logs\`。
