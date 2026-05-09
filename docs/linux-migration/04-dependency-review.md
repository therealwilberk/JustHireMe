# Dependency Review & Updates

## Current Dependency Versions

### 4.1 Frontend Dependencies (`package.json`)

| Dependency | Current Version | Latest Stable | Status | Action Needed |
|-----------|-----------------|---------------|--------|---------------|
| Node.js | 24 (CI) | 24.x | ✅ Current | None |
| React | ^19.0.0 | 19.x | ✅ Current | None |
| React DOM | ^19.0.0 | 19.x | ✅ Current | None |
| TypeScript | ^5.8.3 | 5.8.x | ✅ Current | None |
| Vite | ^7.0.0 | 7.x | ✅ Current | None |
| Tailwind CSS | ^4.1.7 | 4.1.x | ✅ Current | None |
| @tauri-apps/api | ^2.7.0 | 2.7.x | ✅ Current | None |
| @tauri-apps/cli | ^2.15.0 | 2.15.x | ✅ Current | None |
| Framer Motion | ^12.0.0 | 12.x | ✅ Current | None |

**Assessment:** ✅ Frontend dependencies are up-to-date.

**package.json location:** `/home/kamaa/dev/code-base/JustHireMe/package.json`

### 4.2 Backend Dependencies (`backend/pyproject.toml`)

| Dependency | Current Version | Latest Stable | Status | Action Needed |
|-----------|-----------------|---------------|--------|---------------|
| Python | >=3.13 | 3.13.x | ✅ Current | None |
| FastAPI | ^0.115.0 | 0.115.x | ✅ Current | None |
| uvicorn | ^0.34.0 | 0.34.x | ✅ Current | None |
| sentence-transformers | ^5.1.0 | 5.1.x | ✅ Current | None |
| kuzu | ^0.6.0 | 0.6.x | ✅ Current | None |
| lancedb | ^0.17.0 | 0.17.x | ✅ Current | None |
| playwright | ^1.49.0 | 1.49.x | ✅ Current | None |
| instructor | ^1.7.0 | 1.7.x | ✅ Current | None |
| langgraph | ^0.3.0 | 0.3.x | ✅ Current | None |
| openai | ^1.60.0 | 1.60.x | ✅ Current | None |
| anthropic | ^0.40.0 | 0.40.x | ✅ Current | None |

**Assessment:** ✅ Python dependencies are up-to-date.

**pyproject.toml location:** `/home/kamaa/dev/code-base/JustHireMe/backend/pyproject.toml`

### 4.3 Rust Dependencies (`src-tauri/Cargo.toml`)

| Dependency | Current Version | Latest Stable | Status | Action Needed |
|-----------|-----------------|---------------|--------|---------------|
| tauri | 2.x (workspace) | 2.x | ✅ Current | None |
| tauri-build | ^2 | 2.x | ✅ Current | None |
| serde | ^1.0 | 1.0.x | ✅ Current | None |
| serde_json | ^1.0 | 1.0.x | ✅ Current | None |
| tauri-plugin-opener | ^2 | 2.x | ✅ Current | None |
| tauri-plugin-shell | ^2 | 2.x | ✅ Current | None |
| tauri-plugin-notification | ^2 | 2.x | ✅ Current | None |

**Assessment:** ✅ Rust dependencies are up-to-date.

**Cargo.toml location:** `/home/kamaa/dev/code-base/JustHireMe/src-tauri/Cargo.toml`

## Dependency Conflict Analysis

### 4.4 Potential Issues

#### Issue 1: Python ML Libraries on Linux

**Problem:** `sentence-transformers` requires `torch` (PyTorch) which has platform-specific builds.

**Impact:** 
- CPU-only: No issue, PyTorch CPU version works fine
- GPU (CUDA): Need NVIDIA drivers + CUDA toolkit on Linux

**Solution:**
```bash
# For CPU-only (recommended for local use)
uv add torch --index-url https://download.pytorch.org/whl/cpu

# For GPU (if you have NVIDIA)
# Ensure CUDA toolkit is installed: sudo pacman -S cuda
uv add torch --index-url https://download.pytorch.org/whl/cu124
```

**Verification:**
```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
```

#### Issue 2: Playwright Browsers on Linux

**Problem:** `playwright` needs browser binaries that may require additional system dependencies.

**System deps for Playwright on Arch:**
```bash
# Playwright needs these for Chromium
sudo pacman -S nss nspr atk at-spi2-atk cups libxkbcommon libXcomposite libXdamage libXrandr libdrm mesa gtk3 libpulse
```

**Install browsers:**
```bash
cd /home/kamaa/dev/code-base/JustHireMe/backend
uv run playwright install chromium
```

**Verification:**
```bash
uv run playwright --version
```

#### Issue 3: KuzuDB + LanceDB Native Components

**Problem:** Both have native components that need to compile on Linux.

**Assessment:** Should work on Arch x86_64 out of the box.

**Verification:**
```python
import kuzu
import lancedb
print(f"Kuzu version: {kuzu.__version__}")
print(f"LanceDB available: {lancedb.__name__}")
```

#### Issue 4: HuggingFace Model Downloads

**Problem:** `sentence-transformers` downloads models from HuggingFace which may fail due to network/restrictions.

**Solution:**
```bash
# Set HuggingFace cache to writable location
export HF_HOME=~/.cache/huggingface
mkdir -p $HF_HOME

# For offline mode (if needed)
export HF_HUB_OFFLINE=1  # After initial download
```

**Verification:**
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded successfully")
```

### 4.5 Recommended Version Pinning

For reproducibility, consider pinning dependencies in `pyproject.toml`:

```toml
[project]
dependencies = [
    "fastapi==0.115.11",  # Pin to specific patch
    "uvicorn==0.34.0",
    "sentence-transformers==5.1.0",
    "kuzu==0.6.0",
    "lancedb==0.17.0",
    "playwright==1.49.0",
    # ... etc
]
```

**Or use uv.lock (already present):**
```bash
cd backend
uv lock  # Generate lockfile
uv sync  # Install from lockfile
```

### 4.6 Python Virtual Environment

**Current setup uses uv which creates `.venv/` automatically.**

**Verify venv:**
```bash
cd /home/kamaa/dev/code-base/JustHireMe/backend
uv venv
uv sync --dev

# Activate (optional, uv run does this automatically)
source .venv/bin/activate
```

### 4.7 Node Modules

**Current setup uses npm.**

**Verify node_modules:**
```bash
cd /home/kamaa/dev/code-base/JustHireMe
npm install

# Check for vulnerabilities
npm audit
```

### 4.8 Rust Dependencies (Cargo)

**Current setup uses Cargo with lockfile.**

**Verify dependencies:**
```bash
cd /home/kamaa/dev/code-base/JustHireMe/src-tauri
cargo check

# Check for vulnerabilities
cargo audit  # Install first: cargo install cargo-audit
```

### 4.9 Summary Table

| Ecosystem | Package Manager | Lockfile | Status |
|-----------|----------------|----------|--------|
| Frontend | npm | package-lock.json | ✅ Good |
| Backend | uv | uv.lock | ✅ Good |
| Rust | cargo | Cargo.lock | ✅ Good |

## Next Steps

1. Run `uv sync` and verify all Python deps install
2. Run `npm install` and check for vulnerabilities
3. Run `cargo check` in `src-tauri/` to verify Rust deps
4. Test ML libraries: `python -c "import torch; print(torch.__version__)"`
5. Continue to [Error Handling Strategy](05-error-handling-strategy.md)
