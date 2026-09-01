# OpenLPUG

**OpenLPUG** is a Windows-focused fork of [OpenLP](https://openlp.org/) 3.1.7 — free church
presentation / lyrics-projection software. The fork's goals:

1. **Stabilize** the application (bug/crash hardening, raised test coverage, reproducible Windows build).
2. **Stay light** on modest hardware (dual-core, 4–8 GB RAM, integrated GPU) — heavier features are
   gated behind settings and hardware detection.
3. **Add selected production-AV features**: CCLI SongSelect import, generalized video-behind-lyrics,
   a stage display with timers/countdowns, and video-in-video (picture-in-picture).

## Licensing

OpenLP is licensed **GPL-3.0-or-later**. OpenLPUG is a derivative work and therefore remains
**GPL-3.0-or-later**. All original OpenLP copyright headers and attribution are preserved. See
[`LICENSE`](LICENSE) and [`copyright.txt`](copyright.txt).

## Development

The upstream release is preserved on the `3.1.7` git tag; fork work happens on `openlpug-main`.

```bash
# Linux dev/test (offscreen Qt)
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install -e ".[test]"          # needs: pkg-config libicu-dev python3-pyqt5.qt{webengine,multimedia,svg}
QT_QPA_PLATFORM=offscreen pytest --disable-warnings -q
```

On **Windows** (Python 3.12 64-bit):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
# PyICU has no PyPI wheel on Windows — install the matching cgohlke prebuilt wheel first:
pip install "https://github.com/cgohlke/pyicu-build/releases/download/v2.16.2/pyicu-2.16.2-cp312-cp312-win_amd64.whl"
pip install -e ".[test,mp4]"
python run_openlp.py
```

Gotchas on Windows (all one-time):
- **Python 3.12, not 3.13** — some deps (PyQt5/PyICU/lxml) lack ready 3.13 wheels; 3.12 is our baseline.
- **No stray `PYTHON*` env vars.** A leftover `PYTHONHOME`/`PYTHONPATH`/`PYTHON`/`PYTHON3`/`PYTHONEXECUTABLE`
  pointing at another install breaks venv isolation (`sys.prefix` won't be the `.venv`). Remove them and
  reopen the shell.
- **PyICU wheel** — as above; the wheel version must match your Python (`cp312`).
- **VLC 64-bit** must be installed for `import vlc` / media playback (`python-vlc` is only the ctypes binding).
- **`openlp/core/resources.py`** is a generated file (from `resources/images/openlp-2.qrc`). The fork
  **tracks** it so a clone/CI/build works out of the box. Only regenerate when icons/the `.qrc` change:
  `pyrcc5 -o openlp/core/resources.py resources/images/openlp-2.qrc` (on Linux, `apt install pyqt5-dev-tools`
  first), then commit it. `flake8` already excludes this file. CI runs
  `scripts/check_resources_current.py`, which **fails the build if the tracked file drifts** from the
  `.qrc`/images (compares decompressed resource contents, so it's robust to pyrcc5 version differences).

CI (lint + Windows/Linux tests) is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
Windows packaging lives in [`packaging/`](packaging/).

## Roadmap

See the phased plan the fork is built against (Phase 0 fork/build → Phase 1 stabilization →
Phase 2 features). NDI / alpha-channel broadcast output is deferred.
