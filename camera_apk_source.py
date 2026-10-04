# SPDX-License-Identifier: Apache-2.0
"""Select the audited 6.7 app separately from flourite's stock Qualcomm blobs."""
import hashlib
import os
from pathlib import Path
import shutil

BASE_VERSION = '6.7.000070.0'
BASE_REPOSITORY = 'https://github.com/Digimend-X-Rodin/android_proprietary_vendor_xiaomi_rodin-miuicamera.git'
BASE_COMMIT = 'd92111308ba4bf74ad6cf332372add6399b8800b'
BASE_SHA256 = '259c761925d1be2ce6d5cbbc3986042dbaaf3c5476c88cbc358aab85f70c20e1'
BASE_ENV = 'FLOURITE_MIUI_CAMERA_APK'


def pinned_camera_apk():
    source = os.environ.get(BASE_ENV)
    if not source:
        raise ValueError(f'Set {BASE_ENV} to the pinned {BASE_VERSION} base APK; see README.md')
    source = Path(source)
    with source.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != BASE_SHA256:
        raise ValueError(f'Unexpected {BASE_VERSION} base APK SHA-256: {digest}; expected {BASE_SHA256}')
    return source


def select_camera_apk(ctx, file, file_path, *args, **kwargs):
    source = pinned_camera_apk()
    if source.resolve() != Path(file_path).resolve():
        shutil.copyfile(source, file_path)
