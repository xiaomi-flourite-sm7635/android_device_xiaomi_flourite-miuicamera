# Xiaomi Camera for flourite

Initial integration for LineageOS 24, using flourite **OS3.0.304.0.WPRMIXM**
Camera **6.4.000320.1** and its Qualcomm JNI libraries. Runtime validation on
the phone is still required; this is not a claim that every mode works.

Original stock APK SHA-256:
`2e8ed1892c302cb6505964b9bddaaf5cc7f21490ee562b654de83a6753756f63`.

The integration layout and resource-loader fix follow the local
[rodin camera tree](https://github.com/Digimend-X-Rodin/android_proprietary_device_xiaomi_rodin-miuicamera).
The APK patches are re-targeted to flourite's own version. No rodin device
spoofing, MediaTek libraries, blackbox services, forced Leica/RAW modes,
permissive domains, or framework modifications are included. Aperture stays
installed as a fallback. Runtime camera/microphone grants remain revocable.

## Local setup

Place this tree at `device/xiaomi/flourite-miuicamera` in the ROM checkout.
From that directory, run `./extract-files.py /absolute/path/to/flourite-stock`
with the extracted stock dump. This generates `vendor/xiaomi/flourite-miuicamera`.
Do not use a rodin vendor tree or publish the extracted APK/blobs. Run
`./setup-makefiles.py` after changing the blob list or extraction rules.

The flourite DT conditionally inherits the camera product and BoardConfig
when this companion tree is present. Its generated vendor namespace imports
`device/xiaomi/flourite-miuicamera` and `vendor/xiaomi/flourite`.
The existing flourite camera provider and MIVI/AIDL BGService are reused.
No Xiaomi framework JARs are added to the boot classpath: this APK already
contains its BGService interfaces and marks miui-cameraopt optional.
The source-side APK import declares all three optional Java libraries from
the manifest and keeps `enforce_uses_libs` enabled. The extracted APK is
exposed through a vendor filegroup so regenerating makefiles preserves this.

Only native libraries actually present in the flourite stock dump are used.
Unlike the older rodin JNI, these do not import `BnProducerListener::onBufferDetached`;
do not add the rodin libgui shim without a demonstrated missing symbol.
ELF checks remain enabled for the next ROM build.

The initial permission allowlist covers the privileged Android permissions
requested by this APK. The camera domain is enforcing and uses the existing
camera/MIVI/BGService HAL interfaces. It does not bypass the platform neverallow
on direct core-app access to `/mnt/vendor`; calibration remains HAL-owned.

## Pre-build checks

Extraction and APK repacking were tested with the stock version above. The
repacked manifest, resources, assets and bundled native libraries match stock;
apktool also reassembles the DEX files. The four external native libraries have
no unresolved strong imports against their direct dependencies in the local
LineageOS 24 outputs. These checks do not replace a full ROM build or runtime
testing; keep ELF and privileged-permission checks enabled.
The new TE rules and app context also pass an isolated platform-policy
compile/neverallow check; the complete flourite policy must still be built.

## First hardware check

Test launch/close, rear main/ultrawide/front preview, normal still photos,
video start/stop and viewing saved media. Keep Aperture for comparison.
Collect full logcat and enforcing SELinux AVCs on failure; do not switch
SELinux to permissive or blindly copy rodin permissions. Offline processing,
optional modes and regional camera variants still need on-device validation.
