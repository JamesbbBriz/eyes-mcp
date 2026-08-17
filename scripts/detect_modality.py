#!/usr/bin/env python3
"""Detect whether an agent's model is text-only (needs eyes-mcp) or multimodal.

Resolution order per model:
  1. OpenRouter public model list (architecture.input_modalities) — best effort, 4s timeout
  2. Static rules (offline fallback)
  3. unknown → assume text-only (enabling eyes-mcp is harmless either way)

Usage:
  python3 scripts/detect_modality.py            # human table
  python3 scripts/detect_modality.py --json     # machine readable
  python3 scripts/detect_modality.py --shell    # "agent|verdict|model" lines for scripts
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

HOME = Path.home()

# Checked FIRST — multimodal families (lowercased regex on the model id)
MULTIMODAL_PATTERNS = [
    r"-vl([-\s_]|$)",     # qwen3-vl, glm-4.6v is handled below, internvl separately
    r"glm-[0-9.]*v",      # glm-5v-turbo, glm-4.6v
    r"vision",            # *-vision, vision-*
    r"gpt-4o", r"gpt-4\.1", r"gpt-5", r"^o[34]\b",
    r"claude", r"gemini", r"^grok", r"pixtral", r"internvl", r"llava",
    r"smolvlm", r"minicpm-v", r"gemma-[34]", r"medgemma", r"deepseek-ocr",
]
# Checked SECOND — known text-only families (lowercased prefix)
TEXT_ONLY_PREFIXES = [
    "deepseek", "glm-", "qwen", "llama", "mistral", "kimi", "minimax",
    "yi-", "doubao", "ernie", "command-r",
]

VERDICTS = {
    "text-only":  "needs eyes      ← enable eyes-mcp",
    "multimodal": "sees natively   ← eyes redundant, skip",
    "unknown":    "unknown         ← assume text-only (harmless to enable)",
}


def normalize(model: str) -> str:
    m = model.strip().lower()
    m = re.sub(r"\[[^\]]*\]$", "", m)  # strip [1m] style suffixes
    return m


def openrouter_lookup(model: str, index: dict | None) -> str | None:
    if index is None:
        return None
    m = normalize(model)
    entry = index.get(m)
    if entry is None:
        return None
    return "multimodal" if "image" in entry else "text-only"


def static_lookup(model: str) -> str | None:
    m = normalize(model)
    for p in MULTIMODAL_PATTERNS:
        if re.search(p, m):
            return "multimodal"
    for p in TEXT_ONLY_PREFIXES:
        if m.startswith(p) or ("/" + p) in m:
            return "text-only"
    return None


def load_openrouter_index() -> dict | None:
    try:
        with urllib.request.urlopen(
            "https://openrouter.ai/api/v1/models", timeout=4
        ) as r:
            data = json.load(r)["data"]
        return {
            entry["id"].lower(): entry.get("architecture", {}).get("input_modalities", [])
            for entry in data
        }
    except Exception:
        return None


def claude_model() -> str | None:
    p = HOME / ".claude" / "settings.json"
    if not p.exists():
        return None
    try:
        env = json.load(open(p)).get("env", {})
        for key in (
            "ANTHROPIC_MODEL",
            "ANTHROPIC_DEFAULT_OPUS_MODEL",
            "ANTHROPIC_DEFAULT_SONNET_MODEL",
            "ANTHROPIC_DEFAULT_HAIKU_MODEL",
        ):
            if env.get(key):
                return env[key]
    except Exception:
        pass
    return None


def codex_model() -> str | None:
    p = HOME / ".codex" / "config.toml"
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        m = re.match(r'\s*model\s*=\s*"([^"]+)"', line)
        if m:
            return m.group(1)
    return None


def detect_agents() -> list[dict]:
    or_index = load_openrouter_index()
    agents = []
    specs = [
        ("claude-code", (HOME / ".claude").is_dir() or (HOME / ".claude.json").exists(), claude_model),
        ("codex", (HOME / ".codex" / "config.toml").exists(), codex_model),
        ("cursor", (HOME / ".cursor").is_dir()
         or (HOME / "Library/Application Support/Cursor").exists(), lambda: None),
    ]
    for name, installed, get_model in specs:
        if not installed:
            continue
        model = get_model()
        if not model:
            verdict = "unknown"
        else:
            verdict = (
                openrouter_lookup(model, or_index)
                or static_lookup(model)
                or "unknown"
            )
        agents.append({"agent": name, "installed": True, "model": model, "verdict": verdict})
    return agents


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--shell", action="store_true", help='"agent|verdict|model" lines')
    args = ap.parse_args()

    agents = detect_agents()
    if not agents:
        print("no agents detected", file=sys.stderr)

    if args.json:
        print(json.dumps(agents, indent=2))
        return
    if args.shell:
        for a in agents:
            print(f"{a['agent']}|{a['verdict']}|{a['model'] or ''}")
        return

    width = max(len(a["agent"]) for a in agents) if agents else 8
    print(f"{'agent':<{width}}  {'model':<40}  verdict")
    print("-" * (width + 70))
    for a in agents:
        print(f"{a['agent']:<{width}}  {(a['model'] or '(not found)'):<40}  {VERDICTS[a['verdict']]}")


if __name__ == "__main__":
    main()
