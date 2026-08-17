#!/usr/bin/env bash
# eyes-mcp installer: deps + model + modality detection + auto-registration.
#
#   ./install.sh                          # interactive (recommended)
#   EYES_PRESET=fast ./install.sh         # pick a model tier
#   HF_ENDPOINT=https://hf-mirror.com ./install.sh    # mainland-CN mirror
#   ./install.sh --yes                    # accept all recommendations, no prompts
#   ./install.sh --dry-run                # show what would happen, change nothing
set -euo pipefail

cd "$(dirname "$0")/.."
PRESET="${EYES_PRESET:-lfm-450m}"
DRY_RUN=0; ASSUME_YES=0; FORCE=0
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --yes|-y)  ASSUME_YES=1 ;;
    --force)   FORCE=1 ;;
    *) echo "unknown flag: $arg (supported: --dry-run --yes --force)" >&2; exit 2 ;;
  esac
done

run() { # run or echo in dry-run mode
  if [ "$DRY_RUN" = "1" ]; then echo "  [dry-run] $*"; else "$@"; fi
}

echo "== eyes-mcp install (preset: $PRESET) =="

# ---- 1. Python deps -------------------------------------------------------
if command -v uv >/dev/null 2>&1; then
  run uv sync
else
  echo "! uv not found — falling back to pip (get uv for a better experience: https://docs.astral.sh/uv/)"
  run python3 -m venv .venv
  run ./.venv/bin/pip install -e .
fi
UV_BIN="${UV_BIN:-$(command -v uv || echo "$PWD/.venv/bin/python")}"

# ---- 2. llama-server ------------------------------------------------------
if ! command -v llama-server >/dev/null 2>&1; then
  echo "! llama-server not on PATH."
  if command -v brew >/dev/null 2>&1; then
    echo "  installing via homebrew: llama.cpp"
    run brew install llama.cpp
  else
    echo "  Please install it manually: https://github.com/ggml-org/llama.cpp#usage" >&2
    exit 127
  fi
fi

# ---- 3. Model files -------------------------------------------------------
run ./scripts/download_models.sh

# ---- 4. Detect agents & their model modality ------------------------------
echo
echo "== agent detection (does your model need eyes?) =="
python3 scripts/detect_modality.py   # read-only; runs even in dry-run
echo

# ---- 5. Auto-register into agents that need eyes ---------------------------
echo "== registration =="
while IFS='|' read -r agent verdict model; do
  [ -z "$agent" ] && continue
  case "$verdict" in
    text-only) want=1; reason="model '$model' is text-only — it needs eyes" ;;
    multimodal)
      if [ "$FORCE" = "1" ]; then want=1; reason="--force: registering despite multimodal model '$model'"
      else echo "✗ $agent: skipped (model '$model' sees images natively; use --force to override)"; continue; fi ;;
    *) want=1; reason="model unknown — assuming text-only (harmless)" ;;
  esac

  if [ "$ASSUME_YES" != "1" ] && [ "$DRY_RUN" != "1" ]; then
    read -r -p "register eyes-mcp into $agent? ($reason) [Y/n] " reply
    case "$reply" in n*|N*) echo "  skipped $agent"; continue ;; esac
  fi
  echo "→ $agent: $reason"

  case "$agent" in
    claude-code)
      if command -v claude >/dev/null 2>&1; then
        run claude mcp add -s user -e "EYES_PRESET=$PRESET" eyes-mcp -- \
          "$UV_BIN" --directory "$PWD" run eyes-mcp
      else echo "  (claude CLI not found — add manually, see README)" ; fi ;;
    codex)
      if command -v codex >/dev/null 2>&1; then
        run codex mcp add --env "EYES_PRESET=$PRESET" eyes-mcp -- \
          "$UV_BIN" --directory "$PWD" run eyes-mcp
      else echo "  (codex CLI not found — add manually, see README)" ; fi ;;
    *) echo "  (no auto-registration for $agent yet — see README for manual config)" ;;
  esac
done < <(python3 scripts/detect_modality.py --shell)

echo
echo "== done ✓  restart your agent, then ask: \"what's in this screenshot?\" =="
