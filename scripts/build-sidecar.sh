#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

TARGET_DIR="src-tauri/resources/backend"

echo "Cleaning previous build output..."
rm -rf "$TARGET_DIR"

echo "Building Python sidecar..."
cd backend
uv run pyinstaller backend.spec --distpath ../src-tauri/resources --noconfirm
cd ..

echo "Sidecar built as: src-tauri/resources/backend"
echo "Renaming for Tauri's triple-target naming..."

TRIPLE=$(rustc -vV | grep 'host:' | awk '{print $2}')
# PyInstaller places the binary at src-tauri/resources/backend (a single file).
# We need to move it into a directory with the triple-target name.
TMPDIR="src-tauri/resources/.jhm-tmp"
mkdir -p "$TMPDIR"

if [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "win"* ]]; then
  DST_NAME="jhm-sidecar-${TRIPLE}.exe"
else
  DST_NAME="jhm-sidecar-${TRIPLE}"
fi

mv "src-tauri/resources/backend" "$TMPDIR/$DST_NAME"
rm -rf "$TARGET_DIR"
mv "$TMPDIR" "$TARGET_DIR"
chmod +x "$TARGET_DIR/$DST_NAME" 2>/dev/null || true
echo "Sidecar ready: $TARGET_DIR/$DST_NAME"
