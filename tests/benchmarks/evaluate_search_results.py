#!/usr/bin/env python3
"""Evaluate ranked search results against relevance judgments."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


DEFAULT_JUDGMENTS = (
    Path(__file__).resolve().parent
    / "relevance_judgments.json"
)


def load_json(path: Path) -> Any:
    """Load a UTF-8 JSON document."""
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def ranked_ids_from_response(
    response: dict[str, Any],
) -> list[str]:
    """Extract ordered grant IDs from an API response."""
    metadatas = response.get("metadatas", [[]])

    if (
        not isinstance(metadatas, list)
        or not metadatas
        or not isinstance(metadatas[0], list)
    ):
        return []

    ranked_ids: list[str] = []

    for metadata in metadatas[0]:
        if not isinstance(metadata, dict):
            continue

        grant_id = (
            metadata.get("grant_id")
            or metadata.get("id")
        )

        if grant_id:
            ranked_ids.append(str(grant_id))

    return ranked_ids


def hit_rate_at_k(
    ranked_ids: list[str],
    relevance: dict[str, int],
    *,
    threshold: int,
    k: int,
) -> float:
    """Return 1 when top-k includes a binary-relevant result."""
    return float(
        any(
            relevance.get(grant_id, 0) >= threshold
            for grant_id in ranked_ids[:k]
        )
    )


def reciprocal_rank_at_k(
    ranked_ids: list[str],
    relevance: dict[str, int],
    *,
    threshold: int,
    k: int,
) -> float:
    """Return reciprocal rank of first relevant result."""
    for rank, grant_id in enumerate(
        ranked_ids[:k],
        start=1,
    ):
        if relevance.get(grant_id, 0) >= threshold:
            return 1.0 / rank

    return 0.0


def discounted_cumulative_gain(
    grades: list[int],
) -> float:
    """Calculate graded discounted cumulative gain."""
    return sum(
        ((2**grade) - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(
            grades,
            start=1,
        )
    )


def ndcg_at_k(
    ranked_ids: list[str],
    relevance: dict[str, int],
    *,
    k: int,
) -> float:
    """Calculate normalized graded DCG at k."""
    observed = [
        relevance.get(grant_id, 0)
        for grant_id in ranked_ids[:k]
    ]

    ideal = sorted(
        relevance.values(),
        reverse=True,
    )[:k]

    ideal_score = discounted_cumulative_gain(ideal)

    if ideal_score == 0:
        return 0.0

    return (
        discounted_cumulative_gain(observed)
        / ideal_score
    )


def evaluate_results(
    result_dir: Path,
    judgments_path: Path = DEFAULT_JUDGMENTS,
) -> dict[str, Any]:
    """Evaluate all JSON responses in a benchmark run."""
    judgments = load_json(judgments_path)
    cases = judgments["queries"]
    threshold = int(
        judgments.get(
            "binary_relevance_threshold",
            2,
        )
    )

    rows: list[dict[str, Any]] = []

    for number, case in enumerate(cases, start=1):
        result_path = result_dir / f"{number:02d}.json"

        if not result_path.is_file():
            raise FileNotFoundError(
                f"Nedostaje rezultat: {result_path}"
            )

        ranked_ids = ranked_ids_from_response(
            load_json(result_path)
        )

        if not ranked_ids:
            raise ValueError(
                f"Nema rangiranih ID-eva: {result_path}"
            )

        if len(ranked_ids) != len(set(ranked_ids)):
            raise ValueError(
                f"Duplicirani grant ID-evi: {result_path}"
            )

        relevance = {
            str(grant_id): int(grade)
            for grant_id, grade
            in case["relevance"].items()
        }

        rows.append(
            {
                "number": number,
                "query": case["query"],
                "hit_rate_at_5": hit_rate_at_k(
                    ranked_ids,
                    relevance,
                    threshold=threshold,
                    k=5,
                ),
                "reciprocal_rank_at_10":
                    reciprocal_rank_at_k(
                        ranked_ids,
                        relevance,
                        threshold=threshold,
                        k=10,
                    ),
                "ndcg_at_10": ndcg_at_k(
                    ranked_ids,
                    relevance,
                    k=10,
                ),
                "ranked_ids": ranked_ids,
            }
        )

    count = len(rows)

    if count == 0:
        raise ValueError("Nema benchmark upita.")

    return {
        "judgments_version": judgments["version"],
        "binary_relevance_threshold": threshold,
        "query_count": count,
        "metrics": {
            "hit_rate_at_5": sum(
                row["hit_rate_at_5"]
                for row in rows
            ) / count,
            "mrr_at_10": sum(
                row["reciprocal_rank_at_10"]
                for row in rows
            ) / count,
            "ndcg_at_10": sum(
                row["ndcg_at_10"]
                for row in rows
            ) / count,
        },
        "queries": rows,
    }


def print_report(report: dict[str, Any]) -> None:
    """Print a concise text report."""
    metrics = report["metrics"]

    print("===== P1 SEARCH BASELINE =====")
    print(f"Queries:   {report['query_count']}")
    print(
        "HitRate@5: "
        f"{metrics['hit_rate_at_5']:.4f}"
    )
    print(f"MRR@10:    {metrics['mrr_at_10']:.4f}")
    print(f"NDCG@10:   {metrics['ndcg_at_10']:.4f}")
    print()
    print("===== PER-QUERY =====")

    for row in report["queries"]:
        print(
            f"{row['number']:02d} "
            f"Hit={row['hit_rate_at_5']:.0f} "
            f"RR={row['reciprocal_rank_at_10']:.4f} "
            f"NDCG={row['ndcg_at_10']:.4f} "
            f"| {row['query']}"
        )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate FinAssistBH search benchmark results."
        )
    )

    parser.add_argument(
        "result_dir",
        type=Path,
        help="Directory containing 01.json through 15.json.",
    )
    parser.add_argument(
        "--judgments",
        type=Path,
        default=DEFAULT_JUDGMENTS,
    )
    parser.add_argument(
        "--json",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    """Run the benchmark evaluator."""
    args = parse_args()

    report = evaluate_results(
        args.result_dir,
        args.judgments,
    )

    if args.json:
        print(
            json.dumps(
                report,
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_report(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
