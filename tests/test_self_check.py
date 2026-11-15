import logging

import pytest

from src import recommender as r
from src.recommender import recommend_songs, recommend_with_report, self_check

@pytest.fixture(autouse=True)
def isolated_log(tmp_path, monkeypatch):
    """Keep test log output out of the real logs/app.log."""
    monkeypatch.setattr(r, "LOG_PATH", tmp_path / "logs" / "app.log")
    logger = logging.getLogger("recommender")
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    yield
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()


PROFILE = {
    "favorite_genre": "k-pop", "favorite_mood": "cozy",
    "secondary_genres": [], "secondary_moods": [],
    "target_energy": 0.5, "target_valence": 0.5, "target_danceability": 0.5,
    "target_acousticness": 0.5, "target_tempo_bpm": 100,
}


def song(i, artist=None, genre="rock", mood="calm", energy=0.5):
    return {"id": i, "title": f"S{i:02d}", "artist": artist or f"A{i}", "genre": genre, "mood": mood,
            "energy": energy, "tempo_bpm": 100.0, "valence": 0.5, "danceability": 0.5, "acousticness": 0.5}


def res(score, artist="A", reasons=()):
    return ({"title": "t", "artist": artist}, score, list(reasons))


def flag_codes(results):
    return [code for code, _ in self_check(results)]


def test_clean_set_raises_no_flags():
    results = [res(6.0 - i, f"A{i}", ["genre match (+2.000)"] if i == 0 else []) for i in range(5)]
    assert flag_codes(results) == []


def test_each_flag_fires():
    flat = [res(3.0, f"A{i}") for i in range(5)]
    codes = flag_codes(flat)
    assert r.FLAG_LOW_CONFIDENCE in codes and r.FLAG_NO_LABEL_MATCH in codes and r.FLAG_CLUSTERED in codes
    assert r.FLAG_ARTIST_REPEATED not in codes
    dup = [res(6.0 - i, "Same", ["mood match (+1.000)"]) for i in range(5)]
    assert r.FLAG_ARTIST_REPEATED in flag_codes(dup)


def test_cluster_boundary_is_inclusive_at_025():
    results = [res(3.25, f"A{i}", ["genre match"]) for i in range(4)] + [res(3.0, "A9", ["genre match"])]
    assert r.FLAG_CLUSTERED in flag_codes(results)
    results[-1] = res(2.99, "A9", ["genre match"])
    assert r.FLAG_CLUSTERED not in flag_codes(results)


def test_self_check_handles_empty():
    assert self_check([]) == []


def test_no_label_match_widens_secondary_labels_and_changes_output():
    songs = [song(i, genre="jazz" if i < 3 else "rock", mood="calm" if i < 3 else "tense",
                  energy=0.5 if i < 3 else 0.1 + i * 0.01) for i in range(8)]
    before = recommend_songs(PROFILE, songs, 5, self_check_enabled=False)
    after, notes = recommend_with_report(PROFILE, songs, 5)
    assert not any(rs for _, _, rs in before if any(x.startswith("genre match") for x in rs))
    assert any("widened secondary labels" in n for n in notes)
    assert any("secondary genre match" in x for _, _, rs in after for x in rs)
    assert [sc for _, sc, _ in after] != [sc for _, sc, _ in before]  # label points changed the scores


def test_artist_repeat_is_limited_and_recorded():
    songs = [song(i, artist="Same" if i < 3 else None, genre="pop", mood="happy",
                  energy=0.5 - i * 0.05) for i in range(8)]
    profile = {**PROFILE, "favorite_genre": "pop", "favorite_mood": "happy"}
    results, notes = recommend_with_report(profile, songs, 5)
    artists = [s["artist"] for s, _, _ in results]
    assert artists.count("Same") == r.MAX_PER_ARTIST
    assert len(results) == 5
    assert any("limited to" in n and "Same" in n for n in notes)


def test_notes_are_attached_to_rank_one_reasons():
    songs = [song(i) for i in range(6)]
    results = recommend_songs(PROFILE, songs, 3)
    assert any(x.startswith(r.SELF_CHECK_PREFIX) for x in results[0][2])
    assert not any(x.startswith(r.SELF_CHECK_PREFIX) for _, _, rs in results[1:] for x in rs)


def test_disabled_self_check_matches_plain_ranking():
    songs = [song(i, artist="Same") for i in range(6)]
    results = recommend_songs(PROFILE, songs, 3, self_check_enabled=False)
    assert [s["title"] for s, _, _ in results] == ["S00", "S01", "S02"]
    assert not any(x.startswith(r.SELF_CHECK_PREFIX) for _, _, rs in results for x in rs)


def test_fully_repeated_artist_catalog_still_returns_k():
    songs = [song(i, artist="Same") for i in range(6)]
    assert len(recommend_songs(PROFILE, songs, 4)) == 4


def test_low_confidence_flag_alone():
    results = [res(3.0 - 0.01 * i, f"A{i}", ["mood match"] if i == 0 else []) for i in range(5)]
    codes = flag_codes(results)
    assert r.FLAG_LOW_CONFIDENCE in codes and r.FLAG_NO_LABEL_MATCH not in codes


def test_no_label_match_flag_alone():
    results = [res(6.0 - 1.2 * i, f"A{i}") for i in range(5)]
    codes = flag_codes(results)
    assert r.FLAG_NO_LABEL_MATCH in codes
    assert r.FLAG_CLUSTERED not in codes and r.FLAG_ARTIST_REPEATED not in codes


def test_clustered_scores_flag_alone():
    results = [res(5.0 - 0.05 * i, f"A{i}", ["genre match", "mood match"]) for i in range(5)]
    codes = flag_codes(results)
    assert r.FLAG_CLUSTERED in codes and r.FLAG_NO_LABEL_MATCH not in codes
    assert r.FLAG_ARTIST_REPEATED not in codes


def test_artist_twice_flag_alone():
    results = [res(6.0 - 1.0 * i, "Neon" if i < 2 else f"A{i}", ["genre match"]) for i in range(5)]
    codes = flag_codes(results)
    assert codes == [r.FLAG_ARTIST_REPEATED]


def test_fallback_returns_notes_naming_flag_and_change():
    songs = [song(i, artist="Same" if i < 3 else None, genre="pop", mood="happy",
                  energy=0.5 - i * 0.05) for i in range(8)]
    _, notes = recommend_with_report({**PROFILE, "favorite_genre": "pop", "favorite_mood": "happy"}, songs, 5)
    assert notes[0].startswith("flags before:") and "artist_repeated" in notes[0]
    assert notes[-1] == "flags after: none"
