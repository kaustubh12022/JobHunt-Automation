"""
Production & Benchmark Scoring Audit Runner.

Runs high-throughput, rate-limited, fault-tolerant scoring runs across:
1. Synthetic Benchmark Dataset (300 JDs)
2. Real Production Jobs (~73 JDs)

Supports both Gemini and Groq in parallel pipelines.
Strictly excludes DeepSeek.
Saves incremental JSONL results with automatic resumption.
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scoring_audit.ai_engine_v2 import DualProviderScoringEngine, ScoringResult

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [scorer_runner] %(message)s",
)
logger = logging.getLogger("scorer_runner")


def load_synthetic_jds(file_path: Path) -> List[Dict[str, Any]]:
    """Load the 300 synthetic test JDs."""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} synthetic JDs from {file_path}")
    return data


def load_real_jobs(file_path: Path) -> List[Dict[str, Any]]:
    """Load the ~73 real jobs that survived regex filtering."""
    jobs = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                jobs.append(json.loads(line))
    logger.info(f"Loaded {len(jobs)} real jobs from {file_path}")
    return jobs


def load_existing_scored_ids(jsonl_path: Path, id_field: str = "id") -> Set[str]:
    """Read existing jsonl output to resume without re-scoring already completed jobs."""
    scored_ids = set()
    if not jsonl_path.exists():
        return scored_ids

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                rec_id = str(rec.get(id_field) or rec.get("synthetic_id") or rec.get("job_id"))
                if rec_id:
                    scored_ids.add(rec_id)
            except Exception:
                pass
    return scored_ids


async def score_dataset_for_provider(
    dataset: List[Dict[str, Any]],
    provider: str,
    prompt_path: Path,
    output_path: Path,
    is_synthetic: bool,
    engine: DualProviderScoringEngine,
) -> None:
    """Score a dataset for a single provider sequentially (pacing handled by rate limiter)."""
    id_field = "id" if is_synthetic else "id"
    existing_ids = load_existing_scored_ids(output_path, id_field=id_field)
    logger.info(
        f"[{provider.upper()}] Starting scoring on {'synthetic' if is_synthetic else 'real'} dataset: "
        f"{len(dataset)} total, {len(existing_ids)} already scored, {len(dataset) - len(existing_ids)} remaining."
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "a", encoding="utf-8", buffering=1) as out_f:
        for idx, item in enumerate(dataset, start=1):
            item_id = str(item.get("id") or item.get("synthetic_id") or item.get("job_id"))
            if item_id in existing_ids:
                continue

            jd_text = item.get("description", "")
            title = item.get("title", "")
            category = item.get("category", "")
            ground_truth = item.get("ground_truth", {})

            t0 = time.perf_counter()
            try:
                res: ScoringResult = await engine.score_job(
                    jd_text=jd_text,
                    provider=provider,
                    prompt_template_path=prompt_path,
                )
                latency = round(time.perf_counter() - t0, 3)

                # Ground truth comparison if available
                within_expected = None
                if is_synthetic and ground_truth:
                    min_s = ground_truth.get("expected_min_score", 0)
                    max_s = ground_truth.get("expected_max_score", 100)
                    within_expected = min_s <= res.fit_score <= max_s

                record = {
                    "id": item_id,
                    "title": title,
                    "category": category,
                    "provider": provider,
                    "model": res.model or (engine.gemini_model if provider == "gemini" else engine.groq_model),
                    "fit_score": res.fit_score,
                    "match_score": res.match_score,
                    "is_testing_role": res.is_testing_role,
                    "missing_skills": res.missing_skills,
                    "reasoning": res.reasoning,
                    "reason": res.reason,
                    "latency_seconds": latency,
                    "scored_at": datetime.now(timezone.utc).isoformat(),
                }

                if is_synthetic:
                    record["expected_score_range"] = [
                        ground_truth.get("expected_min_score"),
                        ground_truth.get("expected_max_score"),
                    ]
                    record["expected_is_testing_role"] = ground_truth.get("is_testing_role")
                    record["expected_missing_skills"] = ground_truth.get("expected_missing_skills", [])
                    record["score_within_expected"] = within_expected

                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_f.flush()
                existing_ids.add(item_id)

                if len(existing_ids) % 10 == 0 or len(existing_ids) == len(dataset):
                    logger.info(
                        f"[{provider.upper()}] Progress: {len(existing_ids)}/{len(dataset)} jobs scored. "
                        f"(Last: {title[:30]} -> {res.fit_score} in {latency}s)"
                    )

            except Exception as e:
                logger.error(f"[{provider.upper()}] Error scoring job {item_id} ({title}): {e}")
                # Wait briefly before continuing to prevent spin loops
                await asyncio.sleep(2.0)

    logger.info(f"[{provider.upper()}] Completed scoring on {output_path.name}")


async def main_async():
    parser = argparse.ArgumentParser(description="Run AI scoring audit across Gemini and Groq")
    parser.add_argument("--prompt", type=str, default="src/prompts/scoring_prompt.txt", help="Prompt template path")
    parser.add_argument("--synthetic", action="store_true", default=True, help="Score synthetic dataset")
    parser.add_argument("--real", action="store_true", default=True, help="Score real jobs dataset")
    parser.add_argument("--providers", nargs="+", default=["gemini", "groq"], help="Providers to score with")
    parser.add_argument("--prefix", type=str, default="", help="Prefix for output file names (e.g. 'v2_')")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    prompt_path = project_root / args.prompt
    synthetic_path = project_root / "scoring_audit/synthetic_jds.json"
    real_path = project_root / "regex_audit/filter_results/layer1_pandas_pass.jsonl"
    scores_dir = project_root / "scoring_audit/scores"
    scores_dir.mkdir(parents=True, exist_ok=True)

    engine = DualProviderScoringEngine()

    synthetic_jds = load_synthetic_jds(synthetic_path) if (args.synthetic and synthetic_path.exists()) else []
    real_jobs = load_real_jobs(real_path) if (args.real and real_path.exists()) else []

    async def run_pipeline_for_provider(prov: str):
        if synthetic_jds:
            out_file = scores_dir / f"{args.prefix}synthetic_{prov}_scores.jsonl"
            await score_dataset_for_provider(
                dataset=synthetic_jds,
                provider=prov,
                prompt_path=prompt_path,
                output_path=out_file,
                is_synthetic=True,
                engine=engine,
            )
        if real_jobs:
            out_file = scores_dir / f"{args.prefix}real_{prov}_scores.jsonl"
            await score_dataset_for_provider(
                dataset=real_jobs,
                provider=prov,
                prompt_path=prompt_path,
                output_path=out_file,
                is_synthetic=False,
                engine=engine,
            )

    provider_tasks = [run_pipeline_for_provider(p) for p in args.providers]
    logger.info(f"Starting {len(provider_tasks)} parallel provider pipelines: {', '.join(args.providers)}...")
    await asyncio.gather(*provider_tasks)
    logger.info("All scoring pipelines completed successfully!")


if __name__ == "__main__":
    asyncio.run(main_async())
