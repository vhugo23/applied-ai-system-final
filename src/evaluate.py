"""
Evaluation harness: runs every baseline, adversarial and bad-input profile through the
recommender and prints a markdown table of what each guardrail did.

Run it from the project root with: python -m src.evaluate
"""

import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from src.experiments import ADVERSARIAL_PROFILES, CORE_PROFILES
from src.recommender import (
    SELF_CHECK_MIN_CONFIDENCE,
    load_songs,
    recommend_songs,
    recommend_with_report,
    recommendation_confidence,
    self_check,
    validate_profile,
)

SONGS_PATH = Path(__file__).resolve().parent.parent / "data" / "songs.csv"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "evaluation_output.txt"

# --- Pass criteria (every one must hold for a row to Pass) -------------------------------
EVAL_K = 5               # P2: exactly this many results come back (catalog is larger)
MAX_SCORE = 7.0          # P3: every score is finite and within 0..MAX_SCORE
PASS_CRITERIA = (
    "P1 no exception is raised",
    f"P2 exactly {EVAL_K} results are returned",
    f"P3 every score is finite and within 0-{MAX_SCORE}",
    "P4 confidence is within 0-1",
    "P5 every guardrail the case declares as expected actually fired",
    "P6 a clean input (no declared issue) fires no validation guardrail",
    f"P7 after self-check no flag remains, or confidence is at least {SELF_CHECK_MIN_CONFIDENCE}",
)

# validate_profile warning text -> guardrail label
VALIDATION_GUARDRAILS = (
    ("clamped", "clamp"),
    ("missing required key", "missing key"),
    ("not in the catalog", "unknown label"),
    ("is not a number", "type fix"),
    ("is not a string", "type fix"),
    ("is not a list", "type fix"),
    ("is not a dict", "type fix"),
    ("unexpected error", "validation error"),
)
# self-check note prefix -> fallback label
FALLBACK_GUARDRAILS = (
    ("widened", "widen labels"),
    ("switched to numeric-only", "numeric-only"),
    ("limited to", "artist cap"),
)


@dataclass
class Case:
    name: str
    group: str                       # baseline | adversarial | bad input
    profile: object
    issue: str                       # "none" for a clean profile
    expect: Optional[Set[str]] = None  # guardrail labels that must fire (None = no requirement)


@dataclass
class Row:
    case: Case
    guardrails: List[str]
    confidence: Optional[float]
    self_check: str
    passed: bool
    crashed: bool
    failures: List[str]


def _good(**overrides) -> dict:
    profile = {
        "favorite_genre": "pop", "favorite_mood": "happy",
        "secondary_genres": [], "secondary_moods": [],
        "target_energy": 0.8, "target_valence": 0.8, "target_danceability": 0.8,
        "target_acousticness": 0.2, "target_tempo_bpm": 120,
    }
    profile.update(overrides)
    return profile


def _without(*keys: str) -> dict:
    return {k: v for k, v in _good().items() if k not in keys}


ADVERSARIAL_META = {
    "conflicting_sad_but_hyper": ("conflicting targets: calm, sad, acoustic but max energy and fast tempo", None),
    "unknown_labels": ("genre and mood not in the catalog", {"unknown label"}),
    "out_of_range_tempo": ("tempo 400 BPM, outside 40-200", {"clamp"}),
}

BAD_INPUT_CASES = (
    Case("missing_keys", "bad input", _without("target_energy", "secondary_genres", "secondary_moods"),
         "required keys missing", {"missing key"}),
    Case("empty_profile", "bad input", {}, "empty dict", {"missing key"}),
    Case("none_profile", "bad input", None, "profile is None", {"type fix"}),
    Case("non_numeric_targets", "bad input", _good(target_energy="loud", target_tempo_bpm=None),
         "non-numeric energy and tempo", {"type fix"}),
    Case("nan_target", "bad input", _good(target_valence=float("nan")), "NaN valence", {"type fix"}),
    Case("out_of_range_features", "bad input", _good(target_energy=5, target_valence=-2),
         "energy 5 and valence -2, outside 0-1", {"clamp"}),
    Case("wrong_label_types", "bad input", _good(favorite_genre=123, secondary_genres="rock"),
         "genre is a number, secondary genres is a string", {"type fix"}),
)


def build_cases() -> List[Case]:
    """Every profile the harness runs: baseline, adversarial, then bad-input cases."""
    cases = [Case(name, "baseline", profile, "none") for name, profile in CORE_PROFILES.items()]
    for name, profile in ADVERSARIAL_PROFILES.items():
        issue, expect = ADVERSARIAL_META.get(name, ("adversarial profile", None))
        cases.append(Case(name, "adversarial", profile, issue, expect))
    cases.extend(BAD_INPUT_CASES)
    return cases


def _validation_guardrails(profile, songs) -> List[str]:
    _, warnings = validate_profile(profile, songs)
    fired = []
    for warning in warnings:
        for text, label in VALIDATION_GUARDRAILS:
            if text in warning and label not in fired:
                fired.append(label)
    return fired


def evaluate_case(case: Case, songs: List[Dict]) -> Row:
    """Run one case and apply the pass criteria. Never raises."""
    failures: List[str] = []
    try:
        guardrails = _validation_guardrails(case.profile, songs)
        before = recommend_songs(case.profile, songs, EVAL_K, self_check_enabled=False)
        flags_before = [code for code, _ in self_check(before)]
        results, notes = recommend_with_report(case.profile, songs, EVAL_K)
        flags_after = [code for code, _ in self_check(results)]
        confidence = recommendation_confidence(results)
    except Exception as exc:  # P1
        return Row(case, [], None, "crashed", False, True, [f"P1 raised {type(exc).__name__}: {exc}"])

    for prefix, label in FALLBACK_GUARDRAILS:
        if any(note.startswith(prefix) for note in notes) and label not in guardrails:
            guardrails.append(label)

    if len(results) != EVAL_K:
        failures.append(f"P2 got {len(results)} results")
    scores = [score for _, score, _ in results]
    if not all(math.isfinite(s) and 0 <= s <= MAX_SCORE for s in scores):
        failures.append("P3 score out of range")
    if not 0 <= confidence <= 1:
        failures.append("P4 confidence out of range")
    missing = (case.expect or set()) - set(guardrails)
    if missing:
        failures.append(f"P5 expected guardrail did not fire: {sorted(missing)}")
    validation_fired = _validation_guardrails(case.profile, songs)
    if case.issue == "none" and validation_fired:
        failures.append(f"P6 clean input fired {validation_fired}")
    if flags_after and confidence < SELF_CHECK_MIN_CONFIDENCE:
        failures.append(f"P7 unresolved flags {flags_after} with confidence {confidence:.2f}")

    if not flags_before:
        outcome = "clean"
    elif not flags_after:
        outcome = f"fixed: {', '.join(flags_before)}"
    else:
        outcome = f"residual: {', '.join(flags_after)} (was {', '.join(flags_before)})"
    return Row(case, guardrails, confidence, outcome, not failures, False, failures)


def run_all(songs: Optional[List[Dict]] = None) -> List[Row]:
    songs = songs if songs is not None else load_songs(str(SONGS_PATH))
    return [evaluate_case(case, songs) for case in build_cases()]


def _cell(text: str) -> str:
    return text.replace("|", "/")


def render_table(rows: List[Row]) -> str:
    lines = ["| Profile | Input issue | Guardrail fired | Confidence | Self-check result | Pass/Fail |",
             "|---|---|---|---|---|---|"]
    for row in rows:
        confidence = "n/a" if row.confidence is None else f"{row.confidence:.2f}"
        verdict = "Pass" if row.passed else "Fail: " + "; ".join(row.failures)
        lines.append("| " + " | ".join(_cell(c) for c in (
            f"{row.case.name} ({row.case.group})", row.case.issue,
            ", ".join(row.guardrails) or "none", confidence, row.self_check, verdict)) + " |")
    return "\n".join(lines)


def render_report(rows: List[Row]) -> str:
    """The full report: the markdown table, the pass criteria and a summary line."""
    failed = sum(not r.passed for r in rows)
    lines = [render_table(rows), "", "Pass criteria:"]
    lines += [f"- {criterion}" for criterion in PASS_CRITERIA]
    lines += ["", f"{len(rows) - failed}/{len(rows)} profiles passed."]
    return "\n".join(lines)


def main(output_path: Path = OUTPUT_PATH) -> int:
    """Print the report, save a copy to output_path, and return 1 if any profile failed."""
    rows = run_all()
    report = render_report(rows)
    print(report)
    output_path.write_text(report + "\n", encoding="utf-8")
    return 1 if any(not r.passed for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
