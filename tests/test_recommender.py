import math

import pytest

from src.recommender import (
    Recommender,
    Song,
    UserProfile,
    WEIGHT_SUM,
    score_song,
    score_song_detailed,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _pop_song() -> Song:
    return Song(
        id=1,
        title="Test Pop Track",
        artist="Test Artist",
        genre="pop",
        mood="happy",
        energy=0.8,
        tempo_bpm=120,
        valence=0.9,
        danceability=0.8,
        acousticness=0.2,
        popularity=75,
        release_decade=2020,
        mood_tags="upbeat,bright,feel-good",
    )


def _lofi_song() -> Song:
    return Song(
        id=2,
        title="Chill Lofi Loop",
        artist="Test Artist",
        genre="lofi",
        mood="chill",
        energy=0.4,
        tempo_bpm=80,
        valence=0.6,
        danceability=0.5,
        acousticness=0.9,
        popularity=60,
        release_decade=2020,
        mood_tags="mellow,focused,dreamy",
    )


def _pop_profile() -> UserProfile:
    return UserProfile(
        favorite_genre="pop",
        favorite_mood="happy",
        target_energy=0.8,
        target_valence=0.9,
        target_danceability=0.8,
        target_acousticness=0.2,
        target_tempo_bpm=120,
        target_popularity=75,
        target_decade=2020,
        preferred_mood_tags=["upbeat", "bright", "feel-good"],
        likes_acoustic=False,
    )


def make_small_recommender() -> Recommender:
    return Recommender([_pop_song(), _lofi_song()])


# ---------------------------------------------------------------------------
# OOP Recommender: the pre-existing tests (now meaningful after wiring)
# ---------------------------------------------------------------------------

def test_recommend_returns_songs_sorted_by_score():
    rec = make_small_recommender()
    results = rec.recommend(_pop_profile(), k=2)

    assert len(results) == 2
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    rec = make_small_recommender()
    explanation = rec.explain_recommendation(_pop_profile(), rec.songs[0])

    assert isinstance(explanation, str)
    assert explanation.strip() != ""
    assert "Match score" in explanation


def test_recommend_actually_ranks_lofi_profile_correctly():
    """Regression guard: before wiring, recommend() returned songs[:k] blindly,
    so changing the list order would flip the result. Verify a lofi profile
    now puts the lofi song first even though it's at index 1 in the list."""
    lofi_profile = UserProfile(
        favorite_genre="lofi",
        favorite_mood="chill",
        target_energy=0.4,
        target_valence=0.6,
        target_danceability=0.5,
        target_acousticness=0.9,
        target_tempo_bpm=80,
        target_popularity=60,
        target_decade=2020,
        preferred_mood_tags=["mellow", "focused", "dreamy"],
        likes_acoustic=True,
    )
    rec = make_small_recommender()  # pop is at index 0, lofi at index 1
    results = rec.recommend(lofi_profile, k=2)

    assert results[0].genre == "lofi"
    assert results[1].genre == "pop"


# ---------------------------------------------------------------------------
# score_song_detailed: the feature-importance-ready API
# ---------------------------------------------------------------------------

EXPECTED_FEATURES = {
    "Genre", "Mood", "Energy", "Acousticness", "Valence",
    "Danceability", "Tempo", "Popularity", "Decade", "Mood Tags",
}


def test_score_song_detailed_returns_all_features():
    result = score_song_detailed(vars(_pop_profile()), vars(_pop_song()))

    assert set(result["features"].keys()) == EXPECTED_FEATURES
    for name, entry in result["features"].items():
        assert {"raw", "weight", "weighted"} <= entry.keys()
        assert 0.0 <= entry["raw"] <= 1.0
        assert entry["weight"] > 0
        assert math.isclose(entry["weighted"], entry["weight"] * entry["raw"] / WEIGHT_SUM)


def test_feature_weights_sum_to_total():
    """The weighted contributions across all features must equal the total score."""
    result = score_song_detailed(vars(_pop_profile()), vars(_lofi_song()))
    summed = sum(f["weighted"] for f in result["features"].values())

    assert math.isclose(summed, result["total"], rel_tol=1e-9, abs_tol=1e-9)


def test_score_song_backward_compatible():
    """The tuple-returning score_song() still works — main.py depends on this shape."""
    total, reasons = score_song(vars(_pop_profile()), vars(_pop_song()))

    assert 0.0 <= total <= 1.0
    assert isinstance(reasons, list)
    assert all(isinstance(r, str) for r in reasons)
    assert len(reasons) > 0


def test_score_song_and_score_song_detailed_agree():
    """Backward-compat wrapper must produce the same total as the detailed API."""
    total_simple, _ = score_song(vars(_pop_profile()), vars(_pop_song()))
    detailed = score_song_detailed(vars(_pop_profile()), vars(_pop_song()))

    assert math.isclose(total_simple, detailed["total"], rel_tol=1e-9, abs_tol=1e-9)


def test_perfect_match_scores_near_one():
    """A profile that exactly matches a song should score very close to 1.0."""
    song = _pop_song()
    profile = UserProfile(
        favorite_genre=song.genre,
        favorite_mood=song.mood,
        target_energy=song.energy,
        target_valence=song.valence,
        target_danceability=song.danceability,
        target_acousticness=song.acousticness,
        target_tempo_bpm=song.tempo_bpm,
        target_popularity=song.popularity,
        target_decade=song.release_decade,
        preferred_mood_tags=[t.strip() for t in song.mood_tags.split(",")],
        likes_acoustic=False,
    )
    result = score_song_detailed(vars(profile), vars(song))

    assert result["total"] > 0.99
