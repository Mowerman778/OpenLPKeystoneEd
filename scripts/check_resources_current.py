#!/usr/bin/env python3
# -*- coding: utf-8 -*-

##########################################################################
# OpenLP - Open Source Lyrics Projection                                 #
# ---------------------------------------------------------------------- #
# Copyright (c) 2008-2024 OpenLP Developers                              #
# ---------------------------------------------------------------------- #
# This program is free software: you can redistribute it and/or modify   #
# it under the terms of the GNU General Public License as published by   #
# the Free Software Foundation, either version 3 of the License, or      #
# (at your option) any later version.                                    #
#                                                                        #
# This program is distributed in the hope that it will be useful,        #
# but WITHOUT ANY WARRANTY; without even the implied warranty of         #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the          #
# GNU General Public License for more details.                           #
#                                                                        #
# You should have received a copy of the GNU General Public License      #
# along with this program.  If not, see <https://www.gnu.org/licenses/>. #
##########################################################################
"""
Drift guard for the tracked ``openlp/core/resources.py``.

OpenLPUG tracks the generated ``openlp/core/resources.py`` so a fresh clone / CI / PyInstaller build all
work without needing pyrcc5 + patch on every machine. The risk of tracking a generated file is that it can
drift from its source (``resources/images/openlp-2.qrc`` and the images it references) if someone edits the
source and forgets to regenerate + recommit.

This script regenerates the resources with pyrcc5 and compares the **decompressed resource contents**
(every ``:/`` path and a hash of its bytes) between the tracked file and the fresh one. Comparing contents
rather than the raw file text makes it robust to pyrcc5 version / compression differences and to the
cosmetic header/style normalisation that upstream's generate_resources.sh applies.

Exit codes: 0 = up to date (or pyrcc5 unavailable → skipped, so the check never blocks on a missing dev
tool); 1 = drift detected; 2 = an unexpected error while listing resources.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QRC = ROOT / 'resources' / 'images' / 'openlp-2.qrc'
TRACKED = ROOT / 'openlp' / 'core' / 'resources.py'

# Runs in a clean subprocess: import a resources module by path, register it, and print "<path> <sha256>"
# for every resource file it contains.
LISTER = r'''
import hashlib
import importlib.util
import sys

from PyQt5 import QtCore

spec = importlib.util.spec_from_file_location('_res_under_test', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.qInitResources()

iterator = QtCore.QDirIterator(':', QtCore.QDirIterator.Subdirectories)
while iterator.hasNext():
    path = iterator.next()
    file = QtCore.QFile(path)
    if file.open(QtCore.QIODevice.ReadOnly):
        digest = hashlib.sha256(bytes(file.readAll())).hexdigest()
        file.close()
        print('{0} {1}'.format(path, digest))
'''


def find_pyrcc5():
    """Return the command (as a list) that runs pyrcc5, or None if it is not available."""
    executable = shutil.which('pyrcc5')
    if executable:
        return [executable]
    try:
        import PyQt5.pyrcc_main  # noqa: F401
        return [sys.executable, '-m', 'PyQt5.pyrcc_main']
    except ImportError:
        return None


def resource_listing(module_path):
    """Return the sorted "<path> <sha>" listing of every resource in the given module, as a set."""
    result = subprocess.run([sys.executable, '-c', LISTER, str(module_path)],
                            capture_output=True, text=True, env={'QT_QPA_PLATFORM': 'offscreen'})
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.exit(2)
    return set(line for line in result.stdout.splitlines() if line.strip())


def main():
    pyrcc5 = find_pyrcc5()
    if not pyrcc5:
        print('pyrcc5 not available - skipping resources.py drift check')
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        generated = Path(tmp) / 'resources_generated.py'
        build = subprocess.run(pyrcc5 + ['-o', str(generated), str(QRC)], capture_output=True, text=True)
        if build.returncode != 0:
            # A pyrcc5 failure is a tooling problem, not drift - don't block CI on it.
            sys.stderr.write(build.stderr)
            print('pyrcc5 failed to run - skipping resources.py drift check')
            return 0
        tracked = resource_listing(TRACKED)
        fresh = resource_listing(generated)
    if tracked != fresh:
        only_tracked = sorted(entry.split(' ', 1)[0] for entry in tracked - fresh)
        only_fresh = sorted(entry.split(' ', 1)[0] for entry in fresh - tracked)
        print('ERROR: openlp/core/resources.py is out of date with resources/images/openlp-2.qrc')
        if only_fresh:
            print('  Present in the .qrc but missing/changed in the tracked file:')
            print('\n'.join('    ' + path for path in only_fresh))
        if only_tracked:
            print('  Present in the tracked file but not in a fresh build:')
            print('\n'.join('    ' + path for path in only_tracked))
        print('  Regenerate and commit: pyrcc5 -o openlp/core/resources.py resources/images/openlp-2.qrc')
        return 1
    print('openlp/core/resources.py is up to date with the .qrc ({0} resources)'.format(len(tracked)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
