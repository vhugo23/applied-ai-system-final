import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

NUMERIC_FIELDS = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")

# Scoring weights (max total score is 7.0)
GENRE_EXACT_POINTS = 2.0
GENRE_SECONDARY_POINTS = 1.0
MOOD_EXACT_POINTS = 1.0
MOOD_SECONDARY_POINTS = 0.5
ENERGY_WEIGHT = 2.0
VALENCE_WEIGHT = 0.5
DANCEABILITY_WEIGHT = 0.5
ACOUSTICNESS_WEIGHT = 0.5
TEMPO_WEIGHT = 0.5
TEMPO_RANGE_BPM = 160  # fixed 40-200 BPM bounds

# (song feature, profile target key, weight) for terms that use 1 - |diff|
NUMERIC_TERMS = (
    ("energy", "target_energy", ENERGY_WEIGHT),
    ("valence", "target_valence", VALENCE_WEIGHT),
    ("danceability", "target_danceability", DANCEABILITY_WEIGHT),
    ("acousticness", "target_acousticness", ACOUSTICNESS_WEIGHT),
)

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file into a list of dicts with numbers converted."""
    try:
        with open(csv_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
    except FileNotFoundError:
        raise FileNotFoundError(f"Song file not found: {csv_path}") from None

    songs = []
    for row in rows:
        song = dict(row)
        song["id"] = int(row["id"])
        for field in NUMERIC_FIELDS:
            song[field] = float(row[field])
        songs.append(song)
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """Score one song against a user profile and return (score, reasons)."""
    score = 0.0
    reasons = []

    def add(points: float, reason: str) -> None:
        nonlocal score
        score += points
        if points > 0:
            reasons.append(f"{reason} (+{points:.3f})")

    if song["genre"] == user_prefs["favorite_genre"]:
        add(GENRE_EXACT_POINTS, "genre match")
    elif song["genre"] in user_prefs["secondary_genres"]:
        add(GENRE_SECONDARY_POINTS, "secondary genre match")

    if song["mood"] == user_prefs["favorite_mood"]:
        add(MOOD_EXACT_POINTS, "mood match")
    elif song["mood"] in user_prefs["secondary_moods"]:
        add(MOOD_SECONDARY_POINTS, "secondary mood match")

    for feature, target_key, weight in NUMERIC_TERMS:
        similarity = 1 - abs(song[feature] - user_prefs[target_key])
        add(weight * similarity, f"{feature} close to target")

    similarity = 1 - abs(song["tempo_bpm"] - user_prefs["target_tempo_bpm"]) / TEMPO_RANGE_BPM
    add(TEMPO_WEIGHT * similarity, "tempo close to target")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, List[str]]]:
    """Return the top k (song, score, reasons) results, best first, ties by title A-Z."""
    scored = [(song, *score_song(user_prefs, song)) for song in songs]
    return sorted(scored, key=lambda item: (-item[1], item[0]["title"]))[:k]
