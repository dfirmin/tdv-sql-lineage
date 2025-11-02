# tdv-sql-lineage

A lightweight static analysis tool for extracting table-level lineage from Python ETL scripts that embed Teradata SQL in `ccw.Statement` calls.

The tool parses Python source code, reconstructs SQL strings (including `common_config` substitutions), analyses SQL statements with [`sqlglot`](https://github.com/tobymao/sqlglot), and emits lineage edges as JSON.

## Features

- AST-based discovery of `ccw.Statement(...)` calls
- String reconstruction with support for multiline literals, concatenation, and `common_config[...]` placeholders
- SQL parsing with `sqlglot` and regex fallback when parsing fails
- Identification of source and target tables for `INSERT`, `CREATE`, `UPDATE`, and `DELETE` statements
- Optional multi-hop inference that collapses volatile table hops into direct edges

## Requirements

- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) for dependency management

Install dependencies into a virtual environment using `uv`:

```bash
uv venv
uv pip install sqlglot
```

> **Note**: This project declares its dependencies in `pyproject.toml`. If the environment has network restrictions, you may need to provide wheels manually.

## Usage

Run the scanner with the package entry point:

```bash
python -m lineage scan PATH/TO/PROJECT \
  --file path/to/single_script.py \
  --config config.json \
  --output lineage.json \
  --infer
```

- `PATH/TO/PROJECT`: Optional project directory to scan recursively. Omit this argument when only `--file` inputs are needed.
- `--file`: One or more explicit Python files to include. Repeat the flag to combine multiple single-file scans.
- `--config`: Optional JSON file that provides values for `common_config`. The tool accepts either a top-level `{"common_config": {...}}` object or a bare dictionary. You can also include an optional `label_overrides` block to rewrite table names in the output:

  ```json
  {
    "common_config": {
      "lz_dbname": "LZ",
      "base_dbname": "BASE"
    },
    "label_overrides": {
      "{{common_config.lz_dbname}}": "CCW_LZ",
      "{{common_config.base_dbname}}": "CCW_BASE"
    }
  }
  ```

- `--output`: Output file for lineage results (default `lineage.json`).
- `--infer`: Enable inference of indirect lineage through volatile tables.

### Example Commands

Scan a single file and write the output to `test_output_1.json`:

```bash
uv run -m lineage scan --file test/test_1.py \
  --config config_labels.json \
  --output test_output_1.json
```

Scan an entire directory (recursively) and infer indirect edges:

```bash
uv run -m lineage scan test \
  --config config_labels.json \
  --infer \
  --output test_output_inferred.json
```

Mix a directory with additional single-file targets:

```bash
uv run -m lineage scan src/etl --file scripts/extra_job.py \
  --config config_labels.json \
  --output lineage.json
```

The generated JSON is a list of objects:

```json
[
  {
    "source_table": "CCW_LZ.CCW_CDSET_XWALK",
    "target_table": "vt_src_cd_val_xwalk",
    "temp": true,
    "file": "example.py",
    "function": "vt_src_cd_val_xwalk",
    "source_column": "SRC_CDSET_NM",
    "target_column": "SRC_CDSET_NM",
    "mapping_rule": "DIRECT_MOVE"
  }
]
```

- `source_table` / `target_table`: Table-level lineage.
- `temp`: `true` when the target came from a `CREATE VOLATILE TABLE` (useful for identifying session-scoped tables), otherwise `false`.
- `source_column` / `target_column`: Column lineage when available.
- `mapping_rule`: Either `DIRECT_MOVE` (the target column is a direct passthrough of the source column, e.g., `COALESCE(src.col, ' ')`) or `TRANSFORMATION` for derived values (hashes, concatenations, CASE expressions, multi-column expressions, constants, etc.). Missing `source_column` entries indicate that the tool could not resolve the exact input (for example, `DELETE FROM` without sources).

## Development

Run the scanner against the included sample using:

```bash
python -m lineage scan ./tests/fixtures --config config.json
```

Pull requests should include updated lineage examples and unit tests once available.
