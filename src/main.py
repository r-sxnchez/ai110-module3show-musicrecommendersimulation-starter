"""
main.py
=======
Command-line runner for the Music Recommender Simulation.

Run with:
    python -m src.main
"""

from src.recommender import load_songs, recommend_songs


def main() -> None:
    # Step 1: load the catalog using the csv module.
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs.\n")

    # Step 2: define a user preference profile.
    # Change these values to test different listener personas.
    user_prefs = {
        "genre":          "pop",
        "mood":           "happy",
        "energy":         0.8,
        "likes_acoustic": False,
        # Optional — defaults: valence=0.5, danceability=0.5, tempo_bpm=100
        "valence":        0.5,
        "danceability":   0.5,
        "tempo_bpm":      100.0,
    }

    # Step 3: score and rank all songs, return the top k.
    results = recommend_songs(user_prefs, songs, k=5)

    # Step 4: display results in a clean, readable layout.
    print(
        f"Top {len(results)} recommendations  "
        f"[genre={user_prefs['genre']!r}, "
        f"mood={user_prefs['mood']!r}, "
        f"energy={user_prefs['energy']}]"
    )
    print("=" * 62)

    for rank, (song, score, reasons) in enumerate(results, start=1):
        print(f"\n#{rank}  {song['title']}  by  {song['artist']}")
        print(f"    Score: {score:.4f}")
        print("    Why this song was recommended:")
        for reason in reasons:
            print(f"      • {reason}")
        print("-" * 62)


if __name__ == "__main__":
    main()
