# Progress — worker_replay_m1

**Last visited**: 2026-09-29T15:23:45Z

## Current Status
- Created `regex_audit/run_filter_replay.py`.
- Executed `regex_audit/run_filter_replay.py` across all 1,137 jobs from `regex_audit/master_raw_dataset_2026-09-29.jsonl`.
- Successfully generated all 4 target JSONL files in `regex_audit/filter_results/`:
  - `layer1_pandas_pass.jsonl` (73 records)
  - `layer1_pandas_fail.jsonl` (1,064 records)
  - `layer2_regex_pass.jsonl` (58 records)
  - `layer2_regex_fail.jsonl` (15 records)
- Confirmed 100% accounting identity:
  - 1,137 raw jobs = 73 Layer 1 pass + 1,064 Layer 1 fail
  - 73 Layer 1 pass = 58 Layer 2 pass + 15 Layer 2 fail
- Schema integrity verified: All records contain full schema metadata including `job_index`, `id`, `title`, `company`, `filter_layer`, `rejection_reason`, `rejection_detail`, `matched_pattern`.
- Verified `src/scraper.py` and `src/scorer.py` remain untouched by this worker.
- Writing final hard handoff report to `handoff.md`.
