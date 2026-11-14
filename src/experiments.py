"""
Phase 4 experiments: adversarial profiles, a weight sensitivity test, and pairwise comparisons.

Run it from the project root with: python -m src.experiments
"""

from itertools import combinations

from src import recommender
from src.main import CHILL_LOFI, HIGH_ENERGY_POP, INTENSE_ROCK, print_recommendations
from src.recommender import load_songs, recommend_songs

CORE_PROFILES = {
    "chill_lofi": CHILL_LOFI,
    "intense_rock": INTENSE_ROCK,
    "high_energy_pop": HIGH_ENERGY_POP,
}

ADVERSARIAL_PROFILES = {
    # Wants calm, sad, acoustic music but also maximum energy and a fast tempo.
    "conflicting_sad_but_hyper": {
        "favorite_genre": "classical", "favorite_mood": "melancholy",
        "secondary_genres": [], "secondary_moods": ["wistful"],
        "target_energy": 0.95, "target_valence": 0.20, "target_danceability": 0.20,
        "target_acousticness": 0.95, "target_tempo_bpm": 170,
    },
    # Genre and mood that do not exist in the catalog, so no label can ever match.
    "unknown_labels": {
        "favorite_genre": "k-pop", "favorite_mood": "cozy",
        "secondary_genres": [], "secondary_moods": [],
        "target_energy": 0.50, "target_valence": 0.50, "target_danceability": 0.50,
        "target_acousticness": 0.50, "target_tempo_bpm": 100,
    },
    # A tempo target far outside the 40-200 BPM range the formula assumes.
    "out_of_range_tempo": {
        "favorite_genre": "pop", "favorite_mood": "happy",
        "secondary_genres": [], "secondary_moods": [],
        "target_energy": 0.80, "target_valence": 0.80, "target_danceability": 0.80,
        "target_acousticness": 0.20, "target_tempo_bpm": 400,
    },
}


def run_with_weights(overrides: dict, profile: dict, songs: list, k: int = 5) -> list:
    """Rank songs with some weight constants temporarily changed, then restore them."""
    saved = {name: getattr(recommender, name) for name in overrides}
    saved_terms = recommender.NUMERIC_TERMS
    try:
        for name, value in overrides.items():
            setattr(recommender, name, value)
        recommender.NUMERIC_TERMS = (
            ("energy", "target_energy", recommender.ENERGY_WEIGHT),
            ("valence", "target_valence", recommender.VALENCE_WEIGHT),
            ("danceability", "target_danceability", recommender.DANCEABILITY_WEIGHT),
            ("acousticness", "target_acousticness", recommender.ACOUSTICNESS_WEIGHT),
        )
        return recommend_songs(profile, songs, k)
    finally:
        for name, value in saved.items():
            setattr(recommender, name, value)
        recommender.NUMERIC_TERMS = saved_terms


def run_adversarial(songs: list) -> None:
    """Print the top 5 and the lowest scores for each adversarial profile."""
    print("##### ADVERSARIAL PROFILES #####\n")
    for name, profile in ADVERSARIAL_PROFILES.items():
        print_recommendations(name, profile, songs)
        everything = recommend_songs(profile, songs, k=len(songs))
        print(f"Lowest score for {name}: {everything[-1][0]['title']} {everything[-1][1]:.3f}\n")


def run_sensitivity(songs: list) -> None:
    """Compare normal weights with genre halved and energy doubled for each core profile."""
    experiment = {
        "GENRE_EXACT_POINTS": 1.0, "GENRE_SECONDARY_POINTS": 0.5, "ENERGY_WEIGHT": 4.0,
    }
    print("##### SENSITIVITY EXPERIMENT: genre exact 2.0 -> 1.0 (secondary 1.0 -> 0.5), energy 2.0 -> 4.0 #####")
    print("(max score becomes 8.0)\n")
    for name, profile in CORE_PROFILES.items():
        base = recommend_songs(profile, songs, k=5)
        changed = run_with_weights(experiment, profile, songs, k=5)
        print(f"--- {name} ---")
        print(f"{'rank':<5}{'baseline':<34}{'experiment':<34}")
        for rank, (b, e) in enumerate(zip(base, changed), start=1):
            left = f"{b[0]['title']} {b[1]:.3f}"
            right = f"{e[0]['title']} {e[1]:.3f}"
            print(f"{rank:<5}{left:<34}{right:<34}")
        print()


def run_pairwise(songs: list) -> None:
    """Print the top-5 overlap between each pair of core profiles."""
    print("##### PAIRWISE TOP-5 OVERLAP (core profiles) #####\n")
    tops = {
        name: [song["title"] for song, _, _ in recommend_songs(profile, songs, k=5)]
        for name, profile in CORE_PROFILES.items()
    }
    for (name_a, titles_a), (name_b, titles_b) in combinations(tops.items(), 2):
        shared = [t for t in titles_a if t in titles_b]
        print(f"{name_a} vs {name_b}: {len(shared)} shared {shared}")


def main() -> None:
    """Run every experiment against the real catalog."""
    songs = load_songs("data/songs.csv")
    run_adversarial(songs)
    run_sensitivity(songs)
    run_pairwise(songs)


if __name__ == "__main__":
    main()
