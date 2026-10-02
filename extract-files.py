#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

from extract_utils.fixups_blob import blob_fixup
from extract_utils.main import ExtractUtils, ExtractUtilsModule

module = ExtractUtilsModule(
    'flourite-miuicamera',
    'xiaomi',
    blob_fixups={
        'system/priv-app/MiuiCamera/MiuiCamera.apk': blob_fixup().apktool_patch('patches'),
    },
    namespace_imports=[
        'device/xiaomi/flourite-miuicamera',
        'vendor/xiaomi/flourite',
    ],
)

if __name__ == '__main__':
    ExtractUtils.device(module).run()
