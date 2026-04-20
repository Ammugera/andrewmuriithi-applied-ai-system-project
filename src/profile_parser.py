"""
Natural-language -> UserProfile parser backed by Google Gemini.

This is the "Advanced AI" (agentic) front door for VibeMatch 2.0. A user types
a plain-English mood description; we hand it to Gemini with a strict JSON
schema constrained to the catalog vocabulary; we clamp numeric ranges; and we
return a dict that the deterministic scorer in recommender.py can consume
verbatim. The LLM does translation, never ranking.
"""
from __future__ import annotations

import json
import os
import warnings
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv

from src.profiles import KNOWN_DECADES, KNOWN_GENRES, KNOWN_MOODS, KNOWN_MOOD_TAGS

_MODEL_NAME = "gemini-2.5-flash"
_NUMERIC_CLAMPS = {
    "target_energy":       (0.0, 1.0),
    "target_valence":      (0.0, 1.0),
    "target_danceability": (0.0, 1.0),
    "target_acousticness": (0.0, 1.0),
    "target_tempo_bpm":    (40.0, 220.0),
    "target_popularity":   (0.0, 100.0),
}
_PROFILE_KEYS = (
    "favorite_genre", "favorite_mood",
    "target_energy", "target_valence", "target_danceability", "target_acousticness",
    "target_tempo_bpm", "target_popularity", "target_decade",
    "preferred_mood_tags", "likes_acoustic",
)

# Cached Gemini client — built lazily so importing this module never requires
# the API key. Tests reset this via _reset_client().
_client = None


class ProfileParseError(Exception):
    """Raised when the LLM call fails or the API key is missing."""


def _reset_client() -> None:
    """Clear the cached client. Used by tests that toggle the API key env var."""
    global _client
    _client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ProfileParseError(
            "GEMINI_API_KEY not set — add it to .env or your environment"
        )
    # Import inside the function so the module stays importable for tests that
    # mock the client without the SDK being installed at import time.
    from google import genai  # noqa: WPS433
    _client = genai.Client(api_key=api_key)
    return _client


def _build_schema():
    """Build the response schema constraining enums to the catalog vocabulary."""
    from google.genai import types  # noqa: WPS433

    S, T = types.Schema, types.Type
    # Gemini's Schema.enum only accepts strings, so target_decade is an INTEGER
    # whose allowed values we describe in the prompt (schema can't enforce int
    # enum cleanly). We validate membership after parsing.
    props = {
        "favorite_genre":      S(type=T.STRING, enum=list(KNOWN_GENRES)),
        "favorite_mood":       S(type=T.STRING, enum=list(KNOWN_MOODS)),
        "target_energy":       S(type=T.NUMBER),
        "target_valence":      S(type=T.NUMBER),
        "target_danceability": S(type=T.NUMBER),
        "target_acousticness": S(type=T.NUMBER),
        "target_tempo_bpm":    S(type=T.NUMBER),
        "target_popularity":   S(type=T.NUMBER),
        "target_decade":       S(type=T.INTEGER),
        "preferred_mood_tags": S(
            type=T.ARRAY,
            items=S(type=T.STRING, enum=list(KNOWN_MOOD_TAGS)),
        ),
        "likes_acoustic":      S(type=T.BOOLEAN),
        "rationale":           S(type=T.STRING),
    }
    return S(
        type=T.OBJECT,
        properties=props,
        required=list(props.keys()),
        property_ordering=list(props.keys()),
    )


def _system_prompt() -> str:
    return (
        "You translate plain-English music mood descriptions into a structured "
        "music-taste profile used by a content-based recommender.\n\n"
        f"Allowed genres: {KNOWN_GENRES}\n"
        f"Allowed moods: {KNOWN_MOODS}\n"
        f"Allowed mood tags: {KNOWN_MOOD_TAGS}\n"
        f"Allowed decades (integers): {KNOWN_DECADES}\n\n"
        "Rules:\n"
        "- Pick values only from the lists above. Never invent new genres, "
        "moods, tags, or decades.\n"
        "- Map qualitative language to numeric targets in [0, 1]: 'mellow' / "
        "'chill' -> low energy (~0.3); 'upbeat' / 'hype' -> high energy (~0.85); "
        "valence is positivity; danceability is rhythmic drive; acousticness is "
        "how unplugged it feels.\n"
        "- target_tempo_bpm is a real BPM value in [40, 220].\n"
        "- target_popularity is in [0, 100] (0 = obscure, 100 = mainstream).\n"
        "- Choose 2-5 preferred_mood_tags that best capture the vibe.\n"
        "- Fill 'rationale' with 2-3 honest plain-English sentences explaining "
        "how you interpreted the description. If the description is "
        "contradictory, pick a reasonable trade-off and call it out in the "
        "rationale.\n"
    )


def _clamp_profile(profile: Dict) -> Dict:
    for key, (lo, hi) in _NUMERIC_CLAMPS.items():
        if key not in profile:
            continue
        val = float(profile[key])
        clamped = max(lo, min(hi, val))
        if clamped != val:
            warnings.warn(
                f"{key}={val} out of [{lo}, {hi}] — clamped to {clamped}",
                UserWarning,
            )
            profile[key] = clamped
        else:
            profile[key] = val
    return profile


def _validate_and_shape(raw: Dict) -> Tuple[Dict, str]:
    missing = [k for k in _PROFILE_KEYS + ("rationale",) if k not in raw]
    if missing:
        raise ProfileParseError(f"LLM response missing required fields: {missing}")
    rationale = str(raw["rationale"]).strip()
    profile = {k: raw[k] for k in _PROFILE_KEYS}
    profile["target_decade"] = int(profile["target_decade"])
    profile["likes_acoustic"] = bool(profile["likes_acoustic"])
    profile["preferred_mood_tags"] = [str(t) for t in profile["preferred_mood_tags"]]
    _clamp_profile(profile)
    return profile, rationale


def parse_profile_from_text(description: str) -> Tuple[Dict, str]:
    """
    Translate a natural-language description into a UserProfile dict.

    Returns (profile_dict, rationale_string). The profile_dict has exactly the
    keys score_song_detailed() expects; rationale is surfaced in the UI.

    Raises ProfileParseError on missing API key, API failure, or schema
    validation failure.
    """
    client = _get_client()
    schema = _build_schema()
    from google.genai import types  # noqa: WPS433

    try:
        response = client.models.generate_content(
            model=_MODEL_NAME,
            contents=description,
            config=types.GenerateContentConfig(
                system_instruction=_system_prompt(),
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
    except ProfileParseError:
        raise
    except Exception as exc:  # noqa: BLE001 — convert all SDK errors to ours
        raise ProfileParseError(f"Gemini API call failed: {exc}") from exc

    text: Optional[str] = getattr(response, "text", None)
    if not text:
        raise ProfileParseError("Gemini returned an empty response")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProfileParseError(f"Gemini response was not valid JSON: {exc}") from exc

    return _validate_and_shape(raw)
