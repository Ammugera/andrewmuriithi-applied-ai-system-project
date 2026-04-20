# VibeMatch 2.0 — Parser Reliability Report

- **Generated:** 2026-04-19T23:23:36
- **Model:** `gemini-2.5-flash`
- **Cases:** 8 (0 errored)
- **Constraints checked:** 18
- **Passed:** 18 (100.0%)
- **Failed:** 0

> This report measures whether the LLM-backed natural-language profile parser
> produces sensible, predictable output on known inputs. The scoring engine
> is deterministic and covered by unit tests; this harness covers the non-
> deterministic piece — the LLM itself.

## Summary

| Case | Passed | Result |
|---|---|---|
| Chill study | 3/3 | ✅ All pass |
| Gym pump | 3/3 | ✅ All pass |
| Sunday morning | 2/2 | ✅ All pass |
| Sad folk | 2/2 | ✅ All pass |
| 80s retro | 1/1 | ✅ All pass |
| Wedding dance | 2/2 | ✅ All pass |
| Evening wind-down | 2/2 | ✅ All pass |
| Adversarial contradiction | 3/3 | ✅ All pass |

---
## Case: Chill study

> *"late-night studying, chill but focused"*

**What this tests:** Does the model map 'chill but focused' to low-energy, mellow-tag genres rather than high-energy dance music?

### Parsed profile

```json
{
  "favorite_genre": "lofi",
  "favorite_mood": "chill",
  "likes_acoustic": true,
  "preferred_mood_tags": [
    "calm",
    "focused",
    "mellow",
    "peaceful",
    "introspective"
  ],
  "target_acousticness": 0.6,
  "target_danceability": 0.25,
  "target_decade": 2020,
  "target_energy": 0.35,
  "target_popularity": 35.0,
  "target_tempo_bpm": 80.0,
  "target_valence": 0.55
}
```

### Rationale from the model

> The user explicitly requested 'chill but focused' for 'late-night studying', which strongly points to the lofi genre. I've set energy and danceability low to support concentration, while maintaining a neutral-positive valence. The acousticness is moderate to reflect the often organic, sampled sounds in lofi, and the popularity is kept low to minimize distractions.

### Constraint checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | `target_energy < 0.55` | < `0.55` | `0.35` | ✅ Pass |
| 2 | `favorite_genre in ['ambient', 'classical', 'folk', 'jazz', 'lofi', 'r&b']` | in `['ambient', 'classical', 'folk', 'jazz', 'lofi', 'r&b']` | `lofi` | ✅ Pass |
| 3 | `preferred_mood_tags any_in ['calm', 'dreamy', 'focused', 'mellow']` | any of `['calm', 'dreamy', 'focused', 'mellow']` | `['mellow', 'calm', 'focused']` | ✅ Pass |

---
## Case: Gym pump

> *"gym pump, high-energy and euphoric"*

**What this tests:** Does the model map 'gym pump' to high energy + high danceability, and avoid calm genres?

### Parsed profile

```json
{
  "favorite_genre": "electronic",
  "favorite_mood": "euphoric",
  "likes_acoustic": false,
  "preferred_mood_tags": [
    "high-energy",
    "euphoric",
    "pumped",
    "driven",
    "vibrant"
  ],
  "target_acousticness": 0.15,
  "target_danceability": 0.75,
  "target_decade": 2020,
  "target_energy": 0.88,
  "target_popularity": 75.0,
  "target_tempo_bpm": 130.0,
  "target_valence": 0.85
}
```

### Rationale from the model

> The description 'gym pump, high-energy and euphoric' clearly indicates a need for motivating, upbeat music. I selected electronic music as it often provides the driving beats and synthetic sounds suitable for intense workouts. The high energy, valence, and danceability targets reflect the desire for an uplifting and rhythmic experience.

### Constraint checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | `target_energy > 0.7` | > `0.7` | `0.88` | ✅ Pass |
| 2 | `target_danceability > 0.6` | > `0.6` | `0.75` | ✅ Pass |
| 3 | `favorite_genre not_in ['ambient', 'classical', 'folk', 'lofi']` | not in `['ambient', 'classical', 'folk', 'lofi']` | `electronic` | ✅ Pass |

---
## Case: Sunday morning

> *"Sunday morning coffee and journaling, slow and acoustic"*

**What this tests:** Does the model map 'slow and acoustic' to high acousticness and low-to-moderate energy?

### Parsed profile

```json
{
  "favorite_genre": "folk",
  "favorite_mood": "peaceful",
  "likes_acoustic": true,
  "preferred_mood_tags": [
    "calm",
    "peaceful",
    "mellow",
    "introspective",
    "quiet"
  ],
  "target_acousticness": 0.95,
  "target_danceability": 0.2,
  "target_decade": 2020,
  "target_energy": 0.25,
  "target_popularity": 55.0,
  "target_tempo_bpm": 70.0,
  "target_valence": 0.75
}
```

### Rationale from the model

> The description 'Sunday morning coffee and journaling, slow and acoustic' strongly suggests a peaceful and relaxed mood. I've set high acousticness and low energy/danceability to match the 'slow and acoustic' preference. The preferred mood tags reflect the calm and introspective nature of journaling.

### Constraint checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | `target_acousticness > 0.55` | > `0.55` | `0.95` | ✅ Pass |
| 2 | `target_energy < 0.55` | < `0.55` | `0.25` | ✅ Pass |

---
## Case: Sad folk

> *"I want to cry to something, sad and melancholy"*

**What this tests:** Does the model produce low-valence, low-energy output for clearly sad language?

### Parsed profile

```json
{
  "favorite_genre": "indie pop",
  "favorite_mood": "sad",
  "likes_acoustic": true,
  "preferred_mood_tags": [
    "sorrowful",
    "wistful",
    "emotional",
    "introspective"
  ],
  "target_acousticness": 0.75,
  "target_danceability": 0.2,
  "target_decade": 2010,
  "target_energy": 0.25,
  "target_popularity": 55.0,
  "target_tempo_bpm": 70.0,
  "target_valence": 0.15
}
```

### Rationale from the model

> The user explicitly requested music to 'cry to' that is 'sad and melancholy'. This translates to very low energy and valence, with a focus on emotional and introspective qualities. A higher acousticness is chosen to enhance the raw, heartfelt feel of the music.

### Constraint checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | `target_valence < 0.5` | < `0.5` | `0.15` | ✅ Pass |
| 2 | `target_energy < 0.6` | < `0.6` | `0.25` | ✅ Pass |

---
## Case: 80s retro

> *"80s retro synthwave, driving and nostalgic"*

**What this tests:** Does the model respect an explicit decade cue? Note that the catalog only has decades 1990-2020, so the 'honest' interpretation is the earliest available retro decade.

### Parsed profile

```json
{
  "favorite_genre": "synthwave",
  "favorite_mood": "nostalgic",
  "likes_acoustic": false,
  "preferred_mood_tags": [
    "driven",
    "nostalgic",
    "retro",
    "high-energy",
    "vibrant"
  ],
  "target_acousticness": 0.05,
  "target_danceability": 0.75,
  "target_decade": 2010,
  "target_energy": 0.8,
  "target_popularity": 65.0,
  "target_tempo_bpm": 125.0,
  "target_valence": 0.7
}
```

### Rationale from the model

> The profile focuses on synthwave with a strong nostalgic and driving feel, reflected in high energy and danceability. While '80s retro' was requested, the closest allowed decade for modern synthwave's popularity is 2010. Acousticness is set very low as synthwave is an electronic genre.

### Constraint checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | `target_decade <= 2010` | <= `2010` | `2010` | ✅ Pass |

---
## Case: Wedding dance

> *"something to dance to at a wedding reception, upbeat and happy"*

**What this tests:** Does the model raise danceability and valence for a clear dance-party prompt?

### Parsed profile

```json
{
  "favorite_genre": "pop",
  "favorite_mood": "happy",
  "likes_acoustic": false,
  "preferred_mood_tags": [
    "upbeat",
    "joyful",
    "celebratory",
    "high-energy",
    "feel-good"
  ],
  "target_acousticness": 0.2,
  "target_danceability": 0.8,
  "target_decade": 2010,
  "target_energy": 0.85,
  "target_popularity": 80.0,
  "target_tempo_bpm": 120.0,
  "target_valence": 0.9
}
```

### Rationale from the model

> This profile aims for high energy and positivity, reflecting the 'upbeat and happy' description. High danceability and a moderate-to-fast tempo are chosen to ensure the music is suitable for dancing at a wedding reception. The genre and popularity are set to appeal to a broad audience for a celebratory event.

### Constraint checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | `target_danceability > 0.6` | > `0.6` | `0.8` | ✅ Pass |
| 2 | `target_valence > 0.55` | > `0.55` | `0.9` | ✅ Pass |

---
## Case: Evening wind-down

> *"calm but not sleepy, an evening wind-down after work"*

**What this tests:** Does the model thread 'calm but not sleepy' into mid-low energy (not near zero)?

### Parsed profile

```json
{
  "favorite_genre": "lofi",
  "favorite_mood": "relaxed",
  "likes_acoustic": false,
  "preferred_mood_tags": [
    "calm",
    "mellow",
    "peaceful",
    "serene",
    "dreamy"
  ],
  "target_acousticness": 0.6,
  "target_danceability": 0.4,
  "target_decade": 2020,
  "target_energy": 0.45,
  "target_popularity": 60.0,
  "target_tempo_bpm": 80.0,
  "target_valence": 0.65
}
```

### Rationale from the model

> The request for 'calm but not sleepy' suggests a relaxed, low-energy vibe that isn't completely static, leading to a moderate energy and danceability. 'Evening wind-down' points to a peaceful and mellow mood, with a slightly positive valence. Lofi is a suitable genre for this specific combination of traits.

### Constraint checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | `target_energy >= 0.2` | >= `0.2` | `0.45` | ✅ Pass |
| 2 | `target_energy <= 0.55` | <= `0.55` | `0.45` | ✅ Pass |

---
## Case: Adversarial contradiction

> *"I want something both extremely calm and extremely loud at the same time"*

**What this tests:** Given a contradictory prompt, does the model make a coherent trade-off and acknowledge the contradiction in its rationale, rather than returning garbage?

### Parsed profile

```json
{
  "favorite_genre": "ambient",
  "favorite_mood": "peaceful",
  "likes_acoustic": false,
  "preferred_mood_tags": [
    "calm",
    "peaceful",
    "serene",
    "dreamy",
    "floating"
  ],
  "target_acousticness": 0.3,
  "target_danceability": 0.2,
  "target_decade": 2010,
  "target_energy": 0.25,
  "target_popularity": 55.0,
  "target_tempo_bpm": 70.0,
  "target_valence": 0.55
}
```

### Rationale from the model

> The request for 'extremely calm and extremely loud' presents a contradiction. I've interpreted 'calm' as low energy and peaceful, while 'loud' is understood as a full, immersive soundscape that can be experienced at high volume, rather than high energy or aggression. Ambient music is chosen as it can provide a serene atmosphere with rich, expansive sound textures.

### Constraint checks

| # | Check | Expected | Actual | Result |
|---|---|---|---|---|
| 1 | `__rationale__ len_gt 40` | length > 40 | `366` | ✅ Pass |
| 2 | `target_energy >= 0.0` | >= `0.0` | `0.25` | ✅ Pass |
| 3 | `target_energy <= 1.0` | <= `1.0` | `0.25` | ✅ Pass |

