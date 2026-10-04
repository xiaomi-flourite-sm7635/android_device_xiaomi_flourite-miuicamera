# Xiaomi Camera for flourite

Integration for LineageOS 24, using Camera **6.7.000070.0** from the pinned
Rodin app base below, with flourite **OS3.0.306.0.WPRMIXM** Qualcomm JNI and
vendor libraries. The user tested 6.7 successfully after clearing the previous
app state; this does not establish that the intermittent ADSP resets are fixed.
The 306 firmware refresh and the changes below still need device testing.

Previous flourite 6.4.000320.1 stock APK SHA-256 (historical reference):
`2e8ed1892c302cb6505964b9bddaaf5cc7f21490ee562b654de83a6753756f63`.

The integration layout and resource-loader fix follow the local
[rodin camera tree](https://github.com/Digimend-X-Rodin/android_proprietary_device_xiaomi_rodin-miuicamera).
The 6.7 app already contains Flourite, Flourite_pro and Flourite_pre profiles.
The Flourite patches in `patches-6.7/` are applied to the pinned base,
which already includes Rodin's AOSP resource and permission-flow fixes.
The old `patches/` directory is retained only as the 6.4 reference. No rodin device
spoofing, MediaTek libraries, forced Leica/RAW modes,
permissive domains, or framework modifications are included. MiuiCamera's
module overrides Aperture and ApertureOverlayFlourite only when selected;
builds without this companion keep Aperture. Runtime camera/microphone grants
remain revocable.

## Pinned 6.7 base

Repository: `Digimend-X-Rodin/android_proprietary_vendor_xiaomi_rodin-miuicamera`.
Commit: `d92111308ba4bf74ad6cf332372add6399b8800b` (before the later forced
Leica/RAW customizations). Concatenate that commit's
`proprietary/system/priv-app/MiuiCamera/MiuiCamera.apk.part00` through `.part08`
in numerical order. Do not use the current Rodin APK or mix parts from commits.
Expected base SHA-256:
`259c761925d1be2ce6d5cbbc3986042dbaaf3c5476c88cbc358aab85f70c20e1`.
`camera_apk_source.py` rejects any other input, including already patched APKs.
No automatic download or Rodin vendor-library extraction is performed.

## MiSys integration (October 3)

The first hardware logs show that watermark transfer calls the AIDL V3
`vendor.xiaomi.hardware.misys.common.IMiSysImpl/default`, not the older HIDL
interfaces. Include flourite's `hypsys_vendor` and its three missing interface
libraries; existing `libmisight` and `xiaomi.system.hypsys.common` come from
the main flourite vendor tree. No extra system Java jars are needed for this
observed Binder call.

`configs/hypsys-camera.rc` intentionally replaces the stock init file. It
does not import logger triggers, a kmsg FD, privileged groups or the root
MiSysCore daemon. The core interface **library** is required for linking;
that is not permission to install or expose its server. The common executable
also registers HypSys/Blackbox interfaces, declared in the stock manifest;
their separate service labels allow registration but give MiCAM no client
access. The daemon remains enforcing, with data access confined to
`vendor_camera_data_file`, no block-device access and no persist/app-data
access. This minimal integration still requires build and on-device testing;
non-camera diagnostic code may report denied operations.

Camera/QSPM client attributes and exact capability-property labels address
observed denials. Do not turn the remaining AVC list into blanket permissions.
Native provider crashes and intermittent whole-device resets still require
on-device validation; the integration does not establish that they are fixed.

## AOSP capability enumeration

Patch 0003 keeps flourite's existing `CameraMetadataNative.getAllVendorKeys`
path even without HyperOS version properties. The alternative request-key
list omits static Xiaomi capabilities: a device dump already contains beauty
version 39 and the JSON beauty config, but the app falls back to the unsupported
legacy beauty type 1. The same gate hides the stock custom-HFR video table.
This changes only key enumeration in CameraCapabilities, not individual
feature values, device identity, or the framework. Video/lens capability checks
remain stock; no 4K60 or RAW mode is forced.

The October 3 AVCs also require MiSys to use camera-owned ashmem FDs for
watermark transfer. Read-only access to the observed camera/display/audio
property types is granted, but unrelated boot-status/diagnostic denials are
not turned into permissions. Runtime re-testing remains necessary, especially
RAW session negotiation and the separate native AI-scene null dereference.

## Scoped AOSP processing (October 4, R6)

Patch 0004 starts the app-private `FlouriteProcessingService` after a shutter
task is registered. It uses a camera foreground service and a low-importance
notification while MIVI tasks are pending, with a two-second drain period and
a 120-second maximum after the latest capture. It is not sticky, does not run
at boot, does not hold a wakelock, and does not bypass permission, AppOps or
sensor-privacy checks. Stale callbacks from a closed/idle image reader are
discarded; genuine processing errors from a live session remain visible.

The helper is compiled from `compat/FlouriteProcessingService.java` and added
as `classes12.dex` in 6.7 (`classes8.dex` in the historical 6.4 build).
`camera_manifest.py` appends a private camera-service entry
to the binary manifest, preserving existing string indices and XML nodes.
The stock manifest already requests the camera foreground-service permission.
Do not rebuild the obfuscated resources with apktool: the extraction flow
uses no-res mode, preserving resources, assets and bundled native libraries.
Against the pinned 6.7 input, only the manifest, `classes.dex` (tracking,
its settings and brightness cleanup), `classes4.dex` (capabilities and Flourite mode list), and
`classes5.dex` (processing) change, plus the new DEX.
`tools/test_camera_manifest.py` checks malformed inputs and preservation.

Patch 0006 releases the temporary auto-brightness adjustment with `Float.NaN`
on normal and exception cleanup. A zero adjustment remains active on AOSP
and suppresses brightness animation after leaving the app. The active camera
boost, internal bookkeeping and window-based screen flash are unchanged.
`tools/test_camera_brightness.py` covers both release paths and patch scope.

## Night, video tracking and launcher icon (October 4, firmware 306)

Patch 0005 adds the existing Night mode (173) to the Flourite_pro default mode
strip inherited by Flourite. Saved custom mode orders are not overwritten.
Stock night pipelines and capability checks are retained.

For normal video (162), motion tracking defaults on only if the current camera
advertises TrackAF support. Existing saved preferences, quality/fps restrictions
and mutually exclusive features still take precedence. Firmware 306 advertises
720p30, 1080p30 and 4K24/30; this patch does not force tracking at 60 fps or add
unsupported HAL capabilities. A previously saved off choice stays off.

`MiuiCameraOverlayFlourite` replaces the regular and round adaptive launcher
icons using the three foreground PNGs from the requested Rodin 16.2 patch.
See its NOTICE for provenance. The overlay is platform-signed and installed
only with this camera companion. The APK's obfuscated resources are unchanged;
none of the unrelated Rodin patch is applied. `tools/test_camera_features.py`
checks the scope and capability/preference guards.

The main flourite tree also selects the VNDK 34 tinyxml2 ABI for five camera
importers. R6's `persist.vendor.camera.setDngTag=true` exposed extended JPEG
sizes as well as RAW, causing undersized JPEG buffers. R7 defaults it to false
and uses a firmware-pinned metadata adapter to append only stock RAW16 output
configurations to the original standard table. It handles a persisted R6 true
value too, without changing JPEG dimensions or allocation limits. This is a
main-device-tree fix; the R6 APK/background changes remain unchanged.
The delivered R7 core had a packed-relocation corruption and must not be used.
R8 replaces its ELF rename with an index-preserving import edit and verifies
all relocation targets; the core and rebuilt metadata adapter must be paired.
This does not change the APK or establish on-device capture stability.
Re-test front/rear JPEG, entering the gallery immediately after capture, and
Pro JPEG/RAW. These changes are candidates for device validation, not proof
that the separate CHI metadata teardown crash or whole-device resets are fixed.

## Local setup

Place this tree at `device/xiaomi/flourite-miuicamera` in the ROM checkout.
From that directory, run:

```sh
FLOURITE_MIUI_CAMERA_APK=/absolute/path/to/MiuiCamera-6.7.000070.0-base.apk \
    ./extract-files.py /absolute/path/to/flourite-stock
```

The stock dump still supplies all external native/vendor blobs. The APK input
is replaced with the pinned app base before patching. This generates
`vendor/xiaomi/flourite-miuicamera`. Do not replace it with a Rodin vendor tree
or publish the extracted APK/blobs. Run
`./setup-makefiles.py` after changing the blob list or extraction rules.

The flourite DT conditionally inherits the camera product and BoardConfig
when this companion tree is present. Its generated vendor namespace imports
`device/xiaomi/flourite-miuicamera` and `vendor/xiaomi/flourite`.
The existing flourite camera provider and MIVI/AIDL BGService are reused.
No Xiaomi framework JARs are added to the boot classpath: this APK already
contains its BGService interfaces and marks miui-cameraopt optional.
The source-side APK import declares all four optional Java libraries from
the manifest and keeps `enforce_uses_libs` enabled. The extracted APK is
exposed through a vendor filegroup so regenerating makefiles preserves this.

External native libraries come only from the flourite stock dump. Bundled
app libraries are kept intact from the pinned 6.7 APK.
Unlike the older rodin JNI, these do not import `BnProducerListener::onBufferDetached`;
do not add the rodin libgui shim without a demonstrated missing symbol.
ELF checks remain enabled for the next ROM build.

The initial permission allowlist covers the privileged Android permissions
requested by this APK. The camera domain is enforcing and uses the existing
camera/MIVI/BGService HAL interfaces. It does not bypass the platform neverallow
on direct core-app access to `/mnt/vendor`; calibration remains HAL-owned.

HAL client attributes are Android-only: recovery does not install MiCAM and
its non-Treble macro expansion would inherit permissions meant for the camera
HAL itself. The new public app domain is declared in the 202504 compatibility
ignore map, inherited by older maps, because no older policy contains it.
202504 is the latest older API for the current 202604 platform: Soong skips
compatibility maps whose version equals the current platform API.

## Pre-build checks

Extraction and APK repacking must be verified against the pinned version. APK
resources, assets and bundled native libraries remain unchanged; R6 appends
the private service without rewriting existing manifest nodes. Apktool
reassembles the patched DEX. The four external native libraries have
no unresolved strong imports against their direct dependencies in the local
LineageOS 24 outputs. These checks do not replace a full ROM build or runtime
testing; keep ELF and privileged-permission checks enabled.
The new TE rules and app context also pass an isolated platform-policy
compile/neverallow check; the complete flourite policy must still be built.

`tools/test_processing_lifecycle.py` compiles the real foreground-service
helper against host-only Android fakes, then checks nine scheduling, timeout,
cleanup and failure scenarios. The fakes are never included in the APK. This
does not replace testing Android's permission/AppOps behavior on the phone.

## First hardware check

Test launch/close, rear main/ultrawide/front preview, normal still photos,
video start/stop and viewing saved media. Aperture is no longer co-installed
when this companion is enabled; retain the known-working R8 OTA for recovery.
Collect full logcat and enforcing SELinux AVCs on failure; do not switch
SELinux to permissive or blindly copy rodin permissions. Offline processing,
optional modes and regional camera variants still need on-device validation.
