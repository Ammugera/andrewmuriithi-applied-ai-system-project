"""
LLM Parser Reliability Harness.

Runs a golden set of natural-language descriptions through the Gemini-backed
parser in src/profile_parser.py and checks that each returned UserProfile
satisfies hand-written constraints about what a sensible interpretation
should look like.

Usage:
    python -m scripts.evaluate_parser          # hits the live Gemini API
    python -m scripts.evaluate_parser --dry    # skip API, report template only

Writes assets/reliability_report.md and prints a one-line summary to stdout.

Why this exists:
    The recommender's scoring engine is deterministic and already covered by
    unit tests. The LLM parser is not — its output depends on a model we don't
    control. This harness asserts falsifiable properties about the parser's
    output on known cases, so we can *measure* reliability, not just hope it
    works.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.profile_parser import ProfileParseError, parse_profile_from_text
from src.profiles import KNOWN_GENRES, KNOWN_MOOD_TAGS

REPORT_PATH = REPO_ROOT / "assets" / "reliability_report.md"


# ---------------------------------------------------------------------------
# Constraint system
# ---------------------------------------------------------------------------

@dataclass
class Constraint:
    field: str          # e.g. "target_energy", "favorite_genre", "__rationale__"
    op: str             # "<", "<=", ">", ">=", "==", "!=", "in", "not_in", "any_in", "len_gt"
    value: Any
    why: str            # human-readable rationale for the check


@dataclass
class GoldenCase:
    name: str
    description: str
    what_it_tests: str
    constraints: List[Constraint]


@dataclass
class CaseResult:
    case: GoldenCase
    errored: bool = False
    error_message: Optional[str] = None
    profile: Optional[dict] = None
    rationale: Optional[str] = None
    checks: List[Tuple[Constraint, bool, Any]] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for _, p, _ in self.checks if p)

    @property
    def total(self) -> int:
        return len(self.checks)


def _check(profile_and_rationale: dict, c: Constraint) -> Tuple[bool, Any]:
    actual = profile_and_rationale.get(c.field)
    if c.op == "<":      return actual < c.value, actual
    if c.op == "<=":     return actual <= c.value, actual
    if c.op == ">":      return actual > c.value, actual
    if c.op == ">=":     return actual >= c.value, actual
    if c.op == "==":     return actual == c.value, actual
    if c.op == "!=":     return actual != c.value, actual
    if c.op == "in":     return actual in c.value, actual
    if c.op == "not_in": return actual not in c.value, actual
    if c.op == "any_in":
        return bool(set(actual or []) & set(c.value)), list(set(actual or []) & set(c.value))
    if c.op == "len_gt": return len(actual or "") > c.value, len(actual or "")
    raise ValueError(f"Unknown op: {c.op}")


# ---------------------------------------------------------------------------
# Golden set — hand-crafted cases covering common user intents + one
# adversarial case that probes how the model handles contradictions.
# ---------------------------------------------------------------------------

CHILL_GENRES = {g for g in {"lofi", "jazz", "folk", "ambient", "classical", "r&b", "soul"} if g in KNOWN_GENRES}
ENERGETIC_EXCLUDED = {g for g in {"classical", "folk", "lofi", "ambient"} if g in KNOWN_GENRES}

GOLDEN_SET: List[GoldenCase] = [
    GoldenCase(
        name="Chill study",
        description="late-night studying, chill but focused",
        what_it_tests="Does the model map 'chill but focused' to low-energy, mellow-tag genres rather than high-energy dance music?",
        constraints=[
            Constraint("target_energy", "<", 0.55, "'chill' implies low energy"),
            Constraint("favorite_genre", "in", CHILL_GENRES, f"must pick a relaxed genre from {sorted(CHILL_GENRES)}"),
            Constraint("preferred_mood_tags", "any_in", {"focused", "mellow", "calm", "dreamy"}, "should surface at least one calm/focus tag"),
        ],
    ),
    GoldenCase(
        name="Gym pump",
        description="gym pump, high-energy and euphoric",
        what_it_tests="Does the model map 'gym pump' to high energy + high danceability, and avoid calm genres?",
        constraints=[
            Constraint("target_energy", ">", 0.70, "'high-energy' means target_energy > 0.7"),
            Constraint("target_danceability", ">", 0.60, "gym music is usually danceable"),
            Constraint("favorite_genre", "not_in", ENERGETIC_EXCLUDED, f"should not pick a mellow genre ({sorted(ENERGETIC_EXCLUDED)})"),
        ],
    ),
    GoldenCase(
        name="Sunday morning",
        description="Sunday morning coffee and journaling, slow and acoustic",
        what_it_tests="Does the model map 'slow and acoustic' to high acousticness and low-to-moderate energy?",
        constraints=[
            Constraint("target_acousticness", ">", 0.55, "'acoustic' implies high acousticness"),
            Constraint("target_energy", "<", 0.55, "'slow' implies low-to-moderate energy"),
        ],
    ),
    GoldenCase(
        name="Sad folk",
        description="I want to cry to something, sad and melancholy",
        what_it_tests="Does the model produce low-valence, low-energy output for clearly sad language?",
        constraints=[
            Constraint("target_valence", "<", 0.50, "'sad' means low valence"),
            Constraint("target_energy", "<", 0.60, "'melancholy' songs are usually low-energy"),
        ],
    ),
    GoldenCase(
        name="80s retro",
        description="80s retro synthwave, driving and nostalgic",
        what_it_tests="Does the model respect an explicit decade cue? Note that the catalog only has decades 1990-2020, so the 'honest' interpretation is the earliest available retro decade.",
        constraints=[
            Constraint("target_decade", "<=", 2010, "should pick an older/retro decade, not 2020 (catalog's earliest is 1990)"),
        ],
    ),
    GoldenCase(
        name="Wedding dance",
        description="something to dance to at a wedding reception, upbeat and happy",
        what_it_tests="Does the model raise danceability and valence for a clear dance-party prompt?",
        constraints=[
            Constraint("target_danceability", ">", 0.60, "'dance to' implies high danceability"),
            Constraint("target_valence", ">", 0.55, "'happy' implies high valence"),
        ],
    ),
    GoldenCase(
        name="Evening wind-down",
        description="calm but not sleepy, an evening wind-down after work",
        what_it_tests="Does the model thread 'calm but not sleepy' into mid-low energy (not near zero)?",
        constraints=[
            Constraint("target_energy", ">=", 0.20, "'not sleepy' means energy shouldn't bottom out"),
            Constraint("target_energy", "<=", 0.55, "'calm' means energy stays low-to-moderate"),
        ],
    ),
    GoldenCase(
        name="Adversarial contradiction",
        description="I want something both extremely calm and extremely loud at the same time",
        what_it_tests="Given a contradictory prompt, does the model make a coherent trade-off and acknowledge the contradiction in its rationale, rather than returning garbage?",
        constraints=[
            Constraint("__rationale__", "len_gt", 40, "rationale should be substantive (> 40 chars), showing the model thought about the contradiction"),
            Constraint("target_energy", ">=", 0.0, "sanity: energy stays in [0, 1] after clamping"),
            Constraint("target_energy", "<=", 1.0, "sanity: energy stays in [0, 1] after clamping"),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def _truncate_error(msg: str, limit: int = 140) -> str:
    """Keep error messages short in the report — the 429 quota error from
    Google dumps a ~800-char JSON blob that wrecks the markdown table."""
    msg = str(msg).replace("\n", " ").strip()
    return msg if len(msg) <= limit else msg[:limit].rstrip() + "…"


def run_case(case: GoldenCase, dry: bool) -> CaseResult:
    result = CaseResult(case=case)
    if dry:
        result.errored = True
        result.error_message = "dry-run: API call skipped"
        return result

    try:
        profile, rationale = parse_profile_from_text(case.description)
    except ProfileParseError as err:
        result.errored = True
        result.error_message = _truncate_error(f"ProfileParseError: {err}")
        return result
    except Exception as err:  # pragma: no cover — defensive
        result.errored = True
        result.error_message = _truncate_error(f"{type(err).__name__}: {err}")
        return result

    result.profile = profile
    result.rationale = rationale
    merged = {**profile, "__rationale__": rationale}
    for c in case.constraints:
        passed, actual = _check(merged, c)
        result.checks.append((c, passed, actual))
    return result


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def _tick(ok: bool) -> str:
    return "✅ Pass" if ok else "❌ Fail"


def _render_constraint_row(idx: int, c: Constraint, passed: bool, actual: Any) -> str:
    expected = _fmt_expected(c)
    return f"| {idx} | `{c.field} {c.op} {_fmt_value(c.value)}` | {expected} | `{actual}` | {_tick(passed)} |"


def _fmt_expected(c: Constraint) -> str:
    if c.op in ("in", "not_in"):
        return f"{'in' if c.op == 'in' else 'not in'} `{sorted(c.value) if isinstance(c.value, set) else c.value}`"
    if c.op == "any_in":
        return f"any of `{sorted(c.value)}`"
    if c.op == "len_gt":
        return f"length > {c.value}"
    return f"{c.op} `{c.value}`"


def _fmt_value(v: Any) -> str:
    if isinstance(v, set):
        return str(sorted(v))
    return str(v)


def render_report(results: List[CaseResult], model_name: str) -> str:
    total_constraints = sum(r.total for r in results)
    total_passed = sum(r.passed for r in results)
    errored = sum(1 for r in results if r.errored)
    non_errored = [r for r in results if not r.errored]
    pct = (total_passed / total_constraints * 100) if total_constraints else 0.0

    lines: List[str] = []
    lines.append("# VibeMatch 2.0 — Parser Reliability Report\n")
    lines.append(f"- **Generated:** {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- **Model:** `{model_name}`")
    lines.append(f"- **Cases:** {len(results)} ({errored} errored)")
    lines.append(f"- **Constraints checked:** {total_constraints}")
    lines.append(f"- **Passed:** {total_passed} ({pct:.1f}%)")
    lines.append(f"- **Failed:** {total_constraints - total_passed}")
    lines.append("")
    lines.append("> This report measures whether the LLM-backed natural-language profile parser")
    lines.append("> produces sensible, predictable output on known inputs. The scoring engine")
    lines.append("> is deterministic and covered by unit tests; this harness covers the non-")
    lines.append("> deterministic piece — the LLM itself.")
    lines.append("")

    lines.append("## Summary")
    lines.append("")
    lines.append("| Case | Passed | Result |")
    lines.append("|---|---|---|")
    for r in results:
        if r.errored:
            lines.append(f"| {r.case.name} | — | ⚠️ Errored ({r.error_message}) |")
        else:
            status = "✅ All pass" if r.passed == r.total else f"❌ {r.total - r.passed} fail"
            lines.append(f"| {r.case.name} | {r.passed}/{r.total} | {status} |")
    lines.append("")

    for r in results:
        lines.append("---")
        lines.append(f"## Case: {r.case.name}\n")
        lines.append(f"> *\"{r.case.description}\"*\n")
        lines.append(f"**What this tests:** {r.case.what_it_tests}\n")

        if r.errored:
            lines.append(f"**⚠️ Errored:** `{r.error_message}`\n")
            continue

        lines.append("### Parsed profile\n")
        lines.append("```json")
        lines.append(json.dumps(r.profile, indent=2, sort_keys=True))
        lines.append("```\n")
        lines.append("### Rationale from the model\n")
        lines.append(f"> {r.rationale}\n")
        lines.append("### Constraint checks\n")
        lines.append("| # | Check | Expected | Actual | Result |")
        lines.append("|---|---|---|---|---|")
        for i, (c, passed, actual) in enumerate(r.checks, start=1):
            lines.append(_render_constraint_row(i, c, passed, actual))
        lines.append("")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry", action="store_true", help="Skip the live API call — useful for report-template iteration.")
    parser.add_argument("--model", default="gemini-2.5-flash", help="Informational only; the model is selected inside profile_parser.py.")
    args = parser.parse_args()

    if args.dry:
        print("[dry-run] Skipping live Gemini calls.", file=sys.stderr)

    # Gemini 2.5 Flash free tier is 5 RPM — pace the live calls so we don't
    # trip a 429. 13 seconds between calls gives a small safety margin.
    PACE_SECONDS = 0 if args.dry else 13

    print(f"Running {len(GOLDEN_SET)} cases through the parser...", file=sys.stderr)
    start = time.time()
    results: List[CaseResult] = []
    for i, case in enumerate(GOLDEN_SET, start=1):
        print(f"  [{i}/{len(GOLDEN_SET)}] {case.name}...", file=sys.stderr)
        results.append(run_case(case, dry=args.dry))
        if PACE_SECONDS and i < len(GOLDEN_SET):
            time.sleep(PACE_SECONDS)
    elapsed = time.time() - start

    report_md = render_report(results, model_name=args.model)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report_md)

    total_constraints = sum(r.total for r in results)
    total_passed = sum(r.passed for r in results)
    pct = (total_passed / total_constraints * 100) if total_constraints else 0.0
    errored = sum(1 for r in results if r.errored)

    summary = (
        f"Done in {elapsed:.1f}s. "
        f"Passed {total_passed}/{total_constraints} constraints ({pct:.1f}%). "
        f"{errored} cases errored. "
        f"Report written to {REPORT_PATH.relative_to(REPO_ROOT)}"
    )
    print(summary)
    return 0 if errored == 0 and total_passed == total_constraints else 1


if __name__ == "__main__":
    sys.exit(main())
