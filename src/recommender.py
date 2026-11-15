import csv
import logging
import math
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

NUMERIC_FIELDS = ("energy", "tempo_bpm", "valence", "danceability", "acousticness")

LOG_PATH = Path(__file__).resolve().parent.parent / "logs" / "app.log"
TEMPO_MIN_BPM = 40
TEMPO_MAX_BPM = 200
UNIT_KEYS = ("target_energy", "target_valence", "target_danceability", "target_acousticness")
REQUIRED_KEYS = ("favorite_genre", "favorite_mood", "secondary_genres", "secondary_moods",
                 *UNIT_KEYS, "target_tempo_bpm")
# Neutral fallbacks used only so scoring cannot crash; a warning is always emitted.
DEFAULTS = {key: 0.5 for key in UNIT_KEYS}
DEFAULTS["target_tempo_bpm"] = 120

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

# Confidence formula (see recommendation_confidence). The three weights sum to 1.0.
CONFIDENCE_GAP_WEIGHT = 0.30      # rank 1 clearly ahead of rank 2
CONFIDENCE_SPREAD_WEIGHT = 0.30   # rank 1 clearly ahead of the bottom of the top 5
CONFIDENCE_LABEL_WEIGHT = 0.40    # a genre or mood label actually matched
CONFIDENCE_GAP_FULL = 0.5         # a rank 1-2 gap of this many points earns the full gap term
CONFIDENCE_SPREAD_FULL = 1.5      # a rank 1-5 spread of this many points earns the full spread term
LABEL_EXACT_TERM = 1.0            # an exact genre or mood match in the set
LABEL_SECONDARY_TERM = 0.5        # only secondary genre/mood matches in the set

# Self-check thresholds and fallback settings (see self_check / recommend_with_report).
SELF_CHECK_TOP_N = 5               # how many results self_check inspects
SELF_CHECK_MIN_CONFIDENCE = 0.5    # below this, flag low confidence
SELF_CHECK_CLUSTER_RANGE = 0.25    # flag when top-5 scores are all within this many points
SELF_CHECK_NEIGHBOURS = 3          # songs whose labels are borrowed when widening
MAX_PER_ARTIST = 1                 # artist cap applied by the diversify fallback
SELF_CHECK_PREFIX = "self-check:"  # prefix of the notes added to the rank 1 reasons
FLAG_LOW_CONFIDENCE = "low_confidence"
FLAG_NO_LABEL_MATCH = "no_label_match"
FLAG_CLUSTERED = "clustered_scores"
FLAG_ARTIST_REPEATED = "artist_repeated"
LABEL_REASON_PREFIXES = ("genre match", "mood match", "secondary genre match", "secondary mood match")

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

def score_song(user_prefs: Dict, song: Dict, numeric_only: bool = False) -> Tuple[float, List[str]]:
    """Score one song against a user profile and return (score, reasons).

    With numeric_only=True the genre and mood points are skipped (self-check fallback).
    """
    score = 0.0
    reasons = []

    def add(points: float, reason: str) -> None:
        """Add points to the score and record a reason if they are above zero."""
        nonlocal score
        score += points
        if points > 0:
            reasons.append(f"{reason} (+{points:.3f})")

    if not numeric_only:
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

def recommendation_confidence(results: List[Tuple[Dict, float, List[str]]]) -> float:
    """Return a 0-1 confidence for one ranked recommendation set (best first).

    confidence = CONFIDENCE_GAP_WEIGHT    * min(1, (score1 - score2) / CONFIDENCE_GAP_FULL)
               + CONFIDENCE_SPREAD_WEIGHT * min(1, (score1 - score_last) / CONFIDENCE_SPREAD_FULL)
               + CONFIDENCE_LABEL_WEIGHT  * label_term
    where score_last is the lowest score in the set (rank 5 for k=5) and label_term is
    LABEL_EXACT_TERM if any result has an exact genre/mood match, else LABEL_SECONDARY_TERM
    if any has a secondary match, else 0.
    """
    if not results:
        return 0.0
    scores = [score for _, score, _ in results]
    gap = scores[0] - scores[1] if len(scores) > 1 else 0.0
    spread = scores[0] - scores[-1]
    reasons = [reason for _, _, rs in results for reason in rs]
    if any(r.startswith(("genre match", "mood match")) for r in reasons):
        label_term = LABEL_EXACT_TERM
    elif any(r.startswith(("secondary genre match", "secondary mood match")) for r in reasons):
        label_term = LABEL_SECONDARY_TERM
    else:
        label_term = 0.0
    confidence = (CONFIDENCE_GAP_WEIGHT * min(1.0, gap / CONFIDENCE_GAP_FULL)
                  + CONFIDENCE_SPREAD_WEIGHT * min(1.0, spread / CONFIDENCE_SPREAD_FULL)
                  + CONFIDENCE_LABEL_WEIGHT * label_term)
    return max(0.0, min(1.0, confidence))


confidence = recommendation_confidence  # short public name; see its docstring for the formula


def _get_logger() -> logging.Logger:
    """Return the module logger, attaching a logs/app.log file handler once."""
    logger = logging.getLogger("recommender")
    if not any(getattr(h, "_recommender_file", False) for h in logger.handlers):
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            handler._recommender_file = True
            logger.addHandler(handler)
        except OSError:
            pass  # logging must never break recommendations
        logger.setLevel(logging.INFO)
    return logger


def _clamp(profile: Dict, key: str, low: float, high: float, warnings: List[str]) -> None:
    """Clamp profile[key] into [low, high]; replace missing or non-numeric values with a default."""
    value = profile.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or math.isnan(value):
        if key in profile:
            warnings.append(f"{key} is not a number ({value!r}); using default {DEFAULTS[key]}")
        profile[key] = DEFAULTS[key]
        return
    clamped = min(max(value, low), high)
    if clamped != value:
        warnings.append(f"{key}={value} is outside {low}-{high}; clamped to {clamped}")
    profile[key] = clamped


def validate_profile(profile: Dict, songs: Optional[List[Dict]] = None) -> Tuple[Dict, List[str]]:
    """Return (clean_profile, warnings) for a user profile. Never raises on bad input.

    Clamps 0-1 features and tempo (40-200 BPM), warns about missing keys and about
    a favorite genre/mood that is not in the catalog (when songs is given).
    Every warning is also logged to logs/app.log.
    """
    warnings: List[str] = []
    try:
        clean = dict(profile) if isinstance(profile, dict) else {}
        if not isinstance(profile, dict):
            warnings.append(f"profile is not a dict ({type(profile).__name__}); using defaults")

        for key in REQUIRED_KEYS:
            if key not in clean:
                warnings.append(f"missing required key: {key}")

        for key in ("favorite_genre", "favorite_mood"):
            if not isinstance(clean.get(key), str):
                if key in clean:
                    warnings.append(f"{key} is not a string ({clean[key]!r}); using empty value")
                clean[key] = ""
        for key in ("secondary_genres", "secondary_moods"):
            if not isinstance(clean.get(key), (list, tuple, set)):
                if key in clean:
                    warnings.append(f"{key} is not a list ({clean[key]!r}); using empty list")
                clean[key] = []

        for key in UNIT_KEYS:
            _clamp(clean, key, 0.0, 1.0, warnings)
        _clamp(clean, "target_tempo_bpm", TEMPO_MIN_BPM, TEMPO_MAX_BPM, warnings)

        if songs is not None:
            genres = {s.get("genre") for s in songs}
            moods = {s.get("mood") for s in songs}
            if clean["favorite_genre"] and clean["favorite_genre"] not in genres:
                warnings.append(f"favorite_genre {clean['favorite_genre']!r} is not in the catalog")
            if clean["favorite_mood"] and clean["favorite_mood"] not in moods:
                warnings.append(f"favorite_mood {clean['favorite_mood']!r} is not in the catalog")
    except Exception as exc:  # last-resort guard: validation must never raise
        clean = {"favorite_genre": "", "favorite_mood": "", "secondary_genres": [],
                 "secondary_moods": [], **DEFAULTS}
        warnings.append(f"unexpected error validating profile ({exc!r}); using defaults")

    logger = _get_logger()
    for message in warnings:
        logger.warning(message)
    return clean, warnings


Results = List[Tuple[Dict, float, List[str]]]


def _ranked(profile: Dict, songs: List[Dict], numeric_only: bool = False) -> Results:
    """Score every song and return all of them, best first, ties by title A-Z."""
    scored = [(song, *score_song(profile, song, numeric_only)) for song in songs]
    return sorted(scored, key=lambda item: (-item[1], item[0]["title"]))


def self_check(results: Results, profile: Optional[Dict] = None) -> List[Tuple[str, str]]:
    """Inspect the top 5 and return (flag_code, message) for every problem found.

    Flags: low confidence, no genre/mood label matched, all top-5 scores within
    SELF_CHECK_CLUSTER_RANGE of each other, and one artist repeated.
    """
    top = results[:SELF_CHECK_TOP_N]
    if not top:
        return []
    flags = []
    confidence = recommendation_confidence(top)
    if confidence < SELF_CHECK_MIN_CONFIDENCE:
        flags.append((FLAG_LOW_CONFIDENCE,
                      f"confidence {confidence:.2f} is below {SELF_CHECK_MIN_CONFIDENCE}"))
    reasons = [r for _, _, rs in top for r in rs]
    if not any(r.startswith(LABEL_REASON_PREFIXES) for r in reasons):
        flags.append((FLAG_NO_LABEL_MATCH, "no genre or mood label matched in the top 5"))
    scores = [score for _, score, _ in top]
    if len(scores) > 1 and max(scores) - min(scores) <= SELF_CHECK_CLUSTER_RANGE:
        flags.append((FLAG_CLUSTERED,
                      f"top {len(scores)} scores are within {max(scores) - min(scores):.3f} "
                      f"(limit {SELF_CHECK_CLUSTER_RANGE})"))
    artists = [song["artist"] for song, _, _ in top]
    repeated = sorted({a for a in artists if artists.count(a) > 1})
    if repeated:
        flags.append((FLAG_ARTIST_REPEATED, f"artist repeated in the top 5: {', '.join(repeated)}"))
    return flags


def _diversify(ranked: Results, k: int) -> Results:
    """Keep at most MAX_PER_ARTIST songs per artist in the top k, back-filling if the catalog is short."""
    chosen, skipped, counts = [], [], {}
    for item in ranked:
        artist = item[0]["artist"]
        if counts.get(artist, 0) < MAX_PER_ARTIST:
            counts[artist] = counts.get(artist, 0) + 1
            chosen.append(item)
        else:
            skipped.append(item)
    return (chosen + skipped)[:k] if len(chosen) < k else chosen[:k]


def _widen_profile(profile: Dict, songs: List[Dict]) -> Tuple[Dict, List[str], List[str]]:
    """Copy the profile, adding the genres/moods of its numeric-only nearest songs as secondary labels."""
    neighbours = _ranked(profile, songs, numeric_only=True)[:SELF_CHECK_NEIGHBOURS]
    widened = dict(profile)
    new_genres = [g for g in dict.fromkeys(s["genre"] for s, _, _ in neighbours)
                  if g not in profile["secondary_genres"] and g != profile["favorite_genre"]]
    new_moods = [m for m in dict.fromkeys(s["mood"] for s, _, _ in neighbours)
                 if m not in profile["secondary_moods"] and m != profile["favorite_mood"]]
    widened["secondary_genres"] = list(profile["secondary_genres"]) + new_genres
    widened["secondary_moods"] = list(profile["secondary_moods"]) + new_moods
    return widened, new_genres, new_moods


def recommend_with_report(user_prefs: Dict, songs: List[Dict], k: int = 5) -> Tuple[Results, List[str]]:
    """Rank songs, run self_check, apply documented fallbacks, and return (results, notes).

    Fallbacks, applied in this order and each at most once:
      1. no_label_match -> widen: add the genres/moods of the SELF_CHECK_NEIGHBOURS songs
         nearest on numeric features as secondary labels, then re-rank. Kept only if
         confidence does not drop.
      2. low_confidence or clustered (still firing) -> numeric-only ranking (genre/mood
         points dropped). Kept only if the top-5 spread grows, i.e. the ranking is more decisive.
      3. artist_repeated (still firing) -> keep at most MAX_PER_ARTIST song per artist.
    Every fallback tried, kept or reverted, is described in notes with its reason.
    """
    profile, _ = validate_profile(user_prefs, songs)
    ranked = _ranked(profile, songs)
    notes: List[str] = []

    def codes() -> Dict[str, str]:
        return dict(self_check(ranked[:k], profile))

    flags = codes()
    if flags:
        notes.append("flags before: " + "; ".join(f"{c} ({m})" for c, m in flags.items()))

    if FLAG_NO_LABEL_MATCH in flags:
        widened, genres, moods = _widen_profile(profile, songs)
        candidate = _ranked(widened, songs)
        if (recommendation_confidence(candidate[:k]) >= recommendation_confidence(ranked[:k])
                and (genres or moods)):
            ranked, profile = candidate, widened
            notes.append(f"widened secondary labels with genres {genres} and moods {moods} from the "
                         f"{SELF_CHECK_NEIGHBOURS} numerically nearest songs, because "
                         f"{flags[FLAG_NO_LABEL_MATCH]}")
        else:
            notes.append("tried widening secondary labels but it did not help; reverted")
        flags = codes()

    if FLAG_LOW_CONFIDENCE in flags or FLAG_CLUSTERED in flags:
        reason = flags.get(FLAG_LOW_CONFIDENCE) or flags[FLAG_CLUSTERED]
        candidate = _ranked(profile, songs, numeric_only=True)
        spread = lambda r: r[0][1] - r[min(k, len(r)) - 1][1] if r else 0.0
        if spread(candidate[:k]) > spread(ranked[:k]):
            ranked = candidate
            notes.append(f"switched to numeric-only ranking (genre/mood points dropped), because {reason}; "
                         f"top-{k} spread grew to {spread(candidate[:k]):.3f}")
        else:
            notes.append(f"tried numeric-only ranking because {reason}, but it was not more decisive; reverted")
        flags = codes()

    if FLAG_ARTIST_REPEATED in flags:
        before_titles = {s["title"] for s, _, _ in ranked[:k]}
        ranked = _diversify(ranked, k)
        dropped = sorted(before_titles - {s["title"] for s, _, _ in ranked[:k]})
        notes.append(f"limited to {MAX_PER_ARTIST} song per artist, because {flags[FLAG_ARTIST_REPEATED]}; "
                     f"dropped {dropped}")
        flags = codes()

    if notes:
        notes.append("flags after: " + ("; ".join(flags) if flags else "none"))
        get_logger = _get_logger()
        for note in notes:
            get_logger.info("self-check: %s", note)
    return ranked[:k], notes


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5,
                    self_check_enabled: bool = True) -> Results:
    """Return the top k (song, score, reasons) results, best first, ties by title A-Z.

    With self_check_enabled (default) the results go through self_check and any fallbacks;
    what changed and why is added to the rank 1 reasons as lines starting "self-check:".
    """
    if not self_check_enabled:
        profile, _ = validate_profile(user_prefs, songs)
        return _ranked(profile, songs)[:k]
    results, notes = recommend_with_report(user_prefs, songs, k)
    if results and notes:
        song, score, reasons = results[0]
        results[0] = (song, score, list(reasons) + [f"{SELF_CHECK_PREFIX} {n}" for n in notes])
    return results
