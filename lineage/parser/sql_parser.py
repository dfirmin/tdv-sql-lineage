from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Set, Tuple

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError


@dataclass
class LineageEdge:
    """Represents a directed lineage relationship between tables."""

    source: str
    target: str
    temp: bool = False
    file: Optional[str] = None
    function: Optional[str] = None
    inferred: bool = False

    def to_dict(self) -> dict:
        payload = {"source": self.source, "target": self.target}
        if self.temp:
            payload["temp"] = True
        if self.file:
            payload["file"] = self.file
        if self.function:
            payload["function"] = self.function
        if self.inferred:
            payload["inferred"] = True
        return payload


def parse_sql_lineage(
    sql_text: str,
    *,
    filename: Optional[str] = None,
    function: Optional[str] = None,
) -> List[LineageEdge]:
    """Parse *sql_text* and return lineage edges discovered within it."""

    try:
        expressions = sqlglot.parse(sql_text, read="teradata")
    except ParseError:
        return _parse_with_regex(sql_text, filename=filename, function=function)

    edges: List[LineageEdge] = []
    for expression in expressions:
        edges.extend(
            _edges_from_expression(expression, filename=filename, function=function)
        )

    if edges:
        return edges
    return _parse_with_regex(sql_text, filename=filename, function=function)


def _edges_from_expression(
    expression: exp.Expression,
    *,
    filename: Optional[str],
    function: Optional[str],
) -> List[LineageEdge]:
    raw_targets = _extract_targets(expression)
    targets = _augment_targets(raw_targets)
    if not targets:
        return []

    target_nodes = {node for _, _, node in targets}

    source_tables = {
        _table_name(table)
        for table in expression.find_all(exp.Table)
        if table not in target_nodes and _table_name(table)
    }

    edges: List[LineageEdge] = []
    for target_name, temp_flag, _ in targets:
        if source_tables:
            for source_name in sorted(source_tables):
                edges.append(
                    LineageEdge(
                        source=source_name,
                        target=target_name,
                        temp=temp_flag,
                        file=filename,
                        function=function,
                    )
                )
        else:
            # For statements like DELETE without sources, emit a placeholder edge.
            edges.append(
                LineageEdge(
                    source="<unknown>",
                    target=target_name,
                    temp=temp_flag,
                    file=filename,
                    function=function,
                )
            )
    return edges


def _augment_targets(
    targets: Sequence[Tuple[str, bool, exp.Table]]
) -> List[Tuple[str, bool, exp.Table]]:
    """Ensure targets are unique while preserving order and metadata."""

    seen: Set[str] = set()
    result: List[Tuple[str, bool, exp.Table]] = []
    for name, temp, node in targets:
        if name in seen:
            continue
        seen.add(name)
        result.append((name, temp, node))
    return result


def _extract_targets(expression: exp.Expression) -> List[Tuple[str, bool, exp.Table]]:
    targets: List[Tuple[str, bool, exp.Table]] = []

    if isinstance(expression, exp.Insert):
        table = expression.this
        if isinstance(table, exp.Table):
            targets.append((_table_name(table), False, table))
    elif isinstance(expression, exp.Create):
        table = expression.this
        if isinstance(table, exp.Table):
            targets.append((_table_name(table), _is_volatile(expression), table))
    elif isinstance(expression, exp.Update):
        table = expression.this
        if isinstance(table, exp.Table):
            targets.append((_table_name(table), False, table))
    elif isinstance(expression, exp.Delete):
        table = expression.this
        if isinstance(table, exp.Table):
            targets.append((_table_name(table), False, table))
    return targets


def _is_volatile(expression: exp.Expression) -> bool:
    try:
        sql = expression.sql(dialect="teradata").upper()
    except Exception:  # pragma: no cover - defensive
        sql = ""
    return "VOLATILE" in sql


def _table_name(table: Optional[exp.Table]) -> str:
    if table is None:
        return ""
    parts: List[str] = []
    catalog = table.args.get("catalog")
    if isinstance(catalog, exp.Identifier) and catalog.name:
        parts.append(catalog.name)
    db = table.args.get("db")
    if isinstance(db, exp.Identifier) and db.name:
        parts.append(db.name)
    this = table.args.get("this")
    if isinstance(this, exp.Identifier) and this.name:
        parts.append(this.name)
    name = ".".join(parts)
    return name or table.name


# ---------------------------------------------------------------------------
# Regex fallback
# ---------------------------------------------------------------------------
TARGET_REGEXES = [
    re.compile(r"INSERT\s+INTO\s+([\w.]+)", re.IGNORECASE),
    re.compile(r"CREATE\s+(?:VOLATILE\s+)?TABLE\s+([\w.]+)", re.IGNORECASE),
    re.compile(r"UPDATE\s+([\w.]+)", re.IGNORECASE),
    re.compile(r"DELETE\s+FROM\s+([\w.]+)", re.IGNORECASE),
]

SOURCE_REGEX = re.compile(r"(?:FROM|JOIN)\s+([\w.]+)", re.IGNORECASE)


def _parse_with_regex(
    sql_text: str,
    *,
    filename: Optional[str],
    function: Optional[str],
) -> List[LineageEdge]:
    targets = _regex_targets(sql_text)
    if not targets:
        return []

    sources = _regex_sources(sql_text)
    edges: List[LineageEdge] = []
    for target, is_temp in targets:
        if sources:
            for source in sources:
                edges.append(
                    LineageEdge(
                        source=source,
                        target=target,
                        temp=is_temp,
                        file=filename,
                        function=function,
                    )
                )
        else:
            edges.append(
                LineageEdge(
                    source="<unknown>",
                    target=target,
                    temp=is_temp,
                    file=filename,
                    function=function,
                )
            )
    return edges


def _regex_targets(sql_text: str) -> List[Tuple[str, bool]]:
    matches: List[Tuple[str, bool]] = []
    for pattern in TARGET_REGEXES:
        for match in pattern.finditer(sql_text):
            raw = match.group(1)
            name = _clean_identifier(raw)
            is_temp = "VOLATILE" in pattern.pattern.upper() and "VOLATILE" in match.group(0).upper()
            matches.append((name, is_temp))
    return matches


def _regex_sources(sql_text: str) -> List[str]:
    sources = []
    for match in SOURCE_REGEX.finditer(sql_text):
        sources.append(_clean_identifier(match.group(1)))
    return sorted(set(sources))


def _clean_identifier(identifier: str) -> str:
    return identifier.strip().strip(";()\"`[]")
