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

## Still to verify on Windows (cannot be done on the Linux dev box)

- `python run_openlp.py` launches and shows a slide on a second display.
- PyInstaller build (`packaging/openlpug.spec`) + Inno Setup installer (`packaging/openlpug.iss`)
  produce a working `OpenLPUG.exe`.
- python-vlc media playback against an installed 64-bit VLC.
