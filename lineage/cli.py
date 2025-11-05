from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

import yaml

from .analyzer import RepoContext, scan_paths, write_lineage, write_lineage_csv
from .extractor.patterns import load_patterns_from_specs


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
    config_payload: Dict[str, Any] = {}
    config_path: Optional[Path] = None
    if args.config:
        config_path = Path(args.config)
        common_config, label_overrides, config_payload = _load_scan_config(config_path)

    template_variables: Dict[str, str] = {}
    if isinstance(config_payload.get("template_variables"), dict):
        template_variables = {
            str(key): str(value) for key, value in config_payload["template_variables"].items()
        }

    pattern_specs: List[Dict[str, Any]] = []

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

        # Determine pattern specifications
        if args.patterns:
            pattern_specs.extend(_load_patterns_file(Path(args.patterns)))
        elif isinstance(config_payload.get("patterns"), list):
            pattern_specs.extend(config_payload.get("patterns"))
        else:
            pattern_path: Optional[Path] = None
            specified = config_payload.get("patterns_file")
            if specified:
                pattern_path = Path(specified)
            elif config_path is not None:
                candidate = config_path.parent / "patterns.yaml"
                if candidate.exists():
                    pattern_path = candidate
            if pattern_path is not None:
                if config_path is not None and not pattern_path.is_absolute():
                    pattern_path = (config_path.parent / pattern_path).resolve()
                pattern_specs.extend(_load_patterns_file(pattern_path))

        patterns = load_patterns_from_specs(pattern_specs)

        edges = scan_paths(
            target_paths,
            common_config=common_config,
            infer=args.infer,
            repo_contexts=repo_context_map,
            patterns=patterns,
            template_variables=template_variables,
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
        help="Path to YAML configuration file with 'common_config', 'label_overrides', etc.",
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
    scan_parser.add_argument(
        "--patterns",
        help="Optional YAML file describing additional SQL execution patterns",
    )
    return parser


def _load_scan_config(config_path: Path) -> Tuple[Dict[str, Any], Dict[str, str], Dict[str, Any]]:
    text = config_path.read_text(encoding="utf-8")
    payload: Dict[str, Any]
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse YAML config '{config_path}': {exc}") from exc
    if loaded is None:
        payload = {}
    elif isinstance(loaded, dict):
        payload = loaded
    else:
        raise ValueError("Configuration must be a mapping")

    common_config: Dict[str, Any] = {}
    label_overrides: Dict[str, str] = {}

    if "common_config" in payload and isinstance(payload["common_config"], dict):
        common_config = payload["common_config"]
    else:
        residual = {
            key: value
            for key, value in payload.items()
            if key not in {"label_overrides", "output_labels", "patterns", "patterns_file"}
        }
        if residual:
            common_config = residual

    raw_overrides = payload.get("label_overrides") or payload.get("output_labels")
    if isinstance(raw_overrides, dict):
        label_overrides = {str(key): str(value) for key, value in raw_overrides.items()}

    normalized_common = {key: str(value) for key, value in common_config.items()}
    return normalized_common, label_overrides, payload


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


def _load_patterns_file(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Pattern file not found: {path}")
    text = path.read_text(encoding="utf-8")
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse patterns file '{path}': {exc}") from exc

    if isinstance(loaded, dict) and isinstance(loaded.get("patterns"), list):
        return loaded["patterns"]  # type: ignore[return-value]
    if isinstance(loaded, list):
        return loaded  # type: ignore[return-value]
    raise ValueError("Patterns file must contain either a list or a mapping with a 'patterns' list")


__all__ = ["main"]
