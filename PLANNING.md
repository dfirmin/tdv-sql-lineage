# Planning Notes

## Long-Term Automation Goals

- **CI/CD integration**
  - Run `lineage scan` on every merge into main (or nightly) for each ETL repo.
  - Export both JSON and CSV (UDD-friendly) outputs.
  - Publish artifacts to SharePoint/S3/Git commits for downstream consumption.

- **Repository coverage**
- Maintain a manifest (YAML/JSON) listing all codebases plus their scan configs.
- Optionally shard per domain/team to enable incremental onboarding and parallel runs.
- Scheduled weekly (post-release) scan job that reads the manifest, compares repos to prior run state (commit hashes or timestamps), and only triggers UDD regeneration when relevant files changed.

- **Output destinations**
  - Support multiple sinks: local workspace (for dev), S3 bucket, SharePoint document library, or data catalog ingestion.
  - Consider encryption or access controls if UDDs contain sensitive columns.

## Tracking & Auditability

- **Change logs**
  - Persist run metadata (timestamp, repo/ref, scan parameters).
  - Diff the newly generated UDD CSV against the previous version to highlight column additions/removals/mapping changes.
  - Emit summary reports for stakeholders (e.g., Slack/email/github comment).

- **Error reporting**
  - Log extraction or parsing failures with file/function context so developers can resolve problematic SQL.
  - Include retry/backoff if remote fetches (git clone) fail.

## Implementation Backlog (future work)

1. Add a CSV exporter aligned with the current UDD schema.
2. Introduce a manifest-driven `--config-set` that scans multiple repos in one run.
3. Build a logging module that writes run metadata and deltas (JSON/CSV).
4. Provide an “output sink” abstraction (local file, S3, SharePoint) to plug into CI/CD.
5. Document the operational playbook (pipelines, permissions, expected artifacts).
