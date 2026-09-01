# OpenLPUG — Phase 0 baseline

Recorded at fork creation, against the pristine OpenLP 3.1.7 source (git tag `3.1.7`).

## Environment

- **Dev box:** Linux (Ubuntu, kernel 6.17), Python 3.12.3
- **Qt:** system PyQt5 (incl. QtWebEngine, QtMultimedia, QtSvg, QtSerialPort)
- **Install:** `pip install -e ".[test]"` in a `--system-site-packages` venv
- **System build deps required:** `pkg-config`, `libicu-dev` (PyICU builds against ICU 74.2),
  `python3-pyqt5.qt{webengine,multimedia,svg,serialport}`
- VLC not installed on the dev box (only needed for live media playback, not the test suite)

## Test suite baseline

Command: `QT_QPA_PLATFORM=offscreen pytest --disable-warnings -q`

| Metric   | Count |
|----------|-------|
| passed   | 2395  |
| skipped  | 113   |
| xfailed  | 4     |
| failed   | **0** |
| duration | ~33 s |

The suite is **fully green** on Linux/offscreen. This is the regression bar: every fork change must
keep the suite green (`0 failed`), and bug fixes should add regression tests that raise the pass count.

## Known collection gotcha

`tests/openlp_plugins/media/forms/test_streamselectorform.py` imports `PyQt5.QtMultimedia`; without
that submodule installed, pytest **aborts collection for the whole run**. Ensure the Qt multimedia
submodule is present in every environment (handled in CI — see `.github/workflows/ci.yml`).

## Windows setup prerequisites (confirmed on bmserubi, 2026-09-01)

Before `pip install -e ".[test,mp4]"` on Windows:

1. **Python 3.12 (64-bit)** — not 3.13 (missing wheels). Ensure no stray `PYTHON*` env vars
   (`PYTHONHOME`/`PYTHONPATH`/`PYTHON`/`PYTHON3`/`PYTHONEXECUTABLE`) — they break venv isolation.
2. **PyICU** — no PyPI wheel on Windows; install the cgohlke prebuilt first:
   `pip install "https://github.com/cgohlke/pyicu-build/releases/download/v2.16.2/pyicu-2.16.2-cp312-cp312-win_amd64.whl"`
3. **`openlp/core/resources.py`** — generated file, now **tracked in the fork**, so a fresh clone imports
   without running the generator. (Previously untracked → fresh clones died at
   `openlp/core/app.py` `from openlp.core.resources import qInitResources`.)
4. **VLC 64-bit** — required for `import vlc` / media playback.

Verified on bmserubi: `sys.prefix` inside `.venv`, native imports OK (openlp/Qt/sqlalchemy/flask/mako),
headless launch OK. Only `import vlc` outstanding pending the VLC install.

## Still to verify on Windows (cannot be done on the Linux dev box)

- `python run_openlp.py` shows a slide on a second display (projector), with media over VLC.
- PyInstaller build (`packaging/openlpug.spec`) + Inno Setup installer (`packaging/openlpug.iss`)
  produce a working `OpenLPUG.exe`.
