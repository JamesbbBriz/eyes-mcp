#!/usr/bin/env python3
"""Pick an eyes-mcp model preset based on this machine's resources.

Detects total RAM and accelerator (Apple Silicon / CUDA / CPU-only), prints a
preset table with a recommendation, and interactively lets you choose.

Usage:
  python3 scripts/choose_model.py            # interactive (numbered menu)
  python3 scripts/choose_model.py --auto     # no prompts, take the recommendation
  python3 scripts/choose_model.py --print-only  # show table + recommendation, exit
Output: last line is "CHOSEN:<preset>" for shell capture.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys

# disk = download size; ram = comfortable total footprint (model + KV cache),
# deliberately conservative so the model coexists with your agent harness.
PRESETS: dict[str, dict] = {
    "nano":     {"model": "SmolVLM2-256M",     "disk": "~0.3GB", "ram_gb": 1.0,
                 "license": "Apache-2.0", "note": "smallest useful VLM"},
    "lfm-450m": {"model": "LFM2.5-VL-450M",    "disk": "~0.4GB", "ram_gb": 1.2,
                 "license": "Liquid",     "note": "tested default, fastest startup"},
    "fast":     {"model": "Qwen3.5-0.8B",      "disk": "~0.7GB", "ram_gb": 1.8,
                 "license": "Apache-2.0", "note": "natively multimodal (image+video)"},
    "ocr":      {"model": "GLM-OCR",           "disk": "~1.4GB", "ram_gb": 3.5,
                 "license": "MIT",        "note": "dense text / document champion"},
    "strong":   {"model": "Qwen3.5-4B",        "disk": "~3GB",   "ram_gb": 6.0,
                 "license": "Apache-2.0", "note": "best small vision model"},
    "xstrong":  {"model": "Qwen3-VL-8B",       "disk": "~5.5GB", "ram_gb": 10.0,
                 "license": "Apache-2.0", "note": "serious understanding (GPU advised)"},
}
ORDER = ["nano", "lfm-450m", "fast", "ocr", "strong", "xstrong"]


def total_ram_gb() -> float | None:
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["sysctl", "-n", "hw.memsize"],
                                 capture_output=True, text=True, timeout=5).stdout
            return int(out.strip()) / 1024**3
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    return int(line.split()[1]) / 1024**2
    except Exception:
        pass
    return None


def accelerator() -> str:
    try:
        if sys.platform == "darwin":
            brand = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"],
                                   capture_output=True, text=True, timeout=5).stdout
            return "apple-silicon" if brand.strip().startswith("Apple") else "cpu"
    except Exception:
        pass
    if shutil.which("nvidia-smi"):
        try:
            out = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                 capture_output=True, text=True, timeout=5).stdout
            if out.strip():
                return "cuda"
        except Exception:
            pass
    return "cpu"


def recommend(ram: float | None, accel: str) -> str:
    if ram is None:
        return "lfm-450m"
    gpu = accel in ("apple-silicon", "cuda")
    if gpu and ram >= 32:
        return "xstrong"
    if ram >= 16:
        return "strong"
    if ram >= 8:
        return "fast"
    if ram >= 6:
        return "lfm-450m"
    return "nano"


def render(ram: float | None, accel: str, rec: str) -> None:
    ram_s = f"{ram:.0f}GB" if ram else "?"
    print(f"machine: {ram_s} RAM · {accel}")
    print()
    print(f"  #  preset      model                download  RAM   license     note")
    print(f"  {'-'*88}")
    for i, name in enumerate(ORDER, 1):
        p = PRESETS[name]
        mark = "← recommended" if name == rec else ""
        print(f"  {i}.  {name:<10}  {p['model']:<20} {p['disk']:>7}  "
              f"~{p['ram_gb']:.1f}G  {p['license']:<10} {p['note']} {mark}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--auto", action="store_true", help="no prompts, take the recommendation")
    ap.add_argument("--print-only", action="store_true", help="show table, exit 0 (no choice)")
    args = ap.parse_args()

    ram, accel = total_ram_gb(), accelerator()
    rec = recommend(ram, accel)
    render(ram, accel, rec)

    if args.print_only:
        return
    if args.auto or not sys.stdin.isatty():
        print(f"\nrecommendation: {rec}")
        print(f"CHOSEN:{rec}")
        return

    default_i = ORDER.index(rec) + 1
    while True:
        try:
            reply = input(f"\nchoose preset [1-{len(ORDER)}, Enter={default_i}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            sys.exit(1)
        if not reply:
            choice = rec
            break
        if reply.isdigit() and 1 <= int(reply) <= len(ORDER):
            choice = ORDER[int(reply) - 1]
            break
        print("invalid choice")
    print(f"CHOSEN:{choice}")


if __name__ == "__main__":
    main()
