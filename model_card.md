# Model Card: VibeFinder 1.0

---

## 1. Model Name

**VibeFinder 1.0** — A Content-Based Filtering (CBF) music recommendation engine.

---

## 2. Goal / Task

Given a listener's stated preferences (favorite genre, mood, energy level, and
acoustic taste), VibeFinder scores every song in a catalog and returns the
top-k matches in ranked order with a plain-language explanation of why each
song was chosen.

It is designed to simulate how real-world recommenders (Spotify, Apple Music)
use audio features and metadata to match songs to listeners — without needing
any listening history.

---

## 3. Data Used

- **Catalog size:** 20 songs in `data/songs.csv`.
- **Genres covered:** pop, lofi, rock, ambient, jazz, synthwave, indie pop,
  hip-hop, classical, country, metal, r&b, edm, reggae, blues, folk, trap
  (17 genres).
- **Moods covered:** happy, chill, intense, relaxed, moody, focused, confident,
  melancholic, nostalgic, angry, romantic, energetic, sad, dreamy (14 moods).
- **Features per song:** id, title, artist, genre, mood, energy (0–1),
  tempo_bpm (60–200), valence (0–1), danceability (0–1), acousticness (0–1).
- **What is missing:** instrumentalness, speechiness, loudness (dB), key/mode,
  release year, and popularity. These are available in the real Spotify API
  and would make the CBF more precise.
- **All data is synthetic.** Feature values were manually assigned to
  approximate real-world audio patterns. They are not extracted from actual audio.

---

## 4. Algorithm Summary

VibeFinder uses **Content-Based Filtering (CBF)**: it compares audio and
categorical properties of each song directly against what the user says they want.

**Scoring rule** — every song gets a score from 0.0 (no match) to 1.0 (perfect):

```
score = (genre_match × 0.30)
      + (mood_match  × 0.20)
      + (energy_sim  × 0.20)
      + (valence_sim × 0.10)
      + (dance_sim   × 0.10)
      + (tempo_sim   × 0.05)
      + (acoustic_sim× 0.05)
```

- **Genre and mood** are binary: the song either matches the user's preference
  (score = 1.0) or it does not (score = 0.0).
- **Energy, valence, danceability, acousticness** use distance:
  `similarity = 1 - |user_value - song_value|`. The closer, the better.
- **Tempo** is first normalized to [0, 1] by dividing by 200, then the same
  distance formula applies.

**Ranking rule** — after scoring, three filters are applied before returning results:
1. Sort by score descending.
2. Drop songs below 0.35 (poor matches excluded).
3. Cap at 2 songs per artist (prevents one artist dominating the list).

**Scoring modes** — the weight distribution can be changed at runtime:

| Mode | genre | mood | energy | Notes |
|---|---|---|---|---|
| `balanced` | 0.30 | 0.20 | 0.20 | Default |
| `genre-first` | 0.50 | 0.15 | 0.15 | For strong genre identity |
| `mood-first` | 0.15 | 0.40 | 0.20 | For vibe-over-genre listeners |
| `energy-focused` | 0.15 | 0.20 | 0.40 | Phase 3 experiment |

---

## 5. Observed Behavior / Biases

### Bias 1 — Genre over-prioritization with hard string matching

Genre carries the highest single weight (0.30) and is evaluated as a binary
string comparison. This creates a hard boundary: "indie pop" scores 0.0 on
genre for a user who wants "pop", even though the two genres are musically
nearly identical. In testing, "Rooftop Lights" (indie pop/happy, score ~0.63)
ranked below "Gym Hero" (pop/intense, score ~0.76) for the High-Energy Pop
user, even though Gym Hero's mood was wrong. The genre bonus alone outweighed
the mood penalty.

### Bias 2 — Unknown genre collapses score range

When the user's genre is not in the catalog (e.g. "k-pop"), every song scores
0.0 on the 0.30-weight genre feature. The remaining 0.70 of the score is shared
among mood, energy, and audio features. Top scores clustered between 0.46 and
0.63 — tight and undifferentiated. The system still returns results, but with
far less confidence. Any genre-focused user outside the catalog will get a
"best of what we have" list rather than a meaningful match.

### Bias 3 — Conflicted preferences are silently averaged

The "high energy + sad mood" profile (energy=0.90, mood="sad") chose "Empty
Rooms" (blues/sad, energy=0.34) as its top pick with a score of 0.82. The
genre+mood match provided 0.50 points, which overwhelmed the energy penalty
(the energy similarity was only 0.44). The system has no way to detect or flag
that a user's preferences contradict each other — it just averages the signals
and picks a winner. In real life, this user might be frustrated by the result.

### Bias 4 — Energy is the de facto tiebreaker without genre/mood match

For the Deep Intense Rock profile, songs #3–#5 in the results all had no genre
or mood match. Their rankings were determined almost entirely by energy
proximity. This means the system defaults to "closest energy" when categorical
signals fail — which is a reasonable fallback but means the remaining 50% of
weights (valence, danceability, tempo, acousticness) rarely change outcomes.

---

## 6. Evaluation Process

Five user profiles were tested. Three cover typical listener personas; two are
adversarial edge cases designed to stress-test the scoring logic.

### Profile 1 — High-Energy Pop
```
genre="pop", mood="happy", energy=0.9, danceability=0.85, tempo_bpm=128
```
- **#1 Sunrise City** (score 0.9400): genre + mood match, energy/danceability
  near-perfect. Expected and correct.
- **Surprise:** "Storm Runner" (rock/intense) appeared at #5 (score 0.4685)
  with no genre or mood match — purely because its energy (0.91) is almost
  identical to the user's target (0.90). This is the energy tiebreaker bias
  in action.

### Profile 2 — Chill Lofi
```
genre="lofi", mood="chill", energy=0.35, likes_acoustic=True, tempo_bpm=75
```
- **#1 Library Rain** (score 0.9857): near-perfect across all features.
  Energy similarity was 1.00 (exact match at 0.35).
- **Surprise:** "Wildflower Road" (folk/dreamy) appeared at #5 (score 0.4708)
  with no genre or mood match. Its low energy (0.40) and high acousticness
  (0.88) made it numerically close enough to pass the threshold. To a human
  this result would feel wrong — a folk song in a lofi playlist.

### Profile 3 — Deep Intense Rock
```
genre="rock", mood="intense", energy=0.92, valence=0.35, tempo_bpm=155
```
- **#1 Storm Runner** (score 0.9657): genre + mood + energy all nearly
  perfect. Expected and correct.
- **Surprise:** "Iron Collapse" (metal/angry) ranked only #3 (score 0.4587)
  despite being musically closest to the user's taste. Metal ≠ rock as strings,
  and angry ≠ intense — two categorical misses dropped it behind Gym Hero
  (pop/intense, score 0.6073). The mood match alone was worth more than the
  metal song's closer audio profile.

### Profile 4 — Conflicted (adversarial)
```
genre="blues", mood="sad", energy=0.90, valence=0.15, tempo_bpm=140
```
- "Empty Rooms" (blues/sad, energy=0.34) won with 0.8220 despite an energy
  similarity of only 0.44. The genre+mood pair (0.50 weight) silenced the
  conflict. The rest of the top 5 were high-energy songs with no categorical
  match — the system had no other way to satisfy the energy target.
- **Finding:** The system cannot detect internal contradictions. Categorical
  and numerical signals are independent; one can dominate the other silently.

### Profile 5 — Unknown Genre (adversarial)
```
genre="k-pop", mood="happy", energy=0.80
```
- No genre match for any song. Scores compressed into 0.46–0.63.
- The top 5 were all mood="happy" or high-energy songs regardless of genre.
- **Finding:** A user with a genre not in the catalog effectively gets a
  mood + energy recommender. The 0.30 genre weight is simply lost, and the
  system still returns plausible-sounding results without any warning.

### Weight-Shift Experiment (Phase 3)
Energy weight doubled (0.20 → 0.40), genre halved (0.30 → 0.15), applied to
the Chill Lofi profile:

| Rank | Balanced mode | Energy-focused mode |
|---|---|---|
| #1 | Library Rain (lofi) | Library Rain (lofi) |
| #2 | Midnight Coding (lofi) | Midnight Coding (lofi) |
| #3 | Focus Flow (lofi) | **Spacewalk Thoughts (ambient)** |
| #4 | Spacewalk Thoughts (ambient) | **Focus Flow (lofi)** |
| #5 | Wildflower Road (folk) | **Coffee Shop Stories (jazz)** |

Spacewalk Thoughts (energy=0.28) overtook Focus Flow (energy=0.40) in
energy-focused mode because 0.28 is closer to the user's 0.35 target. Coffee
Shop Stories (jazz/relaxed, energy=0.37) entered the top 5, replacing Wildflower
Road. **Conclusion:** doubling the energy weight makes the system more sensitive
to small numerical differences and less loyal to genre labels. Results become
more sonically accurate but genre-blind.

---

## 7. Intended Use and Non-Intended Use

**Intended use:**
- Educational simulation of how content-based filtering works.
- Classroom exploration of bias, weight sensitivity, and edge cases.
- A base for building more sophisticated recommenders with real audio data.

**Not intended for:**
- Production music recommendation. The 20-song catalog is too small for real
  variety and the feature values are not real audio extractions.
- Personalization. The system has no memory — it cannot learn from skips,
  replays, or explicit ratings.
- Any population-level deployment. The catalog underrepresents many genres
  and reflects no real demographic data.

---

## 8. Ideas for Improvement

1. **Genre similarity matrix instead of binary matching.** Treat genres as
   related rather than identical or different. "Indie pop" should score 0.7
   for a "pop" user, not 0.0. This would significantly reduce the hard-boundary
   bias observed in profiles 1 and 3.

2. **Conflict detection in user profiles.** Before scoring, check if the user's
   preferences are internally consistent (e.g. high energy + very low valence +
   sad mood is unusual). Flag it or ask a clarifying question rather than
   silently proceeding.

3. **Implicit feedback loop.** Track which recommended songs the user accepts or
   skips, and adjust weights toward what actually engaged them. This would move
   the system toward a hybrid CBF + collaborative filtering approach.

---

## 9. Personal Reflection

Building VibeFinder 1.0 made the mechanics of recommendation systems concrete
in a way that reading about them never could. The most surprising moment was
seeing "Storm Runner" (rock/intense) appear in the High-Energy Pop top 5 not
because it was a good fit, but because its energy happened to be close. That
single result made the energy-as-tiebreaker bias completely visible — a bias
I had designed into the weights myself without realizing it would produce that
outcome.

Using AI assistance during development helped most at the design stage —
generating ideas for adversarial profiles like "high energy + sad mood" that I
would not have thought to test on my own. But AI also required careful checking:
when weight distributions were suggested, the math needed manual verification
to ensure all seven weights still summed to exactly 1.0. The AI could suggest
a direction; the validation was always mine to do.

What surprised me most about building this is how much a simple weighted sum
*feels* like a recommendation even when the underlying math is transparent. A
user reading "genre match: pop (+0.30)" understands immediately why a song was
chosen — there is no mystery. Real systems like Spotify deliberately hide this
detail, which makes their recommendations feel more "intelligent" but also less
trustworthy. Explainability is a design choice, not a technical limitation.

If I extended this project I would add a genre graph (pop → indie pop → folk
as a continuum) and a session context layer (what the user just listened to
should shift their profile dynamically). Those two changes would get it much
closer to what Spotify actually does.
