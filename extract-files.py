#!/usr/bin/env -S PYTHONPATH=../../../tools/extract-utils python3
# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

from extract_utils.fixups_blob import blob_fixup
from extract_utils.main import ExtractUtils, ExtractUtilsModule
from camera_apk_fixup import add_processing_service, restore_unchanged_dex
from camera_apk_source import select_camera_apk
import os

# extract-utils consumes git's changed-file list when applying APK patches.
# MiCAM profile filenames contain Unicode: disable quoted paths only for
# this process and its children, never via the user's global Git config.
_git_config_count = int(os.environ.get('GIT_CONFIG_COUNT', '0'))
os.environ[f'GIT_CONFIG_KEY_{_git_config_count}'] = 'core.quotepath'
os.environ[f'GIT_CONFIG_VALUE_{_git_config_count}'] = 'false'
os.environ['GIT_CONFIG_COUNT'] = str(_git_config_count + 1)

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
