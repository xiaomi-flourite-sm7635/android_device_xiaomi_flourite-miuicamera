#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Binary XML fixture tests: preserve old nodes/indices, fail closed on drift."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from camera_manifest import SERVICE, TEMPLATE, add_service, chunks, strings


def node(name, attrs=(), end=False):
    header = struct.pack('<HHIII', 0x103 if end else 0x102, 16,
                         24 if end else 36 + 20 * len(attrs), 1, 0xffffffff)
    if end:
        return header + struct.pack('<II', 0xffffffff, name)
    extension = struct.pack('<IIHHHHHH', 0xffffffff, name, 20, 20, len(attrs), 0, 0, 0)
    return header + extension + b''.join(struct.pack('<IIIHBBI', 0, key, 0xffffffff, 8, 0, kind, value)
                                         for key, kind, value in attrs)


def fixture(utf8=True, exported=0, camera_type=0x40):
    names = ['http://schemas.android.com/apk/res/android', 'application', 'service',
             'name', 'exported', 'foregroundServiceType', TEMPLATE]
    offsets, data = [], b''
    for name in names:
        offsets.append(len(data))
        if utf8:
            text = name.encode()
            data += bytes((len(name), len(text))) + text + b'\0'
        else:
            data += struct.pack('<H', len(name)) + name.encode('utf-16le') + b'\0\0'
    data += b'\0' * (-len(data) % 4)
    start = 28 + 4 * len(names)
    pool = struct.pack('<HHIIIIII', 1, 28, start + len(data), len(names), 0, 0x100 if utf8 else 0, start, 0)
    pool += struct.pack('<' + 'I' * len(offsets), *offsets) + data
    body = pool + node(1) + node(2, [(3, 3, 6), (4, 0x12, exported), (5, 0x11, camera_type)])
    body += node(2, end=True) + node(1, end=True)
    return struct.pack('<HHI', 3, 8, len(body) + 8) + body


class ManifestTest(unittest.TestCase):
    def test_utf8_and_utf16_preserve_original_nodes_and_strings(self):
        for utf8 in (True, False):
            with self.subTest(utf8=utf8):
                original = fixture(utf8)
                before = list(chunks(original))
                after = list(chunks(add_service(original)))
                self.assertEqual(strings(after[0][1]), strings(before[0][1]) + [SERVICE])
                self.assertEqual(after[1:4] + after[6:], before[1:])
                self.assertEqual(len(after), len(before) + 2)

    def test_duplicate_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'already present'):
            add_service(add_service(fixture()))

    def test_exported_template_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'private camera'):
            add_service(fixture(exported=1))

    def test_wrong_foreground_type_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'private camera'):
            add_service(fixture(camera_type=0x80))

    def test_truncated_manifest_is_rejected(self):
        with self.assertRaises(ValueError):
            add_service(fixture()[:-1])

    def test_wrong_chunk_size_is_rejected(self):
        data = bytearray(fixture())
        struct.pack_into('<I', data, 12, 0)
        with self.assertRaises(ValueError):
            add_service(bytes(data))


if __name__ == '__main__':
    unittest.main(verbosity=2)
