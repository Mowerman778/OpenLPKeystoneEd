# -*- mode: python ; coding: utf-8 -*-
#
# PyInstaller spec for building the OpenLPUG Windows executable.
#
#   pyinstaller packaging/openlpug.spec
#
# Notes:
#  - Run from the repo root on Windows with the project installed in the active venv
#    (`pip install -e ".[mp4]"`) and VLC (64-bit) installed.
#  - Qt WebEngine, Mako templates, the display HTML/JS, and plugin resources must be
#    bundled explicitly because they are loaded at runtime, not imported.
#  - This is the Phase 0 packaging scaffold; refine hiddenimports/datas as the build
#    is exercised on a real Windows runner.

import glob
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
repo_root = os.path.abspath(os.getcwd())
openlp_dir = os.path.join(repo_root, 'openlp')

# Runtime data that is read from disk (not imported). When frozen, OpenLP looks for its files (core/..., plugins/...,
# .version) beside the executable, rather than in an openlp folder, so the openlp/ prefix is dropped.
datas = []
# Every file that is not Python (fonts, Bible book names, display HTML/JS, .version...), so none is missed
for source, destination in collect_data_files('openlp', excludes=['**/__pycache__/**', '**/*.sfd']):
    datas.append((source, os.path.relpath(destination, 'openlp')))
# Plugins and presentation controllers are found by looking for their files on disk, then imported from the bundle
for pattern in ('plugins/*/[!.]*plugin.py', 'plugins/presentations/lib/[!.]*controller.py'):
    for source in glob.glob(os.path.join(openlp_dir, pattern)):
        datas.append((source, os.path.relpath(os.path.dirname(source), openlp_dir)))

# Plugins are discovered dynamically -> force-include them
hiddenimports = []
hiddenimports += collect_submodules('openlp.plugins')
hiddenimports += collect_submodules('openlp.core')
hiddenimports += ['vlc']
# run_openlp.py does `from openlp import __main__`, which PyInstaller does not follow by itself
hiddenimports += ['openlp.__main__']

a = Analysis(
    ['..\\run_openlp.py'],
    pathex=[repo_root],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OpenLPUG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,               # GUI app, no console window
    contents_directory='.',      # files beside the executable, where OpenLP looks for them, not in _internal
    icon='..\\resources\\images\\OpenLP.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='OpenLPUG',
)
