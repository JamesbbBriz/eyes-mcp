#!/usr/bin/env bash
# eyes-mcp installer: deps + model preset + llama-server check.
#   ./install.sh                       # default preset (lfm-450m)
#   EYES_PRESET=fast ./install.sh      # Apache-2.0 500M preset
#   HF_ENDPOINT=https://hf-mirror.com ./install.sh   # mainland-CN mirror
set -euo pipefail

cd "$(dirname "$0")/.."
PRESET="${EYES_PRESET:-lfm-450m}"

echo "== eyes-mcp install (preset: $PRESET) =="

# 1. Python deps via uv (fallback: pip)
if command -v uv >/dev/null 2>&1; then
  uv sync
else
  echo "! uv not found — falling back to pip (get uv for a better experience: https://docs.astral.sh/uv/)"
  python3 -m venv .venv
  ./.venv/bin/pip install -e .
fi

# 2. llama-server
if ! command -v llama-server >/dev/null 2>&1; then
  echo "! llama-server not on PATH."
  if command -v brew >/dev/null 2>&1; then
    echo "  installing via homebrew: llama.cpp"
    brew install llama.cpp
  else
    echo "  Please install it manually: https://github.com/ggml-org/llama.cpp#usage" >&2
    echo "  (macOS: brew install llama.cpp)" >&2
    exit 127
  fi
fi

# 3. Model files
./scripts/download_models.sh

# 4. Smoke test
echo "== smoke test =="
uv run python -c "import eyes_mcp.server; print('import OK, MCP server:', eyes_mcp.server.server.name)"

cat <<'EOF'

== next: register the MCP server ==

Claude Code   (~/.claude.json → mcpServers):
  "eyes-mcp": {
    "command": "uv",
    "args": ["--directory", "/ABS/PATH/TO/eyes-mcp", "run", "eyes-mcp"],
    "env": { "EYES_PRESET": "lfm-450m" }
  }

Codex         (~/.codex/config.toml):
  [mcp_servers.eyes-mcp]
  command = "uv"
  args = ["--directory", "/ABS/PATH/TO/eyes-mcp", "run", "eyes-mcp"]
  env = { EYES_PRESET = "lfm-450m" }

Cursor        (.cursor/mcp.json): same shape as Claude Code.
EOF
echo "install complete ✓"
