# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Give your model a short, descriptive name.  
Example: **VibeFinder 1.0**  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
- What assumptions does it make about the user  
- Is this for real users or classroom exploration  

---

## 3. How the Model Works  

**What it does.** This is a content-based recommender. It never looks at other listeners. It compares each song's attributes (genre, mood, energy, valence, danceability, acousticness and tempo) to one user's stated taste, gives every song a score, and returns the best matches with the reasons for each.

**The taste profile.** A profile is a plain Python dictionary with a favorite genre and mood, a short list of secondary genres and moods, and a target number for energy, valence, danceability, acousticness and tempo (BPM). The project also keeps the small `UserProfile` dataclass from the starter code, because the starter tests and the `Recommender` class still use it. The dictionary profiles are what the CLI uses. They are richer than that dataclass, which only has four fields.

**Scoring one song (maximum 7.0).** All the weights are named constants at the top of `src/recommender.py`.

| Part | Rule | Points |
|---|---|---|
| Genre | exact match / listed as secondary / neither | 2.0 / 1.0 / 0 |
| Mood | exact match / listed as secondary / neither | 1.0 / 0.5 / 0 |
| Energy | 2.0 x (1 - distance from target) | up to 2.0 |
| Valence | 0.5 x (1 - distance from target) | up to 0.5 |
| Danceability | 0.5 x (1 - distance from target) | up to 0.5 |
| Acousticness | 0.5 x (1 - distance from target) | up to 0.5 |
| Tempo | 0.5 x (1 - BPM distance / 160) | up to 0.5 |

Distance is the absolute difference between the song's value and the target (all 0 to 1 scales). Tempo uses a fixed 40 to 200 BPM range, so 160 BPM is the largest possible gap. The maximum is 2.0 + 1.0 + 2.0 + 0.5 + 0.5 + 0.5 + 0.5 = 7.0, reached only by a song that matches the genre, the mood and every target exactly.

**Ranking.** The program scores every song, sorts by score from highest to lowest, breaks ties by title from A to Z, and keeps the top k (5 in the CLI).

**Reasons.** The scorer writes one line for each part that earned points, such as `energy close to target (+1.840)`, using the exact points added to the score. The printed lines add up to the song's total score to within a few thousandths (rounding). A part that earns zero points is left out of the list, so a missing line means "no points" (for example, no genre line means the genre did not match).

**Changes from the starter.** The starter's `load_songs`, `score_song` and `recommend_songs` were empty stubs. They are now implemented. The starter `Recommender` class is unchanged and still returns placeholder results.

**Known limits.**

- The catalog has 18 songs and only one rock song (Storm Runner). The rock profile's genre match is rarely available, so its secondary list (metal) matters a lot. Without metal as a secondary genre, Gym Hero would outrank Iron Tide.
- Genres and moods are exact-match text labels. "indie pop" earns no credit for a "pop" fan, and "chill" earns none for "relaxed" unless the profile lists it.
- Secondary genres and moods are written by hand for each profile. They are not learned.
- Scores for songs with no label match are close together, so lower ranks rest on small numeric differences.
- Omitting zero-point terms from the reasons keeps them short, but it can hide why a song lost points.

---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
- What genres or moods are represented  
- Did you add or remove data  
- Are there parts of musical taste missing in the dataset  

---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
- Any patterns you think your scoring captures correctly  
- Cases where the recommendations matched your intuition  

---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider  
- Genres or moods that are underrepresented  
- Cases where the system overfits to one preference  
- Ways the scoring might unintentionally favor some users  

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
- What you looked for in the recommendations  
- What surprised you  
- Any simple tests or comparisons you ran  

No need for numeric metrics unless you created some.

---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences  
- Better ways to explain recommendations  
- Improving diversity among the top results  
- Handling more complex user tastes  

---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
- Something unexpected or interesting you discovered  
- How this changed the way you think about music recommendation apps  
