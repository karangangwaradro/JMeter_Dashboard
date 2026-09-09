"""
generate_favicon.py — Generates a 32x32 standard Windows ICO file in pure Python.
Creates web/favicon.ico matching PerfPilot's branding.
"""

import struct
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
OUT_PATH = ROOT_DIR / "web" / "favicon.ico"

WIDTH = 32
HEIGHT = 32

def create_ico():
    pixels = []
    # Bottom to top
    for y in range(HEIGHT - 1, -1, -1):
        for x in range(WIDTH):
            # Check rounded corner
            dx = min(x, WIDTH - 1 - x)
            dy = min(y, HEIGHT - 1 - y)
            is_corner = (dx < 4 and dy < 4 and (3 - dx)**2 + (3 - dy)**2 > 9)

            if is_corner:
                # Transparent
                pixels.append((0, 0, 0, 0))
                continue

            # Telemetry wave coordinates on 32x32 grid:
            # Baseline is at y = 16
            # Points: (4,16) -> (9,16) -> (12,24) -> (17,8) -> (21,20) -> (24,16) -> (28,16)
            is_pulse = False
            is_peak = False

            # Draw pulse line approximation
            if y == 16 and (4 <= x <= 9 or 24 <= x <= 28):
                is_pulse = True
            elif x in (10, 11) and 16 <= y <= 24:
                is_pulse = True
            elif x in (12, 13) and 20 <= y <= 24:
                is_pulse = True
            elif 14 <= x <= 16 and 8 <= y <= 20:
                is_pulse = True
            elif x in (17, 18) and y in (7, 8, 9):
                is_peak = True
                is_pulse = True
            elif x in (19, 20) and 9 <= y <= 20:
                is_pulse = True
            elif x in (21, 22, 23) and 16 <= y <= 20:
                is_pulse = True

            if is_peak:
                # Electric cyan glow dot
                pixels.append((255, 220, 56, 255))  # BGRA
            elif is_pulse:
                # Electric cyan / indigo wave
                pixels.append((248, 189, 56, 255))  # BGRA (#38bdf8)
            elif y == 16 and x % 3 == 0:
                # Subtle grid line
                pixels.append((85, 65, 51, 255))    # BGRA (#334155)
            else:
                # Dark slate background #0f172a
                pixels.append((42, 23, 15, 255))    # BGRA (#0f172a)

    pixel_bytes = bytearray()
    for b, g, r, a in pixels:
        pixel_bytes.extend([b, g, r, a])

    mask_bytes = b"\x00" * (WIDTH * HEIGHT // 8)  # 128 bytes

    bmp_header = struct.pack(
        "<IiiHHIIiiII",
        40,          # biSize
        WIDTH,       # biWidth
        HEIGHT * 2,  # biHeight (image + mask)
        1,           # biPlanes
        32,          # biBitCount
        0,           # biCompression (BI_RGB)
        len(pixel_bytes), # biSizeImage
        0,           # biXPelsPerMeter
        0,           # biYPelsPerMeter
        0,           # biClrUsed
        0            # biClrImportant
    )

    image_data = bmp_header + pixel_bytes + mask_bytes

    ico_header = struct.pack("<HHH", 0, 1, 1)  # reserved, type (1=icon), count
    ico_entry = struct.pack(
        "<BBBBHHII",
        WIDTH,
        HEIGHT,
        0,   # color count
        0,   # reserved
        1,   # planes
        32,  # bit count
        len(image_data),
        22   # offset (6 + 16)
    )

    full_ico = ico_header + ico_entry + image_data
    OUT_PATH.write_bytes(full_ico)
    print(f"[+] Wrote {OUT_PATH} ({len(full_ico)} bytes)")

if __name__ == "__main__":
    create_ico()
