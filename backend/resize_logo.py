#!/usr/bin/env python3
"""Resize logo to a small PNG and output its base64 encoding."""
import base64
import sys

try:
    from PIL import Image
    import io
    img = Image.open("/home/user/marshaall/frontend/imagenes/logotipo.png")
    img.thumbnail((120, 120), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode()
    print(b64)
except ImportError:
    # Fallback: just read and base64 encode the original (will be large)
    import subprocess
    # Use ImageMagick convert if available
    try:
        subprocess.run(
            ["convert", "/home/user/marshaall/frontend/imagenes/logotipo.png",
             "-resize", "120x120", "/tmp/logo_small.png"],
            check=True, capture_output=True
        )
        with open("/tmp/logo_small.png", "rb") as f:
            print(base64.b64encode(f.read()).decode())
    except Exception:
        print("ERROR: Need PIL or ImageMagick", file=sys.stderr)
        sys.exit(1)
