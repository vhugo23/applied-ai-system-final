"""Streamlit demo for the music recommender. Run with: streamlit run app.py"""

import pandas as pd
import streamlit as st

from src.evaluate import SONGS_PATH, render_report, run_all
from src.experiments import ADVERSARIAL_PROFILES, CORE_PROFILES
from src.recommender import (
    SELF_CHECK_PREFIX, load_songs, recommend_with_report, recommendation_confidence,
    validate_profile,
)

CUSTOM = "type my own..."
PRESETS = {**CORE_PROFILES, **ADVERSARIAL_PROFILES}
UNIT_INPUTS = (
    ("target_energy", "Target energy"),
    ("target_valence", "Target valence"),
    ("target_danceability", "Target danceability"),
    ("target_acousticness", "Target acousticness"),
)

st.set_page_config(page_title="Music Recommender Demo", page_icon="🎧", layout="wide")


@st.cache_data
def get_songs() -> list:
    """Load the real song catalog once."""
    return load_songs(str(SONGS_PATH))


def apply_preset(name: str, songs: list) -> None:
    """Copy a project profile into the sidebar widget state."""
    profile = PRESETS[name]
    genres = sorted({s["genre"] for s in songs})
    moods = sorted({s["mood"] for s in songs})
    for key, options, own_key in (("favorite_genre", genres, "genre_own"),
                                  ("favorite_mood", moods, "mood_own")):
        value = profile[key]
        st.session_state[key + "_pick"] = value if value in options else CUSTOM
        st.session_state[own_key] = "" if value in options else value
    st.session_state["secondary_genres"] = [g for g in profile["secondary_genres"] if g in genres]
    st.session_state["secondary_moods"] = [m for m in profile["secondary_moods"] if m in moods]
    for key, _ in UNIT_INPUTS:
        st.session_state[key] = float(profile[key])
    st.session_state["target_tempo_bpm"] = int(profile["target_tempo_bpm"])


def label_input(title: str, options: list, key: str, own_key: str) -> str:
    """Dropdown of catalog labels plus a free-text option; returns the chosen label."""
    pick = st.sidebar.selectbox(title, options + [CUSTOM], key=key + "_pick")
    if pick == CUSTOM:
        return st.sidebar.text_input(f"{title} (your own)", key=own_key).strip()
    return pick


def sidebar_profile(songs: list) -> dict:
    """Draw the sidebar widgets and return the profile dict they describe."""
    genres = sorted({s["genre"] for s in songs})
    moods = sorted({s["mood"] for s in songs})
    st.sidebar.header("Taste profile")
    st.sidebar.selectbox("Preset", list(PRESETS), key="preset",
                         on_change=lambda: apply_preset(st.session_state["preset"], songs))
    profile = {
        "favorite_genre": label_input("Favorite genre", genres, "favorite_genre", "genre_own"),
        "favorite_mood": label_input("Favorite mood", moods, "favorite_mood", "mood_own"),
        "secondary_genres": st.sidebar.multiselect("Secondary genres", genres, key="secondary_genres"),
        "secondary_moods": st.sidebar.multiselect("Secondary moods", moods, key="secondary_moods"),
    }
    for key, label in UNIT_INPUTS:
        profile[key] = st.sidebar.slider(label, 0.0, 1.0, step=0.05, key=key)
    profile["target_tempo_bpm"] = st.sidebar.number_input(
        "Target tempo (BPM, any value)", min_value=0, max_value=2000, step=1, key="target_tempo_bpm")
    return profile


def show_recommendations(profile: dict, songs: list) -> None:
    """Run the real pipeline and show confidence, warnings, self-check notes and the top 5."""
    _, warnings = validate_profile(profile, songs)
    results, notes = recommend_with_report(profile, songs, 5)
    confidence = recommendation_confidence(results)

    st.metric("Confidence", f"{confidence:.2f}")
    st.progress(min(max(confidence, 0.0), 1.0))
    for warning in warnings:
        st.warning(warning)
    for note in notes:
        st.info(f"{SELF_CHECK_PREFIX} {note}")

    st.subheader("Top 5")
    st.table(pd.DataFrame(
        [{"Rank": i, "Title": s["title"], "Artist": s["artist"], "Score": f"{score:.3f}"}
         for i, (s, score, _) in enumerate(results, start=1)]).set_index("Rank"))
    for i, (song, score, reasons) in enumerate(results, start=1):
        with st.expander(f"{i}. {song['title']} - {song['artist']} (score {score:.3f})"):
            for reason in reasons:
                st.write(f"- {reason}")


def show_evaluation() -> None:
    """Run the same code as python -m src.evaluate and show the table and summary line."""
    rows = run_all()
    st.dataframe(pd.DataFrame([{
        "Profile": f"{r.case.name} ({r.case.group})",
        "Input issue": r.case.issue,
        "Guardrail fired": ", ".join(r.guardrails) or "none",
        "Confidence": "n/a" if r.confidence is None else f"{r.confidence:.2f}",
        "Self-check result": r.self_check,
        "Pass/Fail": "Pass" if r.passed else "Fail: " + "; ".join(r.failures),
    } for r in rows]), hide_index=True, width="stretch")
    summary = render_report(rows).strip().splitlines()[-1]  # "13/13 profiles passed."
    (st.success if all(r.passed for r in rows) else st.error)(summary)


def main() -> None:
    """Build the page: a Recommend tab and an Evaluation tab, never showing a traceback."""
    st.title("🎧 Music Recommender Demo")
    try:
        songs = get_songs()
        if "preset" not in st.session_state:
            st.session_state["preset"] = next(iter(PRESETS))
            apply_preset(st.session_state["preset"], songs)
        profile = sidebar_profile(songs)
    except Exception as exc:
        st.error(f"Could not load the catalog or build the inputs: {exc}")
        return

    recommend_tab, evaluation_tab = st.tabs(["Recommend", "Evaluation"])
    with recommend_tab:
        if st.button("Recommend", type="primary"):
            try:
                show_recommendations(profile, songs)
            except Exception as exc:
                st.error(f"Something went wrong while recommending songs: {exc}")
        else:
            st.caption("Pick a preset or set your own profile in the sidebar, then press Recommend.")
    with evaluation_tab:
        if st.button("Run evaluation"):
            try:
                show_evaluation()
            except Exception as exc:
                st.error(f"Something went wrong while running the evaluation: {exc}")


main()
