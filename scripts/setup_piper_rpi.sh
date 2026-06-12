#!/usr/bin/env bash
# Bootstrap piper-tts on Raspberry Pi 3 (ARM64, 64-bit OS required)
# Run once after cloning the repo:  bash scripts/setup_piper_rpi.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="$REPO_ROOT/models"
VOICE="fr_FR-upmc-medium"
HF_BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/upmc/medium"

echo "=== piper-tts bootstrap for Raspberry Pi 3 ==="
echo ""

# 1. Check architecture
ARCH="$(uname -m)"
if [[ "$ARCH" != "aarch64" ]]; then
    echo "WARNING: expected aarch64 (64-bit ARM), got $ARCH"
    echo "piper-tts requires a 64-bit OS on RPi3 (Raspberry Pi OS 64-bit or Ubuntu 22.04+)"
    echo "Continuing anyway — if pip install fails, switch to a 64-bit OS."
    echo ""
fi

# 2. System dependencies
echo ">>> Installing system dependencies..."
sudo apt-get update -qq
# apt may exit non-zero due to unrelated half-configured packages (e.g. wm8960 DKMS).
# We install with || true and then verify our deps are actually present.
sudo apt-get install -y --no-install-recommends \
    espeak-ng \
    libespeak-ng1 \
    libsndfile1 \
    python3-dev || true
for pkg in espeak-ng libespeak-ng1 libsndfile1 python3-dev; do
    dpkg -l "$pkg" 2>/dev/null | grep -q "^ii" \
        || { echo "ERROR: $pkg is not installed — fix apt before continuing"; exit 1; }
done
echo "  All system dependencies present."

# 3. Install piper-tts Python package
# Bookworm (PEP 668) forbids system-wide pip installs by default.
# The project already uses --break-system-packages (gtts is in /usr/local/lib).
echo ""
echo ">>> Installing piper-tts Python package..."
pip3 install --break-system-packages piper-tts

# 4. Download voice model
echo ""
echo ">>> Downloading voice model: $VOICE (~63 MB)..."
mkdir -p "$MODELS_DIR"

MODEL_FILE="$MODELS_DIR/${VOICE}.onnx"
CONFIG_FILE="$MODELS_DIR/${VOICE}.onnx.json"

if [[ ! -f "$MODEL_FILE" ]]; then
    echo "  Downloading ${VOICE}.onnx..."
    curl -L --progress-bar -o "$MODEL_FILE" "${HF_BASE}/${VOICE}.onnx"
else
    echo "  ${VOICE}.onnx already present, skipping."
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "  Downloading ${VOICE}.onnx.json..."
    curl -L --progress-bar -o "$CONFIG_FILE" "${HF_BASE}/${VOICE}.onnx.json"
else
    echo "  ${VOICE}.onnx.json already present, skipping."
fi

# 5. Quick smoke test
echo ""
echo ">>> Smoke test: synthesizing a short phrase..."
python3 - <<'PYEOF'
import sys, os
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, 'talking_keyboard'))
os.chdir(os.path.join(repo_root, 'talking_keyboard'))
from audio import PiperTTS
tts = PiperTTS()
data = tts.generate("Bonjour, je suis Jessica.")
if data:
    print(f"  OK — generated {len(data)} bytes of audio.")
else:
    print("  FAILED — check logs above.", file=sys.stderr)
    sys.exit(1)
PYEOF

# 6. Pre-generate bootstrap audio
echo ""
echo ">>> Pre-generating bootstrap audio prompts..."
python3 - <<'PYEOF'
import sys, os
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(repo_root, 'talking_keyboard'))
os.chdir(os.path.join(repo_root, 'talking_keyboard'))
from main import _ensure_bootstrap_audio
_ensure_bootstrap_audio()
print("  Bootstrap audio ready.")
PYEOF

echo ""
echo "=== Setup complete ==="
echo "Voice: $VOICE (speaker: jessica)"
echo "Models stored in: $MODELS_DIR"
echo "Run the app: cd talking_keyboard && python3 main.py"
