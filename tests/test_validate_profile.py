import logging
import re
from pathlib import Path

import pytest

from src import recommender
from src.recommender import load_songs, recommend_songs, validate_profile

CATALOG = [
    {"id": 1, "title": "A", "artist": "X", "genre": "pop", "mood": "happy", "energy": 0.8,
     "tempo_bpm": 120.0, "valence": 0.8, "danceability": 0.8, "acousticness": 0.2},
]

GOOD = {
    "favorite_genre": "pop", "favorite_mood": "happy",
    "secondary_genres": [], "secondary_moods": [],
    "target_energy": 0.8, "target_valence": 0.8, "target_danceability": 0.8,
    "target_acousticness": 0.2, "target_tempo_bpm": 120,
}


@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    """Send log output to a temp file and reset the handler so tests don't touch logs/app.log."""
    log_file = tmp_path / "logs" / "app.log"
    monkeypatch.setattr(recommender, "LOG_PATH", log_file)
    logger = logging.getLogger("recommender")
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    yield log_file
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()


def with_(**overrides):
    return {**GOOD, **overrides}


def test_valid_profile_has_no_warnings():
    clean, warnings = validate_profile(GOOD, CATALOG)
    assert warnings == []
    assert clean == GOOD


def test_does_not_mutate_input():
    bad = with_(target_energy=5)
    validate_profile(bad, CATALOG)
    assert bad["target_energy"] == 5


@pytest.mark.parametrize("key", ["target_energy", "target_valence",
                                 "target_danceability", "target_acousticness"])
def test_unit_features_clamped_high_and_low(key):
    clean, warnings = validate_profile(with_(**{key: 1.7}), CATALOG)
    assert clean[key] == 1.0 and len(warnings) == 1
    clean, warnings = validate_profile(with_(**{key: -0.3}), CATALOG)
    assert clean[key] == 0.0 and len(warnings) == 1


def test_tempo_400_bpm_clamped_to_200():
    clean, warnings = validate_profile(with_(target_tempo_bpm=400), CATALOG)
    assert clean["target_tempo_bpm"] == 200
    assert any("target_tempo_bpm" in w and "clamped" in w for w in warnings)


def test_tempo_too_low_clamped_to_40():
    clean, _ = validate_profile(with_(target_tempo_bpm=5), CATALOG)
    assert clean["target_tempo_bpm"] == 40


def test_in_range_values_untouched():
    clean, warnings = validate_profile(with_(target_energy=1.0, target_tempo_bpm=40), CATALOG)
    assert clean["target_energy"] == 1.0 and clean["target_tempo_bpm"] == 40
    assert warnings == []


def test_unknown_genre_warns():
    _, warnings = validate_profile(with_(favorite_genre="polka"), CATALOG)
    assert any("favorite_genre" in w and "catalog" in w for w in warnings)


def test_unknown_mood_warns():
    _, warnings = validate_profile(with_(favorite_mood="melancholy"), CATALOG)
    assert any("favorite_mood" in w and "catalog" in w for w in warnings)


@pytest.mark.parametrize("key", list(GOOD))
def test_missing_key_warns_and_does_not_raise(key):
    profile = {k: v for k, v in GOOD.items() if k != key}
    clean, warnings = validate_profile(profile, CATALOG)
    assert any(f"missing required key: {key}" in w for w in warnings)
    assert key in clean  # filled so scoring can't KeyError


@pytest.mark.parametrize("bad", [None, "pop", 42, [], {}])
def test_never_raises_on_non_dict_or_empty(bad):
    clean, warnings = validate_profile(bad, CATALOG)
    assert isinstance(clean, dict) and warnings


@pytest.mark.parametrize("value", ["loud", None, float("nan"), True, [1]])
def test_non_numeric_value_does_not_raise(value):
    clean, warnings = validate_profile(with_(target_energy=value, target_tempo_bpm=value), CATALOG)
    assert clean["target_energy"] == 0.5 and clean["target_tempo_bpm"] == 120
    assert warnings


def test_warnings_are_logged_to_file(isolated_log):
    _, warnings = validate_profile(with_(target_tempo_bpm=400, favorite_genre="polka"), CATALOG)
    for h in logging.getLogger("recommender").handlers:
        h.flush()
    text = isolated_log.read_text(encoding="utf-8")
    assert len(warnings) == 2
    assert text.count("WARNING") == 2
    assert "clamped to 200" in text and "polka" in text


def test_recommend_songs_uses_validation_and_survives_bad_profile():
    results = recommend_songs(with_(target_tempo_bpm=400, target_energy=9), CATALOG, k=1)
    assert len(results) == 1
    # Tempo clamped to 200: similarity uses 1 - |120-200|/160 = 0.5, not a negative value.
    assert any("tempo" in r for r in results[0][2])
    assert recommend_songs({}, CATALOG, k=1)  # empty profile still returns results


def _reason_total(reasons):
    return sum(float(m) for r in reasons for m in re.findall(r"\(\+([0-9.]+)\)", r))


def test_400_bpm_reasons_sum_to_score_for_every_song():
    songs = load_songs(str(Path(__file__).resolve().parent.parent / "data" / "songs.csv"))
    profile = with_(target_tempo_bpm=400)
    for self_check_enabled in (False, True):
        results = recommend_songs(profile, songs, k=len(songs), self_check_enabled=self_check_enabled)
        for song, score, reasons in results:
            # each reason is printed to 3 decimals, so allow 0.0005 of rounding per term
            assert _reason_total(reasons) == pytest.approx(score, abs=0.0005 * len(reasons)), song["title"]
            assert any(r.startswith("tempo close to target") for r in reasons)
