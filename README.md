# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Real platforms like Spotify and YouTube mostly learn from behavior (skips, replays, saves, playlist adds) and combine collaborative filtering ("people like you liked this") with content signals. This simulation is purely **content-based**: it has no multi-user behavior data, so it recommends songs whose attributes match one user's stated taste. It prioritizes explainable matching: genre first, then mood, then how *close* a song's numbers are to the user's targets.

### Song features

Each `Song` (loaded from `data/songs.csv`) has:

- `id`, `title`, `artist`: identification and display only
- `genre`, `mood`: categorical, used for exact-match scoring
- `energy`: 0-1, scored by closeness to the user's target
- `acousticness`: 0-1, scored against the user's acoustic preference
- `tempo_bpm`, `valence`, `danceability`: loaded but not scored yet (possible future features)

### UserProfile

Each `UserProfile` stores:

- `favorite_genre`: compared with `Song.genre`
- `favorite_mood`: compared with `Song.mood`
- `target_energy`: the energy level they want (0-1)
- `likes_acoustic`: whether they prefer acoustic (high `acousticness`) or non-acoustic songs

### Scoring a song (scoring rule)

One song plus the profile gives one number between 0 and 1. Each component is scored 0-1, then combined with weights that sum to 1:

| Component | How it is scored | Starting weight |
|---|---|---|
| Genre | 1 if equal to `favorite_genre`, else 0 | 0.35 |
| Mood | 1 if equal to `favorite_mood`, else 0 | 0.25 |
| Energy | `1 - abs(song.energy - target_energy)` | 0.25 |
| Acousticness | `song.acousticness` if `likes_acoustic`, else `1 - song.acousticness` | 0.15 |

`score = 0.35*genre + 0.25*mood + 0.25*energy + 0.15*acoustic`

The weights are starting values to tune, not final choices.

### Choosing recommendations (ranking rule)

1. Run the scoring rule on every song.
2. Sort by score, highest first. Ties are broken deterministically (for example by title).
3. Return the top `k` songs, each with a short explanation of which components matched.

```
songs.csv -> score each song vs UserProfile -> sort by score -> top k + reasons
```

Scoring looks at one song at a time. Ranking only needs the scores, so the weights can change without touching the sorting.

### Known limitation

Because it only matches attributes the user already stated, it tends to stay inside their existing taste (a filter bubble) and cannot find surprising songs the way collaborative filtering can.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Real output of `python -m src.main` (two sample profiles, top 5 each):

```text
Loaded songs: 18

=== Top 5 for chill_lofi ===

1. Library Rain - Paper Lanterns  (score 6.867)
     genre match (+2.000)
     mood match (+1.000)
     energy close to target (+2.000)
     valence close to target (+0.475)
     danceability close to target (+0.485)
     acousticness close to target (+0.420)
     tempo close to target (+0.487)

2. Midnight Coding - LoRoom  (score 6.809)
     genre match (+2.000)
     mood match (+1.000)
     energy close to target (+1.860)
     valence close to target (+0.495)
     danceability close to target (+0.465)
     acousticness close to target (+0.495)
     tempo close to target (+0.494)

3. Focus Flow - LoRoom  (score 6.303)
     genre match (+2.000)
     secondary mood match (+0.500)
     energy close to target (+1.900)
     valence close to target (+0.480)
     danceability close to target (+0.475)
     acousticness close to target (+0.460)
     tempo close to target (+0.487)

4. Spacewalk Thoughts - Orbit Bloom  (score 5.580)
     secondary genre match (+1.000)
     mood match (+1.000)
     energy close to target (+1.860)
     valence close to target (+0.450)
     danceability close to target (+0.430)
     acousticness close to target (+0.390)
     tempo close to target (+0.450)

5. Coffee Shop Stories - Slow Stereo  (score 5.236)
     secondary genre match (+1.000)
     secondary mood match (+0.500)
     energy close to target (+1.960)
     valence close to target (+0.420)
     danceability close to target (+0.495)
     acousticness close to target (+0.405)
     tempo close to target (+0.456)

=== Top 5 for intense_rock ===

1. Storm Runner - Voltline  (score 6.854)
     genre match (+2.000)
     mood match (+1.000)
     energy close to target (+1.980)
     valence close to target (+0.460)
     danceability close to target (+0.420)
     acousticness close to target (+0.500)
     tempo close to target (+0.494)

2. Iron Tide - Black Harbor  (score 5.136)
     secondary genre match (+1.000)
     secondary mood match (+0.500)
     energy close to target (+1.840)
     valence close to target (+0.425)
     danceability close to target (+0.475)
     acousticness close to target (+0.465)
     tempo close to target (+0.431)

3. Gym Hero - Max Pulse  (score 4.484)
     mood match (+1.000)
     energy close to target (+1.940)
     valence close to target (+0.315)
     danceability close to target (+0.310)
     acousticness close to target (+0.475)
     tempo close to target (+0.444)

4. Night Drive Loop - Neon Echo  (score 3.355)
     energy close to target (+1.700)
     valence close to target (+0.455)
     danceability close to target (+0.385)
     acousticness close to target (+0.440)
     tempo close to target (+0.375)

5. Sunrise City - Neon Echo  (score 3.335)
     energy close to target (+1.840)
     valence close to target (+0.280)
     danceability close to target (+0.355)
     acousticness close to target (+0.460)
     tempo close to target (+0.400)
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



