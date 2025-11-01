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
- `--config`: Optional JSON file that provides values for `common_config`. The tool accepts either a top-level `{"common_config": {...}}` object or a bare dictionary.
- `--output`: Output file for lineage results (default `lineage.json`).
- `--infer`: Enable inference of indirect lineage through volatile tables.

The generated JSON is a list of objects:

```json
[
  {
    "source": "LZ.CCW_CDSET_XWALK",
    "target": "vt_src_cd_val_xwalk",
    "temp": true,
    "file": "example.py",
    "function": "vt_src_cd_val_xwalk"
  }
]
```

## Development

Run the scanner against the included sample using:

```bash
python -m lineage scan ./tests/fixtures --config config.json
```

Pull requests should include updated lineage examples and unit tests once available.
