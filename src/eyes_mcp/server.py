"""eyes-mcp — local vision + OCR for text-only LLM agents (stateless MCP, mcp SDK 2.x).

Two MCP tools:
  - analyze_image: send an image to a llama.cpp VLM server (OpenAI-compatible /v1) for description/QA.
  - ocr_image:     extract text from an image with RapidOCR (onnx, fully local).

Text-only models are everywhere — DeepSeek, GLM, Qwen-Coder, Llama — and none of
them can see the screenshot you just pasted. eyes-mcp gives them eyes: a tiny
local VLM describes the image, RapidOCR pulls the text, and your agent reads
the answer as plain text. Nothing leaves your machine.

The llama.cpp VLM server is managed here, tied to the agent harness lifecycle:
when this MCP server starts (harness launches it via stdio) it ensures the VLM
server is running on a floating port (never a fixed 8080 — that port is always
taken by something); when this MCP server exits (harness closes / SIGTERM /
stdio EOF) the VLM server it spawned is cleaned up. No orphan processes.

Config via env (all optional):
  EYES_PRESET    model preset: lfm-450m (default) | nano | fast | ocr | strong
  VLM_BASE_URL   fallback endpoint — used only when an external VLM already runs there
  VLM_MODEL      model name to send in payloads (default: local-vlm, the --alias)
  VLM_MAX_DIM    images are downscaled to this longest edge before the VLM (default 1024)
  VLM_START_CMD  override to manage the VLM entirely externally
"""

from __future__ import annotations

import atexit
import base64
import io
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer

REPO_DIR = Path(__file__).resolve().parent.parent.parent
EYES_HOME = Path(os.environ.get("EYES_HOME", str(Path.home() / ".eyes-mcp"))).expanduser()
VLM_MODEL = os.environ.get("VLM_MODEL", "local-vlm")
VLM_MAX_DIM = int(os.environ.get("VLM_MAX_DIM", "1024"))
# Base URL is mutable: when we spawn the VLM ourselves it floats to a free port
# (never the fixed 8080, which Vespa/other local services occupy), so it
# cannot be fixed at import time. The env var is the fallback URL — used only
# when an external VLM server is already running there.
_vlm_base_url = os.environ.get("VLM_BASE_URL", "http://127.0.0.1:8080/v1")
VLM_START_CMD = os.environ.get(
    "VLM_START_CMD", str(REPO_DIR / "scripts" / "start_vlm_server.sh")
)
VLM_LOG = EYES_HOME / "logs" / "llama-server.log"
DEFAULT_QUESTION = (
    "Describe this image concisely (answer in the user's language), "
    "including any text, UI elements, and layout."
)

server = MCPServer(name="eyes-mcp", version="0.1.0")

_ocr_engine = None
_llama_proc: subprocess.Popen | None = None


# ---------------------------------------------------------------------------
# VLM server lifecycle (tied to harness)
# ---------------------------------------------------------------------------

def _vlm_health_url() -> str:
    return _vlm_base_url.rstrip("/") + "/health"


def _vlm_healthy() -> bool:
    try:
        return httpx.get(_vlm_health_url(), timeout=1).status_code == 200
    except httpx.HTTPError:
        return False


def _find_free_port() -> int:
    """Return a currently-free TCP port on loopback.

    Tiny TOCTOU window between close and the VLM binding it; acceptable for a
    single-user local tool, and we retry on a fresh port if it ever loses the race.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _ensure_vlm_server() -> None:
    """Spawn the llama.cpp VLM server if it is not already reachable.

    The VLM binds a floating port: we pre-pick a free one and pass it via VLM_PORT,
    so it never collides with other local services that sit on the default 8080.
    """
    global _llama_proc, _vlm_base_url
    if _vlm_healthy():
        return  # already running (e.g. started externally); don't own it

    VLM_LOG.parent.mkdir(parents=True, exist_ok=True)
    log = open(VLM_LOG, "ab")
    for attempt in range(3):
        port = _find_free_port()
        _vlm_base_url = f"http://127.0.0.1:{port}/v1"
        env = dict(os.environ)
        env["VLM_PORT"] = str(port)
        env["VLM_BASE_URL"] = _vlm_base_url
        _llama_proc = subprocess.Popen([VLM_START_CMD], stdout=log, stderr=log, env=env)
        for _ in range(60):
            if _vlm_healthy():
                return
            if _llama_proc.poll() is not None:
                if attempt < 2:
                    break  # port raced away; retry on a fresh one
                raise RuntimeError(
                    f"llama-server exited during startup (code {_llama_proc.returncode}); "
                    f"see {VLM_LOG}"
                )
            time.sleep(1)
    raise RuntimeError(f"llama-server did not become healthy (last try: {_vlm_base_url})")


def _cleanup_vlm_server() -> None:
    """Terminate the VLM server only if we spawned it (never one started externally)."""
    global _llama_proc
    proc, _llama_proc = _llama_proc, None
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


atexit.register(_cleanup_vlm_server)


def _on_signal(signum: int, _frame) -> None:
    _cleanup_vlm_server()
    sys.exit(128 + signum)


signal.signal(signal.SIGTERM, _on_signal)
signal.signal(signal.SIGINT, _on_signal)


# ---------------------------------------------------------------------------
# OCR engine
# ---------------------------------------------------------------------------

def _get_ocr_engine():
    """Lazily init the RapidOCR engine (model files download on first run, ~20MB)."""
    global _ocr_engine
    if _ocr_engine is None:
        from rapidocr import RapidOCR

        _ocr_engine = RapidOCR()
    return _ocr_engine


# ---------------------------------------------------------------------------
# Tool helpers
# ---------------------------------------------------------------------------

def _load_downscaled_image_b64(image_path: str, max_dim: int) -> bytes:
    from PIL import Image

    with Image.open(image_path) as img:
        img.thumbnail((max_dim, max_dim))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()


def _vlm_complete(text: str, image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "model": VLM_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 512,
    }
    with httpx.Client(base_url=_vlm_base_url, timeout=180) as client:
        resp = client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"unexpected VLM response: {data}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

@server.tool()
def analyze_image(image_path: str, question: str = "") -> str:
    """Look at an image and answer a question about it using a local VLM (llama.cpp server).

    For text-only LLMs that cannot see images.

    Args:
        image_path: path to a local image file.
        question: optional question about the image. Defaults to a general description.
    """
    text = question.strip() or DEFAULT_QUESTION
    img_bytes = _load_downscaled_image_b64(image_path, VLM_MAX_DIM)
    try:
        return _vlm_complete(text, img_bytes)
    except httpx.HTTPError as e:
        raise RuntimeError(
            f"VLM server unreachable at {_vlm_base_url}: {e}. "
            "Ensure scripts/start_vlm_server.sh is runnable."
        ) from e


@server.tool()
def ocr_image(image_path: str) -> str:
    """Extract text from an image using local RapidOCR (onnx, no network).

    Faster and more accurate on dense text than the VLM; use for screenshots of documents/terminals.

    Args:
        image_path: path to a local image file.
    """
    engine = _get_ocr_engine()
    out = engine(image_path)
    texts = getattr(out, "txts", None)
    if not texts:
        return "(no text detected)"
    return "\n".join(texts)


def main() -> None:
    _ensure_vlm_server()
    server.run()


if __name__ == "__main__":
    main()
