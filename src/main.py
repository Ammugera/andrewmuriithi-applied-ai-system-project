"""
Command-line runner for the Music Recommender Simulation.

Prints the top recommendations for each preset profile in src/profiles.py.
The Streamlit dashboard (src/app.py) is the primary deliverable; this CLI
remains as a sanity check that the scoring engine is unchanged.
"""

from src.profiles import PROFILES
from src.recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")

    for profile_name, user_prefs in PROFILES.items():
        recommendations = recommend_songs(user_prefs, songs, k=3)

        print("\n" + "=" * 50)
        print(f"  PROFILE: {profile_name}")
        print("=" * 50)

        for rank, (song, score, explanation) in enumerate(recommendations, start=1):
            print(f"\n#{rank}  {song['title']} by {song['artist']}")
            print(f"    Genre: {song['genre']}  |  Mood: {song['mood']}")
            print(f"    Score: {score:.2f} / 1.00")
            print(f"    Why:")
            for reason in explanation.split("\n  "):
                print(f"      - {reason}")
            print("    " + "-" * 44)

        print()

    recommendations = recommend_songs(PROFILES["Chill Lofi Student"], songs, k=5)

    print("\n" + "=" * 50)
    print("  MUSIC RECOMMENDATIONS")
    print("=" * 50)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n#{rank}  {song['title']} by {song['artist']}")
        print(f"    Genre: {song['genre']}  |  Mood: {song['mood']}")
        print(f"    Score: {score:.2f} / 1.00")
        print(f"    Why:")
        for reason in explanation.split("\n  "):
            print(f"      - {reason}")
        print("    " + "-" * 44)

    print()


if __name__ == "__main__":
    main()
