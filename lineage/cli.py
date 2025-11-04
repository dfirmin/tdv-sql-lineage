from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

from .analyzer import RepoContext, scan_paths, write_lineage, write_lineage_csv


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
    if not target_strings and not args.repo:
        parser.error("provide either a project path or at least one --file")

    target_paths = [Path(item) for item in target_strings]
    repo_context_map: Dict[Path, RepoContext] = {}
    common_config: Dict[str, Any] = {}
    label_overrides: Dict[str, str] = {}
    if args.config:
        common_config, label_overrides = _load_scan_config(args.config)

    repo_tempdir: Optional[tempfile.TemporaryDirectory] = None
    try:
        if args.repo:
            repo_tempdir = tempfile.TemporaryDirectory()
            (
                repo_paths,
                repo_base_url,
                repo_root,
                _repo_subpath,
            ) = _materialize_repo(
                args.repo,
                destination=Path(repo_tempdir.name),
                ref_override=args.ref,
                subpath_override=args.repo_subpath,
            )
            target_paths.extend(repo_paths)
            effective_ref = args.ref
            if effective_ref is None:
                _, parsed_ref, _ = _parse_repo_arg(args.repo)
                effective_ref = parsed_ref
            repo_context = RepoContext(
                base_url=repo_base_url,
                ref=effective_ref,
                root=repo_root,
            )
            for repo_path in repo_paths:
                repo_context_map[repo_path] = repo_context
                try:
                    repo_context_map[repo_path.resolve()] = repo_context
                except OSError:
                    pass

        if not target_paths:
            parser.error("provide a local path/--file or specify --repo")

        edges = scan_paths(
            target_paths,
            common_config=common_config,
            infer=args.infer,
            repo_contexts=repo_context_map,
        )
        output_path = Path(args.output)
        write_lineage(edges, output_path, label_overrides=label_overrides)
        if args.csv_output:
            csv_path = Path(args.csv_output)
            write_lineage_csv(edges, csv_path, label_overrides=label_overrides)
    finally:
        if repo_tempdir is not None:
            repo_tempdir.cleanup()


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
    scan_parser.add_argument(
        "--csv-output",
        help="Optional CSV file to generate alongside JSON output",
    )
    scan_parser.add_argument(
        "--repo",
        help="Remote Git repository to scan (HTTPS URL). Supports GitHub '.../tree/<ref>/<path>' URLs.",
    )
    scan_parser.add_argument(
        "--ref",
        help="Repository ref (branch, tag, or commit) to checkout when using --repo. Overrides refs embedded in the URL.",
    )
    scan_parser.add_argument(
        "--repo-subpath",
        help="Optional subdirectory inside the cloned repository to scan (e.g. 'test').",
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


def _materialize_repo(
    repo_arg: str,
    *,
    destination: Path,
    ref_override: Optional[str],
    subpath_override: Optional[str],
) -> Tuple[List[Path], str, Path, Optional[str]]:
    repo_url, parsed_ref, parsed_subpath = _parse_repo_arg(repo_arg)
    effective_ref = ref_override or parsed_ref
    effective_subpath = subpath_override or parsed_subpath

    clone_dir = destination / "repo"
    clone_cmd = ["git", "clone", "--depth", "1"]
    if effective_ref:
        clone_cmd.extend(["--branch", effective_ref])
    clone_cmd.extend([repo_url, str(clone_dir)])

    result = subprocess.run(
        clone_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git clone failed (exit code {result.returncode}):\n{result.stderr.strip()}"
        )

    target = clone_dir / effective_subpath if effective_subpath else clone_dir
    if not target.exists():
        raise ValueError(
            f"Subpath '{effective_subpath}' not found in cloned repository" if effective_subpath else "Cloned repository path does not exist"
        )
    return [target], repo_url, clone_dir, effective_subpath


# Match GitHub.com and GitHub Enterprise hosts.
TREE_PATTERN = re.compile(
    r"^(https://[^/]+/[^/]+/[^/]+)(?:/tree/([^/]+)(?:/(.*))?)?$"
)
BLOB_PATTERN = re.compile(
    r"^(https://[^/]+/[^/]+/[^/]+)/blob/([^/]+)/(.*)$"
)


def _parse_repo_arg(repo_arg: str) -> Tuple[str, Optional[str], Optional[str]]:
    tree_match = TREE_PATTERN.match(repo_arg)
    if tree_match:
        base_url, ref, subpath = tree_match.groups()
        return base_url, ref, subpath
    blob_match = BLOB_PATTERN.match(repo_arg)
    if blob_match:
        base_url, ref, subpath = blob_match.groups()
        return base_url, ref, subpath
    return repo_arg, None, None


__all__ = ["main"]
