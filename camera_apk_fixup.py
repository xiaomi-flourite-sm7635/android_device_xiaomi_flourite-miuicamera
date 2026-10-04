# SPDX-License-Identifier: Apache-2.0
"""Compile the small AOSP foreground-service adapter; never ship stub classes."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile
from camera_manifest import add_service
from camera_apk_source import pinned_camera_apk


def preserve_base_payload(base, assembled, output):
    """Only retain apktool output for the three DEX files our patches touch."""
    processing_dex_name(base.namelist())
    processing_dex_name(assembled.namelist())
    if sorted(base.namelist()) != sorted(assembled.namelist()):
        raise ValueError('Unexpected entries after MiCAM reassembly')
    for entry in base.infolist():
        name = entry.filename
        before = base.read(entry)
        after = assembled.read(name)
        if name in ('classes.dex', 'classes4.dex', 'classes5.dex'):
            contents = after
        else:
            if not re.fullmatch(r'classes\d*\.dex', name) and before != after:
                raise ValueError(f'Unexpected non-code change after MiCAM reassembly: {name}')
            contents = before
        output.writestr(entry, contents)


def restore_unchanged_dex(ctx, file, file_path, *args, **kwargs):
    source = pinned_camera_apk()
    with tempfile.TemporaryDirectory(prefix='flourite-camera-dex-') as temporary:
        restored = Path(temporary) / 'MiuiCamera.apk'
        with zipfile.ZipFile(source) as base, zipfile.ZipFile(file_path) as assembled:
            with zipfile.ZipFile(restored, 'w') as output:
                preserve_base_payload(base, assembled, output)
        shutil.copyfile(restored, file_path)


def processing_dex_name(names):
    """Fail closed if the pinned 6.7 base changes or is already processed."""
    existing = [name for name in names if re.fullmatch(r'classes\d*\.dex', name)]
    expected = ['classes.dex'] + [f'classes{i}.dex' for i in range(2, 12)]
    if sorted(existing) != sorted(expected):
        raise ValueError('Unexpected MiCAM 6.7 DEX layout; re-audit the APK')
    return 'classes12.dex'


def add_processing_service(ctx, file, file_path, *args, **kwargs):
    from extract_utils.tools import android_root, java_path

    root = Path(android_root)
    source = Path(ctx.module_dir) / 'compat/FlouriteProcessingService.java'
    sdk = root / 'prebuilts/sdk/36/public/android.jar'
    d8 = root / 'prebuilts/r8/r8.jar'
    java = Path(java_path)
    with tempfile.TemporaryDirectory(prefix='flourite-camera-service-') as temporary:
        stage = Path(temporary)
        classes = stage / 'classes'
        dex = stage / 'dex'
        classes.mkdir()
        dex.mkdir()
        subprocess.run([str(java.with_name('javac')), '-source', '8', '-target', '8',
                        '-classpath', str(sdk), '-d', str(classes), str(source)], check=True)
        compiled = list(classes.rglob('*.class'))
        if len(compiled) != 1 or compiled[0].name != 'FlouriteProcessingService.class':
            raise ValueError('Unexpected foreground service compiler output')
        subprocess.run([str(java), '-cp', str(d8), 'com.android.tools.r8.D8',
                        '--min-api', '34', '--lib', str(sdk), '--output', str(dex),
                        str(compiled[0])], check=True)
        payload = (dex / 'classes.dex').read_bytes()
        rebuilt = stage / 'MiuiCamera.apk'
        with zipfile.ZipFile(file_path) as apk:
            service_dex = processing_dex_name(apk.namelist())
            manifest = add_service(apk.read('AndroidManifest.xml'))
            with zipfile.ZipFile(rebuilt, 'w') as output:
                for entry in apk.infolist():
                    contents = manifest if entry.filename == 'AndroidManifest.xml' else apk.read(entry)
                    output.writestr(entry, contents)
                output.writestr(service_dex, payload, compress_type=zipfile.ZIP_DEFLATED)
        # No replacement until compilation and manifest validation succeed.
        shutil.copyfile(rebuilt, file_path)
