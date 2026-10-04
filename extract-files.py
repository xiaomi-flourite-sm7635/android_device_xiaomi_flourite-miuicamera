#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

from extract_utils.fixups_blob import blob_fixup
from extract_utils.main import ExtractUtils, ExtractUtilsModule
from camera_apk_fixup import add_processing_service, restore_unchanged_dex
from camera_apk_source import select_camera_apk

module = ExtractUtilsModule(
    'flourite-miuicamera',
    'xiaomi',
    blob_fixups={
        'system/priv-app/MiuiCamera/MiuiCamera.apk': blob_fixup()
            .call(select_camera_apk)
            .apktool_patch('patches-6.7')
            .call(restore_unchanged_dex)
            .call(add_processing_service)
            .stripzip(),
    },
    namespace_imports=[
        'device/xiaomi/flourite-miuicamera',
        'vendor/xiaomi/flourite',
    ],
)

if __name__ == '__main__':
    ExtractUtils.device(module).run()
