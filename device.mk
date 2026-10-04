# SPDX-FileCopyrightText: 2026 The LineageOS Project
# SPDX-License-Identifier: Apache-2.0

FLOURITE_MIUI_CAMERA_PATH := device/xiaomi/flourite-miuicamera

$(call inherit-product, vendor/xiaomi/flourite-miuicamera/flourite-miuicamera-vendor.mk)

PRODUCT_SOONG_NAMESPACES += $(FLOURITE_MIUI_CAMERA_PATH)

PRODUCT_PACKAGES += MiuiCamera

PRODUCT_COPY_FILES += \
    $(FLOURITE_MIUI_CAMERA_PATH)/configs/hypsys-camera.rc:$(TARGET_COPY_OUT_VENDOR)/etc/init/hypsys-camera.rc \
    $(FLOURITE_MIUI_CAMERA_PATH)/configs/default-permissions-miuicamera.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/default-permissions/default-permissions-miuicamera.xml \
    $(FLOURITE_MIUI_CAMERA_PATH)/configs/privapp-permissions-miuicamera.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/permissions/privapp-permissions-miuicamera.xml \
    $(FLOURITE_MIUI_CAMERA_PATH)/configs/miuicamera-hiddenapi-package-whitelist.xml:$(TARGET_COPY_OUT_SYSTEM)/etc/sysconfig/miuicamera-hiddenapi-package-whitelist.xml \
    $(FLOURITE_MIUI_CAMERA_PATH)/configs/public.libraries-xiaomi.txt:$(TARGET_COPY_OUT_SYSTEM)/etc/public.libraries-xiaomi.txt

PRODUCT_VENDOR_PROPERTIES += \
    persist.vendor.camera.privapp.list=com.android.camera,org.lineageos.aperture,org.codeaurora.snapcam

PRODUCT_SYSTEM_PROPERTIES += \
    ro.com.google.lens.oem_camera_package=com.android.camera
