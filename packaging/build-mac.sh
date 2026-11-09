#!/bin/bash
# Build the macOS app bundle and DMG for LUMIX Photo Manager.
# Usage: bash packaging/build-mac.sh   (macOS, Apple Silicon, Python 3.12)
set -euo pipefail
cd "$(dirname "$0")/.."

VERSION=$(sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml)
PY=${PYTHON:-$(command -v python3.12 || true)}
[ -n "$PY" ] || { echo "需要 Python 3.12，可用 PYTHON=/path/to/python3.12 指定" >&2; exit 1; }

[ -d .venv-mac ] || "$PY" -m venv .venv-mac
.venv-mac/bin/python -m pip install -q --upgrade pip
.venv-mac/bin/python -m pip install -q -r packaging/requirements-mac.txt

if [ ! -f models/face_detection_yunet_2023mar.onnx ] || [ ! -f models/face_recognition_sface_2021dec.onnx ]; then
  .venv-mac/bin/python packaging/fetch_models.py
fi
.venv-mac/bin/python packaging/make_icns.py

rm -rf build-mac dist-mac
.venv-mac/bin/python -m PyInstaller --noconfirm --clean \
  --distpath dist-mac --workpath build-mac packaging/pianji-mac.spec

APP="dist-mac/LUMIX Photo Manager.app"
# Localized display name so Finder shows 「LUMIX 洗衣机管理器」while the bundle
# keeps an ASCII filename. Must run before signing: resources are sealed.
mkdir -p "$APP/Contents/Resources/zh_CN.lproj"
printf 'CFBundleName = "洗衣机管理器";\nCFBundleDisplayName = "LUMIX 洗衣机管理器";\n' \
  > "$APP/Contents/Resources/zh_CN.lproj/InfoPlist.strings"
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/dmg-readme.txt "$STAGE/首次打开说明.txt"
DMG="dist-mac/LUMIX-Photo-Manager-${VERSION}-arm64.dmg"
hdiutil create -volname "LUMIX 洗衣机管理器" -srcfolder "$STAGE" \
  -ov -fs HFS+ -format UDZO -imagekey zlib-level=9 "$DMG" >/dev/null

cd dist-mac && shasum -a 256 "$(basename "$DMG")" | tee SHA256SUMS.txt
echo "完成：$(pwd)/$(basename "$DMG")"
