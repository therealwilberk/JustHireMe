# Linux Release Checklist

## Prerequisites

- Arch Linux (or Debian/Ubuntu for deb builds)
- Rust toolchain, Node.js 20+, Python 3.13+
- System deps: `webkit2gtk-4.1`, `gtk3`, `libayatana-appindicator`, etc.
- Sidecar built: `scripts/build-sidecar.sh`

## Build

```bash
npm install
cd backend
uv sync --dev
cd ..
./scripts/build-sidecar.sh
```

### Individual formats

```bash
# AppImage (portable, single-file)
npm run package:appimage

# Debian/Ubuntu package
npm run package:deb
```

### Both formats

```bash
npm run package:linux:all
```

### Fast local smoke test (no bundle)

```bash
npm run package:fast
./src-tauri/target/release/justhireme
```

## Artifacts

| Format | Path | Use case |
|--------|------|----------|
| AppImage | `src-tauri/target/release/bundle/appimage/JustHireMe_<version>_x86_64.AppImage` | Portable — run anywhere with FUSE |
| deb | `src-tauri/target/release/bundle/deb/justhireme_<version>_amd64.deb` | Debian/Ubuntu install |

## Smoke Test

- Launch AppImage: `chmod +x ./JustHireMe*.AppImage && ./JustHireMe*.AppImage`
- Install deb: `sudo dpkg -i justhireme_*.deb && justhireme`
- Verify app appears in system launcher (after deb install)
- Verify backend starts and WebSocket connects
- Run a scan cycle

## Verification

```bash
# Check deb dependencies
dpkg -I src-tauri/target/release/bundle/deb/justhireme_*.deb | grep Depends

# Validate desktop file (if installed)
desktop-file-validate /usr/share/applications/justhireme.desktop

# Generate checksums
cd src-tauri/target/release/bundle
sha256sum appimage/*.AppImage deb/*.deb > SHA256SUMS.txt
```

## Notes

- AppImage requires FUSE2 or FUSE3 at runtime
- deb package registers the app in the system launcher automatically
- The `package:linux` script (AppImage-only) is maintained for backward compatibility — use `package:linux:all` for both formats
- CI release builds are not yet automated (see Phase 4)
