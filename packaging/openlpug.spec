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

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
repo_root = os.path.abspath(os.getcwd())

# Runtime data that is read from disk (not imported)
datas = []
datas += collect_data_files('openlp', includes=[
    '**/*.html', '**/*.js', '**/*.css', '**/*.png', '**/*.json',
    '**/*.mako', '**/*.ui', '.version',
])

# Plugins are discovered dynamically -> force-include them
hiddenimports = []
hiddenimports += collect_submodules('openlp.plugins')
hiddenimports += collect_submodules('openlp.core')
hiddenimports += ['vlc']

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
