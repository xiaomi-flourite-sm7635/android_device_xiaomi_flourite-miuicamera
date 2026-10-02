# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

FLOURITE_MIUI_CAMERA_PATH := device/xiaomi/flourite-miuicamera

include vendor/xiaomi/flourite-miuicamera/BoardConfigVendor.mk

SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS += $(FLOURITE_MIUI_CAMERA_PATH)/sepolicy/public
SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS += $(FLOURITE_MIUI_CAMERA_PATH)/sepolicy/private
BOARD_VENDOR_SEPOLICY_DIRS += $(FLOURITE_MIUI_CAMERA_PATH)/sepolicy/vendor
