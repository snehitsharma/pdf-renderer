#!/usr/bin/env python3
import argparse
import copy
import os
import sys

# Ensure the package folder is in sys.path when running cli.py directly
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from config import CONFIG
from parser import load_content
from renderer import render


def main():
    ap = argparse.ArgumentParser(description="Deterministic resume PDF renderer")
    ap.add_argument("content", help="path to content file (.txt, .json or .yaml)")
    ap.add_argument("-o", "--out", default="resume.pdf")
    ap.add_argument("--no-fit", action="store_true", help="disable auto-fit")
    ap.add_argument("--pages", type=int, default=1, help="target page count")
    ap.add_argument("--size", choices=["A4", "LETTER"], default=None)
    ap.add_argument("--accent", default=None, help="accent hex, e.g. #1F4E79")
    ap.add_argument("--fill", action="store_true",
                    help="expand spacing to balance a short resume on the page")
    args = ap.parse_args()

    data = load_content(args.content)

    cfg = copy.deepcopy(CONFIG)
    if args.no_fit:
        cfg["autofit"]["enabled"] = False
    cfg["autofit"]["target_pages"] = args.pages
    if args.size:
        cfg["page"]["size"] = args.size
    if args.accent:
        cfg["accent"] = args.accent
    if args.fill:
        cfg["autofit"]["fill_enabled"] = True

    render(data, cfg, args.out)


if __name__ == "__main__":
    main()
