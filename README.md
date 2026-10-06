# Xiaomi Camera for flourite

LineageOS 24 integration for Camera **6.7.000070.0**, with native libraries
from flourite **OS3.0.306.0.WPRMIXM**.

Place this repository at `device/xiaomi/flourite-miuicamera` and its matching
vendor repository at `vendor/xiaomi/flourite-miuicamera`. The main flourite tree
includes this companion when present; MiuiCamera then replaces Aperture.

## Extraction

Set `FLOURITE_MIUI_CAMERA_APK` to the pinned, unmodified 6.7 base APK and run
`extract-files.py` against the flourite stock dump. The extractor applies
`patches-6.7`, adds the processing service, and preserves the app resources.

Base APK: [Rodin camera vendor](https://github.com/Digimend-X-Rodin/android_proprietary_vendor_xiaomi_rodin-miuicamera),
commit `d92111308ba4bf74ad6cf332372add6399b8800b`.
Join that revision's APK parts `.part00` through `.part08` in order.
Expected SHA-256: `259c761925d1be2ce6d5cbbc3986042dbaaf3c5476c88cbc358aab85f70c20e1`.
Do not substitute Rodin native libraries.

The older `patches` directory is for the 6.4 app, not the current extraction.
Launcher artwork attribution is in `overlay/MiuiCameraOverlayFlourite/NOTICE`.
