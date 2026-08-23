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

On **Windows**:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[test,mp4]"      # VLC (64-bit) must be installed for python-vlc
python run_openlp.py
```

CI (lint + Windows/Linux tests) is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml).
Windows packaging lives in [`packaging/`](packaging/).

## Roadmap

See the phased plan the fork is built against (Phase 0 fork/build → Phase 1 stabilization →
Phase 2 features). NDI / alpha-channel broadcast output is deferred.
