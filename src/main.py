"""
Command line runner for the Music Recommender Simulation.

Run it from the project root with: python -m src.main
"""

from src.recommender import load_songs, recommend_songs

CHILL_LOFI = {
    "favorite_genre": "lofi",
    "favorite_mood": "chill",
    "secondary_genres": ["ambient", "jazz", "folk"],
    "secondary_moods": ["focused", "relaxed"],
    "target_energy": 0.35,
    "target_valence": 0.55,
    "target_danceability": 0.55,
    "target_acousticness": 0.70,
    "target_tempo_bpm": 76,
}

INTENSE_ROCK = {
    "favorite_genre": "rock",
    "favorite_mood": "intense",
    "secondary_genres": ["metal"],
    "secondary_moods": ["aggressive"],
    "target_energy": 0.90,
    "target_valence": 0.40,
    "target_danceability": 0.50,
    "target_acousticness": 0.10,
    "target_tempo_bpm": 150,
}

HIGH_ENERGY_POP = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "secondary_genres": ["indie pop", "edm"],
    "secondary_moods": ["euphoric"],
    "target_energy": 0.90,
    "target_valence": 0.80,
    "target_danceability": 0.85,
    "target_acousticness": 0.10,
    "target_tempo_bpm": 128,
}


def print_recommendations(name: str, profile: dict, songs: list, k: int = 5) -> None:
    """Print the top k recommendations for one profile, with reasons one per line."""
    print(f"=== Top {k} for {name} ===\n")
    for rank, (song, score, reasons) in enumerate(recommend_songs(profile, songs, k), start=1):
        print(f"{rank}. {song['title']} - {song['artist']}  (score {score:.3f})")
        for reason in reasons:
            print(f"     {reason}")
        print()


def main() -> None:
    """Load the catalog and show recommendations for both sample profiles."""
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}\n")

    print_recommendations("chill_lofi", CHILL_LOFI, songs)
    print_recommendations("intense_rock", INTENSE_ROCK, songs)
    print_recommendations("high_energy_pop", HIGH_ENERGY_POP, songs)


if __name__ == "__main__":
    main()
