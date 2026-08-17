<div align="center">

# 👀 eyes-mcp

**给纯文本 LLM 装上眼睛 —— 本地视觉 + OCR，一个命令，零 API key**

[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](./LICENSE)
[![English](https://img.shields.io/badge/docs-English-blue)](./README.md)

*DeepSeek、GLM、Qwen-Coder、Llama…… 好模型，全是瞎子。*

</div>

---

## ❌ 没有眼睛

往 agent（跑纯文本模型）里贴截图：

```
> UI 报错了，帮我修  [screenshot.png]

抱歉，我无法查看图片，请用文字描述错误。
```

## ✅ 有了眼睛

Agent 调用**本地** VLM + OCR，自己把截图读了：

```
> UI 报错了，帮我修  [screenshot.png]

我看到 CartDrawer.tsx:142 处的 React hydration 报错，OCR 结果：
"Hydration failed because the server rendered HTML didn't match the client." …
```

## 快速开始

```bash
git clone https://github.com/JamesbbBriz/eyes-mcp
cd eyes-mcp && ./scripts/install.sh
```

就这一条。安装器会：

1. 问你**要哪档模型**——按你的内存和 GPU 自动给推荐（设置 `EYES_PRESET` 或 `--yes` 可跳过）
2. 装依赖 + 下载模型（~0.4–2GB，支持断点续传）
3. **检测你的 agent 是不是纯文本模型**（读取 Claude Code / Codex / Cursor 的配置，对模型做模态数据库比对）
4. **只在需要的地方注册** eyes-mcp——多模态模型的 agent 自动跳过

```bash
# 可选项：
EYES_PRESET=fast ./scripts/install.sh            # Apache-2.0 SmolVLM2-500M
HF_ENDPOINT=https://hf-mirror.com ./install.sh  # 国内镜像
./install.sh --yes                              # 全部接受推荐，无交互
./install.sh --dry-run                          # 预览，不改动
```

只想查模态？`python3 scripts/detect_modality.py`

依赖：Python ≥3.11、[llama.cpp](https://github.com/ggml-org/llama.cpp)（`brew install llama.cpp`）、约 1GB 内存。

## 手动注册

**Claude Code**（`~/.claude.json` → `mcpServers`）：

```json
"eyes-mcp": {
  "command": "uv",
  "args": ["--directory", "/绝对路径/eyes-mcp", "run", "eyes-mcp"],
  "env": { "EYES_PRESET": "lfm-450m" }
}
```

**Codex**（`~/.codex/config.toml`）：

```toml
[mcp_servers.eyes-mcp]
command = "uv"
args = ["--directory", "/绝对路径/eyes-mcp", "run", "eyes-mcp"]
env = { EYES_PRESET = "lfm-450m" }
```

## 工具

| 工具 | 引擎 | 用途 |
|---|---|---|
| `analyze_image(path, question?)` | llama.cpp VLM | 看图理解、UI 分析、视觉问答 |
| `ocr_image(path)` | RapidOCR（onnx） | 密集文字：终端、文档、表格 —— 快而准 |

## 模型档位

| 档位 | 模型 | 大小 | 内存 | 许可证 |
|---|---|---|---|---|
| `lfm-450m`（默认） | LFM2.5-VL-450M | ~400MB | ~1GB | Liquid 开放许可 |
| `nano` | SmolVLM2-256M | ~300MB | <1GB | Apache-2.0 |
| `fast` | SmolVLM2-500M | ~600MB | ~1GB | Apache-2.0 |
| `ocr` | PaddleOCR-VL 0.9B | ~1GB | ~2GB | Apache-2.0 |
| `strong` | Qwen3-VL-2B | ~2GB | ~4GB | Apache-2.0 |

随时换档：设置 `EYES_PRESET` 再跑 `./scripts/download_models.sh`。不知道选哪个？`python3 scripts/choose_model.py` 会显示内存/GPU 并标出推荐。

## 原理

```
Claude Code / Codex / Cursor
      │ MCP stdio
      ▼
eyes-mcp（无状态，mcp SDK 2.x）
   ├─ analyze_image → llama.cpp llama-server（本地 VLM）
   └─ ocr_image     → RapidOCR（onnx，~20MB）
```

- **随 agent 启停**：MCP 启动时拉起 VLM，agent 退出时自动清理，无孤儿进程
- **浮动端口**：永不占用固定端口（8080 冲突再见），与本地其他服务共存
- 已有外部 VLM 在 `VLM_BASE_URL` 跑着时自动复用

## 为什么做

当前性价比最高的编码模型——DeepSeek-V4-Flash、GLM-5.x、Qwen-Coder——全是纯文本。所有 harness 都默认你能贴截图，所有廉价模型都在这一步静默失败。eyes-mcp 就是补上的那块：本地小 VLM + OCR，包在你 agent 已经理解的 MCP 生命周期里。

## 许可证

MIT。模型权重各自保留其许可证（安装时下载，本仓库不分发）。
