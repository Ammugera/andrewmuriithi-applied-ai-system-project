"""Unit tests for src.profile_parser — all Gemini calls are mocked."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

# Make the repo root importable so `from src...` works when pytest is run
# from anywhere in the project.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import profile_parser  # noqa: E402
from src.profile_parser import ProfileParseError, parse_profile_from_text  # noqa: E402


def _valid_payload(**overrides):
    payload = {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.35,
        "target_valence": 0.60,
        "target_danceability": 0.55,
        "target_acousticness": 0.80,
        "target_tempo_bpm": 82,
        "target_popularity": 55,
        "target_decade": 2020,
        "preferred_mood_tags": ["mellow", "focused"],
        "likes_acoustic": True,
        "rationale": "Late-night study suggests low energy, high acousticness, and a focused vibe. Lofi fits naturally.",
    }
    payload.update(overrides)
    return payload


def _fake_response(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(text=json.dumps(payload))


def test_raises_without_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    # Also stub load_dotenv so a local .env can't sneak the key back in.
    monkeypatch.setattr(profile_parser, "load_dotenv", lambda *a, **kw: None)
    profile_parser._reset_client()
    with pytest.raises(ProfileParseError, match="GEMINI_API_KEY"):
        parse_profile_from_text("something chill")


def test_valid_response_parsed(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    profile_parser._reset_client()

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _fake_response(_valid_payload())

    with patch("google.genai.Client", return_value=mock_client):
        profile, rationale = parse_profile_from_text("chill late-night study music")

    assert profile["favorite_genre"] == "lofi"
    assert profile["favorite_mood"] == "chill"
    assert isinstance(profile["target_energy"], float)
    assert profile["target_energy"] == 0.35
    assert profile["target_decade"] == 2020
    assert isinstance(profile["target_decade"], int)
    assert profile["preferred_mood_tags"] == ["mellow", "focused"]
    assert profile["likes_acoustic"] is True
    assert "rationale" not in profile
    assert rationale.startswith("Late-night study")


def test_out_of_range_values_clamped(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    profile_parser._reset_client()

    payload = _valid_payload(target_energy=1.5, target_tempo_bpm=500)
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _fake_response(payload)

    with patch("google.genai.Client", return_value=mock_client):
        with pytest.warns(UserWarning):
            profile, _ = parse_profile_from_text("pure chaos")

    assert profile["target_energy"] == 1.0
    assert profile["target_tempo_bpm"] == 220.0


def test_api_failure_raises_parse_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")
    profile_parser._reset_client()

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = RuntimeError("network boom")

    with patch("google.genai.Client", return_value=mock_client):
        with pytest.raises(ProfileParseError, match="Gemini API call failed"):
            parse_profile_from_text("anything")
