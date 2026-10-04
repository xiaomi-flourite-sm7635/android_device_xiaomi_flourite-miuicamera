#!/usr/bin/env python3
"""Narrow scope guards for the 6.7 UI feature and icon changes."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

class CameraFeaturesTest(unittest.TestCase):
    def test_night_entry_enabled_only_in_flourite_profile(self):
        patch = (ROOT / 'patches-6.7/0007-enable-flourite-night-module-entry.patch').read_text()
        targets = [line for line in patch.splitlines() if line.startswith('+++ ')]
        self.assertEqual(len(targets), 1)
        self.assertIn('學孴孶嬵孶孲嬵孿孾孭孲學孾嬵孝孷孴孮孩孲孯孾孄孫孩孴.smali', targets[0])
        self.assertIn('.method public final Z6()Z', patch)
        self.assertIn('-    const/4 p0, 0x0', patch)
        self.assertIn('+    const/4 p0, 0x1', patch)
        added = [line for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++')]
        self.assertEqual(added, ['+    const/4 p0, 0x1'])

    def test_feature_patch_keeps_hardware_checks_and_user_choice(self):
        patch = (ROOT / 'patches-6.7/0005-flourite-night-and-video-tracking.patch').read_text()
        added = '\n'.join(line[1:] for line in patch.splitlines() if line.startswith('+') and not line.startswith('+++'))
        self.assertIn('        0xad', added)
        self.assertIn('const/16 v0, 0xa2', added)
        self.assertIn('Ln9/g;->e4(Ln9/f;)Z', added)
        self.assertIn('if-eqz p0, :flourite_default_off', added)
        self.assertNotIn('Lii/a;->n(', added)  # never overwrite a stored choice
        self.assertNotIn('TrackAFSupportedMask', added)
        self.assertNotIn('VideoTrackAFQuality', added)

    def test_icon_overlay_is_scoped_and_covers_round_launcher(self):
        overlay = ROOT / 'overlay/MiuiCameraOverlayFlourite'
        xml = ET.parse(overlay / 'AndroidManifest.xml').getroot()
        self.assertEqual(xml.find('overlay').get('{http://schemas.android.com/apk/res/android}targetPackage'), 'com.android.camera')
        for name in ('etk_ic_launcher', 'etk_ic_launcher_round'):
            icon = ET.parse(overlay / f'res/mipmap-anydpi-v26/{name}.xml').getroot()
            self.assertEqual(icon.tag, 'adaptive-icon')
            self.assertIn('flourite_camera_foreground', icon.find('foreground').get('{http://schemas.android.com/apk/res/android}drawable'))
        for density in ('xhdpi', 'xxhdpi', 'xxxhdpi'):
            self.assertTrue((overlay / f'res/mipmap-{density}/flourite_camera_foreground.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertIn('MiuiCameraOverlayFlourite', (ROOT / 'device.mk').read_text())

if __name__ == '__main__':
    unittest.main(verbosity=2)
