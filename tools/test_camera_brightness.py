#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Apply the brightness patch to small, non-proprietary instruction fixtures."""
import math
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / 'patches-6.7/0006-release-temporary-auto-brightness-on-aosp.patch'
NORMAL = '''.method public final b()V
    .locals 5

    const/high16 v2, 0x3f000000    # 0.5f
    invoke-static {v1, v2}, Lgq/a;->a(Landroid/hardware/display/DisplayManager;F)V

    const/4 v0, 0x0

    iput v0, p0, LF1/x2;->g:F

    invoke-static {v1, v0}, Lgq/a;->a(Landroid/hardware/display/DisplayManager;F)V

    return-void
.end method
'''
CLEANUP = '''.method public final uncaughtException(Ljava/lang/Thread;Ljava/lang/Throwable;)V
    .locals 11

    if-ne v1, v5, :cond_4

    const/4 v5, 0x0

    invoke-static {v0, v5}, Lgq/a;->a(Landroid/hardware/display/DisplayManager;F)V
    :try_end_0
    .catch Landroid/provider/Settings$SettingNotFoundException; {:try_start_0 .. :try_end_0} :catch_0
    .catch Ljava/lang/SecurityException; {:try_start_0 .. :try_end_0} :catch_0
.end method
'''


class CameraBrightnessTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='camera-brightness-test-')
        self.addCleanup(self.temporary.cleanup)
        self.stage = Path(self.temporary.name)
        (self.stage / 'smali/F1').mkdir(parents=True)
        self.normal = self.stage / 'smali/F1/x2.smali'
        self.cleanup = self.stage / 'smali/F1/L2.smali'
        self.normal.write_text(NORMAL)
        self.cleanup.write_text(CLEANUP)
        subprocess.run(['git', 'apply', '--check', str(PATCH)], cwd=self.stage,
                       check=True, capture_output=True)
        subprocess.run(['git', 'apply', str(PATCH)], cwd=self.stage,
                       check=True, capture_output=True)

    def test_normal_release_keeps_local_zero_and_active_boost(self):
        patched = self.normal.read_text()
        self.assertIn('const/high16 v2, 0x3f000000    # 0.5f\n'
                      '    invoke-static {v1, v2}', patched)
        self.assertIn('const/4 v0, 0x0\n\n    iput v0, p0, LF1/x2;->g:F', patched)
        self.assertRegex(patched, r'iput v0, p0, LF1/x2;->g:F\s+'
                         r'#[^\n]+\n\s+const/high16 v0, 0x7fc00000[^\n]*\s+'
                         r'invoke-static \{v1, v0\}, Lgq/a;->a\(')

    def test_both_release_values_disable_aosp_temporary_flag(self):
        # AOSP considers every non-NaN value (including neutral zero) temporary.
        self.assertTrue(not math.isnan(0.0))
        for path, register in ((self.normal, 'v0'), (self.cleanup, 'v5')):
            with self.subTest(path=path.name):
                bits = re.search(r'const/high16 ' + register + r', (0x[0-9a-f]+)',
                                 path.read_text()).group(1)
                value = struct.unpack('>f', int(bits, 16).to_bytes(4, 'big'))[0]
                self.assertTrue(math.isnan(value))
        self.assertNotIn('const/4 v5, 0x0', self.cleanup.read_text())
        self.assertIn('if-ne v1, v5, :cond_4', self.cleanup.read_text())

    def test_patch_is_narrow_and_rejects_duplicate_application(self):
        patch = PATCH.read_text()
        self.assertEqual(re.findall(r'^\+\+\+ b/(.+)$', patch, re.M),
                         ['smali/F1/x2.smali', 'smali/F1/L2.smali'])
        removed = [s for s in patch.splitlines() if s.startswith('-') and not s.startswith('---')]
        self.assertEqual(removed, ['-    const/4 v5, 0x0'])
        result = subprocess.run(['git', 'apply', '--check', str(PATCH)], cwd=self.stage,
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_extraction_applies_patch_and_preserves_changed_dex(self):
        extractor = (ROOT / 'extract-files.py').read_text()
        self.assertIn(".apktool_patch('patches-6.7')", extractor)
        self.assertLess(extractor.index('.call(select_camera_apk)'),
                        extractor.index(".apktool_patch('patches-6.7')"))
        self.assertIn("('classes.dex', 'classes4.dex', 'classes5.dex')",
                      (ROOT / 'camera_apk_fixup.py').read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
