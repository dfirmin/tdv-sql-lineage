from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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
    common_config: Dict[str, Any] = {}
    label_overrides: Dict[str, str] = {}
    if args.config:
        common_config, label_overrides = _load_scan_config(args.config)

    edges = scan_paths(target_paths, common_config=common_config, infer=args.infer)
    output_path = Path(args.output)
    write_lineage(edges, output_path, label_overrides=label_overrides)


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


def _load_scan_config(config_path: str) -> Tuple[Dict[str, Any], Dict[str, str]]:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    common_config: Dict[str, Any] = {}
    label_overrides: Dict[str, str] = {}

    if not isinstance(payload, dict):
        raise ValueError("Configuration file must contain a JSON object")

    if "common_config" in payload:
        candidate = payload["common_config"]
        if isinstance(candidate, dict):
            common_config = candidate
    else:
        residual = {
            key: value
            for key, value in payload.items()
            if key not in {"label_overrides", "output_labels"}
        }
        common_config = residual

    raw_overrides = payload.get("label_overrides") or payload.get("output_labels")
    if isinstance(raw_overrides, dict):
        label_overrides = {str(key): str(value) for key, value in raw_overrides.items()}

    normalized_common = {key: str(value) for key, value in common_config.items()}
    return normalized_common, label_overrides


__all__ = ["main"]
