from __future__ import annotations

import json
from dataclasses import dataclass
import csv
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .extractor.ast_extractor import extract_statements_from_file
from .extractor.patterns import CallPattern, DEFAULT_PATTERNS
from .parser.sql_parser import LineageEdge, parse_sql_lineage


@dataclass(frozen=True)
class RepoContext:
    base_url: str
    ref: Optional[str]
    root: Path

    def file_url(self, file_path: Path) -> Optional[str]:
        try:
            relative = file_path.relative_to(self.root)
        except ValueError:
            return None
        ref = self.ref or "HEAD"
        return f"{self.base_url}/blob/{ref}/{relative.as_posix()}"


def scan_paths(
    paths: Sequence[Path],
    *,
    common_config: Optional[Dict[str, object]] = None,
    infer: bool = False,
    repo_contexts: Optional[Dict[Path, RepoContext]] = None,
    patterns: Optional[Sequence[CallPattern]] = None,
) -> List[LineageEdge]:
    """Scan *paths* (files or directories) and return lineage edges."""

    normalized_config = {key: str(value) for key, value in (common_config or {}).items()}

    edges: List[LineageEdge] = []
    context_map = repo_contexts or {}
    resolved_map: Dict[Path, RepoContext] = {}
    for key, value in context_map.items():
        resolved_map[key] = value
        try:
            resolved_map[key.resolve()] = value
        except OSError:
            pass
    active_patterns: Sequence[CallPattern] = patterns or DEFAULT_PATTERNS
    for path in paths:
        context = resolved_map.get(path)
        if context is None:
            context = resolved_map.get(path.resolve())
        edges.extend(_scan_single_path(path, normalized_config, context, active_patterns))

    deduped = _deduplicate_edges(edges)
    if infer:
        inferred = _infer_indirect_edges(deduped)
        deduped = _deduplicate_edges(deduped + inferred)

    return sorted(deduped, key=lambda edge: (edge.target, edge.source))


def scan_path(
    path: Path,
    *,
    common_config: Optional[Dict[str, object]] = None,
    infer: bool = False,
    repo_context: Optional[RepoContext] = None,
    patterns: Optional[Sequence[CallPattern]] = None,
) -> List[LineageEdge]:
    """Scan a single *path* for Python files and return lineage edges."""

    context_map = {path: repo_context} if repo_context else None
    return scan_paths(
        [path],
        common_config=common_config,
        infer=infer,
        repo_contexts=context_map,
        patterns=patterns,
    )


def _scan_single_path(
    path: Path,
    normalized_config: Dict[str, str],
    repo_context: Optional[RepoContext],
    patterns: Sequence[CallPattern],
) -> List[LineageEdge]:
    files = _gather_files(path)
    base_dir = path if path.is_dir() else path.parent

    edges: List[LineageEdge] = []
    for file_path in files:
        statements = extract_statements_from_file(
            file_path,
            normalized_config,
            patterns=patterns,
        )
        rel_path = _relative_path(file_path, base_dir)
        if repo_context:
            url = repo_context.file_url(file_path)
            if url:
                rel_path = url
        for statement in statements:
            edges.extend(
                parse_sql_lineage(
                    statement.sql,
                    filename=rel_path,
                    function=statement.function,
                )
            )
    return edges


def _gather_files(path: Path) -> List[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*.py") if p.is_file())


def _relative_path(file_path: Path, base_dir: Path) -> str:
    try:
        return str(file_path.relative_to(base_dir))
    except ValueError:
        return file_path.name


def _deduplicate_edges(edges: Iterable[LineageEdge]) -> List[LineageEdge]:
    unique: Dict[tuple, LineageEdge] = {}
    for edge in edges:
        key = (
            edge.source,
            edge.target,
            edge.source_column,
            edge.target_column,
            edge.mapping_rule,
            edge.temp,
            edge.inferred,
        )
        existing = unique.get(key)
        if existing is None:
            unique[key] = edge
        else:
            # Prefer the edge that carries file/function metadata.
            if not existing.file and edge.file:
                unique[key] = edge
    return list(unique.values())


def _infer_indirect_edges(edges: Iterable[LineageEdge]) -> List[LineageEdge]:
    target_to_sources: Dict[str, set[str]] = {}
    volatile_targets = {edge.target for edge in edges if edge.temp}

    for edge in edges:
        if edge.source == "<unknown>":
            continue
        target_to_sources.setdefault(edge.target, set()).add(edge.source)

    inferred: List[LineageEdge] = []
    for edge in edges:
        if edge.source not in volatile_targets:
            continue
        upstream_sources = target_to_sources.get(edge.source, set())
        for upstream in upstream_sources:
            if upstream == edge.target:
                continue
            inferred.append(
                LineageEdge(
                    source=upstream,
                    target=edge.target,
                    temp=edge.temp,
                    file=edge.file,
                    function=edge.function,
                    inferred=True,
                )
            )
    return inferred


def write_lineage(
    edges: List[LineageEdge],
    output_path: Path,
    *,
    label_overrides: Optional[Dict[str, str]] = None,
) -> None:
    overrides = label_overrides or {}
    payload = []
    for edge in edges:
        data = edge.to_dict()
        data["source_table"] = _apply_label_override(data.get("source_table"), overrides)
        data["target_table"] = _apply_label_override(data.get("target_table"), overrides)
        payload.append(data)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _apply_label_override(value: Optional[str], overrides: Dict[str, str]) -> Optional[str]:
    if not value:
        return value
    result = value
    for key, replacement in overrides.items():
        if not key:
            continue
        if result == key:
            return replacement
        if result.startswith(key):
            return replacement + result[len(key) :]
    return result


def write_lineage_csv(
    edges: List[LineageEdge],
    output_path: Path,
    *,
    label_overrides: Optional[Dict[str, str]] = None,
) -> None:
    overrides = label_overrides or {}
    headers = [
        "source_table",
        "source_column",
        "target_table",
        "target_column",
        "temp",
        "mapping_rule",
        "file",
        "function",
        "inferred",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        for edge in edges:
            source = _apply_label_override(edge.source, overrides)
            target = _apply_label_override(edge.target, overrides)
            writer.writerow(
                {
                    "source_table": source or "",
                    "source_column": edge.source_column or "",
                    "target_table": target or "",
                    "target_column": edge.target_column or "",
                    "temp": str(edge.temp).lower(),
                    "mapping_rule": edge.mapping_rule or "",
                    "file": edge.file or "",
                    "function": edge.function or "",
                    "inferred": str(edge.inferred).lower(),
                }
            )


__all__ = [
    "scan_path",
    "scan_paths",
    "write_lineage",
    "write_lineage_csv",
    "LineageEdge",
    "RepoContext",
]
