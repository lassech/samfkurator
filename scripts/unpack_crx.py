#!/usr/bin/env python3
"""Unpack a Chrome extension (.crx) file to a directory."""

import struct
import sys
import zipfile


def unpack_crx(crx_path: str, output_dir: str) -> None:
    with open(crx_path, "rb") as f:
        magic = f.read(4)
        if magic == b"Cr24":
            version = struct.unpack("<I", f.read(4))[0]
            if version == 2:
                key_len = struct.unpack("<I", f.read(4))[0]
                sig_len = struct.unpack("<I", f.read(4))[0]
                f.read(key_len + sig_len)
            elif version == 3:
                header_len = struct.unpack("<I", f.read(4))[0]
                f.read(header_len)
            zip_data = f.read()
        else:
            f.seek(0)
            zip_data = f.read()

    zip_path = crx_path + ".zip"
    with open(zip_path, "wb") as zf:
        zf.write(zip_data)

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(output_dir)

    import os
    os.remove(zip_path)
    print(f"Extension udpakket til {output_dir}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Brug: {sys.argv[0]} <crx-fil> <output-mappe>")
        sys.exit(1)
    unpack_crx(sys.argv[1], sys.argv[2])
