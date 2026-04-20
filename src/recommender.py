import csv
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Scoring weights — single source of truth. Total score is in [0, 1].
# ---------------------------------------------------------------------------
WEIGHTS: Dict[str, float] = {
    "Genre":        1.5,
    "Mood":         2.0,
    "Energy":       4.0,
    "Acousticness": 2.0,
    "Valence":      1.0,
    "Danceability": 1.0,
    "Tempo":        1.0,
    "Popularity":   1.0,
    "Decade":       0.5,
    "Mood Tags":    1.5,
}
WEIGHT_SUM: float = sum(WEIGHTS.values())  # 15.5


@dataclass
class Song:
    """A catalog song. Fields mirror the columns in data/songs.csv."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    popularity: int
    release_decade: int
    mood_tags: str  # comma-separated, e.g. "mellow,focused,dreamy"


@dataclass
class UserProfile:
    """A user's taste profile. All fields required by the scoring engine."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    target_valence: float
    target_danceability: float
    target_acousticness: float
    target_tempo_bpm: float
    target_popularity: float
    target_decade: int
    preferred_mood_tags: List[str] = field(default_factory=list)
    likes_acoustic: bool = False


# ---------------------------------------------------------------------------
# Functional scoring API (used by main.py, app.py, and the OOP Recommender).
# ---------------------------------------------------------------------------

def score_song_detailed(user_prefs: Dict, song: Dict, alpha: float = 10.0) -> Dict:
    """
    Score a single song against a user profile and return a structured breakdown.

    Returns:
        {
          "total": float,                    # final weighted score in [0, 1]
          "features": {name: {"raw", "weight", "weighted"}, ...},
          "reasons": [str, ...]              # human-readable explanations
        }

    The `weighted` values across all features sum to `total` (within float tolerance).
    This is the shape consumed by the feature-importance bar chart.
    """
    reasons: List[str] = []

    genre_score = 1.0 if song["genre"] == user_prefs["favorite_genre"] else 0.0
    mood_score = 1.0 if song["mood"] == user_prefs["favorite_mood"] else 0.0
    if genre_score:
        reasons.append(f"genre match: {song['genre']} (+1.5 weight)")
    if mood_score:
        reasons.append(f"mood match: {song['mood']} (+2.0 weight)")

    tempo_norm = song["tempo_bpm"] / 200.0
    target_tempo_norm = user_prefs["target_tempo_bpm"] / 200.0
    popularity_norm = song["popularity"] / 100.0
    target_popularity_norm = user_prefs["target_popularity"] / 100.0
    decade_norm = (song["release_decade"] - 1980) / 50.0
    target_decade_norm = (user_prefs["target_decade"] - 1980) / 50.0

    def gaussian(x: float, p: float) -> float:
        return math.exp(-alpha * (x - p) ** 2)

    s_energy       = gaussian(song["energy"],       user_prefs["target_energy"])
    s_valence      = gaussian(song["valence"],      user_prefs["target_valence"])
    s_danceability = gaussian(song["danceability"], user_prefs["target_danceability"])
    s_acousticness = gaussian(song["acousticness"], user_prefs["target_acousticness"])
    s_tempo        = gaussian(tempo_norm,           target_tempo_norm)
    s_popularity   = gaussian(popularity_norm,      target_popularity_norm)
    s_decade       = gaussian(decade_norm,          target_decade_norm)

    reasons.append(f"energy score: {s_energy:.2f} (target {user_prefs['target_energy']}, song {song['energy']})")
    reasons.append(f"valence score: {s_valence:.2f} (target {user_prefs['target_valence']}, song {song['valence']})")
    reasons.append(f"danceability score: {s_danceability:.2f} (target {user_prefs['target_danceability']}, song {song['danceability']})")
    reasons.append(f"acousticness score: {s_acousticness:.2f} (target {user_prefs['target_acousticness']}, song {song['acousticness']})")
    reasons.append(f"tempo score: {s_tempo:.2f} (target {user_prefs['target_tempo_bpm']} bpm, song {song['tempo_bpm']} bpm)")
    reasons.append(f"popularity score: {s_popularity:.2f} (target {user_prefs['target_popularity']}, song {song['popularity']})")
    reasons.append(f"decade score: {s_decade:.2f} (target {user_prefs['target_decade']}, song {song['release_decade']})")

    song_tags = {t.strip() for t in song["mood_tags"].split(",")} if song.get("mood_tags") else set()
    user_tags = set(user_prefs.get("preferred_mood_tags") or [])
    tag_matches = len(song_tags & user_tags)
    s_mood_tags = tag_matches / len(song_tags) if song_tags else 0.0
    reasons.append(
        f"mood tags score: {s_mood_tags:.2f} "
        f"({tag_matches}/{len(song_tags)} tags matched: {song_tags & user_tags or 'none'})"
    )

    raw_scores = {
        "Genre":        genre_score,
        "Mood":         mood_score,
        "Energy":       s_energy,
        "Acousticness": s_acousticness,
        "Valence":      s_valence,
        "Danceability": s_danceability,
        "Tempo":        s_tempo,
        "Popularity":   s_popularity,
        "Decade":       s_decade,
        "Mood Tags":    s_mood_tags,
    }
    features = {
        name: {
            "raw": raw,
            "weight": WEIGHTS[name],
            "weighted": WEIGHTS[name] * raw / WEIGHT_SUM,
        }
        for name, raw in raw_scores.items()
    }
    total = sum(f["weighted"] for f in features.values())

    return {"total": total, "features": features, "reasons": reasons}


def score_song(user_prefs: Dict, song: Dict, alpha: float = 10.0) -> Tuple[float, List[str]]:
    """Backward-compatible wrapper — returns (total, reasons)."""
    result = score_song_detailed(user_prefs, song, alpha=alpha)
    return result["total"], result["reasons"]


def load_songs(csv_path: str) -> List[Dict]:
    """Load the catalog from CSV, coercing numeric fields to the right types."""
    float_fields = {"energy", "tempo_bpm", "valence", "danceability", "acousticness"}
    int_fields = {"id", "popularity", "release_decade"}
    songs: List[Dict] = []
    with open(csv_path, newline="") as f:
        for row in csv.DictReader(f):
            for field_name in float_fields:
                row[field_name] = float(row[field_name])
            for field_name in int_fields:
                row[field_name] = int(row[field_name])
            songs.append(row)
    return songs


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    alpha: float = 10.0,
) -> List[Tuple[Dict, float, str]]:
    """Rank all songs and return top-k as (song, score, joined_reasons) tuples."""
    scored = [(song, *score_song(user_prefs, song, alpha=alpha)) for song in songs]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [(song, score, "\n  ".join(reasons)) for song, score, reasons in scored[:k]]


def recommend_songs_detailed(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    alpha: float = 10.0,
) -> List[Dict]:
    """
    Same ranking as recommend_songs, but returns the full structured breakdown
    per song — the shape the Streamlit dashboard consumes for feature-importance charts.

    Returns a list of {"song": dict, "score": float, "features": {...}, "reasons": [...]}.
    """
    scored = [
        {"song": song, **score_song_detailed(user_prefs, song, alpha=alpha)}
        for song in songs
    ]
    scored.sort(key=lambda x: x["total"], reverse=True)
    return [
        {"song": s["song"], "score": s["total"], "features": s["features"], "reasons": s["reasons"]}
        for s in scored[:k]
    ]


# ---------------------------------------------------------------------------
# OOP facade — delegates to the functional API. Used by tests/test_recommender.py.
# ---------------------------------------------------------------------------

class Recommender:
    """Object-oriented wrapper that delegates to the functional scoring API."""

    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5, alpha: float = 10.0) -> List[Song]:
        user_dict = vars(user)
        scored = sorted(
            self.songs,
            key=lambda s: score_song(user_dict, vars(s), alpha=alpha)[0],
            reverse=True,
        )
        return scored[:k]

    def explain_recommendation(self, user: UserProfile, song: Song, alpha: float = 10.0) -> str:
        total, reasons = score_song(vars(user), vars(song), alpha=alpha)
        header = f"Match score: {total:.2f} / 1.00"
        return header + "\n" + "\n".join(f"  - {r}" for r in reasons)
