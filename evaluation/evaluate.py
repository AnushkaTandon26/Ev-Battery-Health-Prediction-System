#!/usr/bin/env python3
"""Reproducible NLP evaluation for the EV battery diagnostic reporter.

Runs the deterministic NLG pipeline over a fixed, versioned corpus
(``corpus.json``) and reports measurable quality metrics. It also compares the
context-aware generator against the naive fixed-template baseline.

Metrics (see PRD section 13 / TRD section 15):
  * diagnostic fact (finding) coverage       - did expected findings appear?
  * factual consistency / grounding pass rate - does the report survive the
                                                grounding+schema validators?
  * unsupported-claim rate                    - share of reports with any
                                                grounding violation
  * recommendation coverage                   - do findings get an action?
  * readability (Flesch Reading Ease, approx.)
  * redundancy (duplicate-sentence ratio)
  * generation latency (ms, per report)
  * ROUGE-1 F1 vs reference reports (lexical-overlap only; NOT a correctness
    measure - stated explicitly below)

IMPORTANT: BLEU/ROUGE measure textual similarity to a reference, not diagnostic
correctness. The corpus is synthetic. Metrics are reported as measured; no
targets are claimed as achieved.

Usage:
    python evaluation/evaluate.py
    python evaluation/evaluate.py --json out.json
Standard library + the project's nlg package only (no external deps).
"""

import argparse
import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "backend")))

from nlg.report_generator import generate_report, build_report_object  # noqa: E402
from nlg.fact_extractor import build_facts  # noqa: E402
from nlg.report_planner import plan_report  # noqa: E402
from nlg.diagnostic_rules import evaluate as rules_evaluate, detect_conflicts  # noqa: E402
from nlg.sentence_realizer import realize  # noqa: E402


# --------------------------- text metrics ---------------------------

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD = re.compile(r"[A-Za-z]+")


def _sentences(text):
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def _count_syllables(word):
    word = word.lower()
    groups = re.findall(r"[aeiouy]+", word)
    count = len(groups)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def flesch_reading_ease(text):
    words = _WORD.findall(text)
    sents = _sentences(text)
    if not words or not sents:
        return 0.0
    syllables = sum(_count_syllables(w) for w in words)
    wps = len(words) / len(sents)
    spw = syllables / len(words)
    return round(206.835 - 1.015 * wps - 84.6 * spw, 1)


def redundancy_ratio(text):
    """Fraction of sentences that are exact duplicates of an earlier one."""
    sents = [s.lower() for s in _sentences(text)]
    if not sents:
        return 0.0
    seen = set()
    dupes = 0
    for s in sents:
        if s in seen:
            dupes += 1
        seen.add(s)
    return round(dupes / len(sents), 3)


def rouge1_f1(candidate, reference):
    """Unigram ROUGE-1 F1 (lexical overlap only)."""
    cand = _WORD.findall(candidate.lower())
    ref = _WORD.findall(reference.lower())
    if not cand or not ref:
        return 0.0
    from collections import Counter
    cc, rc = Counter(cand), Counter(ref)
    overlap = sum((cc & rc).values())
    if overlap == 0:
        return 0.0
    prec = overlap / len(cand)
    rec = overlap / len(ref)
    return round(2 * prec * rec / (prec + rec), 3)


# --------------------------- evaluation ---------------------------

def load_corpus():
    with open(os.path.join(_HERE, "corpus.json"), encoding="utf-8") as fh:
        return json.load(fh)


def evaluate_method(corpus, method):
    per_case = []
    for sc in corpus["scenarios"]:
        tel = dict(sc["telemetry"])
        tel["temperature"] = tel.pop("temp", tel.get("temperature"))
        recent = sc.get("recent_records")

        t0 = time.perf_counter()
        env = generate_report(
            sc["telemetry"], sc["prediction"], record_id=1,
            recent_records=recent, method=method)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        row = {"id": sc["id"], "status": env["report_status"],
               "latency_ms": round(latency_ms, 2)}

        if env["report_status"] != "generated":
            row.update({"grounded": False, "coverage": 0.0,
                        "rec_coverage": 0.0, "flesch": 0.0,
                        "redundancy": 0.0, "rouge1": 0.0,
                        "unsupported": True})
            per_case.append(row)
            continue

        report = env["report"]
        text = report.get("_rendered_text", "")

        got_codes = {f["code"] for f in report["findings"]}
        expected = set(sc["expected_finding_codes"])
        coverage = 1.0 if not expected else len(got_codes & expected) / len(expected)

        # recommendation coverage: fraction of non-info findings that have at
        # least one recommendation referencing them.
        linked = set()
        for rec in report["recommendations"]:
            linked.update(rec.get("related_finding_codes", []))
        actionable = {f["code"] for f in report["findings"]
                      if f["severity"] not in ("info",)}
        rec_cov = 1.0 if not actionable else len(linked & actionable) / len(actionable)

        grounded = not env["grounding_errors"] and not env["schema_errors"]

        row.update({
            "grounded": grounded,
            "unsupported": bool(env["grounding_errors"]),
            "coverage": round(coverage, 3),
            "rec_coverage": round(rec_cov, 3),
            "flesch": flesch_reading_ease(text),
            "redundancy": redundancy_ratio(text),
            "rouge1": rouge1_f1(text, sc.get("reference_report", "")),
            "word_count": len(_WORD.findall(text)),
        })
        per_case.append(row)
    return per_case


def summarize(per_case):
    generated = [c for c in per_case if c["status"] == "generated"]
    n = len(per_case)
    g = len(generated)

    def avg(key):
        vals = [c[key] for c in generated if key in c]
        return round(sum(vals) / len(vals), 3) if vals else 0.0

    return {
        "cases": n,
        "generation_success_rate": round(g / n, 3) if n else 0.0,
        "grounding_pass_rate": round(
            sum(1 for c in generated if c["grounded"]) / g, 3) if g else 0.0,
        "unsupported_claim_rate": round(
            sum(1 for c in generated if c["unsupported"]) / g, 3) if g else 0.0,
        "avg_finding_coverage": avg("coverage"),
        "avg_recommendation_coverage": avg("rec_coverage"),
        "avg_flesch_reading_ease": avg("flesch"),
        "avg_redundancy_ratio": avg("redundancy"),
        "avg_rouge1_f1_vs_reference": avg("rouge1"),
        "avg_word_count": avg("word_count"),
        "avg_latency_ms": avg("latency_ms"),
        "p95_latency_ms": round(sorted(c["latency_ms"] for c in generated)[
            max(0, int(0.95 * g) - 1)], 2) if g else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="write full results to this JSON file")
    args = ap.parse_args()

    corpus = load_corpus()
    results = {}
    for method in ("context_aware", "baseline"):
        per_case = evaluate_method(corpus, method)
        results[method] = {"summary": summarize(per_case), "cases": per_case}

    print(f"EV Battery NLG Evaluation  (corpus v{corpus['corpus_version']}, "
          f"{len(corpus['scenarios'])} synthetic scenarios)")
    print("=" * 70)
    print("NOTE: ROUGE-1 measures lexical overlap with a reference text, not")
    print("      diagnostic correctness. All scenarios are synthetic.")
    print()

    ca = results["context_aware"]["summary"]
    bl = results["baseline"]["summary"]
    rows = [
        ("Generation success rate", "generation_success_rate"),
        ("Grounding pass rate", "grounding_pass_rate"),
        ("Unsupported-claim rate", "unsupported_claim_rate"),
        ("Avg finding coverage", "avg_finding_coverage"),
        ("Avg recommendation coverage", "avg_recommendation_coverage"),
        ("Avg Flesch reading ease", "avg_flesch_reading_ease"),
        ("Avg redundancy ratio", "avg_redundancy_ratio"),
        ("Avg ROUGE-1 F1 vs ref", "avg_rouge1_f1_vs_reference"),
        ("Avg word count", "avg_word_count"),
        ("Avg latency (ms)", "avg_latency_ms"),
        ("P95 latency (ms)", "p95_latency_ms"),
    ]
    print(f"{'Metric':<34}{'context_aware':>16}{'baseline':>14}")
    print("-" * 70)
    for label, key in rows:
        print(f"{label:<34}{ca[key]:>16}{bl[key]:>14}")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2)
        print(f"\nFull results written to {args.json}")


if __name__ == "__main__":
    main()
