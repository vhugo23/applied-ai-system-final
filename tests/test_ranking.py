from src.recommender import recommend_songs

PROFILE = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "secondary_genres": [],
    "secondary_moods": [],
    "target_energy": 0.8,
    "target_valence": 0.8,
    "target_danceability": 0.8,
    "target_acousticness": 0.2,
    "target_tempo_bpm": 120,
}


def make_song(title, **overrides):
    song = {
        "id": 1, "title": title, "artist": "Test Artist",
        "genre": "pop", "mood": "happy", "energy": 0.8, "tempo_bpm": 120.0,
        "valence": 0.8, "danceability": 0.8, "acousticness": 0.2,
    }
    song.update(overrides)
    return song


def test_tie_break_sorts_equal_scores_by_title():
    songs = [make_song("Zebra"), make_song("Apple"), make_song("Mango")]
    results = recommend_songs(PROFILE, songs, k=3)

    assert len({score for _, score, _ in results}) == 1  # scores really are tied
    assert [song["title"] for song, _, _ in results] == ["Apple", "Mango", "Zebra"]


def test_recommend_songs_returns_k_results_sorted_high_to_low():
    songs = [
        make_song("Low", genre="rock", mood="sad", energy=0.1, tempo_bpm=60.0),
        make_song("High"),
        make_song("Mid", genre="rock", energy=0.6),
        make_song("Lower", genre="rock", mood="sad", energy=0.3),
    ]
    results = recommend_songs(PROFILE, songs, k=3)
    scores = [score for _, score, _ in results]

    assert len(results) == 3
    assert scores == sorted(scores, reverse=True)
    assert results[0][0]["title"] == "High"
