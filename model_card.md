# Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0** — A Content-Based Filtering (CBF) music recommendation engine.

---

## 2. Intended Use

VibeFinder 1.0 suggests the most musically compatible songs from a small catalog
based on a user's stated preferences for genre, mood, energy, and other audio features.

- **What it does:** Given a user taste profile, it scores every song in the catalog
  and returns the top-k matches ranked by similarity score.
- **Who it is for:** Educational and simulation use. This is a classroom project
  designed to explore the mechanics of real-world recommender systems.
- **What it assumes:** The user can express their taste as concrete numeric targets
  (e.g. "I want energy ≈ 0.8") and a preferred genre/mood. It does not learn from
  listening history — every recommendation run uses the provided profile only.
- **What it is NOT:** A production system. It has no user database, no implicit
  feedback loop, and no A/B testing infrastructure.

---

## 3. How the Model Works

VibeFinder uses **Content-Based Filtering (CBF)**: it compares the acoustic and
categorical properties of each song directly against what a user says they want.

### The Scoring Formula

Every song receives a score between 0.0 and 1.0:

```
score(user, song) = Σᵢ ( wᵢ × featureScoreᵢ )
```

This means: for each feature, we measure how closely the song matches the user's
preference, then multiply that closeness by the feature's importance (its weight).
Add all those weighted values together and you get the final score.

### Feature Rules

| Feature | Type | Rule | Weight |
|---|---|---|---|
| `genre` | Categorical | 1.0 if user genre = song genre, else 0.0 | **0.30** |
| `mood` | Categorical | 1.0 if user mood = song mood, else 0.0 | **0.20** |
| `energy` | Numerical | `1 - |user_energy - song_energy|` | **0.20** |
| `valence` | Numerical | `1 - |user_valence - song_valence|` | **0.10** |
| `danceability` | Numerical | `1 - |user_danceability - song_danceability|` | **0.10** |
| `tempo_bpm` | Numerical (normalized ÷ 200) | `1 - |user_tempo_norm - song_tempo_norm|` | **0.05** |
| `acousticness` | Numerical | `1 - |user_acoustic_pref - song_acousticness|` | **0.05** |
| **TOTAL** | | | **1.00** |

### Weight Rationale

- **Genre (0.30)** is the single strongest signal because genre defines the
  listener's fundamental expectation of what a song will sound like.
- **Mood (0.20)** captures the emotional context the user is in — "chill" vs.
  "intense" produces dramatically different listening experiences even within
  the same genre.
- **Energy (0.20)** is the most important continuous audio feature. It directly
  determines workout vs. study vs. relaxation fit.
- **Valence and Danceability (0.10 each)** refine the emotional and rhythmic fit.
- **Tempo and Acousticness (0.05 each)** provide fine-tuning but matter less than
  the core categorical and energy signals.

### Categorical vs. Numerical Similarity

- **Categorical (genre, mood):** Binary — either it matches or it does not.
  A "pop" song scores 0.0 on genre if the user wants "jazz", regardless of how
  close the audio features are.
- **Numerical:** Distance-based. A song with `energy=0.82` compared to a user
  target of `energy=0.80` gives `1 - |0.80 - 0.82| = 0.98` — almost perfect.
  A song with `energy=0.20` gives `1 - 0.60 = 0.40` — a weak match.

### Tempo Normalization

Tempo is measured in BPM (beats per minute), which can range from ~60 to ~200.
To compare it fairly with the other features (which are all on a 0–1 scale),
we normalize it by dividing by 200 before computing the distance.

### Acoustic Preference Conversion

The `likes_acoustic` field is a boolean. We convert it to a target float:
- `likes_acoustic = True`  → target acousticness = **0.85**
- `likes_acoustic = False` → target acousticness = **0.15**

This lets us use the same distance formula as all other numerical features.

---

## 4. Data

- **Catalog size:** 20 songs in `data/songs.csv` (10 original + 10 added).
- **Genres covered:** pop, lofi, rock, ambient, jazz, synthwave, indie pop,
  hip-hop, classical, country, metal, r&b, edm, reggae, blues, folk, trap (17 genres).
- **Moods covered:** happy, chill, intense, relaxed, moody, focused, confident,
  melancholic, nostalgic, angry, romantic, energetic, sad, dreamy (14 moods).
- **Features per song:** id, title, artist, genre, mood, energy, tempo_bpm,
  valence, danceability, acousticness (10 columns).
- **No data was removed.** All 20 songs are used as-is.
- **What is missing:** instrumentalness, speechiness, loudness (dB), key/mode,
  release year, and popularity. These are all available in the real Spotify API
  and would make the CBF more precise.
- **Whose taste does this data reflect?** The catalog is synthetic. It was
  designed to cover a wide variety of moods and genres and does not represent any
  real demographic. All audio feature values are manually assigned approximations,
  not extracted from real audio.

---

## 5. Strengths

- **Transparent and explainable.** Every recommendation comes with a full
  per-feature breakdown showing exactly how each feature contributed to the score.
  There is no "black box" — a user can read the output and understand why a song
  was recommended.
- **No cold start problem.** Unlike collaborative filtering, CBF does not need
  listening history. A brand new user with stated preferences gets meaningful
  recommendations immediately.
- **Works well for genre-specific users.** A user with a strong genre preference
  (e.g. "I only want jazz") will reliably see jazz songs at the top because genre
  has the highest weight (0.30) and categorical matching is strict.
- **Handles multi-dimensional taste.** Energy + mood together account for 40% of
  the score, meaning the system distinguishes between a "chill lofi" user and an
  "intense rock" user even if they share some numerical feature values.

---

## 6. Limitations and Bias

- **Binary genre matching creates hard edges.** "Indie pop" and "pop" are different
  strings, so a user who likes "pop" gets 0.0 on genre score for "Rooftop Lights"
  even though it is musically very similar. Real systems use genre embeddings or
  hierarchies to handle this.
- **Small catalog (20 songs)** means there can still be songs in the top-k even
  when the match is poor. With 20 songs and k=5, the threshold filter (score ≥ 0.35)
  matters more now, but score variance is still limited by the catalog size.
- **Genre and mood dominate.** Together they account for 50% of the score. A song
  that is a perfect genre/mood match but acoustically very different will still
  outscore a song that is acoustically identical but a different genre. This is by
  design but can feel wrong in edge cases.
- **Limited diversity mechanism.** The per-artist cap (max 2 per artist) prevents
  a single artist from dominating, but there is no genre diversity enforcement.
  All top-k results could still share the same genre.
- **No feedback loop.** The system cannot learn. If a user skips recommended songs,
  VibeFinder 1.0 will recommend the same songs next time.
- **All genres are synthetic.** Feature values were hand-assigned, not extracted
  from real audio. Real songs within these genres have much wider value distributions
  than this catalog captures.
- **Boolean acoustic preference is a coarse signal.** Converting True/False to
  0.85/0.15 is a simplification. Real users may want "slightly acoustic" (e.g. 0.5).

---

## 7. Evaluation

Three user profiles were tested manually to verify the system behaved as expected:

**Profile 1 — Pop/Happy/High-energy user**
```
genre="pop", mood="happy", energy=0.8, likes_acoustic=False
```
Expected top result: "Sunrise City" (pop, happy, energy=0.82).
Result: Correct — "Sunrise City" ranked #1 with a high score.

**Profile 2 — Lofi/Chill/Low-energy user**
```
genre="lofi", mood="chill", energy=0.35, likes_acoustic=True
```
Expected top results: "Library Rain" and "Midnight Coding" (both lofi/chill).
Result: Correct — both lofi songs ranked #1 and #2.

**Profile 3 — Neutral user (no genre/mood match)**
```
genre="metal", mood="angry", energy=0.5, likes_acoustic=False
```
Expected behavior: no genre or mood matches, scores driven entirely by
numerical features.
Result: Scores clustered tightly (low variance), demonstrating that without
categorical matches the system relies solely on audio proximity — a known
limitation for users outside the catalog's genre coverage.

Automated tests in `tests/test_recommender.py` verify:
1. Recommendations are sorted by score (pop/happy song ranks above lofi/chill
   when the user prefers pop/happy).
2. Explanations are non-empty strings.

---

## 8. Future Work

- **Genre similarity matrix:** Instead of binary genre matching, use a distance
  matrix where "indie pop" is close to "pop" and "lofi" is close to "ambient".
  This would smooth the hard categorical boundary.
- **Expand the catalog:** 50–100 songs would produce more meaningful score
  variance. Currently top-5 from 10 songs means half the catalog is always shown.
- **Add missing Spotify features:** instrumentalness, speechiness, loudness, and
  key/mode would all improve matching precision, especially for distinguishing
  vocal vs. instrumental preferences.
- **Diversity enforcement:** Add a post-ranking filter that limits songs per
  artist and ensures genre spread in the top-k.
- **User feedback loop:** Track which recommended songs the user accepts or skips
  and update the user profile weights accordingly — moving toward hybrid CBF + CF.
- **Adjustable weights:** Let users tune how much genre vs. energy matters to them
  (a slider UI would make this intuitive).
- **Context awareness:** Recommend differently at 7am (high energy) vs. 11pm
  (low energy) based on time-of-day signals.

---

## 9. Personal Reflection

*(Fill in after running the simulation and observing results.)*

Prompts to guide your reflection:
- What surprised you about how your system behaved?
- How did building this change how you think about real music recommenders like
  Spotify or TikTok?
- Where do you think human judgment still matters, even when the model seems "smart"?
- Did the formula feel fair? Were there cases where the output felt wrong?
