from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .analyzer import scan_paths, write_lineage


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command != "scan":
        parser.print_help()
        return

    target_strings = []
    if args.path:
        target_strings.append(args.path)
    if args.file:
        target_strings.extend(args.file)
    if not target_strings:
        parser.error("provide either a project path or at least one --file")

    target_paths = [Path(item) for item in target_strings]
    common_config = _load_common_config(args.config) if args.config else {}
    edges = scan_paths(target_paths, common_config=common_config, infer=args.infer)
    output_path = Path(args.output)
    write_lineage(edges, output_path)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lineage")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan Python files for SQL lineage")
    scan_parser.add_argument(
        "path",
        nargs="?",
        help="Directory to recursively scan for Python files",
    )
    scan_parser.add_argument(
        "--file",
        action="append",
        default=[],
        help="Specific Python file to scan (can be provided multiple times)",
    )
    scan_parser.add_argument(
        "--config",
        help="Path to JSON configuration file containing a 'common_config' mapping",
    )
    scan_parser.add_argument(
        "--output", default="lineage.json", help="Destination JSON file for lineage results"
    )
    scan_parser.add_argument(
        "--infer", action="store_true", help="Infer multi-hop lineage through volatile tables"
    )
    return parser


def _load_common_config(config_path: str) -> Dict[str, Any]:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "common_config" in payload:
        candidate = payload["common_config"]
        if isinstance(candidate, dict):
            return candidate
    if isinstance(payload, dict):
        return payload
    raise ValueError("Configuration file must contain a JSON object")


__all__ = ["main"]
