"""
main.py
=======
Command-line runner for the Music Recommender Simulation.

Runs five user profiles (three standard + two adversarial edge cases)
in "balanced" mode, then runs a weight-shift experiment that compares
"balanced" vs "energy-focused" mode for the Chill Lofi profile.

Run with:
    python -m src.main
"""

from src.recommender import load_songs, recommend_songs, SCORING_MODES


# ---------------------------------------------------------------------------
# User profiles
# ---------------------------------------------------------------------------

# Three standard listener personas.
PROFILES = {
    "High-Energy Pop": {
        "genre":          "pop",
        "mood":           "happy",
        "energy":         0.9,
        "likes_acoustic": False,
        "danceability":   0.85,
        "tempo_bpm":      128.0,
    },
    "Chill Lofi": {
        "genre":          "lofi",
        "mood":           "chill",
        "energy":         0.35,
        "likes_acoustic": True,
        "valence":        0.55,
        "tempo_bpm":      75.0,
    },
    "Deep Intense Rock": {
        "genre":          "rock",
        "mood":           "intense",
        "energy":         0.92,
        "likes_acoustic": False,
        "valence":        0.35,
        "tempo_bpm":      155.0,
    },
    # ── Adversarial / edge-case profiles ────────────────────────────────────
    # High energy but sad mood — internally conflicted preferences.
    # Tests whether the system handles contradictory signals gracefully.
    "Conflicted (high energy + sad mood)": {
        "genre":          "blues",
        "mood":           "sad",
        "energy":         0.90,
        "likes_acoustic": False,
        "valence":        0.15,
        "tempo_bpm":      140.0,
    },
    # Genre not present in the catalog — forces pure audio-feature ranking.
    # Tests what happens when the 0.30-weight genre signal is always zero.
    "Unknown Genre (k-pop)": {
        "genre":          "k-pop",
        "mood":           "happy",
        "energy":         0.80,
        "likes_acoustic": False,
    },
}

# The experiment compares these two modes for the same profile.
EXPERIMENT_PROFILE = "Chill Lofi"
EXPERIMENT_MODES   = ["balanced", "energy-focused"]


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _separator(char: str = "-", width: int = 64) -> str:
    return char * width


def print_profile_results(
    name: str,
    user_prefs: dict,
    results: list,
) -> None:
    """Print a labelled block of recommendations for one profile."""
    print(f"\n{'=' * 64}")
    print(f"  PROFILE: {name}")
    print(f"  Prefs:   genre={user_prefs.get('genre')!r}, "
          f"mood={user_prefs.get('mood')!r}, "
          f"energy={user_prefs.get('energy', 0.5)}")
    print(f"{'=' * 64}")

    if not results:
        print("  No songs passed the minimum score threshold (0.35).")
        return

    for rank, (song, score, reasons) in enumerate(results, start=1):
        print(f"\n  #{rank}  {song['title']}  by  {song['artist']}")
        print(f"       Score : {score:.4f}")
        print(f"       Why   :")
        for reason in reasons:
            print(f"         • {reason}")
        print(f"  {_separator()}")


def print_experiment(songs: list) -> None:
    """
    Run the weight-shift experiment:
    same profile, 'balanced' vs 'energy-focused' mode, side by side.
    """
    prefs = PROFILES[EXPERIMENT_PROFILE]

    print(f"\n{'#' * 64}")
    print(f"  EXPERIMENT — Weight Shift: balanced vs energy-focused")
    print(f"  Profile : {EXPERIMENT_PROFILE}")
    print(f"  Change  : energy 0.20->0.40 | genre 0.30->0.15")
    print(f"{'#' * 64}")

    for mode in EXPERIMENT_MODES:
        w = SCORING_MODES[mode]
        results = recommend_songs(prefs, songs, k=5, mode=mode)

        print(f"\n  Mode: {mode.upper()}"
              f"  (genre={w['genre']:.2f}, mood={w['mood']:.2f},"
              f" energy={w['energy']:.2f})")
        print(f"  {_separator()}")

        for rank, (song, score, _) in enumerate(results, start=1):
            print(f"    #{rank}  {song['title']:<22}"
                  f"  [{song['genre']:<10} / {song['mood']:<10}]"
                  f"  score={score:.4f}")

    print(
        f"\n  FINDING: In 'energy-focused' mode the genre match bonus is "
        f"halved,\n"
        f"  so songs with very close energy values can overtake genre matches.\n"
        f"  Watch for non-lofi songs climbing the lofi profile ranking."
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs.\n")

    # Run all five profiles in balanced mode.
    for name, prefs in PROFILES.items():
        results = recommend_songs(prefs, songs, k=5, mode="balanced")
        print_profile_results(name, prefs, results)

    # Run the weight-shift experiment.
    print_experiment(songs)


if __name__ == "__main__":
    main()
