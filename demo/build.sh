#!/usr/bin/env bash
# Build the csm demo GIF/MP4 with VHS in Docker (no host bloat).
# Usage: cd demo && ./build.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "→ generating fake demo data (demo/home)…"
python3 make_demo_data.py

echo "→ building VHS+python image…"
docker build -t csm-vhs -f Dockerfile ..

echo "→ rendering demo.tape → picker.gif + picker.mp4…"
docker run --rm -v "$PWD":/vhs csm-vhs demo.tape

echo "✓ done:"
ls -lh picker.gif picker.mp4 2>/dev/null || true
