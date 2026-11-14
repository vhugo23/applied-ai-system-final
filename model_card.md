# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

A small program that picks songs from a short list by comparing them to one person's taste, and says why it picked each one.

---

## 2. Goal / Task

The goal is to suggest the songs that best fit one listener's taste.

It works from two things:

- A **taste profile**: a favorite genre and mood, a few backup genres and moods, and target numbers for energy, valence (how happy a song sounds), danceability, acousticness (how acoustic it sounds) and tempo (beats per minute).
- The **song features** stored for each song in the catalog.

It compares the profile to every song, gives each song a score, and returns the top five with the reasons. It does not learn from anyone's listening history. It only compares attributes.

---

## 3. Data Used

- **Catalog:** 18 songs in `data/songs.csv`.
- **Columns:** `id`, `title`, `artist`, `genre`, `mood`, `energy`, `tempo_bpm`, `valence`, `danceability`, `acousticness`.
- **Number ranges:** energy, valence, danceability and acousticness run from 0 to 1. Tempo runs from 54 to 172 beats per minute. Energy in the catalog runs from 0.12 to 0.98.
- **Genres (15):** pop (2 songs), lofi (3), rock, ambient, jazz, synthwave, indie pop, classical, hip hop, metal, country, reggae, folk, edm and r&b (1 each).
- **Moods (14):** chill (3 songs), happy (2), intense (2), and relaxed, moody, focused, melancholy, confident, aggressive, nostalgic, peaceful, wistful, euphoric and romantic (1 each).

**Limits of the data:**

- The catalog is very small.
- The first 10 songs came with the starter project. An AI assistant added the last 8 (ids 11 to 18) in this project, using genres and moods that were not in the file yet.
- All titles and artists are invented.
- There is only one rock song (Storm Runner). Most genres and moods have just one song.
- Whole parts of musical taste are missing, such as lyrics, language, and anything about the artist or how popular a song is.

---

## 4. Algorithm Summary

**Scoring one song (maximum 7.0).** The weights are named constants at the top of `src/recommender.py`. The scorer gives points for each part below and adds them up.

| Part | Rule | Points |
|---|---|---|
| Genre | exact match / listed as a backup genre / neither | 2.0 / 1.0 / 0 |
| Mood | exact match / listed as a backup mood / neither | 1.0 / 0.5 / 0 |
| Energy | 2.0 x (1 - distance from target) | up to 2.0 |
| Valence | 0.5 x (1 - distance from target) | up to 0.5 |
| Danceability | 0.5 x (1 - distance from target) | up to 0.5 |
| Acousticness | 0.5 x (1 - distance from target) | up to 0.5 |
| Tempo | 0.5 x (1 - beats-per-minute distance / 160) | up to 0.5 |

"Distance" is the plain gap between the song's number and the target. The closer the song is, the more points it earns. Tempo uses a fixed range of 40 to 200 beats per minute, so 160 is the biggest possible gap. The top score is 2.0 + 1.0 + 2.0 + 0.5 + 0.5 + 0.5 + 0.5 = **7.0**. A song only reaches it by matching the genre, the mood and every target exactly.

**Ranking.** The program scores every song. It sorts from highest score to lowest. If two songs tie, the one whose title comes first in A to Z order goes first. It keeps the top five.

**Reasons.** Each part that earns points writes one line, such as `energy close to target (+1.840)`. The line shows the exact points added. The lines add up to the song's total score, give or take a few thousandths from rounding. A part that earns zero points is left out, so a missing line means "no points".

**Profiles.** The profiles the program uses are simple lists of settings. The older `UserProfile` shape from the starter project is still in the code. It has only four fields. The starter's `Recommender` class and its tests still use it, so I kept it. That class is unchanged and still gives placeholder answers.

---

## 5. Observed Behavior / Biases

All numbers below come from the real run of `python -m src.main` (see "Sample Recommendation Output" in the README) and from the catalog.

- **Rock listeners fall off a cliff after rank 1.** Storm Runner, the only rock song, scores 6.854. Rank 2 (Iron Tide) scores 5.136. That is a drop of 1.718. For the lofi profile the first drop is only 0.058, because the catalog has three lofi songs.
- **Most songs get no label points.** For intense_rock, 15 of the 18 songs earn no genre or mood points. For chill_lofi, 12 of 18 earn none. Those songs are ranked only by how close their numbers are.
- **Lower ranks are packed together.** For intense_rock, ranks 4 to 8 span just 0.206 points (3.355 down to 3.149). Ranks 4 and 5 differ by 0.020 (Night Drive Loop 3.355, Sunrise City 3.335). Small number differences decide those places.
- **The backup lists decide some results.** Iron Tide (metal) beats Gym Hero (pop) only because the rock profile lists metal as a backup genre and aggressive as a backup mood. In a quick test run without the metal backup, Iron Tide scored 4.14 and Gym Hero 4.48, so Gym Hero came first. A person writes these lists by hand. The program does not learn them.
- **Labels must match exactly.** "indie pop" earns nothing for a "pop" fan. "relaxed" earns nothing for a "chill" fan unless the profile lists it. For chill_lofi, Coffee Shop Stories (jazz, relaxed) ranks 5th only because jazz and relaxed are listed as backups. It earns 1.5 label points that way.
- **A pop song ranks 3rd for the rock profile.** Gym Hero (pop, intense) scores 4.484. It earns the 1.0 mood match and a high energy score (+1.940). That is a reasonable result for a listener who wants intense, high-energy songs. It shows that mood can lift a song from a different genre.
- **Two songs by the same artist share the rock list.** Night Drive Loop and Sunrise City, both by Neon Echo, are ranks 4 and 5. Nothing in the program tries to vary artists.

- **Labels can outweigh what the listener asked for.** For the conflicting profile (classical, melancholy, but energy 0.95), Cathedral Dust wins with 4.933. Its genre and mood give 3.0 of those points. Its energy is 0.12 against a target of 0.95, so it earns only +0.340 of a possible 2.0. The songs that fit the energy best (Iron Tide 3.324, Storm Runner 3.069) have no label match and rank behind it.
- **A tempo target outside the 40 to 200 range breaks the reasons.** For the out-of-range tempo profile (target 400 BPM), every song's tempo term goes negative. The score quietly loses points, but no reason line is written for a negative term. Sunrise City's printed reasons add up to 6.425 but its score is 6.044. The lowest score drops to 0.559. This is a gap in the current code. I have not changed it.
- **Unknown labels turn the system into a numbers-only ranking.** For the unknown-labels profile (k-pop, cozy), no song earns label points. The top 5 sit within 0.207 of each other (3.709 down to 3.502), so the order is nearly arbitrary.
- **Pop listeners also fall off a cliff.** For high_energy_pop, only four songs earn any label points. Rank 4 scores 5.230 and rank 5 scores 3.650, a drop of 1.580. Rank 5 (Storm Runner, a rock song) is there on energy alone.
- **Energy is the strongest pull across different tastes.** The rock and pop profiles share 3 of their 5 songs (Storm Runner, Gym Hero, Sunrise City), because energy is worth up to 2.0 points and both profiles want high energy.

**Biggest weakness.** The system lets labels override numbers. In my conflicting profile (classical, melancholy, energy 0.95), Cathedral Dust won with 4.933 even though its energy fit earned only +0.340 of 2.0. Genre and mood gave it 3.0 points, more than any song can earn from energy alone. A listener whose labels and numbers disagree gets results that ignore half of what they asked for.

**What seems to work.** The three lofi songs take ranks 1 to 3 for chill_lofi, followed by an ambient and a jazz song, which fits that taste. For intense_rock, Storm Runner is first and the metal song Iron Tide is second. That matches my reading of the taste, but I did not test it with real listeners.

**Features not used:** lyrics, language, artist, popularity, and when or where someone listens.

---

## 6. Evaluation Process

**Profiles run through the program (`python -m src.main`):**

- `chill_lofi`: lofi, chill, energy 0.35, valence 0.55, danceability 0.55, acousticness 0.70, tempo 76. Backup genres: ambient, jazz, folk. Backup moods: focused, relaxed.
- `intense_rock`: rock, intense, energy 0.90, valence 0.40, danceability 0.50, acousticness 0.10, tempo 150. Backup genre: metal. Backup mood: aggressive.
- `high_energy_pop`: pop, happy, energy 0.90, valence 0.80, danceability 0.85, acousticness 0.10, tempo 128. Backup genres: indie pop, edm. Backup mood: euphoric. (I chose these numbers and backup labels myself. Change them if they do not match your idea of this listener.)

**Results (top 5):**

| Rank | chill_lofi | Score | intense_rock | Score | high_energy_pop | Score |
|---|---|---|---|---|---|---|
| 1 | Library Rain | 6.867 | Storm Runner | 6.854 | Sunrise City | 6.719 |
| 2 | Midnight Coding | 6.809 | Iron Tide | 5.136 | Gym Hero | 5.872 |
| 3 | Focus Flow | 6.303 | Gym Hero | 4.484 | Rooftop Lights | 5.562 |
| 4 | Spacewalk Thoughts | 5.580 | Night Drive Loop | 3.355 | Laser Bloom | 5.230 |
| 5 | Coffee Shop Stories | 5.236 | Sunrise City | 3.335 | Storm Runner | 3.650 |

**Main comparison: Iron Tide vs Gym Hero (intense_rock).** Iron Tide scores 5.136 and Gym Hero scores 4.484, so Iron Tide comes first. Iron Tide gets 1.5 label points (backup genre 1.0, backup mood 0.5). Gym Hero gets 1.0 (mood). Gym Hero gets a little back from energy (+1.940 against +1.840). This was the problem that the new scoring weights were meant to fix.

### Adversarial profiles

These three profiles were built to push the program into odd cases. They are defined in `src/experiments.py` and run with `python -m src.experiments`. This is the real terminal output.

<details>
<summary>Terminal output: adversarial profiles</summary>

```text
##### ADVERSARIAL PROFILES #####

=== Top 5 for conflicting_sad_but_hyper ===

1. Cathedral Dust - Helena Voss  (score 4.933)
     genre match (+2.000)
     mood match (+1.000)
     energy close to target (+0.340)
     valence close to target (+0.490)
     danceability close to target (+0.475)
     acousticness close to target (+0.490)
     tempo close to target (+0.138)

2. Iron Tide - Black Harbor  (score 3.324)
     energy close to target (+1.940)
     valence close to target (+0.475)
     danceability close to target (+0.375)
     acousticness close to target (+0.040)
     tempo close to target (+0.494)

3. Storm Runner - Voltline  (score 3.069)
     energy close to target (+1.920)
     valence close to target (+0.360)
     danceability close to target (+0.270)
     acousticness close to target (+0.075)
     tempo close to target (+0.444)

4. Gym Hero - Max Pulse  (score 2.766)
     energy close to target (+1.960)
     valence close to target (+0.215)
     danceability close to target (+0.160)
     acousticness close to target (+0.050)
     tempo close to target (+0.381)

5. Laser Bloom - Pixel Parade  (score 2.649)
     energy close to target (+1.980)
     valence close to target (+0.135)
     danceability close to target (+0.130)
     acousticness close to target (+0.035)
     tempo close to target (+0.369)

Lowest score for conflicting_sad_but_hyper: Island Hammock 1.971

=== Top 5 for unknown_labels ===

1. Dusty Porch Light - Willow Creek Band  (score 3.709)
     energy close to target (+1.960)
     valence close to target (+0.410)
     danceability close to target (+0.465)
     acousticness close to target (+0.380)
     tempo close to target (+0.494)

2. Midnight Coding - LoRoom  (score 3.576)
     energy close to target (+1.840)
     valence close to target (+0.470)
     danceability close to target (+0.440)
     acousticness close to target (+0.395)
     tempo close to target (+0.431)

3. Island Hammock - Sol Rivers  (score 3.565)
     energy close to target (+1.900)
     valence close to target (+0.350)
     danceability close to target (+0.390)
     acousticness close to target (+0.475)
     tempo close to target (+0.450)

4. Velvet Hours - Amara Lux  (score 3.532)
     energy close to target (+1.900)
     valence close to target (+0.400)
     danceability close to target (+0.370)
     acousticness close to target (+0.400)
     tempo close to target (+0.463)

5. Focus Flow - LoRoom  (score 3.502)
     energy close to target (+1.800)
     valence close to target (+0.455)
     danceability close to target (+0.450)
     acousticness close to target (+0.360)
     tempo close to target (+0.438)

Lowest score for unknown_labels: Laser Bloom 2.317

=== Top 5 for out_of_range_tempo ===

1. Sunrise City - Neon Echo  (score 6.044)
     genre match (+2.000)
     mood match (+1.000)
     energy close to target (+1.960)
     valence close to target (+0.480)
     danceability close to target (+0.495)
     acousticness close to target (+0.490)

2. Gym Hero - Max Pulse  (score 4.772)
     genre match (+2.000)
     energy close to target (+1.740)
     valence close to target (+0.485)
     danceability close to target (+0.460)
     acousticness close to target (+0.425)

3. Rooftop Lights - Indigo Parade  (score 3.968)
     mood match (+1.000)
     energy close to target (+1.920)
     valence close to target (+0.495)
     danceability close to target (+0.490)
     acousticness close to target (+0.425)

4. Concrete Crown - Kid Marlow  (score 2.810)
     energy close to target (+1.960)
     valence close to target (+0.410)
     danceability close to target (+0.450)
     acousticness close to target (+0.440)

5. Night Drive Loop - Neon Echo  (score 2.794)
     energy close to target (+1.900)
     valence close to target (+0.345)
     danceability close to target (+0.465)
     acousticness close to target (+0.490)

Lowest score for out_of_range_tempo: Cathedral Dust 0.559
```

</details>

- `conflicting_sad_but_hyper` (classical, melancholy, energy 0.95, acousticness 0.95, tempo 170): the song that matches the labels (Cathedral Dust, 4.933) wins even though its energy is very far from the target. See section 5.
- `unknown_labels` (k-pop, cozy, every number near the middle): no label can match, so only the numbers count. Dusty Porch Light is first at 3.709. The top 5 span only 0.207.
- `out_of_range_tempo` (pop, happy, tempo 400): tempo points go negative and are silently subtracted. No tempo lines appear in the reasons, and the reasons no longer add up to the score. See section 5.

### Sensitivity experiment: genre halved, energy doubled

I halved the genre weight (exact 2.0 to 1.0, backup 1.0 to 0.5) and doubled the energy weight (2.0 to 4.0). The maximum score becomes 8.0. Everything else stayed the same. I ran it on all three profiles.

```text
##### SENSITIVITY EXPERIMENT: genre exact 2.0 -> 1.0 (secondary 1.0 -> 0.5), energy 2.0 -> 4.0 #####
(max score becomes 8.0)

--- chill_lofi ---
rank baseline                          experiment                        
1    Library Rain 6.867                Library Rain 7.867                
2    Midnight Coding 6.809             Midnight Coding 7.669             
3    Focus Flow 6.303                  Focus Flow 7.202                  
4    Spacewalk Thoughts 5.580          Spacewalk Thoughts 6.940          
5    Coffee Shop Stories 5.236         Coffee Shop Stories 6.696         

--- intense_rock ---
rank baseline                          experiment                        
1    Storm Runner 6.854                Storm Runner 7.834                
2    Iron Tide 5.136                   Iron Tide 6.476                   
3    Gym Hero 4.484                    Gym Hero 6.424                    
4    Night Drive Loop 3.355            Sunrise City 5.175                
5    Sunrise City 3.335                Laser Bloom 5.166                 

--- high_energy_pop ---
rank baseline                          experiment                        
1    Sunrise City 6.719                Sunrise City 7.559                
2    Gym Hero 5.872                    Gym Hero 6.812                    
3    Rooftop Lights 5.562              Rooftop Lights 6.782              
4    Laser Bloom 5.230                 Laser Bloom 6.610                 
5    Storm Runner 3.650                Storm Runner 5.630                
```

What changed:

- The top 3 songs and their order stayed the same for all three profiles. For chill_lofi and high_energy_pop the whole top 5 stayed in the same order.
- For intense_rock, ranks 4 and 5 changed. Sunrise City (5.175) and Laser Bloom (5.166) replaced Night Drive Loop. Both have energy closer to 0.90.
- Iron Tide still beats Gym Hero, but the gap shrank from 0.652 to 0.052 (6.476 against 6.424). The rock result is thin under these weights.
- Takeaway: the best matches are stable. The lower places are sensitive to how much weight energy gets.

### Pairwise comparisons (core profiles)

```text
##### PAIRWISE TOP-5 OVERLAP (core profiles) #####

chill_lofi vs intense_rock: 0 shared []
chill_lofi vs high_energy_pop: 0 shared []
intense_rock vs high_energy_pop: 3 shared ['Storm Runner', 'Gym Hero', 'Sunrise City']
```

- **chill_lofi vs intense_rock: 0 shared songs.** These are opposite tastes: energy 0.35 against 0.90, and acousticness 0.70 against 0.10. The program separates them cleanly.
- **chill_lofi vs high_energy_pop: 0 shared songs.** Same reason. The lofi list is quiet and acoustic, and the pop list is loud and danceable. It also shows that the lofi list needs its backup genres (ambient, jazz) to fill ranks 4 and 5.
- **intense_rock vs high_energy_pop: 3 shared songs** (Storm Runner, Gym Hero, Sunrise City). Both profiles want high energy and low acousticness, and energy is the heaviest weight. Gym Hero is 3rd for rock and 2nd for pop. Sunrise City is 5th for rock (3.335, no label points) and 1st for pop (6.719). Labels are what pull these two lists apart at the top.

**Tests in `tests/` (4 tests, all passing):**

- `test_recommend_returns_songs_sorted_by_score` and `test_explain_recommendation_returns_non_empty_string` come from the starter. They check the starter `Recommender` class only. That class is still a placeholder.
- `test_tie_break_sorts_equal_scores_by_title` checks that three songs with the same score come back in A to Z order by title.
- `test_recommend_songs_returns_k_results_sorted_high_to_low` checks that asking for 3 results returns exactly 3, from highest score to lowest.

The experiments in `src/experiments.py` have no tests of their own.

**Quick experiments from the design stage.** I ran these in throwaway scripts on the real catalog before the experiment file existed. The scripts were not saved.

- *Linear vs squared closeness.* Squared closeness gave the same top 3 for both original profiles. For chill_lofi the top 5 was identical. For intense_rock, ranks 4 to 6 reshuffled, but they were within 0.02 of each other. I kept the simple linear version.
- *Mood weight raised from 1.0 to 3.0 (backup 1.5).* This made Gym Hero (6.48) beat Iron Tide (6.14) again. For chill_lofi it put Spacewalk Thoughts (7.58) above Focus Flow (7.30). I did not adopt it.
- *Removing metal from the rock backup genres.* Gym Hero (4.48) beat Iron Tide (4.14), as noted in section 5.

**Not yet run:** testing with real listeners.

---

## 7. Intended Use and Non-Intended Use

**Intended use:**

- Classroom learning about how a simple recommender works.
- Small simulations that show how scores, ranking and explanations fit together.
- Exploring what happens when you change a weight or a profile.

**Not intended for:**

- Real product recommendations. The catalog is 18 invented songs.
- Judging or labeling people from their taste.
- Anything that needs fairness guarantees. The program has not been checked for fairness across different kinds of listeners.

---

## 8. Ideas for Improvement

1. **Make the catalog bigger,** with several songs per genre. With only one rock song, rock listeners drop from 6.854 to 5.136 after rank 1. More songs per genre would fix that.
2. **Give partial credit for related genres** from a small shared table (for example, rock and metal), instead of a hand-written backup list for each profile. This would remove the dependence on lists like the one that put Iron Tide above Gym Hero.
3. **Add a variety rule** so a top-5 list does not repeat an artist (Neon Echo took ranks 4 and 5 for intense_rock) or fill up with one genre.

---

## 9. Personal Reflection

**My biggest learning moment.** For the rock profile, Iron Tide (metal) lost to Gym Hero (pop) until I listed metal as a backup genre. Then Iron Tide won, 5.136 to 4.484. I had assumed a scoring rule was neutral, but my hand-written backup list flipped the ranking. When I halved the genre weight and doubled the energy weight, the lead shrank to 0.052, so that win is fragile.

**How AI helped, and when I double-checked it.** The AI wrote the song loader, the scoring function, the tests and the first drafts of the docs much faster than I could. It also explained the difference between `sorted()` and `.sort()`. But I had to check its work. The reasons it printed with 2 decimals added up to 5.12 while the score was 5.14, so I asked for 3 decimals. The README still described the old 0.35/0.25/0.25/0.15 weights until the AI flagged it and I had it updated. When we ran a 400 BPM profile, the tempo term went negative and the reasons stopped adding up to the score. For now I documented that instead of fixing it. The AI was confident and mostly right, but its mistakes were quiet ones (rounding, stale docs, untested edge cases), so I needed to check the arithmetic and the changes myself.

**What surprised me about simple algorithms.** A handful of weighted rules produced lists that looked sensible. For chill_lofi, the three lofi songs took ranks 1 to 3, and each came with reasons like "energy close to target (+1.860)". Those explanations are what make it feel smart. But it does not understand music. For the k-pop profile, no song earned any label points and the top five were only 0.207 apart, so the order was close to arbitrary. A good-looking recommendation can hide how little is going on.

**What I would try next.**

- Add more songs per genre. Rock listeners drop from 6.854 to 5.136 after rank 1. I would know it worked if that drop shrank.
- Limit the tempo term so it cannot go below zero, and check the inputs. I would know it worked if the reasons added up to the score for the 400 BPM profile.
- Add a variety rule. Neon Echo took ranks 4 and 5 for intense_rock. I would check that no artist appears twice in a top five.
