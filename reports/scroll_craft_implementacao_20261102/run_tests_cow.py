"""Run unchanged AppTests with independent APFS copies to limit scratch space."""
import ctypes
import os
from pathlib import Path
import shutil
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
original=shutil.copyfile
clone=ctypes.CDLL('/usr/lib/libSystem.B.dylib',use_errno=True).clonefile
clone.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int]
def copy(src,dst,*,follow_symlinks=True):
    if not os.path.exists(dst) and os.path.isfile(src) and not os.path.islink(src):
        if clone(os.fsencode(src),os.fsencode(dst),0)==0:
            assert os.stat(src).st_ino!=os.stat(dst).st_ino
            return dst
    return original(src,dst,follow_symlinks=follow_symlinks)
shutil.copyfile=copy
suite=unittest.defaultTestLoader.loadTestsFromNames(['tests.test_dashboard_app','tests.test_uiux_method','tests.test_fan_journey','tests.test_i18n'])
result=unittest.TextTestRunner(verbosity=1).run(suite)
sys.exit(not result.wasSuccessful())
