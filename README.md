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
uv pip install sqlglot PyYAML
```

> **Note**: This project declares its dependencies in `pyproject.toml`. If the environment has network restrictions, you may need to provide wheels manually.

## Usage

Run the scanner with the package entry point:

```bash
python -m lineage scan PATH/TO/PROJECT \
  --file path/to/single_script.py \
  --config config/config.yaml \
  --output lineage.json \
  --infer
```

- `PATH/TO/PROJECT`: Optional project directory to scan recursively. Omit this argument when only `--file` inputs are needed.
- `--file`: One or more explicit Python files to include. Repeat the flag to combine multiple single-file scans.
- `--config`: Optional YAML file that provides `common_config` overrides, `label_overrides`, and, if desired, an inline `patterns` list or a `patterns_file` reference. See below for an example configuration.

- `--output`: Output file for lineage results (default `lineage.json`).
- `--infer`: Enable inference of indirect lineage through volatile tables.
- `--csv-output`: Optional CSV file path to generate UDD-friendly lineage rows alongside the JSON output.
- `--repo`: Clone a remote repository (HTTPS URL) into a temporary directory and scan it.
- `--ref`: Optional branch, tag, or commit to check out when using `--repo`.
- `--repo-subpath`: Optional subdirectory within the cloned repository to scan (defaults to the repo root or the path parsed from a GitHub `.../tree/<ref>/<path>` URL).

### CLI Flags

| Flag             | Description                                                                                     | Example |
|------------------|-------------------------------------------------------------------------------------------------|---------|
| positional path  | Optional directory to scan recursively. Omit when only using `--file`.                          | `test` |
| `--file`         | Specify a Python file. Repeatable.                                                               | `--file test/test_1.py` |
| `--config`       | Path to YAML providing `common_config`, `label_overrides`, and optionals such as `patterns`.      | `--config config/config.yaml` |
| `--output`       | JSON output file (defaults to `lineage.json`).                                                   | `--output test/output/test_output_1.json` |
| `--infer`        | Adds inferred edges by collapsing volatile table hops.                                           | `--infer` |
| `--csv-output`   | Writes a CSV in addition to JSON (columns align with `source_table`, `mapping_rule`, etc.).      | `--csv-output test/output/test_output_1.csv` |
| `--repo`         | Clone a remote repo (GitHub.com or Enterprise) and scan it. Accepts `tree/...` or `blob/...` URLs.| `--repo https://github.com/org/repo/tree/main/etl` |
| `--ref`          | Ref (branch/tag/commit) to checkout when using `--repo`. Overrides any ref in the URL.            | `--ref release-2024.03` |
| `--repo-subpath` | Subdirectory inside the cloned repo to scan. Overrides path parsed from the URL.                 | `--repo-subpath src/jobs` |
| `--patterns`     | Override the patterns YAML to load (otherwise inferred from the config).                         | `--patterns config/custom_patterns.yaml` |
| `--template-overrides` | Merge additional template variables from a YAML file for this run.                           | `--template-overrides overrides/chnl_trcr.yaml` |

Example `config/config.yaml`:

```yaml
common_config:
  lz_dbname: CCW_LZ
  base_dbname: CCW_BASE
  ccw_aud: CCW_AUD
  stg_dbname: CCW_STG
  view_dbname: CCW_VIEW

label_overrides:
  "{{common_config.lz_dbname}}": CCW_LZ
  "{{common_config.base_dbname}}": CCW_BASE
  "{{common_config.ccw_aud}}": CCW_AUD
  "{{common_config.stg_dbname}}": CCW_STG
  "{{common_config.view_dbname}}": CCW_VIEW

template_variables:
  ccw_view: CCW_VIEW
  ccw_base: CCW_BASE
  ccw_stg: CCW_STG
  proj_nm: PROJECT_NAME
  chnl_src_cd: CHNL_SRC

patterns_file: patterns.yaml
```

- **common_config** – key/value pairs that replace `common_config[...]` lookups in Python code. In the example above, `common_config['base_dbname']` becomes `CCW_BASE`.
- **label_overrides** – optional post-processing of table names in the JSON/CSV output. For instance, if the SQL references `${common_config.view_dbname}`, the output will show `CCW_VIEW` once label overrides are applied.
- **template_variables** – simple string substitutions for `${var}` placeholders embedded directly in SQL literals (useful when ETL scripts use templating or environment variables).
- **patterns_file** – optional pointer to a YAML file that lists additional SQL execution patterns the extractor should recognise. This is helpful if your codebase uses custom wrappers or direct `cursor.execute` calls.

You can also supply run-specific template overrides without editing the main config:

```yaml
# overrides/chnl_trcr.yaml
template_overrides:
  chnl_src_cd: TRCR
  tbl_nm: TMP_CASE_MV_BASE_TRCR
```

Invoke the scanner with `--template-overrides overrides/chnl_trcr.yaml` to merge these values for that run.

And the accompanying `config/patterns.yaml` might contain:

```yaml
patterns:
  - path: ["ccw", "Statement"]
    arg_index: 0
    arg_name: statement
  - path: ["Statement"]
    arg_index: 0
    arg_name: statement
```

### Example Commands

Scan a single file and write the output to `test_output_1.json`:

```bash
uv run -m lineage scan --file test/test_1.py \
  --config config/config.yaml \
  --output test_output_1.json
```

Produce both JSON and CSV from a single-file scan:

```bash
uv run -m lineage scan --file test/test_1.py \
  --config config/config.yaml \
  --output test/output/test_output_1.json \
  --csv-output test/output/test_output_1.csv
```

Scan an entire directory (recursively) and infer indirect edges:

```bash
uv run -m lineage scan test \
  --config config/config.yaml \
  --infer \
  --output test_output_inferred.json
```

Mix a directory with additional single-file targets:

```bash
uv run -m lineage scan src/etl --file scripts/extra_job.py \
  --config config/config.yaml \
  --output lineage.json
```

Scan a remote GitHub directory (branch `main`, subfolder `test` inferred from the URL):

```bash
uv run -m lineage scan --repo https://github.com/dfirmin/tdv-sql-lineage/tree/main/test \
  --config config/config.yaml \
  --output test/output/from_repo.json
```

Scan a single GitHub file (same flags work; just provide a `blob/<ref>/<path>` URL — GitHub Enterprise hosts are supported):

```bash
uv run -m lineage scan --repo https://github.com/dfirmin/tdv-sql-lineage/blob/main/test/test_1.py \
  --config config/config.yaml \
  --output test/output/from_repo_single.json
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
- `file`: Source location. Relative path for local scans, or a GitHub `blob/<ref>/...` URL when `--repo` is used.
- `mapping_rule`: Either `DIRECT_MOVE` (the target column is a direct passthrough of the source column, e.g., `COALESCE(src.col, ' ')`) or `TRANSFORMATION` for derived values (hashes, concatenations, CASE expressions, multi-column expressions, constants, etc.). Missing `source_column` entries indicate that the tool could not resolve the exact input (for example, `DELETE FROM` without sources).

### Output Files

- **JSON** (default): list of edges with keys:
  - `source_table` / `target_table`
  - `temp`
  - `file` / `function`
  - `source_column` / `target_column`
  - `mapping_rule`
  - `inferred` (only present for inferred edges)
- **CSV** (optional via `--csv-output`): columns mirror the JSON fields for UDD-style consumption (`source_table`, `source_column`, `target_table`, `target_column`, `temp`, `mapping_rule`, `file`, `function`, `inferred`).

## Development

Run the scanner against the included sample using:

```bash
python -m lineage scan ./tests/fixtures --config config/config.yaml
```

Pull requests should include updated lineage examples and unit tests once available.

### Extending SQL Detection

The list of SQL execution patterns lives in `lineage/extractor/patterns.py`. Each entry defines:

- The call-path to match (e.g., `("ccw", "Statement")` or `("Statement",)`), and
- Which positional/keyword argument carries the SQL string.

Add new patterns (for example, to support `cursor.execute(...)`) by editing `config/patterns.yaml` (or supplying your own file via `--patterns`). Each entry accepts:

- `path`: An array or dotted string representing the call chain (`["cursor", "execute"]` or `"cursor.execute"`).
- `arg_index`: Optional zero-based index indicating which positional argument contains the SQL string. Set to `null` to skip positional arguments.
- `arg_name`: Optional keyword name when SQL is passed as a named argument (e.g., `statement=`).

The registry is loaded at runtime, so you can tailor SQL detection to your project without touching Python code.
