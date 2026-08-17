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
cd eyes-mcp && ./scripts/install.sh          # deps + model (auto-download, ~400MB)

# pick a different model tier:
EYES_PRESET=fast ./scripts/install.sh        # Apache-2.0 SmolVLM2-500M
EYES_PRESET=ocr  ./scripts/install.sh        # PaddleOCR-VL, dense-text champion
# mainland China: HF_ENDPOINT=https://hf-mirror.com ./scripts/install.sh
```

Requires: Python ≥3.11, [`llama.cpp`](https://github.com/ggml-org/llama.cpp) (`brew install llama.cpp`), ~1GB RAM.

## Register with your agent

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

| Preset | Model | Size | RAM | License | Notes |
|---|---|---|---|---|---|
| `lfm-450m` *(default)* | LFM2.5-VL-450M | ~400MB | ~1GB | [Liquid open license](https://huggingface.co/LiquidAI/LFM2.5-VL-450M-GGUF) | ✅ tested default, fastest startup |
| `nano` | SmolVLM2-256M | ~300MB | <1GB | Apache-2.0 | smallest useful VLM |
| `fast` | SmolVLM2-500M | ~600MB | ~1GB | Apache-2.0 | general vision + video |
| `ocr` | PaddleOCR-VL 0.9B | ~1GB | ~2GB | Apache-2.0 | #1 sub-1B OCR model |
| `strong` | Qwen3-VL-2B | ~2GB | ~4GB | Apache-2.0 | real visual understanding |

Switch anytime: set `EYES_PRESET` and run `./scripts/download_models.sh` again.

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
