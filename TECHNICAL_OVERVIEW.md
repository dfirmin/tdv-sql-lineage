# Technical Overview

This document explains how the `tdv-sql-lineage` codebase discovers lineage in Python ETL scripts, the responsibility of each module, and how data flows through the system.

## High-Level Flow

1. **Entry point** — The `lineage.cli` module exposes the `lineage scan` command (`python -m lineage scan …`). It normalises input arguments, optionally clones remote repositories (`--repo`), loads configuration (both `common_config` substitutions and `label_overrides`), and calls the analyzer.
2. **Analyzer** — `lineage.analyzer` coordinates the scan:
   - Recursively discovers Python files or uses explicit `--file` targets.
   - Passes each file to the AST extractor to recover SQL statements embedded in `ccw.Statement` calls.
   - Invokes the SQL parser to convert those statements into `LineageEdge` objects.
   - Deduplicates edges, optionally infers indirect edges through volatile tables, and writes JSON output (applying any label overrides).
3. **Extractor** — `lineage.extractor.ast_extractor` parses Python source into an AST, walks it to find `Statement` calls, and reconstructs the SQL string (including handling `common_config[...]` placeholders, string concatenation, f-strings, etc.).
4. **Parser** — `lineage.parser.sql_parser` uses [`sqlglot`](https://github.com/tobymao/sqlglot) to parse Teradata SQL. It extracts source/target tables, resolves column-level lineage, and classifies each mapping as a `DIRECT_MOVE` or `TRANSFORMATION`. A regex fallback handles parse failures.

The JSON output contains table lineage (`source_table`, `target_table`), optional column lineage (`source_column`, `target_column`), whether the target table is volatile (`temp`), the originating file/function, and a `mapping_rule`.

## Module Breakdown

### `lineage/__main__.py`
Thin wrapper that calls `cli.main()` when the package is executed via `python -m lineage`.

### `lineage/cli.py`
- Builds the `argparse` CLI (`lineage scan`).
- Loads YAML configuration files. Supports a mixed payload:
  - `common_config`: key/value pairs used by the AST extractor when it encounters `common_config['key']`.
  - `label_overrides` (or `output_labels`): string replacements applied to table names before writing JSON.
  - `template_variables`: simple `${var}` substitutions applied to raw SQL strings (useful for templated ETL code).
- Resolves SQL execution patterns from either inline config (`patterns:`) or companion files such as `patterns.yaml`.
- Optionally clones remote Git repositories (`--repo`, `--ref`, `--repo-subpath`) into a temporary directory before scanning.
- Validates user input, combines `--path` and repeated `--file` arguments, and calls `scan_paths`.
- Writes results via `write_lineage`, forwarding any label overrides so output tables can be aliased.

### `lineage/analyzer.py`
- `scan_paths` / `scan_path` control the end-to-end scan:
  - Collect target files (`_gather_files`).
  - Extract SQL statements from each file.
  - Parse SQL into `LineageEdge` objects.
  - Deduplicate edges while retaining file/function metadata.
  - Optionally infer multi-hop lineage through volatile tables (`--infer`).
  - If a `RepoContext` is provided (via `--repo`), record GitHub `blob/<ref>/...` URLs instead of local file names so the JSON can deep-link into the remote repository.
- `write_lineage` serialises edges to JSON, applying label overrides and preserving new keys:
  - `source_table`, `target_table`
  - `temp` (volatile flag)
  - `source_column`, `target_column`
  - `mapping_rule` (`DIRECT_MOVE` vs `TRANSFORMATION`)
- `write_lineage_csv` mirrors the JSON payload in CSV form (optional `--csv-output`).
- All helper functions live in the same module to keep orchestration logic together.

### `lineage/extractor/__init__.py`
Exposes the extractor package.

### `lineage/extractor/ast_extractor.py`
- Parses Python source using `ast.parse`.
- `StatementExtractor` visits function definitions to track the current function stack, then finds `ccw.Statement(...)` invocations.
- SQL execution call detection is driven by the registry in `lineage/extractor/patterns.py`; each pattern describes a call-path (e.g., `ccw.Statement`, bare `Statement`) and which argument carries the SQL. Adding new adapters (e.g., cursor `.execute` calls) is as simple as appending a pattern.
- Reconstructs the SQL argument:
  - Handles positional or keyword arguments.
  - Evaluates literals, concatenations (`BinOp +`), f-strings, simple wrapper calls (`str(...)`, etc.), and dictionary lookups (`common_config['key']`).
  - Emits placeholders (`{{identifier}}`) when a value cannot be resolved statically.
- Returns `ExtractedStatement` objects containing SQL text, file path, function name, and line numbers.

### `lineage/parser/__init__.py`
Convenience exports for the parser package.

### `lineage/parser/sql_parser.py`
- Defines the `LineageEdge` dataclass and the core SQL analysis pipeline.
- `parse_sql_lineage`:
  - Normalises placeholders and Teradata-specific collation syntax.
  - Parses SQL via `sqlglot`; on failure, falls back to regex heuristics.
  - Aggregates edges per SQL statement (INSERT/CREATE/UPDATE/DELETE).
- Column lineage (`_column_lineage_from_select`, `_column_lineage_from_update`, etc.):
  - Builds a table alias map.
  - Matches target columns to source columns.
  - Handles `SELECT ... AS ...`, CTAS statements, INSERT lists, joins, and UPDATE assignments.
  - For CASE expressions, walks only the value branches, ignoring predicates.
  - Classifies each mapping as:
    - `DIRECT_MOVE` when the expression is effectively a single column passthrough (including wrappers like `COALESCE(col, ' ')`).
    - `TRANSFORMATION` otherwise (hashes, concatenations, arithmetic, multi-column expressions, constants).
- Regex fallback provides best-effort table-level lineage when SQL parsing fails.

### `lineage/__init__.py`
Exports the public API (`LineageEdge`, `scan_path`, `write_lineage`) for consumers who prefer to use the library directly instead of the CLI.

## Extending the Scanner

- **New SQL constructs** — Add cases to `_extract_targets` and `_column_lineage_from_*` to support additional statement types or dialect-specific syntax.
- **Column-mapping heuristics** — `_source_columns_from_expression` and `_mapping_rule_for_expression` are designed to be extensible. Add handlers for additional expression nodes (casts, arithmetic, window functions) to improve direct vs transformation classification.
- **Placeholder handling** — `_prepare_sql` normalises `{{placeholders}}`. Extend this if you encounter other templating syntaxes or environment-specific macros.
- **Label overrides** — Implemented in `write_lineage`; extend the substitution logic if you need regex or suffix replacements instead of the current prefix-based approach.

## Output Schema Summary

Each JSON edge contains:

| Key             | Description                                                                               |
|-----------------|-------------------------------------------------------------------------------------------|
| `source_table`  | Upstream table (post label override).                                                     |
| `target_table`  | Downstream table (post label override).                                                   |
| `temp`          | `true` if the target is a volatile table, `false` otherwise.                              |
| `file`/`function` | File path and function where the SQL statement was discovered (if available).           |
| `source_column` | Source column contributing to the mapping (optional).                                     |
| `target_column` | Target column receiving the data (optional).                                              |
| `mapping_rule`  | `DIRECT_MOVE` or `TRANSFORMATION`, indicating whether the value is passed through or derived. |
| `inferred`      | Present (and `true`) when an edge was added via indirect inference (`--infer`).          |

This overview should help new contributors understand how the components fit together and where to adjust the pipeline when adding features or fixing parsing gaps.
