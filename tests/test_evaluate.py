import logging

import pytest

from src import evaluate, recommender


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    """Keep test log output out of the real logs/app.log."""
    monkeypatch.setattr(recommender, "LOG_PATH", tmp_path / "logs" / "app.log")
    logger = logging.getLogger("recommender")
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    yield
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()


@pytest.fixture(scope="module")
def rows():
    return evaluate.run_all()


def test_runs_every_profile_without_crashing(rows):
    assert len(rows) == len(evaluate.build_cases()) >= 13
    crashed = [r.case.name for r in rows if r.crashed]
    assert crashed == []


def test_all_profiles_meet_pass_criteria(rows):
    assert [(r.case.name, r.failures) for r in rows if not r.passed] == []


def test_table_has_required_columns_and_a_row_per_profile(rows):
    lines = evaluate.render_table(rows).splitlines()
    assert lines[0] == ("| Profile | Input issue | Guardrail fired | Confidence | "
                        "Self-check result | Pass/Fail |")
    assert len(lines) == 2 + len(rows)


def test_400_bpm_case_reports_clamp_guardrail(rows):
    row = next(r for r in rows if r.case.name == "out_of_range_tempo")
    assert "clamp" in row.guardrails


def test_failing_criterion_is_reported_as_fail():
    case = evaluate.Case("x", "bad input", evaluate._good(), "pretend issue", {"missing key"})
    row = evaluate.evaluate_case(case, evaluate.load_songs(str(evaluate.SONGS_PATH)))
    assert not row.passed and not row.crashed
    assert any(f.startswith("P5") for f in row.failures)


def test_main_saves_a_copy_of_the_report(tmp_path, capsys):
    out = tmp_path / "evaluation_output.txt"
    exit_code = evaluate.main(out)
    printed = capsys.readouterr().out
    assert exit_code == 0
    assert out.read_text(encoding="utf-8") == printed
    assert "Pass criteria:" in printed and "13/13 profiles passed." in printed
