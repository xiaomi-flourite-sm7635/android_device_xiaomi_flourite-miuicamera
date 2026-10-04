# SPDX-License-Identifier: Apache-2.0
"""Append one private camera service without rebuilding APK resources.

Clone the stock camera-typed VideoCastService. Every old string index and
XML node stays intact. Reject unknown binary XML instead of guessing.
"""
import struct

SERVICE = 'com.xiaomi.camera.mivi.FlouriteProcessingService'
TEMPLATE = 'com.xiaomi.camera.videocast.VideoCastService'


def chunks(data, start=8):
    offset = start
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError('Truncated XML chunk')
        kind, header, size = struct.unpack_from('<HHI', data, offset)
        if header < 8 or size < header or offset + size > len(data):
            raise ValueError('Invalid XML chunk size')
        yield kind, data[offset:offset + size]
        offset += size


def length(data, offset, utf8):
    unit = 1 if utf8 else 2
    fmt = '<B' if utf8 else '<H'
    value = struct.unpack_from(fmt, data, offset)[0]
    limit = 0x80 if utf8 else 0x8000
    if value & limit:
        following = struct.unpack_from(fmt, data, offset + unit)[0]
        return ((value & (limit - 1)) << (8 if utf8 else 16)) | following, offset + 2 * unit
    return value, offset + unit


def strings(pool):
    _, header, _, count, _, flags, start, _ = struct.unpack_from('<HHIIIIII', pool)
    result = []
    for index in range(count):
        offset = start + struct.unpack_from('<I', pool, header + 4 * index)[0]
        size, offset = length(pool, offset, bool(flags & 0x100))
        if flags & 0x100:
            size, offset = length(pool, offset, True)
            result.append(pool[offset:offset + size].decode('utf-8'))
        else:
            result.append(pool[offset:offset + 2 * size].decode('utf-16le'))
    return result


def append_string(pool, value):
    kind, header, size, count, style_count, flags, start, styles = struct.unpack_from('<HHIIIIII', pool)
    if kind != 1 or header != 28 or style_count or styles or len(value) >= 0x80:
        raise ValueError('Unsupported manifest string pool')
    if start < header + count * 4 or size != len(pool):
        raise ValueError('Invalid manifest string offsets')
    text = pool[start:]
    if flags & 0x100:
        encoded = value.encode('utf-8')
        if len(encoded) >= 0x80:
            raise ValueError('Service name too long')
        encoded = bytes((len(value), len(encoded))) + encoded + b'\0'
    else:
        encoded = struct.pack('<H', len(value)) + value.encode('utf-16le') + b'\0\0'
    expanded = text + encoded
    expanded += b'\0' * (-len(expanded) % 4)
    new_start = start + 4
    return (struct.pack('<HHIIIIII', kind, header, new_start + len(expanded), count + 1,
                        0, flags & ~1, new_start, 0)
            + pool[header:header + count * 4] + struct.pack('<I', len(text))
            + pool[header + count * 4:start] + expanded)


def attributes(chunk, names):
    if struct.unpack_from('<H', chunk, 2)[0] != 16:
        raise ValueError('Unsupported XML node header')
    offset, width, count = struct.unpack_from('<HHH', chunk, 24)
    if width != 20 or 16 + offset + count * width != len(chunk):
        raise ValueError('Unsupported XML attribute layout')
    result = {}
    for index in range(count):
        position = 16 + offset + index * width
        namespace, name, raw, size, reserved, kind, value = struct.unpack_from('<IIIHBBI', chunk, position)
        if (size != 8 or reserved or namespace >= len(names)
                or names[namespace] != 'http://schemas.android.com/apk/res/android'):
            raise ValueError('Unexpected service attribute namespace/type')
        if names[name] in result:
            raise ValueError('Duplicate service attribute')
        result[names[name]] = (position, kind, value)
    return result


def add_service(manifest):
    if len(manifest) < 8 or struct.unpack_from('<HHI', manifest) != (3, 8, len(manifest)):
        raise ValueError('Not a complete Android binary manifest')
    parts = list(chunks(manifest))
    pools = [i for i, (kind, _) in enumerate(parts) if kind == 1]
    if len(pools) != 1:
        raise ValueError('Expected one manifest string pool')
    pool_index = pools[0]
    names = strings(parts[pool_index][1])
    if SERVICE in names:
        raise ValueError('Processing service already present; use the stock APK')
    template = None
    application_end = None
    for index, (kind, data) in enumerate(parts):
        if kind == 0x102 and names[struct.unpack_from('<I', data, 20)[0]] == 'service':
            attrs = attributes(data, names)
            name = attrs.get('name')
            if name and name[1] == 3 and names[name[2]] == TEMPLATE:
                if template is not None or set(attrs) != {'name', 'exported', 'foregroundServiceType'}:
                    raise ValueError('Unexpected service template')
                if (attrs['exported'][1:] != (0x12, 0)
                        or attrs['foregroundServiceType'][1] not in (0x10, 0x11)
                        or attrs['foregroundServiceType'][2] != 0x40):
                    raise ValueError('Template is not a private camera foreground service')
                if index + 1 >= len(parts) or parts[index + 1][0] != 0x103:
                    raise ValueError('Template has unexpected children')
                end = parts[index + 1][1]
                if names[struct.unpack_from('<I', end, 20)[0]] != 'service':
                    raise ValueError('Mismatched service template end')
                clone = bytearray(data)
                position = name[0]
                struct.pack_into('<I', clone, position + 8, len(names))
                struct.pack_into('<I', clone, position + 16, len(names))
                template = [bytes(clone), end]
        if kind == 0x103 and names[struct.unpack_from('<I', data, 20)[0]] == 'application':
            if application_end is not None:
                raise ValueError('Multiple application elements')
            application_end = index
    if template is None or application_end is None:
        raise ValueError('Missing audited service template/application')
    output = []
    for index, (_, data) in enumerate(parts):
        if index == application_end:
            output.extend(template)
        output.append(append_string(data, SERVICE) if index == pool_index else data)
    body = b''.join(output)
    return struct.pack('<HHI', 3, 8, len(body) + 8) + body
