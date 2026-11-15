# VibeFinder 2.0: A Self-Checking Music Recommender

## Base project: Music Recommender Simulation

This system extends my **Music Recommender Simulation**, a small command-line project whose original goals were to represent songs and one listener's taste profile as data, design a scoring rule that turns that data into ranked recommendations, evaluate what the system gets right and wrong, and reflect on how this mirrors real-world recommenders. The original version (VibeFinder 1.0) loads an 18-song catalog, scores every song against a profile (genre, mood, energy, valence, danceability, acousticness, tempo; max score 7.0), and prints the top 5 with the reasons for each.

## New system: VibeFinder 2.0

VibeFinder 2.0 keeps the same explainable scoring but wraps it in guardrails so it behaves sensibly on bad or unusual input. It validates and cleans every profile (clamping, defaults, warnings, logging to `logs/app.log`), computes a 0-1 **confidence** for each recommendation set, runs a **self-check** that flags weak results (low confidence, no label match, clustered scores, a repeated artist), applies a documented **fallback re-rank** when a flag fires, and records what it changed and why in the output. An evaluation harness (`python -m src.evaluate`) runs 13 profiles and prints a Pass/Fail table so a person can review the guardrails.

## Architecture overview

The full flowchart is in [diagrams/architecture.mmd](diagrams/architecture.mmd) (Mermaid). In short:

```
profile -> validate_profile (logging) -> score every song -> rank -> confidence
        -> self_check -> fallback re-rank if flagged -> output (results + notes)
                 human review: evaluation table (src/evaluate.py) and logs/app.log
```

| Stage | Function in `src/` | What it does |
|---|---|---|
| Load | `load_songs` | Reads `data/songs.csv` into dicts with numbers as floats |
| Guardrail 1 | `validate_profile` | Clamps features to 0-1 and tempo to 40-200 BPM, fills missing keys (0.5, or 120 BPM), warns on unknown genre/mood, never raises, logs every warning |
| Score and rank | `score_song`, `_ranked` | One song plus a profile gives a score and reasons; sort high to low, ties by title A-Z |
| Confidence | `confidence` (alias of `recommendation_confidence`) | 0-1 from the rank 1-2 gap, the top-5 spread and whether a label matched |
| Guardrail 2 | `self_check` | Flags low confidence, no label match, top 5 within 0.25, one artist twice |
| Fallback | `recommend_with_report` | Widen labels, numeric-only ranking, or an artist cap; re-ranks and returns `(results, notes)` |
| Entry point | `recommend_songs` | Runs all of the above and adds the notes to the rank 1 reasons |
| Review | `src/evaluate.py` | Runs every profile, prints the table, saves `evaluation_output.txt` |

### Scoring a song

One song plus a profile gives one score from 0 to **7.0**. Every weight is a named constant at the top of `src/recommender.py`.

| Component | How it is scored | Points |
|---|---|---|
| Genre | exact match / in `secondary_genres` / neither | 2.0 / 1.0 / 0 |
| Mood | exact match / in `secondary_moods` / neither | 1.0 / 0.5 / 0 |
| Energy | `2.0 * (1 - abs(song - target))` | up to 2.0 |
| Valence | `0.5 * (1 - abs(song - target))` | up to 0.5 |
| Danceability | `0.5 * (1 - abs(song - target))` | up to 0.5 |
| Acousticness | `0.5 * (1 - abs(song - target))` | up to 0.5 |
| Tempo | `0.5 * (1 - abs(bpm - target_bpm) / 160)` | up to 0.5 |

Each term that earns points writes a reason line such as `energy close to target (+1.840)`. Reasons show 3 decimals, so they add up to the score to within a few thousandths. Because `validate_profile` clamps tempo to 40-200 BPM, no term can go negative.

### Confidence

`confidence = 0.30 * min(1, gap / 0.5) + 0.30 * min(1, spread / 1.5) + 0.40 * label_term`

`gap` is the rank 1 minus rank 2 score, `spread` is rank 1 minus the lowest score in the set, and `label_term` is 1.0 for an exact genre or mood match, 0.5 for only secondary matches, and 0 for none. All weights and thresholds are named constants (`CONFIDENCE_*`, `LABEL_*`) in `src/recommender.py`.

### Self-check flags and fallbacks

| Flag | Fires when | Fallback (applied once, in this order) |
|---|---|---|
| `no_label_match` | no genre or mood label matched in the top 5 | Widen: add the genres and moods of the 3 numerically nearest songs as secondary labels; kept only if confidence does not drop |
| `low_confidence`, `clustered_scores` | confidence below 0.5, or all top-5 scores within 0.25 | Numeric-only ranking (genre and mood points dropped); kept only if the top-5 spread grows |
| `artist_repeated` | one artist appears twice in the top 5 | Keep at most 1 song per artist, back-filling from the ranked list |

Every fallback that was tried, kept or reverted, is written to the output with its reason.

---

## Setup

1. Clone the repo:

   ```bash
   git clone https://github.com/vhugo23/applied-ai-system-final.git
   cd applied-ai-system-final
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Run the app (three sample profiles, top 5 each):

   ```bash
   python -m src.main
   ```

5. Run the evaluation table (also saves `evaluation_output.txt`):

   ```bash
   python -m src.evaluate
   ```

6. Run the tests:

   ```bash
   pytest
   ```

I checked steps 2 to 4 and 6 in a fresh copy of the project folder (new venv, `pip install -r requirements.txt` exited 0, `python -m src.main` printed the sample output, `pytest` passed all 66 tests). I could not check step 1 against the uncommitted changes, because `git clone` only gets what is pushed to GitHub.

---

## Sample runs

All three runs are real output, produced by running the commands shown from the project root. They use `print_recommendations` from `src/main.py`, so the confidence appears in each heading and any self-check notes are printed under the list.

### 1. Normal run (high_energy_pop, no flags)

```bash
python -c "from src.main import HIGH_ENERGY_POP, print_recommendations; from src.recommender import load_songs; print_recommendations('high_energy_pop', HIGH_ENERGY_POP, load_songs('data/songs.csv'))"
```

```text
=== Top 5 for high_energy_pop (confidence 1.00) ===

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

Every guardrail stayed quiet: confidence is 1.00 and there are no self-check notes.

### 2. Unknown labels (k-pop, cozy), self-check fires

```bash
python -c "from src.experiments import ADVERSARIAL_PROFILES; from src.main import print_recommendations; from src.recommender import load_songs; print_recommendations('unknown_labels', ADVERSARIAL_PROFILES['unknown_labels'], load_songs('data/songs.csv'))"
```

```text
=== Top 5 for unknown_labels (confidence 0.58) ===

1. Dusty Porch Light - Willow Creek Band  (score 5.209)
     secondary genre match (+1.000)
     secondary mood match (+0.500)
     energy close to target (+1.960)
     valence close to target (+0.410)
     danceability close to target (+0.465)
     acousticness close to target (+0.380)
     tempo close to target (+0.494)

2. Midnight Coding - LoRoom  (score 5.076)
     secondary genre match (+1.000)
     secondary mood match (+0.500)
     energy close to target (+1.840)
     valence close to target (+0.470)
     danceability close to target (+0.440)
     acousticness close to target (+0.395)
     tempo close to target (+0.431)

3. Island Hammock - Sol Rivers  (score 5.065)
     secondary genre match (+1.000)
     secondary mood match (+0.500)
     energy close to target (+1.900)
     valence close to target (+0.350)
     danceability close to target (+0.390)
     acousticness close to target (+0.475)
     tempo close to target (+0.450)

4. Library Rain - Paper Lanterns  (score 4.843)
     secondary genre match (+1.000)
     secondary mood match (+0.500)
     energy close to target (+1.700)
     valence close to target (+0.450)
     danceability close to target (+0.460)
     acousticness close to target (+0.320)
     tempo close to target (+0.412)

5. Spacewalk Thoughts - Orbit Bloom  (score 3.605)
     secondary mood match (+0.500)
     energy close to target (+1.560)
     valence close to target (+0.425)
     danceability close to target (+0.455)
     acousticness close to target (+0.290)
     tempo close to target (+0.375)

  self-check: flags before: low_confidence (confidence 0.12 is below 0.5); no_label_match (no genre or mood label matched in the top 5); clustered_scores (top 5 scores are within 0.206 (limit 0.25)); artist_repeated (artist repeated in the top 5: LoRoom)
  self-check: widened secondary labels with genres ['country', 'lofi', 'reggae'] and moods ['nostalgic', 'chill', 'peaceful'] from the 3 numerically nearest songs, because no genre or mood label matched in the top 5
  self-check: tried numeric-only ranking because confidence 0.42 is below 0.5, but it was not more decisive; reverted
  self-check: limited to 1 song per artist, because artist repeated in the top 5: LoRoom; dropped ['Focus Flow']
  self-check: flags after: none
```

No song matched `k-pop` or `cozy`, so before the self-check the confidence was 0.12 and the top 5 sat within 0.206 of each other. The self-check widened the secondary labels, tried and reverted a numeric-only ranking, and capped LoRoom at one song. Confidence ended at 0.58. Note that this confidence comes from labels borrowed from the nearest songs, not from knowing what this listener likes.

### 3. Bad input (tempo 400 BPM), validation guardrail fires

```bash
python -c "from src.experiments import ADVERSARIAL_PROFILES; from src.main import print_recommendations; from src.recommender import load_songs, validate_profile; songs = load_songs('data/songs.csv'); p = ADVERSARIAL_PROFILES['out_of_range_tempo']; print('warnings:', validate_profile(p, songs)[1]); print(); print_recommendations('out_of_range_tempo', p, songs)"
tail -n 5 logs/app.log
```

```text
warnings: ['target_tempo_bpm=400 is outside 40-200; clamped to 200']

=== Top 5 for out_of_range_tempo (confidence 1.00) ===

1. Sunrise City - Neon Echo  (score 6.669)
     genre match (+2.000)
     mood match (+1.000)
     energy close to target (+1.960)
     valence close to target (+0.480)
     danceability close to target (+0.495)
     acousticness close to target (+0.490)
     tempo close to target (+0.244)

2. Gym Hero - Max Pulse  (score 5.397)
     genre match (+2.000)
     energy close to target (+1.740)
     valence close to target (+0.485)
     danceability close to target (+0.460)
     acousticness close to target (+0.425)
     tempo close to target (+0.287)

3. Rooftop Lights - Indigo Parade  (score 4.593)
     mood match (+1.000)
     energy close to target (+1.920)
     valence close to target (+0.495)
     danceability close to target (+0.490)
     acousticness close to target (+0.425)
     tempo close to target (+0.263)

4. Concrete Crown - Kid Marlow  (score 3.435)
     energy close to target (+1.960)
     valence close to target (+0.410)
     danceability close to target (+0.450)
     acousticness close to target (+0.440)
     tempo close to target (+0.175)

5. Storm Runner - Voltline  (score 3.350)
     energy close to target (+1.780)
     valence close to target (+0.340)
     danceability close to target (+0.430)
     acousticness close to target (+0.450)
     tempo close to target (+0.350)

  self-check: flags before: artist_repeated (artist repeated in the top 5: Neon Echo)
  self-check: limited to 1 song per artist, because artist repeated in the top 5: Neon Echo; dropped ['Night Drive Loop']
  self-check: flags after: none

$ tail -n 5 logs/app.log
2026-11-15 08:50:05,957 WARNING target_tempo_bpm=400 is outside 40-200; clamped to 200
2026-11-15 08:50:05,957 WARNING target_tempo_bpm=400 is outside 40-200; clamped to 200
2026-11-15 08:50:05,957 INFO self-check: flags before: artist_repeated (artist repeated in the top 5: Neon Echo)
2026-11-15 08:50:05,957 INFO self-check: limited to 1 song per artist, because artist repeated in the top 5: Neon Echo; dropped ['Night Drive Loop']
2026-11-15 08:50:05,957 INFO self-check: flags after: none
```

The log was read with `tail -n 5 logs/app.log` (on Windows PowerShell: `Get-Content logs/app.log -Tail 5`). The clamp warning appears twice because the command calls `validate_profile` itself and then `recommend_songs` calls it again. The tempo target was treated as 200 BPM, so every song has a tempo line and the reasons add up to the score.

---

## Design decisions and tradeoffs

- **Content-based and explainable, not learned.** There is no listening history, so the score is a hand-weighted sum with a reason line per term. The tradeoff is that the weights are my judgment, and they decide results (see Limitations).
- **Clamp and default instead of rejecting bad input.** `validate_profile` never raises: it clamps, fills a neutral default (0.5, or 120 BPM), warns and logs. The tradeoff is that it quietly reinterprets input (a 400 BPM target becomes 200), and a default can invent a preference the user never gave. The warning and the log are the safeguard.
- **Confidence is a heuristic, not a probability.** The weights (0.30 / 0.30 / 0.40) and the thresholds (gap 0.5, spread 1.5) are my choices and are not calibrated against real listeners. Labels get the biggest share, so a set with no label match cannot score above 0.6.
- **Fallbacks are ordered, run once, and can be reverted.** Widening and the numeric-only ranking are only kept if they improve confidence or the spread. The tradeoff is that widening raises confidence by borrowing labels from songs that already match on numbers, which can reinforce a filter bubble.
- **Hard artist cap instead of a penalty.** One song per artist is simple and easy to explain, but it can drop a better-scoring song (it dropped Sunrise City for the rock profile). A score penalty would be gentler.
- **Notes live on the rank 1 reasons.** This kept the `(song, score, reasons)` return type, so existing callers and tests did not change. The tradeoff is that set-level information sits on one song; `recommend_with_report` returns the notes separately.
- **Self-check is on by default** and changes the output, including the baseline profiles that had a repeated artist. `recommend_songs(..., self_check_enabled=False)` gives the raw ranking, and `src/experiments.py` uses it so the earlier experiment numbers stay comparable.
- **Pass criteria are defined in code.** `src/evaluate.py` lists seven criteria (`PASS_CRITERIA`) and the expected guardrail for each case is declared by hand, so the table is only as strict as those declarations.

---

## Testing summary

Real output of `pytest -v` (last line): `66 passed in 0.24s`

| Test file | Tests | What it covers |
|---|---|---|
| `tests/test_confidence.py` | 9 | confidence formula: bounds, weights sum to 1, no-label and secondary-label cases, ties, alias |
| `tests/test_evaluate.py` | 6 | runs every evaluation profile, no crashes, pass criteria, table columns, saved report |
| `tests/test_ranking.py` | 2 | tie-break by title and top-k ordering |
| `tests/test_recommender.py` | 2 | starter tests for the placeholder Recommender class |
| `tests/test_self_check.py` | 14 | each self-check flag, fallbacks, notes on rank 1, self-check off, artist cap |
| `tests/test_validate_profile.py` | 33 | each validation rule (clamps, 400 BPM, missing key, unknown label, bad types), logging, reasons sum to score |

Real output of `python -m src.evaluate` (13 profiles: 3 baseline, 3 adversarial, 7 bad input; also saved to `evaluation_output.txt`):

| Profile | Input issue | Guardrail fired | Confidence | Self-check result | Pass/Fail |
|---|---|---|---|---|---|
| chill_lofi (baseline) | none | artist cap | 0.74 | fixed: artist_repeated | Pass |
| intense_rock (baseline) | none | artist cap | 1.00 | fixed: artist_repeated | Pass |
| high_energy_pop (baseline) | none | none | 1.00 | clean | Pass |
| conflicting_sad_but_hyper (adversarial) | conflicting targets: calm, sad, acoustic but max energy and fast tempo | none | 1.00 | clean | Pass |
| unknown_labels (adversarial) | genre and mood not in the catalog | unknown label, widen labels, artist cap | 0.58 | fixed: low_confidence, no_label_match, clustered_scores, artist_repeated | Pass |
| out_of_range_tempo (adversarial) | tempo 400 BPM, outside 40-200 | clamp, artist cap | 1.00 | fixed: artist_repeated | Pass |
| missing_keys (bad input) | required keys missing | missing key | 1.00 | clean | Pass |
| empty_profile (bad input) | empty dict | missing key, widen labels, artist cap | 0.59 | fixed: low_confidence, no_label_match, clustered_scores, artist_repeated | Pass |
| none_profile (bad input) | profile is None | type fix, missing key, widen labels, artist cap | 0.59 | fixed: low_confidence, no_label_match, clustered_scores, artist_repeated | Pass |
| non_numeric_targets (bad input) | non-numeric energy and tempo | type fix | 1.00 | clean | Pass |
| nan_target (bad input) | NaN valence | type fix, artist cap | 1.00 | fixed: artist_repeated | Pass |
| out_of_range_features (bad input) | energy 5 and valence -2, outside 0-1 | clamp | 1.00 | clean | Pass |
| wrong_label_types (bad input) | genre is a number, secondary genres is a string | type fix, artist cap | 0.76 | fixed: artist_repeated | Pass |

How a row passes (defined in `src/evaluate.py`):

- P1 no exception is raised
- P2 exactly 5 results are returned
- P3 every score is finite and within 0-7.0
- P4 confidence is within 0-1
- P5 every guardrail the case declares as expected actually fired
- P6 a clean input (no declared issue) fires no validation guardrail
- P7 after self-check no flag remains, or confidence is at least 0.5

What the numbers show: all 66 tests and all 13 profiles pass. The artist cap fires on several profiles, including clean baselines, because the 18-song catalog repeats artists (LoRoom, Neon Echo). The empty and `None` profiles reach confidence 0.59 only because the widen fallback borrows labels from the nearest songs, which is a fallback and not real knowledge of the user's taste.

---

## Experiments You Tried

Full outputs and the numbers behind these notes are in [model_card.md](model_card.md), section 6. Run them with `python -m src.experiments`.

- **Three profiles:** chill_lofi, intense_rock and high_energy_pop. Lofi shares no songs with rock or pop in the top 5. Rock and pop share 3 (Storm Runner, Gym Hero, Sunrise City) because both want high energy and energy is the heaviest weight.
- **Weight change (genre halved, energy doubled):** the top 3 stayed the same for every profile. For intense_rock, Iron Tide's lead over Gym Hero shrank from 0.652 to 0.052.
- **Adversarial profiles:**
  - Conflicting taste (classical, melancholy, energy 0.95): Cathedral Dust won at 4.933 on label points, even though its energy fit earned only +0.340 of 2.0.
  - Unknown genre and mood (k-pop, cozy): no song earned label points, and the top 5 sat within 0.207. The self-check now catches this case (sample run 2).
  - Out-of-range tempo (400 BPM): in the original version the tempo term went negative and the reasons stopped adding up to the score. `validate_profile` now clamps it to 200 BPM (sample run 3).

---

## Limitations and Risks

- **Tiny catalog:** 18 songs, with only one rock song. Rock and pop listeners drop sharply after rank 1 (rock: 6.854 to 5.136).
- **Exact-match labels:** "indie pop" earns nothing for a "pop" fan unless the profile lists it as a backup.
- **Hand-written backup lists:** without metal as a backup genre, Gym Hero beats Iron Tide for the rock profile.
- **Labels can outweigh numbers:** genre and mood together give up to 3.0 points, more than energy can (2.0).
- **No popularity or listening history:** it cannot learn from behavior, so it stays inside the taste it is given.
- **Guardrails are heuristics:** the confidence formula and the self-check thresholds are untested against real listeners, and the widen fallback can make a weak result look more certain than it is.

See [model_card.md](model_card.md) for the details, misuse risks and ideas for improvement.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

A simple weighted score plus clear reasons is enough to make a recommender feel smart. My biggest lesson was that the rules are not neutral: a hand-written backup list (metal for the rock profile) flipped Iron Tide ahead of Gym Hero, 5.136 to 4.484, and under different weights that lead shrank to 0.052. Bias shows up in small choices like the catalog (one rock song), exact-match labels, and how much weight labels get compared with numbers. The AI wrote most of the code quickly, but I had to check the arithmetic, the rounding and the docs myself, because its mistakes were quiet ones. The longer reflection is in section 9 of the model card.
