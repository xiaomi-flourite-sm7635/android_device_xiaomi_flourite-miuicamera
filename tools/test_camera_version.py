#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Guards for the pinned app upgrade; no proprietary APK required."""
import os
import io
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import camera_apk_source as source
from camera_apk_fixup import processing_dex_name, preserve_base_payload


class CameraVersionTest(unittest.TestCase):
    def test_only_target_dex_can_change(self):
        def apk(changed=False, bad_asset=False):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w') as output:
                for i in range(1, 12):
                    name = 'classes.dex' if i == 1 else f'classes{i}.dex'
                    output.writestr(name, b'assembled' if changed else b'base')
                output.writestr('assets/config', b'bad' if bad_asset else b'keep')
            buffer.seek(0)
            return zipfile.ZipFile(buffer)
        result = io.BytesIO()
        with apk() as base, apk(changed=True) as assembled, zipfile.ZipFile(result, 'w') as output:
            preserve_base_payload(base, assembled, output)
        with zipfile.ZipFile(result) as result:
            for name in result.namelist():
                expected = b'assembled' if name in ('classes.dex', 'classes4.dex', 'classes5.dex') else b'base'
                if name.startswith('assets/'):
                    expected = b'keep'
                self.assertEqual(result.read(name), expected)
        with apk() as base, apk(bad_asset=True) as assembled, zipfile.ZipFile(io.BytesIO(), 'w') as output:
            with self.assertRaisesRegex(ValueError, 'non-code change'):
                preserve_base_payload(base, assembled, output)

    def test_dex_appended_without_replacing_base_code(self):
        names = ['classes.dex'] + [f'classes{i}.dex' for i in range(2, 12)]
        self.assertEqual(processing_dex_name(names + ['assets/foo']), 'classes12.dex')
        for invalid in (names[:-1], names + ['classes12.dex'], names + ['classes5.dex'],
                        names + ['classes0.dex']):
            with self.assertRaises(ValueError):
                processing_dex_name(invalid)

    def test_missing_base_fails_before_copy(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(source.shutil, 'copyfile') as copy:
            with self.assertRaisesRegex(ValueError, source.BASE_ENV):
                source.select_camera_apk(None, None, '/must-not-change.apk')
            copy.assert_not_called()

    def test_unpinned_base_fails_before_copy(self):
        with tempfile.NamedTemporaryFile() as apk:
            apk.write(b'wrong version or already patched APK')
            apk.flush()
            with patch.dict(os.environ, {source.BASE_ENV: apk.name}), patch.object(source.shutil, 'copyfile') as copy:
                with self.assertRaisesRegex(ValueError, 'SHA-256'):
                    source.select_camera_apk(None, None, '/must-not-change.apk')
                copy.assert_not_called()

    def test_base_selected_before_version_specific_patches(self):
        extractor = (ROOT / 'extract-files.py').read_text()
        self.assertLess(extractor.index('.call(select_camera_apk)'), extractor.index(".apktool_patch('patches-6.7')"))
        self.assertLess(extractor.index(".apktool_patch('patches-6.7')"), extractor.index('.call(add_processing_service)'))

    def test_aperture_override_is_scoped_to_miuicamera(self):
        blueprint = (ROOT / 'Android.bp').read_text()
        app = blueprint.split('android_app_import {', 1)[1]
        overrides = app.split('overrides: [', 1)[1].split(']', 1)[0]
        self.assertIn('name: "MiuiCamera"', app)
        for name in ('Aperture', 'ApertureOverlayFlourite'):
            self.assertIn(f'"{name}"', overrides)
        device = (ROOT.parent / 'flourite/device.mk').read_text()
        self.assertIn('ApertureOverlayFlourite', device)
        self.assertIn('inherit-product-if-exists, device/xiaomi/flourite-miuicamera/device.mk', device)


if __name__ == '__main__':
    unittest.main()
