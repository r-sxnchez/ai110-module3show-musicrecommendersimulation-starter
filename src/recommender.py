"""
recommender.py
==============
Content-Based Filtering (CBF) music recommendation engine.

SCORING RULE  (see score_song)
------------------------------
Each song is compared to a user preference profile using a weighted sum:

    score = sum( weight_i × feature_score_i )

Default feature weights — must sum to 1.0 ("balanced" mode):
    genre        0.30   categorical: 1.0 if match, 0.0 if not
    mood         0.20   categorical: 1.0 if match, 0.0 if not
    energy       0.20   numerical:   1 - |user - song|
    valence      0.10   numerical:   1 - |user - song|
    danceability 0.10   numerical:   1 - |user - song|
    tempo_bpm    0.05   numerical:   1 - |user_norm - song_norm|  (÷ 200 first)
    acousticness 0.05   numerical:   1 - |user_pref - song|

SCORING MODES  (pass mode= to recommend_songs)
----------------------------------------------
    "balanced"      — default weights above
    "genre-first"   — genre weight doubled (0.50); audio features reduced
    "mood-first"    — mood weight doubled (0.40); genre reduced to 0.15
    "energy-focused"— energy weight doubled (0.40); genre halved to 0.15
                      (this is also the weight-shift experiment from Phase 3)

RANKING RULE  (applied in recommend_songs and rank_songs)
---------------------------------------------------------
    1. Sort by score descending — best match first.
    2. Drop songs below MIN_SCORE_THRESHOLD (0.35) — poor matches excluded.
    3. Cap at MAX_SONGS_PER_ARTIST (2) — prevents one artist dominating.
    4. Return the first k survivors.

Score range: 0.0 (no match) → 1.0 (perfect match).
"""

import csv
from dataclasses import dataclass
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default feature weights ("balanced" mode). All modes must sum to 1.0.
WEIGHTS: Dict[str, float] = {
    "genre":        0.30,
    "mood":         0.20,
    "energy":       0.20,
    "valence":      0.10,
    "danceability": 0.10,
    "tempo_bpm":    0.05,
    "acousticness": 0.05,
}

# Preset scoring modes — each is an alternate weight distribution summing to 1.0.
# Pass the mode name to recommend_songs(mode=...) to switch strategies.
SCORING_MODES: Dict[str, Dict[str, float]] = {
    # Default: balanced across genre, mood, and audio features.
    "balanced": WEIGHTS,

    # Prioritises categorical genre match above everything else.
    # Good for users with a very specific genre identity.
    "genre-first": {
        "genre":        0.50,
        "mood":         0.15,
        "energy":       0.15,
        "valence":      0.08,
        "danceability": 0.07,
        "tempo_bpm":    0.03,
        "acousticness": 0.02,
    },

    # Prioritises emotional context over genre.
    # Good for users who care more about vibe than genre label.
    "mood-first": {
        "genre":        0.15,
        "mood":         0.40,
        "energy":       0.20,
        "valence":      0.12,
        "danceability": 0.08,
        "tempo_bpm":    0.03,
        "acousticness": 0.02,
    },

    # Phase 3 experiment: energy weight doubled, genre weight halved.
    # Surfaces songs with the closest energy match regardless of genre.
    "energy-focused": {
        "genre":        0.15,
        "mood":         0.20,
        "energy":       0.40,
        "valence":      0.09,
        "danceability": 0.09,
        "tempo_bpm":    0.04,
        "acousticness": 0.03,
    },
}

MAX_TEMPO_BPM:        float = 200.0  # ceiling used to normalize tempo to [0, 1]
ACOUSTIC_PREF_HIGH:   float = 0.85   # acousticness target when likes_acoustic=True
ACOUSTIC_PREF_LOW:    float = 0.15   # acousticness target when likes_acoustic=False
MIN_SCORE_THRESHOLD:  float = 0.35   # ranking: drop songs scoring below this
MAX_SONGS_PER_ARTIST: int   = 2      # ranking: diversity cap per artist


# ---------------------------------------------------------------------------
# Data classes  (used by the OOP interface and tests)
# ---------------------------------------------------------------------------

@dataclass
class Song:
    """A song and its audio/metadata features."""
    id:           int
    title:        str
    artist:       str
    genre:        str
    mood:         str
    energy:       float   # [0.0–1.0] intensity and activity level
    tempo_bpm:    float   # raw beats per minute (typically 60–200)
    valence:      float   # [0.0–1.0] musical positivity/happiness
    danceability: float   # [0.0–1.0] suitability for dancing
    acousticness: float   # [0.0–1.0] acoustic vs. electronic (1.0 = fully acoustic)


@dataclass
class UserProfile:
    """A listener's stated taste preferences."""
    favorite_genre:      str
    favorite_mood:       str
    target_energy:       float
    likes_acoustic:      bool
    target_valence:      float = 0.5    # default: neutral positivity
    target_danceability: float = 0.5    # default: neutral danceability
    target_tempo_bpm:    float = 100.0  # default: moderate pace


# ---------------------------------------------------------------------------
# Core math
# ---------------------------------------------------------------------------

def _numerical_similarity(user_val: float, song_val: float) -> float:
    """
    Compute similarity for a numerical feature in [0, 1].

        similarity = 1.0 - |user_val - song_val|

    Returns 1.0 when values are identical, 0.0 when they are 1.0 apart.
    """
    return 1.0 - abs(user_val - song_val)


# ---------------------------------------------------------------------------
# Functional Interface  (Step 1–3 of the assignment; used by main.py)
# ---------------------------------------------------------------------------

def load_songs(csv_path: str) -> List[Dict]:
    """
    Load songs from a CSV file using Python's built-in csv module.

    Returns a list of dictionaries — one per song row — with all numeric
    fields cast to the correct Python type so math works downstream.

    Expected CSV columns:
        id, title, artist, genre, mood,
        energy, tempo_bpm, valence, danceability, acousticness

    Raises FileNotFoundError if csv_path does not exist.
    """
    songs: List[Dict] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)          # reads the header row automatically
        for row in reader:
            songs.append({
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    float(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })

    return songs


def score_song(
    user_prefs: Dict,
    song: Dict,
    weights: Dict[str, float] = None,
) -> Tuple[float, List[str]]:
    """
    Score a single song against a user preference dictionary.

    Returns
    -------
    (score, reasons)
        score   : float in [0.0, 1.0] — weighted similarity total.
        reasons : list of strings explaining each feature's contribution,
                  e.g. ["genre match: pop (+0.30)", "energy: song=0.82 ..."].

    user_prefs keys (all optional — missing keys fall back to neutral defaults):
        genre (str), mood (str), energy (float), valence (float),
        danceability (float), tempo_bpm (float), likes_acoustic (bool).
    """
    # Use the provided weight set, or fall back to the default WEIGHTS.
    w = weights if weights is not None else WEIGHTS

    reasons: List[str] = []

    # Resolve user preference values — use neutral defaults for anything missing.
    fav_genre  = str(user_prefs.get("genre",        "")).lower()
    fav_mood   = str(user_prefs.get("mood",         "")).lower()
    tgt_energy = float(user_prefs.get("energy",       0.5))
    tgt_val    = float(user_prefs.get("valence",      0.5))
    tgt_dance  = float(user_prefs.get("danceability", 0.5))
    tgt_tempo  = float(user_prefs.get("tempo_bpm",    100.0))
    likes_ac   = bool(user_prefs.get("likes_acoustic", False))

    # ── Categorical features (binary: match = 1.0, no match = 0.0) ──────────

    if fav_genre == song["genre"].lower():
        genre_pts = w["genre"]
        reasons.append(f"genre match: {song['genre']} (+{genre_pts:.2f})")
    else:
        genre_pts = 0.0
        reasons.append(
            f"genre mismatch: wanted '{fav_genre}', got '{song['genre']}' (+0.00)"
        )

    if fav_mood == song["mood"].lower():
        mood_pts = w["mood"]
        reasons.append(f"mood match: {song['mood']} (+{mood_pts:.2f})")
    else:
        mood_pts = 0.0
        reasons.append(
            f"mood mismatch: wanted '{fav_mood}', got '{song['mood']}' (+0.00)"
        )

    # ── Numerical features (continuous similarity in [0, 1]) ─────────────────

    energy_sim = _numerical_similarity(tgt_energy, song["energy"])
    energy_pts = w["energy"] * energy_sim
    reasons.append(
        f"energy: song={song['energy']:.2f}, user={tgt_energy:.2f}, "
        f"similarity={energy_sim:.2f} (+{energy_pts:.3f})"
    )

    val_sim = _numerical_similarity(tgt_val, song["valence"])
    val_pts = w["valence"] * val_sim
    reasons.append(
        f"valence: song={song['valence']:.2f}, user={tgt_val:.2f}, "
        f"similarity={val_sim:.2f} (+{val_pts:.3f})"
    )

    dance_sim = _numerical_similarity(tgt_dance, song["danceability"])
    dance_pts = w["danceability"] * dance_sim
    reasons.append(
        f"danceability: song={song['danceability']:.2f}, user={tgt_dance:.2f}, "
        f"similarity={dance_sim:.2f} (+{dance_pts:.3f})"
    )

    # Tempo must be normalized to [0, 1] before comparing.
    tempo_sim = _numerical_similarity(
        tgt_tempo / MAX_TEMPO_BPM,
        song["tempo_bpm"] / MAX_TEMPO_BPM,
    )
    tempo_pts = w["tempo_bpm"] * tempo_sim
    reasons.append(
        f"tempo: song={song['tempo_bpm']:.0f} BPM, user={tgt_tempo:.0f} BPM, "
        f"similarity={tempo_sim:.2f} (+{tempo_pts:.3f})"
    )

    # likes_acoustic bool → target float.
    ac_target = ACOUSTIC_PREF_HIGH if likes_ac else ACOUSTIC_PREF_LOW
    ac_sim    = _numerical_similarity(ac_target, song["acousticness"])
    ac_pts    = w["acousticness"] * ac_sim
    reasons.append(
        f"acousticness: song={song['acousticness']:.2f}, "
        f"pref={'high' if likes_ac else 'low'} (target={ac_target:.2f}), "
        f"similarity={ac_sim:.2f} (+{ac_pts:.3f})"
    )

    # ── Weighted sum ─────────────────────────────────────────────────────────
    total = round(
        genre_pts + mood_pts + energy_pts + val_pts
        + dance_pts + tempo_pts + ac_pts,
        4,
    )

    return total, reasons


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    mode: str = "balanced",
) -> List[Tuple[Dict, float, List[str]]]:
    """
    Score every song in the catalog and return the top-k recommendations.

    Uses score_song() as the judge for every song, then applies the ranking
    rule: sort → threshold filter → per-artist diversity cap → top-k.

    Note on sort() vs sorted():
        - list.sort()  : sorts the list *in place*, returns None. Mutates original.
        - sorted(list) : returns a *new* sorted list, leaves original unchanged.
    We use list.sort() here because we own the scored list and don't need the
    original ordering after this point.

    Parameters
    ----------
    user_prefs : Dict       — preference dict (see score_song for keys).
    songs      : List[Dict] — catalog from load_songs().
    k          : int        — max recommendations to return (default 5).
    mode       : str        — scoring mode key from SCORING_MODES
                             ("balanced", "genre-first", "mood-first",
                              "energy-focused"). Unknown keys fall back to
                             "balanced".

    Returns
    -------
    List of (song_dict, score, reasons) tuples, best match first.
    """
    # Look up the weight set for the requested mode; fall back to default.
    weights = SCORING_MODES.get(mode, WEIGHTS)

    # Score every song — collect (song, score, reasons) for the full catalog.
    scored: List[Tuple[Dict, float, List[str]]] = [
        (song, *score_song(user_prefs, song, weights=weights))
        for song in songs
    ]

    # Step 1: sort descending by score (index 1 of each tuple).
    scored.sort(key=lambda t: t[1], reverse=True)

    # Steps 2 + 3: threshold filter and diversity cap in a single pass.
    artist_counts: Dict[str, int] = {}
    ranked: List[Tuple[Dict, float, List[str]]] = []

    for song, score, reasons in scored:
        if score < MIN_SCORE_THRESHOLD:
            continue                                    # step 2: drop poor match

        count = artist_counts.get(song["artist"], 0)
        if count >= MAX_SONGS_PER_ARTIST:
            continue                                    # step 3: diversity cap

        ranked.append((song, score, reasons))
        artist_counts[song["artist"]] = count + 1

        if len(ranked) == k:
            break

    return ranked


# ---------------------------------------------------------------------------
# OOP Interface  (used by tests/test_recommender.py)
# ---------------------------------------------------------------------------

def rank_songs(
    scored: List[Tuple[Song, float]],
    k: int,
    min_score: float = MIN_SCORE_THRESHOLD,
    max_per_artist: int = MAX_SONGS_PER_ARTIST,
) -> List[Tuple[Song, float]]:
    """
    Apply the ranking rule to a list of (Song, score) pairs.

    Steps: sort → threshold filter → per-artist diversity cap → top-k.
    Separated from Recommender so it can be tested independently.
    """
    scored.sort(key=lambda pair: pair[1], reverse=True)

    artist_counts: Dict[str, int] = {}
    ranked: List[Tuple[Song, float]] = []

    for song, score in scored:
        if score < min_score:
            continue
        count = artist_counts.get(song.artist, 0)
        if count >= max_per_artist:
            continue
        ranked.append((song, score))
        artist_counts[song.artist] = count + 1
        if len(ranked) == k:
            break

    return ranked


class Recommender:
    """
    OOP wrapper around the CBF engine.

    Converts Song/UserProfile objects to the dict format that score_song()
    expects, then maps results back to Song objects. This way there is only
    one implementation of the scoring logic (score_song) used by both the
    functional and OOP interfaces.

    Example
    -------
        rec = Recommender(songs)
        top = rec.recommend(user, k=5)
        print(rec.explain_recommendation(user, top[0]))
    """

    def __init__(self, songs: List[Song]) -> None:
        self.songs = songs

    # -- private converters ---------------------------------------------------

    @staticmethod
    def _profile_to_dict(user: UserProfile) -> Dict:
        """Map a UserProfile to the dict format score_song() expects."""
        return {
            "genre":          user.favorite_genre,
            "mood":           user.favorite_mood,
            "energy":         user.target_energy,
            "valence":        user.target_valence,
            "danceability":   user.target_danceability,
            "tempo_bpm":      user.target_tempo_bpm,
            "likes_acoustic": user.likes_acoustic,
        }

    @staticmethod
    def _song_to_dict(song: Song) -> Dict:
        """Map a Song dataclass to the dict format score_song() expects."""
        return {
            "artist":       song.artist,
            "genre":        song.genre,
            "mood":         song.mood,
            "energy":       song.energy,
            "tempo_bpm":    song.tempo_bpm,
            "valence":      song.valence,
            "danceability": song.danceability,
            "acousticness": song.acousticness,
        }

    # -- public methods -------------------------------------------------------

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k Songs for this user, ordered by CBF score."""
        prefs = self._profile_to_dict(user)
        scored = [
            (song, score_song(prefs, self._song_to_dict(song))[0])
            for song in self.songs
        ]
        return [song for song, _ in rank_songs(scored, k)]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable reasons breakdown for a single song."""
        prefs = self._profile_to_dict(user)
        _, reasons = score_song(prefs, self._song_to_dict(song))
        return "\n".join(reasons)
