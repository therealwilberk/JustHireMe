# JustHireMe Linux Migration Documentation

**Target Platform:** Arch Linux with Hyprland (Wayland)  
**Document Version:** 1.0  
**Date:** 2026-05-07  
**Project Status:** Alpha v0.1.7

---

## Overview

This documentation provides a comprehensive guide for migrating JustHireMe from its Windows-centric setup to run on Arch Linux with Hyprland (Wayland compositor). The original codebase is cross-platform by design, but Windows is the primary release target.

### Quick Start

```bash
# Install dependencies
sudo pacman -S base-devel curl file glib2 gtk3 librsvg openssl webkit2gtk-4.1 libxdo pkg-config patchelf wget libappindicator-gtk3

# Clone and setup
git clone https://github.com/vasu-devs/JustHireMe.git
cd JustHireMe
npm install
cd backend && uv sync --dev && cd ..
npm run tauri dev
```

### Migration Difficulty: **MODERATE**

**Why?**
- ✅ Codebase uses proper cross-platform guards (`#[cfg(windows)]`)
- ✅ Tauri 2 officially supports Linux
- ✅ Python backend has proper fallbacks
- ❌ Release tooling is Windows-focused
- ❌ No Linux packaging scripts
- ❌ No Linux documentation (until now!)

---

## Documentation Map

### Core Documents

| File | Description | When to Use |
|------|-------------|--------------|
| [01-executive-summary.md](01-executive-summary.md) | Project overview, compatibility assessment, and migration recommendation | Start here for a high-level understanding |
| [02-current-state-analysis.md](02-current-state-analysis.md) | Detailed analysis of codebase, platform-specific code, and architecture | Review to understand what needs to change |
| [03-arch-hyprland-requirements.md](03-arch-hyprland-requirements.md) | System dependencies, package mappings, and Hyprland-specific config | Use when setting up your Arch system |
| [04-dependency-review.md](04-dependency-review.md) | Version review, conflict analysis, and update recommendations | Check before installing dependencies |
| [05-error-handling-strategy.md](05-error-handling-strategy.md) | Current gaps and recommended improvements for error handling | Reference when debugging issues |
| [06-logging-strategy.md](06-logging-strategy.md) | Logging architecture, key events to log, and implementation recommendations | Use when implementing better logging |
| [07-migration-steps.md](07-migration-steps.md) | Step-by-step migration instructions with verification | Follow this during actual migration |
| [08-known-issues.md](08-known-issues.md) | Common build/runtime issues and their solutions | Consult when encountering problems |
| [09-testing-validation.md](09-testing-validation.md) | Testing procedures, validation checklists, and performance benchmarks | Use to verify successful migration |
| [10-future-work.md](10-future-work.md) | Planned improvements, Linux packaging, and contribution opportunities | Review for next steps after migration |

---

## Reading Path

### For System Administrators / First-Time Setup

1. [01-executive-summary.md](01-executive-summary.md) - Understand the project
2. [03-arch-hyprland-requirements.md](03-arch-hyprland-requirements.md) - Install dependencies
3. [04-dependency-review.md](04-dependency-review.md) - Verify versions
4. [07-migration-steps.md](07-migration-steps.md) - Follow step-by-step
5. [09-testing-validation.md](09-testing-validation.md) - Validate setup

### For Developers / Contributors

1. [02-current-state-analysis.md](02-current-state-analysis.md) - Understand codebase
2. [05-error-handling-strategy.md](05-error-handling-strategy.md) - Improve error handling
3. [06-logging-strategy.md](06-logging-strategy.md) - Enhance logging
4. [10-future-work.md](10-future-work.md) - Find contribution opportunities
5. [08-known-issues.md](08-known-issues.md) - Debug issues

### For Troubleshooting

1. [08-known-issues.md](08-known-issues.md) - Check if your issue is listed
2. [05-error-handling-strategy.md](05-error-handling-strategy.md) - Understand error patterns
3. [06-logging-strategy.md](06-logging-strategy.md) - Enable verbose logging
4. [09-testing-validation.md](09-testing-validation.md) - Run diagnostic tests

---

## Recent Updates

### 2026-05-07
- ✅ Updated `CONTRIBUTING.md` with Node 24+ requirement and Linux-specific instructions
- ✅ Updated `docs/ARCHITECTURE.md` to match actual codebase (fixed outdated module references)
- ✅ Added Linux paths to architecture documentation (`~/.local/share/JustHireMe/`)
- ✅ Verified all linux-migration modules are complete and accurate

### Known Code Issues
- ⚠️ **`backend/agents/generator.py:536`** - Contains placeholder data: `"Github: github.com/handle Mobile: +91-XXXXXXXXXX"` - appears to be test data that should be removed

---

## Quick Reference

### System Dependencies (Arch)

```bash
sudo pacman -S base-devel curl file glib2 gtk3 librsvg openssl \
  webkit2gtk-4.1 libxdo pkg-config patchelf wget \
  libappindicator-gtk3
```

### Key Commands

| Task | Command |
|------|---------|
| Install frontend deps | `npm install` |
| Install backend deps | `cd backend && uv sync --dev` |
| Test backend | `cd backend && uv run python main.py` |
| Run dev mode | `npm run tauri dev` |
| Build (no bundle) | `npm run package:fast` |
| Check Tauri | `npm run tauri info` |
| Run tests | `cd backend && uv run python -m pytest tests/ -v` |

### Log Locations

| Log | Path |
|-----|------|
| Tauri/Rust | `~/.local/share/JustHireMe/logs/tauri.log` (future) |
| Backend/Python | `~/.local/share/JustHireMe/logs/backend.log` (future) |
| Data directory | `~/.local/share/JustHireMe/` |

### Config Files

| Config | Location |
|--------|----------|
| Tauri config | `src-tauri/tauri.conf.json` |
| Frontend config | `vite.config.ts`, `tsconfig.json` |
| Backend config | `backend/pyproject.toml` |
| Hyprland config | `~/.config/hypr/hyprland.conf` |

---

## File Details

### [01-executive-summary.md](01-executive-summary.md)

**Purpose:** High-level overview and migration recommendation

**Contents:**
- Project overview (tech stack, version)
- Platform compatibility assessment table
- Migration difficulty rating with reasoning
- Recommendations (proceed vs reconsider)
- Key migration statistics
- Next steps with links to detailed docs

**Key Takeaway:** JustHireMe is cross-platform by design but Windows-focused. Migration is feasible but requires effort.

---

### [02-current-state-analysis.md](02-current-state-analysis.md)

**Purpose:** Deep dive into codebase architecture and platform-specific code

**Contents:**
- Complete repository structure
- Platform-specific code locations with line numbers
- Rust/Tauri layer analysis (`lib.rs`)
- Python backend analysis (`main.py`)
- Build configuration review (`tauri.conf.json`)
- Package scripts analysis (`package.json`)
- CI/CD analysis (`.github/workflows/`)
- Code quality observations
- File statistics

**Key Takeaway:** Platform-specific code is properly guarded with `#[cfg]` attributes. Main work is adding Linux packaging.

---

### [03-arch-hyprland-requirements.md](03-arch-hyprland-requirements.md)

**Purpose:** System setup guide for Arch Linux with Hyprland

**Contents:**
- Package mapping: Ubuntu CI → Arch Linux
- Installation commands for system dependencies
- Hyprland/Wayland considerations
- Tauri on Wayland (XWayland vs native)
- Known Hyprland issues and solutions
- Hyprland configuration examples
- Rust/Tauri installation on Arch
- Python 3.13 installation
- Node.js 24+ installation
- Verification script

**Key Takeaway:** Use the provided `pacman` command to install all dependencies. Configure Hyprland with the provided config snippets.

---

### [04-dependency-review.md](04-dependency-review.md)

**Purpose:** Ensure all dependencies are up-to-date and compatible

**Contents:**
- Frontend dependencies (`package.json`) review
- Backend dependencies (`pyproject.toml`) review
- Rust dependencies (`Cargo.toml`) review
- Dependency conflict analysis (PyTorch, Playwright, KuzuDB, etc.)
- Version pinning recommendations
- Virtual environment setup
- Lock file verification

**Key Takeaway:** All current dependencies are up-to-date. Watch for PyTorch GPU vs CPU and Playwright browser deps.

---

### [05-error-handling-strategy.md](05-error-handling-strategy.md)

**Purpose:** Identify error handling gaps and provide solutions

**Contents:**
- Tauri sidecar management issues (spawn, port discovery, timeouts)
- Python backend gaps (global exceptions, startup validation)
- Error handling checklist
- Error recovery strategies table
- Logging errors to file (implementation examples)

**Key Takeaway:** Add timeouts for port/token discovery, implement retry logic, and validate dependencies on startup.

---

### [06-logging-strategy.md](06-logging-strategy.md)

**Purpose:** Design comprehensive logging architecture

**Contents:**
- Current logging implementation (Rust + Python)
- Enhancement recommendations (structured logging, file output)
- Logging architecture diagram
- Log levels for debugging
- Key events to log (with code examples)
- Log rotation strategies
- Viewing and searching logs

**Key Takeaway:** Implement logging to both file and stderr, include timestamps, use structured format for machine parsing.

---

### [07-migration-steps.md](07-migration-steps.md)

**Purpose:** Step-by-step migration instructions

**Contents:**
- Pre-migration checklist
- 8 detailed steps with expected output and error solutions
  - Step 1: Clone and install frontend
  - Step 2: Install backend dependencies
  - Step 3: Verify Tauri setup
  - Step 4: Test backend independently
  - Step 5: Test frontend + backend
  - Step 6: Test full Tauri app
  - Step 7: Build for production
  - Step 8: Build Linux package (future)
- Post-migration verification checklist
- Common issues and solutions
- Quick reference table

**Key Takeaway:** Follow steps in order. Test backend independently before running Tauri. Check logs if something fails.

---

### [08-known-issues.md](08-known-issues.md)

**Purpose:** Troubleshooting guide for common problems

**Contents:**
- Build issues (webkit2gtk, libappindicator, Rust compilation)
- Runtime issues (sidecar won't start, WebSocket failures, DB permissions, ML models)
- Hyprland-specific issues (blank window, scaling, system tray)
- Future Linux packaging issues
- Debugging tips (verbose logging, process status, independent testing)

**Key Takeaway:** Consult this document when encountering issues. Each problem has a clear solution or workaround.

---

### [09-testing-validation.md](09-testing-validation.md)

**Purpose:** Validate successful migration

**Contents:**
- Manual testing checklist (backend, frontend, Tauri)
- Integration testing (full app test, functional testing)
- Performance testing (startup time, ML model loading, memory usage)
- Database testing (files, integrity)
- Network testing (API endpoints, WebSocket)
- Automated testing (future)
- Validation checklist (build, functionality, performance, logs)

**Key Takeaway:** Complete the validation checklist to confirm successful migration. All tests should pass.

---

### [10-future-work.md](10-future-work.md)

**Purpose:** Roadmap for improving Linux support

**Contents:**
- Linux packaging (Tauri config, package scripts, .desktop file)
- GitHub Actions for Linux releases
- Wayland native support (testing, GTK4 migration)
- Documentation (linux-release.md, README updates, video walkthrough)
- Code improvements (error messages, logging, timeouts, retry logic, health checks, graceful shutdown)
- Community & contribution (testing guide, CI matrix, SUPPORT_LINUX.md)

**Key Takeaway:** Many improvements are low-effort/high-impact. Consider contributing back to upstream.

---

## Original Monolithic Document

The original monolithic document `MIGRATION_GUIDE.md` is still present in this directory for reference. Once you've confirmed all information has been properly migrated to the modular files, you may choose to:

- Keep it as a fallback/archive
- Delete it to avoid duplication
- Convert it to a PDF for offline reading

**Note:** The modular files are now the canonical documentation. Any updates should be made to the relevant module file, not the monolith.

---

## Documentation References

- **Visual Architecture:** [ARCHITECTURE.html](../ARCHITECTURE.html) - Interactive diagram (canonical reference)
- **Markdown Architecture:** [ARCHITECTURE.md](../ARCHITECTURE.md) - Updated 2026-05-07 to match codebase
- **Windows Docs:** [windows-release.md](../windows-release.md) - Windows-specific release process
- **Contributing:** [CONTRIBUTING.md](../CONTRIBUTING.md) - Updated 2026-05-07 with Linux/Node 24+ info

## Contributing

If you find issues with this documentation or want to improve it:

1. Edit the relevant module file
2. Update this `index.md` if needed
3. Submit PR to the JustHireMe repository

**Suggestions for improvement:**
- Add more diagrams/flowcharts
- Include screenshots for Hyprland setup
- Create video walkthrough
- Add more distribution-specific guides (Ubuntu, Fedora, etc.)

---

## Quick Links

- **Project Repository:** https://github.com/vasu-devs/JustHireMe
- **Tauri Documentation:** https://tauri.app/
- **Arch Wiki:** https://wiki.archlinux.org/
- **Hyprland Wiki:** https://wiki.hyprland.org/
- **Python Documentation:** https://docs.python.org/3.13/
- **Node.js Documentation:** https://nodejs.org/docs/

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-05-07 | Initial modular documentation created from monolithic guide |

---

**End of Index**
