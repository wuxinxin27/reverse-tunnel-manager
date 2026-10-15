; 反向隧道管理器 —— Inno Setup 安装脚本
;
; CI 里的用法（见 .github/workflows/release.yml）：
;   ISCC.exe /DMyAppVersion=1.0.0 packaging\windows\installer.iss
;
; 本地构建：先 PyInstaller 生成 dist\ReverseTunnelManager.exe，再编译本脚本。
; 详见 packaging\windows\README.md

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

#define MyAppName "反向隧道管理器"
#define MyAppPublisher "Ruixin Wu"
#define MyAppExeName "ReverseTunnelManager.exe"

[Setup]
AppId={{7E1B4F0C-9A2D-4C1E-B7A3-2F6D9E8C5A11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\ReverseTunnelManager
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=ReverseTunnelManager-{#MyAppVersion}-setup
SetupIconFile=..\..\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
#if FileExists(AddBackslash(CompilerPath) + "Languages\ChineseSimplified.isl")
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked
Name: "autostart"; Description: "开机自动启动（后台运行）"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "..\..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}（后台）"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--background"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
