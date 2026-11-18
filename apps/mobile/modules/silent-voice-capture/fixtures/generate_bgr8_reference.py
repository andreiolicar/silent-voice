"""Independent standard-library reference. Synthetic pixels only; no camera/model."""
import argparse
import hashlib
import json
from pathlib import Path


def reference():
    width, height = 640, 480
    stride = width * 4 + 16
    source = bytearray([231]) * (stride * height)
    expected = bytearray()
    for y in range(height):
        for x in range(width):
            b, g, r = (x + 3 * y) % 256, (5 * x + y) % 256, (7 * x + 11 * y) % 256
            offset = y * stride + x * 4
            source[offset:offset + 4] = bytes((b, g, r, (x ^ y) % 256))
            expected.extend((b, g, r))
    offsets = [0, 1, 2, 3, 4, 5, 1917, 1918, 1919, 1920, 1921, 1922, 461760, 461761, 461762, 921597, 921598, 921599]
    return {
        "scope": "SYNTHETIC_ONLY_NO_MODEL_NO_PERSON",
        "width": width, "height": height, "pixelFormat": "BGR8",
        "sourceBytesPerRow": stride, "sourceByteCount": len(source),
        "byteCount": len(expected), "sha256": hashlib.sha256(expected).hexdigest(),
        "pattern": "B=(x+3*y)%256; G=(5*x+y)%256; R=(7*x+11*y)%256; A=(x^y)%256; padding=231",
        "samples": [{"offset": i, "value": expected[i]} for i in offsets],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(reference(), output, indent=2)
        output.write("\n")
