# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

**What my version does:** it is a command-line music recommender. It loads an 18-song catalog, scores every song against a taste profile (genre, mood, energy, valence, danceability, acousticness and tempo, max score 7.0), ranks the songs, and prints the top 5 with the reasons for each. Run it with `python -m src.main`.

---

## How The System Works

Real platforms like Spotify and YouTube mostly learn from behavior (skips, replays, saves, playlist adds) and combine collaborative filtering ("people like you liked this") with content signals. This simulation is purely **content-based**: it has no multi-user behavior data, so it recommends songs whose attributes match one user's stated taste. It prioritizes explainable matching: genre and mood labels first, then how *close* each of a song's numbers is to the user's targets.

### Song features

Each song (loaded from `data/songs.csv` as a dict) has:

- `id`, `title`, `artist`: identification and display only
- `genre`, `mood`: categorical, scored by exact match, with partial credit for secondary labels
- `energy`, `valence`, `danceability`, `acousticness`: 0-1, each scored by closeness to the user's target
- `tempo_bpm`: scored by closeness to the user's target tempo

### User profile

A profile is a plain dict (the CLI defines `CHILL_LOFI` and `INTENSE_ROCK` in `src/main.py`) with:

- `favorite_genre`, `favorite_mood`: exact matches for the song's `genre` and `mood`
- `secondary_genres`, `secondary_moods`: lists that earn partial credit
- `target_energy`, `target_valence`, `target_danceability`, `target_acousticness`: the values (0-1) the user wants
- `target_tempo_bpm`: the tempo (BPM) the user wants

The starter `UserProfile` dataclass is still in the code because the starter tests and the `Recommender` class use it, but the scoring functions use the dict profiles above.

### Scoring a song (scoring rule)

One song plus a profile gives one score from 0 to **7.0**. Every weight is a named constant at the top of `src/recommender.py`.

| Component | How it is scored | Points |
|---|---|---|
| Genre | exact match `favorite_genre` / in `secondary_genres` / neither | 2.0 / 1.0 / 0 |
| Mood | exact match `favorite_mood` / in `secondary_moods` / neither | 1.0 / 0.5 / 0 |
| Energy | `2.0 * (1 - abs(song - target))` | up to 2.0 |
| Valence | `0.5 * (1 - abs(song - target))` | up to 0.5 |
| Danceability | `0.5 * (1 - abs(song - target))` | up to 0.5 |
| Acousticness | `0.5 * (1 - abs(song - target))` | up to 0.5 |
| Tempo | `0.5 * (1 - abs(bpm - target_bpm) / 160)` | up to 0.5 |

Tempo is divided by 160 because the fixed BPM range is 40 to 200. The maximum is 2.0 + 1.0 + 2.0 + 0.5 + 0.5 + 0.5 + 0.5 = 7.0.

Each term that earns points also produces a reason line such as `energy close to target (+1.840)`. Reasons show 3 decimals, so they add up to the total score to within a few thousandths. A term that earns 0 points is left out.

### Choosing recommendations (ranking rule)

1. Run the scoring rule on every song.
2. Sort by score, highest first. Ties are broken by title, A to Z.
3. Return the top `k` songs, each with its score and reasons.

```
songs.csv -> score each song vs profile -> sort by score (tie: title A-Z) -> top k + reasons
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

Real output of `python -m src.main` (three sample profiles, top 5 each):

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

=== Top 5 for high_energy_pop ===

1. Sunrise City - Neon Echo  (score 6.719)
     genre match (+2.000)
     mood match (+1.000)
     energy close to target (+1.840)
     valence close to target (+0.480)
     danceability close to target (+0.470)
     acousticness close to target (+0.460)
     tempo close to target (+0.469)

2. Gym Hero - Max Pulse  (score 5.872)
     genre match (+2.000)
     energy close to target (+1.940)
     valence close to target (+0.485)
     danceability close to target (+0.485)
     acousticness close to target (+0.475)
     tempo close to target (+0.487)

3. Rooftop Lights - Indigo Parade  (score 5.562)
     secondary genre match (+1.000)
     mood match (+1.000)
     energy close to target (+1.720)
     valence close to target (+0.495)
     danceability close to target (+0.485)
     acousticness close to target (+0.375)
     tempo close to target (+0.487)

4. Laser Bloom - Pixel Parade  (score 5.230)
     secondary genre match (+1.000)
     secondary mood match (+0.500)
     energy close to target (+1.880)
     valence close to target (+0.435)
     danceability close to target (+0.455)
     acousticness close to target (+0.460)
     tempo close to target (+0.500)

5. Storm Runner - Voltline  (score 3.650)
     energy close to target (+1.980)
     valence close to target (+0.340)
     danceability close to target (+0.405)
     acousticness close to target (+0.500)
     tempo close to target (+0.425)
```

Adversarial profiles, a weight experiment and profile comparisons are run with `python -m src.experiments` (output is pasted in `model_card.md`).

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Full outputs and the numbers behind these notes are in [model_card.md](model_card.md), section 6. Run them with `python -m src.experiments`.

- **Three profiles:** chill_lofi, intense_rock and high_energy_pop. Lofi shares no songs with rock or pop in the top 5. Rock and pop share 3 (Storm Runner, Gym Hero, Sunrise City) because both want high energy and energy is the heaviest weight.
- **Weight change (genre halved, energy doubled):** the top 3 stayed the same for every profile. For intense_rock, Iron Tide's lead over Gym Hero shrank from 0.652 to 0.052.
- **Adversarial profiles:**
  - Conflicting taste (classical, melancholy, energy 0.95): Cathedral Dust won at 4.933 on label points, even though its energy fit earned only +0.340 of 2.0.
  - Unknown genre and mood (k-pop, cozy): no song earned label points, and the top 5 sat within 0.207.
  - Out-of-range tempo (400 BPM): the tempo term went negative, and the reasons stopped adding up to the score.

---

## Limitations and Risks

- **Tiny catalog:** 18 songs, with only one rock song. Rock and pop listeners drop sharply after rank 1 (rock: 6.854 to 5.136).
- **Exact-match labels:** "indie pop" earns nothing for a "pop" fan unless the profile lists it as a backup.
- **Hand-written backup lists:** without metal as a backup genre, Gym Hero beats Iron Tide for the rock profile.
- **Labels can outweigh numbers:** genre and mood together give up to 3.0 points, more than energy can (2.0).
- **No popularity or listening history:** it cannot learn from behavior, so it stays inside the taste it is given. Popularity bias cannot show up here because the catalog has no popularity data.
- **Tempo is not limited:** a target far outside 40 to 200 BPM lowers scores without a reason line. Not fixed yet.

See [model_card.md](model_card.md) for the details and ideas for improvement.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

A simple weighted score plus clear reasons is enough to make a recommender feel smart. My biggest lesson was that the rules are not neutral: a hand-written backup list (metal for the rock profile) flipped Iron Tide ahead of Gym Hero, 5.136 to 4.484, and under different weights that lead shrank to 0.052. Bias shows up in small choices like the catalog (one rock song), exact-match labels, and how much weight labels get compared with numbers. The AI wrote most of the code quickly, but I had to check the arithmetic, the rounding and the docs myself, because its mistakes were quiet ones. The longer reflection is in section 9 of the model card.
