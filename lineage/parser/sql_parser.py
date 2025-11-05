from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

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
    source_column: Optional[str] = None
    target_column: Optional[str] = None
    mapping_rule: Optional[str] = None

    def to_dict(self) -> dict:
        payload = {
            "source_table": self.source,
            "target_table": self.target,
            "temp": self.temp,
        }
        if self.file:
            payload["file"] = self.file
        if self.function:
            payload["function"] = self.function
        if self.inferred:
            payload["inferred"] = True
        if self.source_column:
            payload["source_column"] = self.source_column
        if self.target_column:
            payload["target_column"] = self.target_column
        if self.mapping_rule:
            payload["mapping_rule"] = self.mapping_rule
        return payload


PLACEHOLDER_PATTERN = re.compile(r"\{\{([^{}]+)\}\}")
COLLATION_PATTERN = re.compile(r"('(?:''|[^'])*')\s*\((NOT\s+)?CASESPECIFIC\)", re.IGNORECASE)


def _normalize_placeholders(sql_text: str) -> tuple[str, Dict[str, str]]:
    replacements: Dict[str, str] = {}

    def _replace(match: re.Match[str]) -> str:
        token = f"__placeholder_{len(replacements)}__"
        replacements[token] = match.group(0)
        return token

    normalized = PLACEHOLDER_PATTERN.sub(_replace, sql_text)
    return normalized, replacements


def _restore_placeholders(text: str, replacements: Dict[str, str]) -> str:
    for token, original in replacements.items():
        text = text.replace(token, original)
    return text


def _prepare_sql(sql_text: str) -> tuple[str, Dict[str, str]]:
    normalized, replacements = _normalize_placeholders(sql_text)

    def _collation(match: re.Match[str]) -> str:
        return match.group(1)

    normalized = COLLATION_PATTERN.sub(_collation, normalized)
    return normalized, replacements


def parse_sql_lineage(
    sql_text: str,
    *,
    filename: Optional[str] = None,
    function: Optional[str] = None,
) -> List[LineageEdge]:
    """Parse *sql_text* and return lineage edges discovered within it."""

    normalized_sql, replacements = _prepare_sql(sql_text)

    try:
        expressions = sqlglot.parse(normalized_sql, read="teradata")
    except ParseError:
        return _parse_with_regex(sql_text, filename=filename, function=function)

    edges: List[LineageEdge] = []
    for expression in expressions:
        edges.extend(
            _edges_from_expression(
                expression,
                replacements,
                filename=filename,
                function=function,
            )
        )

    if edges:
        return edges
    return _parse_with_regex(sql_text, filename=filename, function=function)


def _edges_from_expression(
    expression: exp.Expression,
    replacements: Dict[str, str],
    *,
    filename: Optional[str],
    function: Optional[str],
) -> List[LineageEdge]:
    raw_targets = _extract_targets(expression, replacements)
    targets = _augment_targets(raw_targets)
    if not targets:
        return []

    target_metadata = {node: (name, temp) for name, temp, node in targets}
    alias_map = _build_alias_map(expression, replacements)

    column_edges = _column_lineage_edges(
        expression,
        targets,
        target_metadata,
        alias_map,
        replacements,
        filename=filename,
        function=function,
    )
    if column_edges:
        return column_edges

    target_nodes = {node for _, _, node in targets}

    source_tables = {
        _table_name(table, replacements)
        for table in expression.find_all(exp.Table)
        if table not in target_nodes and _table_name(table, replacements)
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


def _extract_targets(
    expression: exp.Expression, replacements: Dict[str, str]
) -> List[Tuple[str, bool, exp.Table]]:
    targets: List[Tuple[str, bool, exp.Table]] = []

    if isinstance(expression, exp.Insert):
        table_expr = expression.this
        if isinstance(table_expr, exp.Schema):
            table = table_expr.this
        else:
            table = table_expr
        if isinstance(table, exp.Table):
            targets.append((_resolved_table_name(table, expression, replacements), False, table))
    elif isinstance(expression, exp.Create):
        table_expr = expression.this
        if isinstance(table_expr, exp.Schema):
            table = table_expr.this
        else:
            table = table_expr
        if isinstance(table, exp.Table):
            targets.append((_resolved_table_name(table, expression, replacements), _is_volatile(expression), table))
    elif isinstance(expression, exp.Update):
        table = expression.this
        if isinstance(table, exp.Table):
            targets.append((_resolved_table_name(table, expression, replacements), False, table))
    elif isinstance(expression, exp.Delete):
        return targets
    return targets


def _resolved_table_name(
    table: exp.Table, expression: exp.Expression, replacements: Dict[str, str]
) -> str:
    name = _table_name(table, replacements)
    if name and name != table.alias_or_name:
        return name

    alias = table.alias_or_name
    from_clause = expression.args.get("from")
    if alias and isinstance(from_clause, exp.From):
        for candidate in from_clause.find_all(exp.Table):
            if candidate is table:
                continue
            if candidate.alias_or_name == alias:
                resolved = _table_name(candidate, replacements)
                if resolved:
                    return resolved
    return name


def _build_alias_map(expression: exp.Expression, replacements: Dict[str, str]) -> Dict[str, str]:
    alias_map: Dict[str, str] = {}
    for table in expression.find_all(exp.Table):
        table_name = _table_name(table, replacements)
        _register_alias(alias_map, table.alias, table_name, replacements)
        _register_alias(alias_map, table.alias_or_name, table_name, replacements)
        _register_alias(alias_map, table.name, table_name, replacements)
        _register_alias(alias_map, table_name, table_name, replacements)
    return alias_map


def _register_alias(
    alias_map: Dict[str, str], key: Optional[str], table_name: str, replacements: Dict[str, str]
) -> None:
    if not key:
        return
    alias_map[key] = table_name
    restored = _restore_placeholders(key, replacements)
    alias_map[restored] = table_name


def _column_lineage_edges(
    expression: exp.Expression,
    targets: Sequence[Tuple[str, bool, exp.Table]],
    target_metadata: Dict[exp.Table, Tuple[str, bool]],
    alias_map: Dict[str, str],
    replacements: Dict[str, str],
    *,
    filename: Optional[str],
    function: Optional[str],
) -> List[LineageEdge]:
    edges: List[LineageEdge] = []

    if isinstance(expression, exp.Insert):
        edges.extend(
            _column_lineage_from_insert(
                expression,
                targets,
                target_metadata,
                alias_map,
                replacements,
                filename=filename,
                function=function,
            )
        )
    elif isinstance(expression, exp.Create):
        edges.extend(
            _column_lineage_from_create(
                expression,
                targets,
                target_metadata,
                alias_map,
                replacements,
                filename=filename,
                function=function,
            )
        )
    elif isinstance(expression, exp.Update):
        edges.extend(
            _column_lineage_from_update(
                expression,
                targets,
                target_metadata,
                alias_map,
                replacements,
                filename=filename,
                function=function,
            )
        )
    return edges


def _column_lineage_from_insert(
    expression: exp.Insert,
    targets: Sequence[Tuple[str, bool, exp.Table]],
    target_metadata: Dict[exp.Table, Tuple[str, bool]],
    alias_map: Dict[str, str],
    replacements: Dict[str, str],
    *,
    filename: Optional[str],
    function: Optional[str],
) -> List[LineageEdge]:
    select = _as_select(expression.args.get("expression"))
    if select is None:
        return []

    schema = expression.this if isinstance(expression.this, exp.Schema) else None
    target_table = schema.this if isinstance(schema, exp.Schema) else expression.this

    if not isinstance(target_table, exp.Table):
        return []

    target_name, temp = _resolve_target_metadata(targets, target_metadata, target_table)
    if not target_name:
        return []

    target_columns = _schema_column_names(schema, replacements) if isinstance(schema, exp.Schema) else None

    return _column_lineage_from_select(
        select,
        target_name,
        temp,
        alias_map,
        replacements,
        filename=filename,
        function=function,
        target_columns=target_columns,
    )


def _column_lineage_from_create(
    expression: exp.Create,
    targets: Sequence[Tuple[str, bool, exp.Table]],
    target_metadata: Dict[exp.Table, Tuple[str, bool]],
    alias_map: Dict[str, str],
    replacements: Dict[str, str],
    *,
    filename: Optional[str],
    function: Optional[str],
) -> List[LineageEdge]:
    select = _as_select(expression.args.get("expression"))
    if select is None:
        return []

    target_table = expression.this if isinstance(expression.this, exp.Table) else None
    target_name, temp = _resolve_target_metadata(targets, target_metadata, target_table)
    if not target_name:
        return []

    return _column_lineage_from_select(
        select,
        target_name,
        temp,
        alias_map,
        replacements,
        filename=filename,
        function=function,
    )


def _column_lineage_from_update(
    expression: exp.Update,
    targets: Sequence[Tuple[str, bool, exp.Table]],
    target_metadata: Dict[exp.Table, Tuple[str, bool]],
    alias_map: Dict[str, str],
    replacements: Dict[str, str],
    *,
    filename: Optional[str],
    function: Optional[str],
) -> List[LineageEdge]:
    target_table = expression.this if isinstance(expression.this, exp.Table) else None
    target_name, temp = _resolve_target_metadata(targets, target_metadata, target_table)
    if not target_name:
        return []

    assignments = list(expression.expressions or [])
    if not assignments:
        return []

    default_table = target_name
    from_clause = expression.args.get("from")
    if isinstance(from_clause, exp.From):
        inferred = _default_source_table(from_clause, alias_map, target_name, replacements)
        if inferred:
            default_table = inferred

    edges: List[LineageEdge] = []
    for assignment in assignments:
        if not isinstance(assignment, exp.EQ):
            continue

        target_column = _column_label(assignment.this, replacements)
        sources = _source_columns_from_expression(
            assignment.expression,
            alias_map,
            replacements,
            default_table=default_table,
        )
        mapping_rule = _mapping_rule_for_expression(assignment.expression, sources)
        if not sources:
            edges.append(
                LineageEdge(
                    source="<unknown>",
                    target=target_name,
                    temp=temp,
                    file=filename,
                    function=function,
                    target_column=target_column,
                    mapping_rule=mapping_rule,
                )
            )
            continue

        for source_table, source_column in sources:
            edges.append(
                LineageEdge(
                    source=source_table,
                    target=target_name,
                    temp=temp,
                    file=filename,
                    function=function,
                    source_column=source_column,
                    target_column=target_column,
                    mapping_rule=mapping_rule,
                )
            )
    return edges


def _resolve_target_metadata(
    targets: Sequence[Tuple[str, bool, exp.Table]],
    target_metadata: Dict[exp.Table, Tuple[str, bool]],
    table: Optional[exp.Table],
) -> Tuple[Optional[str], bool]:
    if table is not None and table in target_metadata:
        return target_metadata[table]
    if targets:
        name, temp, _ = targets[0]
        return name, temp
    return None, False


def _schema_column_names(schema: Optional[exp.Schema], replacements: Dict[str, str]) -> List[str]:
    if schema is None:
        return []
    names: List[str] = []
    for expression in schema.expressions or []:
        if isinstance(expression, exp.Identifier) and expression.name:
            names.append(_restore_placeholders(expression.name, replacements))
        else:
            names.append(_restore_placeholders(expression.sql(dialect="teradata"), replacements))
    return names


def _as_select(expression: Optional[exp.Expression]) -> Optional[exp.Select]:
    if isinstance(expression, exp.Select):
        return expression
    if isinstance(expression, exp.Subquery):
        inner = expression.this
        if isinstance(inner, exp.Select):
            return inner
    return None


def _column_lineage_from_select(
    select: exp.Select,
    target_name: str,
    temp: bool,
    alias_map: Dict[str, str],
    replacements: Dict[str, str],
    *,
    filename: Optional[str],
    function: Optional[str],
    target_columns: Optional[List[str]] = None,
) -> List[LineageEdge]:
    select_expressions = list(select.selects or [])
    if not select_expressions:
        return []

    columns: List[str] = []
    if target_columns is None:
        columns = _infer_target_columns(select_expressions, replacements)
    else:
        columns = list(target_columns)
        if len(columns) < len(select_expressions):
            remaining = _infer_target_columns(
                select_expressions[len(columns) :],
                replacements,
                start_index=len(columns) + 1,
            )
            columns.extend(remaining)

    default_table = _default_source_table(select, alias_map, target_name, replacements)

    edges: List[LineageEdge] = []
    for target_column, expression in zip(columns, select_expressions):
        sources = _source_columns_from_expression(
            expression,
            alias_map,
            replacements,
            default_table=default_table,
        )
        mapping_rule = _mapping_rule_for_expression(expression, sources)
        if not sources:
            edges.append(
                LineageEdge(
                    source="<unknown>",
                    target=target_name,
                    temp=temp,
                    file=filename,
                    function=function,
                    target_column=target_column,
                    mapping_rule=mapping_rule,
                )
            )
            continue
        for source_table, source_column in sources:
            edges.append(
                LineageEdge(
                    source=source_table,
                    target=target_name,
                    temp=temp,
                    file=filename,
                    function=function,
                    source_column=source_column,
                    target_column=target_column,
                    mapping_rule=mapping_rule,
                )
            )
    return edges


def _source_columns_from_expression(
    expression: exp.Expression,
    alias_map: Dict[str, str],
    replacements: Dict[str, str],
    *,
    default_table: Optional[str] = None,
) -> List[Tuple[str, str]]:
    results: List[Tuple[str, str]] = []
    seen: Set[Tuple[str, str]] = set()

    def _record(column: exp.Column) -> None:
        column_name = _restore_placeholders(column.name or column.sql(dialect="teradata"), replacements)
        table_key = column.table or ""
        source_table = alias_map.get(table_key)
        if not source_table and table_key:
            restored_key = _restore_placeholders(table_key, replacements)
            source_table = alias_map.get(restored_key, restored_key)
        if not source_table:
            source_table = default_table
        source_table = source_table or "<unknown>"
        key = (source_table, column_name)
        if key in seen:
            return
        seen.add(key)
        results.append(key)

    def _walk(node: Optional[exp.Expression]) -> None:
        if node is None:
            return
        if isinstance(node, exp.Case):
            branches = node.args.get("ifs") or []
            for branch in branches:
                if isinstance(branch, (tuple, list)) and len(branch) == 2:
                    _, result = branch
                    _walk(result)
                elif isinstance(branch, exp.When):
                    _walk(branch.args.get("true"))
                else:
                    _walk(branch)
            _walk(node.args.get("default"))
            return
        if isinstance(node, exp.When):
            _walk(node.args.get("true"))
            _walk(node.args.get("false"))
            return
        if isinstance(node, exp.If):
            _walk(node.args.get("true"))
            _walk(node.args.get("false"))
            return
        if isinstance(node, exp.Column):
            _record(node)
            return
        for child in node.iter_expressions():
            _walk(child)

    _walk(expression)
    return results


def _mapping_rule_for_expression(
    expression: exp.Expression, sources: Sequence[Tuple[str, str]]
) -> str:
    if isinstance(expression, exp.Alias):
        return _mapping_rule_for_expression(expression.this, sources)
    if len(sources) != 1:
        return TRANSFORMATION
    if isinstance(expression, exp.Column):
        return DIRECT_MOVE
    if isinstance(expression, exp.Identifier):
        return DIRECT_MOVE
    if isinstance(expression, exp.Coalesce):
        first = expression.this
        if isinstance(first, exp.Column):
            return DIRECT_MOVE
    return TRANSFORMATION


def _default_source_table(
    expression: exp.Expression,
    alias_map: Dict[str, str],
    target_name: Optional[str],
    replacements: Dict[str, str],
) -> Optional[str]:
    tables: Set[str] = set()
    for table in expression.find_all(exp.Table):
        candidate = (
            alias_map.get(table.alias)
            or alias_map.get(table.alias_or_name)
            or alias_map.get(table.name)
            or _table_name(table, replacements)
        )
        if not candidate:
            continue
        if target_name and candidate == target_name:
            continue
        tables.add(candidate)
    if len(tables) == 1:
        return next(iter(tables))
    return None


def _infer_target_columns(
    select_expressions: Sequence[exp.Expression],
    replacements: Dict[str, str],
    start_index: int = 1,
) -> List[str]:
    names: List[str] = []
    for index, expression in enumerate(select_expressions, start=start_index):
        names.append(_select_output_name(expression, replacements, index))
    return names


def _select_output_name(
    expression: exp.Expression, replacements: Dict[str, str], position: int
) -> str:
    alias = getattr(expression, "alias", None)
    if alias:
        return _restore_placeholders(alias, replacements)
    name = getattr(expression, "name", None)
    if name:
        return _restore_placeholders(name, replacements)
    if isinstance(expression, exp.Column):
        return _restore_placeholders(expression.sql(dialect="teradata"), replacements)
    return f"column_{position}"


def _column_label(expression: exp.Expression, replacements: Dict[str, str]) -> str:
    if isinstance(expression, exp.Column):
        return _restore_placeholders(expression.name, replacements)
    return _restore_placeholders(expression.sql(dialect="teradata"), replacements)

def _is_volatile(expression: exp.Expression) -> bool:
    try:
        sql = expression.sql(dialect="teradata").upper()
    except Exception:  # pragma: no cover - defensive
        sql = ""
    return "VOLATILE" in sql


def _table_name(table: Optional[exp.Table], replacements: Dict[str, str]) -> str:
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
    name = ".".join(parts) or table.name or ""
    return _restore_placeholders(name, replacements)


# ---------------------------------------------------------------------------
# Regex fallback
# ---------------------------------------------------------------------------
TARGET_REGEXES = [
    ("INSERT", re.compile(r"INSERT\s+INTO\s+([^\s,;()]+)", re.IGNORECASE)),
    ("CREATE", re.compile(r"CREATE\s+(?:VOLATILE\s+)?TABLE\s+([^\s,;()]+)", re.IGNORECASE)),
    ("UPDATE", re.compile(r"UPDATE\s+([^\s,;()]+)", re.IGNORECASE)),
    ("DELETE", re.compile(r"DELETE\s+FROM\s+([^\s,;()]+)", re.IGNORECASE)),
]

SOURCE_REGEX = re.compile(r"(?:FROM|JOIN)\s+([^\s,;()]+)", re.IGNORECASE)


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
    for target, is_temp, stmt_type in targets:
        candidate_sources = sources
        if stmt_type == "DELETE":
            candidate_sources = [source for source in sources if source != target]
        if candidate_sources:
            for source in candidate_sources:
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


def _regex_targets(sql_text: str) -> List[Tuple[str, bool, str]]:
    matches: List[Tuple[str, bool, str]] = []
    for stmt_type, pattern in TARGET_REGEXES:
        for match in pattern.finditer(sql_text):
            raw = match.group(1)
            name = _clean_identifier(raw)
            is_temp = False
            if stmt_type == "CREATE" and "VOLATILE" in match.group(0).upper():
                is_temp = True
            matches.append((name, is_temp, stmt_type))
    return matches


def _regex_sources(sql_text: str) -> List[str]:
    sources = []
    for match in SOURCE_REGEX.finditer(sql_text):
        sources.append(_clean_identifier(match.group(1)))
    return sorted(set(sources))


def _clean_identifier(identifier: str) -> str:
    return identifier.strip().strip(";()\"`[]")
DIRECT_MOVE = "DIRECT_MOVE"
TRANSFORMATION = "TRANSFORMATION"
