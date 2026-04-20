"""
Shared profiles + catalog vocabulary.

Imported by:
  - src/main.py           (CLI entry point)
  - src/app.py            (Streamlit dashboard)
  - src/profile_parser.py (LLM natural-language parser)

The `KNOWN_*` lists are derived from data/songs.csv at import time so they stay
in sync with the catalog. The LLM parser uses them as enum constraints so the
model cannot invent a genre or mood that doesn't exist in the catalog.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SONGS_CSV = _REPO_ROOT / "data" / "songs.csv"


def _load_vocabulary() -> Dict[str, List[str]]:
    genres, moods, tags = set(), set(), set()
    decades = set()
    with open(_SONGS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            genres.add(row["genre"].strip())
            moods.add(row["mood"].strip())
            decades.add(int(row["release_decade"]))
            for t in row["mood_tags"].split(","):
                t = t.strip()
                if t:
                    tags.add(t)
    return {
        "genres":  sorted(genres),
        "moods":   sorted(moods),
        "tags":    sorted(tags),
        "decades": sorted(decades),
    }


_VOCAB = _load_vocabulary()
KNOWN_GENRES: List[str] = _VOCAB["genres"]
KNOWN_MOODS: List[str] = _VOCAB["moods"]
KNOWN_MOOD_TAGS: List[str] = _VOCAB["tags"]
KNOWN_DECADES: List[int] = _VOCAB["decades"]


PROFILES: Dict[str, Dict] = {
    "Chill Lofi Student": {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.40,
        "target_valence": 0.60,
        "target_danceability": 0.60,
        "target_acousticness": 0.75,
        "target_tempo_bpm": 80,
        "likes_acoustic": True,
        "target_popularity": 60,
        "target_decade": 2020,
        "preferred_mood_tags": ["mellow", "focused", "dreamy"],
    },
    "Melancholic Explorer": {
        "favorite_genre": "folk",
        "favorite_mood": "melancholic",
        "target_energy": 0.25,
        "target_valence": 0.35,
        "target_danceability": 0.35,
        "target_acousticness": 0.90,
        "target_tempo_bpm": 75,
        "likes_acoustic": True,
        "target_popularity": 40,
        "target_decade": 2010,
        "preferred_mood_tags": ["wistful", "lonely", "tender"],
    },
    "Festival Headliner": {
        "favorite_genre": "electronic",
        "favorite_mood": "euphoric",
        "target_energy": 0.90,
        "target_valence": 0.85,
        "target_danceability": 0.92,
        "target_acousticness": 0.05,
        "target_tempo_bpm": 138,
        "likes_acoustic": False,
        "target_popularity": 85,
        "target_decade": 2020,
        "preferred_mood_tags": ["electric", "euphoric", "high-energy"],
    },
    "Late Night Jazz": {
        "favorite_genre": "jazz",
        "favorite_mood": "relaxed",
        "target_energy": 0.37,
        "target_valence": 0.70,
        "target_danceability": 0.55,
        "target_acousticness": 0.88,
        "target_tempo_bpm": 90,
        "likes_acoustic": True,
        "target_popularity": 50,
        "target_decade": 2000,
        "preferred_mood_tags": ["warm", "smooth", "nostalgic"],
    },

    # --- Adversarial / Edge Case Profiles ---

    "Impossible Ideal": {
        "favorite_genre": "blues",
        "favorite_mood": "euphoric",
        "target_energy": 0.95,
        "target_valence": 0.95,
        "target_danceability": 0.95,
        "target_acousticness": 0.02,
        "target_tempo_bpm": 170,
        "likes_acoustic": False,
        "target_popularity": 90,
        "target_decade": 2020,
        "preferred_mood_tags": ["euphoric", "powerful", "electric"],
    },
    "Genre Orphan": {
        "favorite_genre": "reggae",
        "favorite_mood": "laid-back",
        "target_energy": 0.44,
        "target_valence": 0.80,
        "target_danceability": 0.68,
        "target_acousticness": 0.58,
        "target_tempo_bpm": 76,
        "likes_acoustic": True,
        "target_popularity": 55,
        "target_decade": 2010,
        "preferred_mood_tags": ["breezy", "sunny", "carefree"],
    },
    "Flat Numeric Strong Categorical": {
        "favorite_genre": "lofi",
        "favorite_mood": "focused",
        "target_energy": 0.50,
        "target_valence": 0.50,
        "target_danceability": 0.50,
        "target_acousticness": 0.50,
        "target_tempo_bpm": 100,
        "likes_acoustic": False,
        "target_popularity": 50,
        "target_decade": 2020,
        "preferred_mood_tags": ["calm", "focused"],
    },
}
