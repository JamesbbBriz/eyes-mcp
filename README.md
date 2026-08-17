<div align="center">

# 👀 eyes-mcp

**Give any text-only LLM eyes. Local vision for your coding agent.**

One command · zero API keys · nothing leaves your machine

[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)
[![MCP](https://img.shields.io/badge/protocol-MCP-black)](https://modelcontextprotocol.io)
[![llama.cpp](https://img.shields.io/badge/engine-llama.cpp-green)](https://github.com/ggml-org/llama.cpp)
[![简体中文](https://img.shields.io/badge/docs-简体中文-yellow)](./README.zh-CN.md)

*DeepSeek, GLM, Qwen-Coder, Llama… great models, all blind.*

</div>

---

## ❌ Without eyes

You paste a screenshot into your agent (running a text-only model via Claude Code / Codex / Cursor):

```
> Here's the error in my UI, fix it  [screenshot.png]

I'm sorry — I cannot see images. Please describe the error in text.
```

## ✅ With eyes

The agent calls a **local** VLM + OCR instead — and reads the screenshot itself:

```
> Here's the error in my UI, fix it  [screenshot.png]

I see a React hydration error in `CartDrawer.tsx:142`. The OCR shows:
"Hydration failed because the server rendered HTML didn't match the client." …
```

## Quickstart

```bash
git clone https://github.com/JamesbbBriz/eyes-mcp
cd eyes-mcp && ./scripts/install.sh
```

That's it. The installer:

1. asks **which model** you want — with a recommendation computed from your RAM and GPU (no preset needed; skip the question with `EYES_PRESET` or `--yes`),
2. installs deps + downloads the model (~400MB–2GB, resumable),
3. **detects which of your agents run text-only models** (reads your Claude Code / Codex / Cursor configs, checks the model against a modality database),
4. registers eyes-mcp **only where it's needed** — multimodal agents are skipped automatically.

```bash
# options:
EYES_PRESET=fast ./scripts/install.sh            # Apache-2.0 SmolVLM2-500M
HF_ENDPOINT=https://hf-mirror.com ./install.sh  # mainland-CN mirror
./install.sh --yes                              # accept all recommendations, no prompts
./install.sh --dry-run                          # preview without changing anything
```

Just want the modality check? `python3 scripts/detect_modality.py`

Requires: Python ≥3.11, [`llama.cpp`](https://github.com/ggml-org/llama.cpp) (`brew install llama.cpp`), ~1GB RAM.

## Manual registration

Skipped auto-install, or an agent the installer doesn't know? Add it by hand.

**Claude Code** — `~/.claude.json` → `mcpServers`:

```json
"eyes-mcp": {
  "command": "uv",
  "args": ["--directory", "/ABS/PATH/eyes-mcp", "run", "eyes-mcp"],
  "env": { "EYES_PRESET": "lfm-450m" }
}
```

**Codex** — `~/.codex/config.toml`:

```toml
[mcp_servers.eyes-mcp]
command = "uv"
args = ["--directory", "/ABS/PATH/eyes-mcp", "run", "eyes-mcp"]
env = { EYES_PRESET = "lfm-450m" }
```

**Cursor** — `.cursor/mcp.json`: same shape as Claude Code.

Restart the agent, then ask: *"what's in this screenshot?"*

## Tools

| Tool | Engine | Use for |
|---|---|---|
| `analyze_image(path, question?)` | VLM via llama.cpp | Descriptions, UI understanding, visual Q&A |
| `ocr_image(path)` | RapidOCR (onnx) | Dense text: terminals, documents, tables — fast and precise |

## Model presets

| Preset | Model | Download | RAM | License | Notes |
|---|---|---|---|---|---|
| `nano` | SmolVLM2-256M | ~0.3GB | ~1GB | Apache-2.0 | smallest useful VLM |
| `lfm-450m` *(default)* | LFM2.5-VL-450M | ~0.4GB | ~1.2GB | [Liquid](https://huggingface.co/LiquidAI/LFM2.5-VL-450M-GGUF) | ✅ tested, fastest startup |
| `fast` | Qwen3.5-0.8B | ~0.7GB | ~1.8GB | Apache-2.0 | natively multimodal (image + video) |
| `ocr` | GLM-OCR | ~1.4GB | ~3.5GB | MIT | dense text / document champion (3M+ downloads/mo) |
| `strong` | Qwen3.5-4B | ~3GB | ~6GB | Apache-2.0 | best small vision model right now |
| `xstrong` | Qwen3-VL-8B | ~5.5GB | ~10GB | Apache-2.0 | serious understanding (GPU advised) |

Hidden extras (still one command): `smol500` (SmolVLM2-500M), `paddle` (PaddleOCR-VL-1.6), `qwen3-2b` (Qwen3-VL-2B).

**Any other GGUF works too** — point the env at it and skip presets entirely:

```bash
EYES_MODEL_DIR=~/models/my-vlm  VLM_MODEL_FILE=model-Q4.gguf  VLM_MMPROJ_FILE=mmproj.gguf
```

Good candidates not shipped as presets: LFM2.5-VL-1.6B/3B, InternVL3.5-2B/4B, MiniCPM-V-4.6, DeepSeek-OCR, dots.ocr, gemma-3n-E2B, moondream2 — anything llama.cpp supports with an mmproj file.

Switch anytime: set `EYES_PRESET` and run `./scripts/download_models.sh` again. Not sure which? `python3 scripts/choose_model.py` shows your RAM/GPU and marks a recommendation.

## How it works

```
Claude Code / Codex / Cursor
      │ MCP stdio
      ▼
eyes-mcp  (stateless, mcp SDK 2.x)
   ├─ analyze_image → llama.cpp llama-server (local VLM)  "understand"
   └─ ocr_image     → RapidOCR (onnx, ~20MB)             "extract text"
```

- **Lifecycle follows your agent**: the VLM server spawns when the MCP starts and is cleaned up when your agent exits. No orphan processes, no daemon to babysit.
- **Floating port**: the VLM never binds a fixed port (goodbye, "8080 already in use"), so it coexists with your other local services.
- **Reuses an external VLM** if you already run one at `VLM_BASE_URL`.

## Why

The cheapest and best coding models right now — DeepSeek-V4-Flash, GLM-5.x, Qwen-Coder — are **text-only**. Every harness assumes you can paste a screenshot; every cheap model silently fails at it. eyes-mcp is the missing sidecar: a tiny local VLM + OCR, wrapped in the lifecycle your agent already understands.

## Roadmap

- [ ] Lazy VLM start (spawn on first tool call, not MCP start)
- [ ] `screenshot_analyze` (grab the screen, no file needed)
- [ ] PDF pages → vision
- [ ] `npx eyes-mcp` one-liner installer
- [ ] Per-model prompt templates (llama.cpp OCR models need specific prompts)

## FAQ

**Does my agent model matter?** Only in that it must be *text-only* for this to be useful. Multimodal models (GPT, Claude, GLM-*V*) already see images — don't bother.

**GPU needed?** No. Runs fine on CPU; Apple Metal is used automatically when available.

**Where are models stored?** `~/.eyes-mcp/models/<preset>/`. Delete them to reset.

## License

MIT. Model weights keep their own licenses (see preset table); they're downloaded at install time, never redistributed here.

---

<div align="center">
<sub>Built for everyone running great models that can't see.</sub>
</div>
