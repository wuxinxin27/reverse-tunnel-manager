#!/usr/bin/env bash
# 构建 Ubuntu/Debian 安装包（.deb）和免安装包（.tar.gz）
#
# 用法:
#   bash packaging/linux/build.sh <版本号> [项目主页 URL]
# 例如:
#   bash packaging/linux/build.sh 1.0.0 https://github.com/OWNER/reverse-tunnel-manager
#
# 产物输出到 dist/ 目录。
set -euo pipefail

VERSION="${1:-0.0.0}"
HOMEPAGE="${2:-}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKG="reverse-tunnel-manager"
DIST="$ROOT/dist"
BUILD="$ROOT/build/linux"

rm -rf "$BUILD"
mkdir -p "$BUILD" "$DIST"

# ---------------------------------------------------------------- .deb

STAGE="$BUILD/deb"
mkdir -p "$STAGE/DEBIAN" \
         "$STAGE/opt/$PKG" \
         "$STAGE/usr/bin" \
         "$STAGE/usr/share/applications" \
         "$STAGE/usr/share/icons/hicolor/scalable/apps" \
         "$STAGE/usr/share/doc/$PKG"

# 程序文件
install -m 644 "$ROOT/app.py" "$ROOT/desktop.py" "$STAGE/opt/$PKG/"
cp -r "$ROOT/static" "$STAGE/opt/$PKG/"
mkdir -p "$STAGE/opt/$PKG/assets"
install -m 644 "$ROOT/assets/icon.svg" "$STAGE/opt/$PKG/assets/"
install -m 644 "$ROOT/README.md" "$STAGE/usr/share/doc/$PKG/"
install -m 644 "$ROOT/LICENSE" "$STAGE/usr/share/doc/$PKG/copyright"

# 启动器
cat > "$STAGE/usr/bin/$PKG" <<'EOF'
#!/bin/sh
exec python3 /opt/reverse-tunnel-manager/desktop.py "$@"
EOF
chmod 755 "$STAGE/usr/bin/$PKG"

# 桌面项与图标
cat > "$STAGE/usr/share/applications/$PKG.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=反向隧道管理器
Name[en]=Reverse Tunnel Manager
Comment=多服务器 SSH 反向隧道可视化管理
Comment[en]=Manage reverse SSH tunnels for multiple servers
Exec=$PKG
Icon=$PKG
Terminal=false
Categories=Network;
StartupNotify=true
EOF
install -m 644 "$ROOT/assets/icon.svg" "$STAGE/usr/share/icons/hicolor/scalable/apps/$PKG.svg"

# DEBIAN 控制信息
cat > "$STAGE/DEBIAN/control" <<EOF
Package: $PKG
Version: $VERSION
Section: net
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), openssh-client | ssh
Recommends: python3-gi, gir1.2-webkit2-4.0 | gir1.2-webkit2-4.1
Maintainer: Ruixin Wu <781785786@qq.com>
${HOMEPAGE:+Homepage: $HOMEPAGE}
Description: 多服务器 SSH 反向隧道管理器
 可视化配置的多服务器 SSH 反向隧道守护工具：把远端端口映射到本机
 （如本机的 Clash 代理 127.0.0.1:7890），支持自动重连、日志与开机自启。
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database -q /usr/share/applications || true
command -v gtk-update-icon-cache  >/dev/null 2>&1 && gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor || true
exit 0
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

dpkg-deb --build --root-owner-group "$STAGE" "$DIST/${PKG}_${VERSION}_all.deb"

# ---------------------------------------------------------------- .tar.gz（免安装）

TARBALL="$BUILD/$PKG-$VERSION"
mkdir -p "$TARBALL"
cp -r "$ROOT/app.py" "$ROOT/desktop.py" "$ROOT/static" "$ROOT/assets" \
      "$ROOT/README.md" "$ROOT/LICENSE" "$TARBALL/"
cat > "$TARBALL/run.sh" <<'EOF'
#!/bin/sh
cd "$(dirname "$0")"
exec python3 desktop.py "$@"
EOF
chmod 755 "$TARBALL/run.sh"
tar -C "$BUILD" -czf "$DIST/${PKG}_${VERSION}.tar.gz" "$PKG-$VERSION"

echo
echo "构建完成："
ls -lh "$DIST"
