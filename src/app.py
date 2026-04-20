"""VibeMatch 2.0 — Streamlit dashboard.

Hero experience: describe how you feel in plain English, an LLM translates it
into a structured taste profile, and the deterministic scoring engine in
src/recommender.py ranks 20 songs with per-feature importance charts.

Alternative profile sources (preset / custom sliders) live in the sidebar as
fallback paths — the main area is built around the natural-language input.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Ensure the repo root is on sys.path so `from src.*` imports resolve whether
# the app is launched via `streamlit run src/app.py` or `python -m streamlit run src/app.py`.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import plotly.graph_objects as go
import streamlit as st

from src.profiles import (
    KNOWN_DECADES,
    KNOWN_GENRES,
    KNOWN_MOODS,
    KNOWN_MOOD_TAGS,
    PROFILES,
)
from src.recommender import load_songs, recommend_songs_detailed

try:
    from src.profile_parser import ProfileParseError, parse_profile_from_text
    _PARSER_AVAILABLE = True
    _PARSER_IMPORT_ERROR: Optional[str] = None
except ImportError as e:  # parser not written yet, or google-genai missing
    _PARSER_AVAILABLE = False
    _PARSER_IMPORT_ERROR = str(e)

    class ProfileParseError(Exception):  # type: ignore[no-redef]
        pass

    def parse_profile_from_text(description: str):  # type: ignore[no-redef]
        raise ProfileParseError("Natural-language parser is not available.")


SONGS_CSV = REPO_ROOT / "data" / "songs.csv"

GENRE_COLOR = "#a855f7"
MOOD_COLOR = "#ec4899"
TAG_COLOR = "#6366f1"
CARD_BG = "#1a1a2e"

EXAMPLE_PROMPTS = [
    "Late-night studying, chill but focused",
    "Sunday morning coffee and journaling",
    "Gym pump, high-energy and euphoric",
    "Winding down after a long day, warm and unhurried",
]


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

@st.cache_data
def _load_songs_cached(csv_path: str) -> List[Dict]:
    return load_songs(csv_path)


# --------------------------------------------------------------------------
# Small UI helpers
# --------------------------------------------------------------------------

def _badge(text: str, color: str) -> str:
    return (
        f"<span style='background:{color};color:white;padding:3px 10px;"
        f"border-radius:12px;font-size:0.82rem;margin-right:6px;"
        f"display:inline-block;margin-bottom:4px;'>{text}</span>"
    )


def _score_color(score: float) -> str:
    if score < 0.45:
        return "#ef4444"
    if score < 0.70:
        return "#eab308"
    return "#22c55e"


def _gradient_bar(score: float) -> str:
    pct = max(0, min(100, int(score * 100)))
    color = _score_color(score)
    return (
        f"<div style='background:#0f0f1a;border-radius:6px;height:14px;"
        f"width:100%;overflow:hidden;margin:4px 0 10px 0;'>"
        f"<div style='background:{color};height:100%;width:{pct}%;"
        f"transition:width .3s;'></div></div>"
        f"<div style='font-size:0.82rem;color:#94a3b8;margin-top:-4px;'>"
        f"Match score: <b style='color:{color}'>{score:.3f}</b></div>"
    )


def _feature_importance_chart(features: Dict[str, Dict]) -> go.Figure:
    items = sorted(features.items(), key=lambda kv: kv[1]["weighted"])
    names = [k for k, _ in items]
    weighted = [v["weighted"] for _, v in items]
    hover = [
        f"{name}: {v['weighted']:.3f} pts (weight {v['weight']} × raw {v['raw']:.2f} / 15.5)"
        for name, v in items
    ]
    colors = ["#a855f7" if w > 0.04 else "#475569" for w in weighted]
    fig = go.Figure(
        go.Bar(
            x=weighted,
            y=names,
            orientation="h",
            marker_color=colors,
            hovertext=hover,
            hoverinfo="text",
        )
    )
    fig.update_layout(
        height=320,
        margin=dict(l=10, r=10, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e2e8f0", size=12),
        xaxis=dict(title="Weighted contribution", gridcolor="#1a1a2e"),
        yaxis=dict(gridcolor="#1a1a2e"),
    )
    return fig


# --------------------------------------------------------------------------
# Sidebar (secondary controls + alternative profile sources)
# --------------------------------------------------------------------------

def _build_custom_profile() -> Dict:
    genre = st.selectbox("Favorite genre", KNOWN_GENRES, key="c_genre")
    mood = st.selectbox("Favorite mood", KNOWN_MOODS, key="c_mood")
    energy = st.slider("Energy", 0.0, 1.0, 0.5, 0.05, key="c_energy")
    valence = st.slider("Valence (positivity)", 0.0, 1.0, 0.5, 0.05, key="c_valence")
    danceability = st.slider("Danceability", 0.0, 1.0, 0.5, 0.05, key="c_dance")
    acousticness = st.slider("Acousticness", 0.0, 1.0, 0.5, 0.05, key="c_acoust")
    tempo = st.slider("Tempo (BPM)", 40, 220, 110, 2, key="c_tempo")
    popularity = st.slider("Popularity", 0, 100, 60, 5, key="c_pop")
    decade = st.selectbox("Decade", KNOWN_DECADES, index=len(KNOWN_DECADES) - 1, key="c_decade")
    tags = st.multiselect("Preferred mood tags", KNOWN_MOOD_TAGS, key="c_tags")
    likes_acoustic = st.checkbox("Likes acoustic", value=False, key="c_acousticflag")
    return {
        "favorite_genre": genre,
        "favorite_mood": mood,
        "target_energy": energy,
        "target_valence": valence,
        "target_danceability": danceability,
        "target_acousticness": acousticness,
        "target_tempo_bpm": tempo,
        "target_popularity": popularity,
        "target_decade": decade,
        "preferred_mood_tags": tags,
        "likes_acoustic": likes_acoustic,
    }


def _render_sidebar() -> tuple[str, Optional[Dict], int, float]:
    """Sidebar = secondary controls. AI description (main area) is the primary path."""
    with st.sidebar:
        st.markdown("### VibeMatch 2.0")
        st.caption("A transparent music recommender.")

        st.markdown("#### Results")
        k = st.slider("How many recommendations?", 1, 10, 5)
        alpha = st.slider(
            "Match strictness (α)",
            2.0, 30.0, 10.0, 1.0,
            help="Lower = songs just need to be in the ballpark; "
                 "Higher = near-exact matches only.",
        )

        st.divider()
        st.markdown("#### Alternative profile source")
        st.caption(
            "By default the description you type above drives the results. "
            "Override it with a preset or custom profile here."
        )
        source = st.radio(
            "Profile source",
            ("AI description", "Preset", "Custom"),
            key="source_radio",
            label_visibility="collapsed",
        )

        alt_profile: Optional[Dict] = None
        if source == "Preset":
            name = st.selectbox("Preset profile", list(PROFILES.keys()))
            alt_profile = dict(PROFILES[name])
        elif source == "Custom":
            alt_profile = _build_custom_profile()

    return source, alt_profile, k, alpha


# --------------------------------------------------------------------------
# Hero — the main NL input, front and center
# --------------------------------------------------------------------------

def _render_hero() -> Optional[Dict]:
    """Main-area hero: title, big NL text area, example prompts, parse button."""
    st.markdown(
        "<h1 style='margin-bottom:0;font-size:2.2rem;'>🎵 VibeMatch 2.0</h1>"
        "<p style='color:#cbd5e1;font-size:1.15rem;margin:6px 0 18px 0;'>"
        "Describe how you feel — we'll find music that matches.</p>",
        unsafe_allow_html=True,
    )

    # A prefill from a chip click needs to be applied BEFORE the text_area renders,
    # otherwise Streamlit's widget-state rules override it.
    if "_pending_prompt" in st.session_state:
        st.session_state["nl_text"] = st.session_state.pop("_pending_prompt")

    st.text_area(
        label="Describe your vibe",
        placeholder=(
            "I want something warm and unhurried for a rainy afternoon, "
            "not too sleepy but definitely not a gym workout..."
        ),
        height=130,
        key="nl_text",
        label_visibility="collapsed",
    )

    col_btn, col_note = st.columns([1, 2])
    with col_btn:
        clicked = st.button(
            "✨ Find my vibe",
            type="primary",
            use_container_width=True,
            disabled=not _PARSER_AVAILABLE,
        )
    with col_note:
        st.caption(
            "Google Gemini translates your description into a structured "
            "profile. The deterministic scoring engine picks the songs — "
            "the LLM never chooses them directly."
        )

    st.markdown(
        "<p style='color:#64748b;font-size:0.82rem;margin:14px 0 4px 0;'>"
        "Or try one of these:</p>",
        unsafe_allow_html=True,
    )
    chip_cols = st.columns(len(EXAMPLE_PROMPTS))
    for i, prompt in enumerate(EXAMPLE_PROMPTS):
        with chip_cols[i]:
            if st.button(prompt, key=f"chip_{i}", use_container_width=True):
                st.session_state["_pending_prompt"] = prompt
                st.rerun()

    if not _PARSER_AVAILABLE:
        st.info(
            "Natural-language input is disabled — the parser module could not be "
            f"imported ({_PARSER_IMPORT_ERROR}). Use **Preset** or **Custom** in "
            "the sidebar instead."
        )
        return st.session_state.get("nl_profile")

    if clicked:
        description = st.session_state.get("nl_text", "").strip()
        if not description:
            st.error("Please describe your vibe first, or click one of the examples.")
        else:
            try:
                with st.spinner("Asking Gemini to interpret your description..."):
                    profile, rationale = parse_profile_from_text(description)
                st.session_state["nl_profile"] = profile
                st.session_state["nl_rationale"] = rationale
            except ProfileParseError as err:
                st.error(f"Could not interpret that: {err}")
            except Exception as err:  # defensive — parser contract may evolve
                st.error(f"Unexpected error from parser: {err}")

    return st.session_state.get("nl_profile")


# --------------------------------------------------------------------------
# Main-area renderers
# --------------------------------------------------------------------------

def _render_parsed_profile_panel(profile: Dict, rationale: str) -> None:
    with st.expander("🧠 How Gemini read you", expanded=True):
        st.markdown(
            f"<blockquote style='border-left:3px solid {GENRE_COLOR};"
            f"padding:6px 14px;color:#cbd5e1;margin:4px 0 14px 0;'>"
            f"{rationale}</blockquote>",
            unsafe_allow_html=True,
        )
        badges = (
            _badge(f"Genre: {profile['favorite_genre']}", GENRE_COLOR)
            + _badge(f"Mood: {profile['favorite_mood']}", MOOD_COLOR)
            + _badge(f"Decade: {profile['target_decade']}", TAG_COLOR)
        )
        st.markdown(badges, unsafe_allow_html=True)

        numeric_rows = [
            ("Energy", profile["target_energy"]),
            ("Valence", profile["target_valence"]),
            ("Danceability", profile["target_danceability"]),
            ("Acousticness", profile["target_acousticness"]),
            ("Tempo (BPM)", profile["target_tempo_bpm"]),
            ("Popularity", profile["target_popularity"]),
        ]
        cols = st.columns(3)
        for i, (label, val) in enumerate(numeric_rows):
            with cols[i % 3]:
                st.metric(label, f"{val}")

        tags = profile.get("preferred_mood_tags") or []
        if tags:
            st.markdown(
                "**Mood tags:** " + "".join(_badge(t, TAG_COLOR) for t in tags),
                unsafe_allow_html=True,
            )


def _render_result_card(rank: int, result: Dict) -> None:
    song = result["song"]
    score = result["score"]
    header = f"#{rank}  {song['title']} — {song['artist']}"
    st.markdown(
        f"<div style='background:{CARD_BG};padding:16px 20px;border-radius:12px;"
        f"margin-bottom:14px;'>"
        f"<div style='font-size:1.1rem;font-weight:600;margin-bottom:6px;'>{header}</div>"
        f"{_badge(song['genre'], GENRE_COLOR)}{_badge(song['mood'], MOOD_COLOR)}"
        f"{_gradient_bar(score)}"
        f"</div>",
        unsafe_allow_html=True,
    )
    with st.expander("▸ Feature Importance"):
        st.plotly_chart(
            _feature_importance_chart(result["features"]),
            use_container_width=True,
        )


def _render_results(profile: Dict, k: int, alpha: float) -> None:
    songs = _load_songs_cached(str(SONGS_CSV))
    results = recommend_songs_detailed(profile, songs, k=k, alpha=alpha)

    if not results:
        st.warning("No songs in the catalog to rank.")
        return

    if results[0]["score"] < 0.45:
        st.warning(
            "⚠️ No strong matches — the catalog may not serve this taste "
            "profile well. Best available options shown below."
        )

    st.markdown("### Top matches")
    for i, result in enumerate(results, start=1):
        _render_result_card(i, result)


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="VibeMatch 2.0",
        page_icon="🎵",
        layout="wide",
    )

    source, alt_profile, k, alpha = _render_sidebar()
    nl_profile = _render_hero()

    active_profile = nl_profile if source == "AI description" else alt_profile

    if source == "AI description" and st.session_state.get("nl_profile"):
        _render_parsed_profile_panel(
            st.session_state["nl_profile"],
            st.session_state.get("nl_rationale", ""),
        )

    if active_profile is None:
        if source == "AI description":
            st.info(
                "Click **Find my vibe** (or an example chip) to generate a profile "
                "and see matching songs. Or use the sidebar to pick a preset / "
                "build a custom profile."
            )
        return

    _render_results(active_profile, k, alpha)


if __name__ == "__main__":
    main()
