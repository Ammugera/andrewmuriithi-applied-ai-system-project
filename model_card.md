# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeMatch 2.0**

An extension of VibeMatch 1.0, the Music Recommender Simulation starter built for AI110 Module 3. The 2.0 version keeps the original deterministic scoring engine and adds a natural-language front door powered by Google Gemini, a Streamlit dashboard with per-feature importance visualizations, and a golden-set evaluation harness for the language model component.

---

## 2. Intended Use

VibeMatch 2.0 is designed to suggest songs from a small catalog based on a user's taste profile, either typed in plain English or configured through presets and sliders. It is built for classroom exploration and portfolio presentation, not for real users or production apps.

It is meant for: learning how content-based recommendation works, exploring how a language model can act as a structured-data translator rather than a decision-maker, and demonstrating responsible-AI design practices like per-feature explanations and falsifiable evaluation.

It is not meant for: real music apps, large catalogs, users with complex or shifting tastes, or any setting where recommendations influence decisions that affect real people.

---

## 3. How the Model Works

Each song has a genre, a mood, a set of mood tags, and seven numeric attributes: energy, valence, danceability, acousticness, tempo (in beats per minute), popularity, and release decade.

Each user profile has a favorite genre, a favorite mood, a list of preferred mood tags, an "likes acoustic" flag, and target values for all seven numeric attributes.

The system has two layers:

**Layer 1: the LLM parser.** Google Gemini 2.5 Flash reads a user's plain-English description (for example, "chill study session, not too sleepy") and returns a structured `UserProfile` JSON via schema-constrained output. The genre, mood, and mood-tag fields are restricted to enum lists drawn from the catalog at import time, so the model cannot invent values that do not exist in the data. The parser also returns a short rationale in English so the user can see how the description was interpreted.

**Layer 2: the deterministic scoring engine.** The same engine from VibeMatch 1.0 scores every song in the catalog against the user profile. Genre and mood give points when they match exactly. For each numeric attribute, the closer a song's value is to the user's target the higher the score, with scores dropping off quickly as values diverge (a Gaussian decay). Mood tags contribute based on set overlap between the user's preferred tags and the song's tags.

All individual scores are combined into one total using weighted averaging:

| Feature | Weight |
|---|---|
| Energy | 4.0 |
| Mood | 2.0 |
| Acousticness | 2.0 |
| Genre | 1.5 |
| Mood Tags | 1.5 |
| Valence | 1.0 |
| Danceability | 1.0 |
| Tempo | 1.0 |
| Popularity | 1.0 |
| Decade | 0.5 |
| **Total (divisor)** | **15.5** |

Energy carries the heaviest weight in the formula, followed by Mood and Acousticness. Songs are ranked from highest to lowest weighted score, and the top results are returned along with a full per-feature breakdown used by the dashboard's feature-importance charts.

**Design principle:** the LLM is a translator, not the decision-maker. All ranking decisions happen inside the deterministic engine, which means every recommendation is auditable and reproducible.

---

## 4. Data

The catalog is 20 songs stored in `data/songs.csv`. Each song has 13 fields: id, title, artist, genre, mood, energy, tempo_bpm, valence, danceability, acousticness, popularity, release_decade, and mood_tags.

**Genres represented** (17 total): lofi, pop, rock, ambient, jazz, synthwave, indie pop, hip-hop, classical, country, metal, r&b, reggae, electronic, blues, folk, latin.

**Decades represented** (4 total): 1990, 2000, 2010, 2020.

**Catalog density imbalance.** Lofi has 3 songs. Most other genres have 1. This imbalance affects results for users outside the lofi cluster and is analyzed in Section 6.

**Decade coverage gap.** The catalog spans only 1990 to 2020. There are no songs from the 1970s or 1980s. This gap was first surfaced during reliability testing when a natural-language prompt for "80s retro synthwave" forced the language model to pick from the available decades.

**Missing from the data:** lyrics, language, release year (only decade is stored), artist popularity separate from song popularity, and listening history. All numeric features were assigned manually by the dataset author, not measured from real audio.

**User profile schema.** The 11-field `UserProfile` dataclass consumed by the scorer contains: favorite_genre, favorite_mood, target_energy, target_valence, target_danceability, target_acousticness, target_tempo_bpm, target_popularity, target_decade, preferred_mood_tags, and likes_acoustic.

---

## 5. Strengths

The system works well for users whose taste matches a well-represented genre. Lofi, jazz, electronic, and folk listeners all receive results that match expectations during testing.

**Per-feature explanations are the system's single biggest strength.** Every recommendation is rendered in the dashboard with an expandable feature-importance chart that shows exactly how much each of the 10 weighted features contributed to the final score. Hover tooltips display the arithmetic (for example, weight 4.0 multiplied by raw Gaussian score 0.98, divided by the 15.5 total). A unit test guarantees that the sum of per-feature contributions equals the displayed score.

**Confidence signals surface uncertainty.** Each result card carries a Strong / Moderate / Weak badge based on the absolute score and the gap to the next result. A ranking-confidence summary above the top-k tells the user how tightly clustered the scores are. A low-match warning banner appears when the top score falls below 0.45.

**The natural-language interface lowers the barrier for non-technical users.** A user can describe a mood in plain English instead of configuring sliders, and the LLM produces a structured profile plus a rationale paragraph explaining its choices.

**The soft scoring approach from 1.0 is preserved.** No songs are completely excluded. A chill ambient song can still rank for a lofi user if its numeric features are close enough.

**Falsifiable evidence for the LLM component.** The reliability harness in `scripts/evaluate_parser.py` runs a hand-written set of natural-language prompts through live Gemini and checks each parsed profile against explicit assertions. Evidence is written to `assets/reliability_report.md` and embedded inline inside the dashboard's Reliability tab.

---

## 6. Limitations and Bias

The 1.0 biases remain and the 2.0 additions introduce several new ones.

**Catalog density bias (inherited from 1.0).** With three lofi songs in a twenty-song catalog compared to one song for most other genres, the system structurally favors lofi listeners, not because the algorithm is better tuned for them, but simply because there are more candidates competing for top spots. This was confirmed by the Genre Orphan adversarial profile, where a reggae listener received a perfect score for the only matching song but had almost no meaningful second or third result. A lofi listener consistently received three strong, differentiated recommendations. In a real-world system this type of catalog imbalance would quietly disadvantage users whose tastes fall outside the majority genre distribution.

**Decade coverage gap (new).** The catalog has no 1970s or 1980s songs. When a user asks for older music, the language model is forced to pick from the available decades and may land on an interpretation that matches the spirit of the request but not the literal decade. This was surfaced by the evaluation harness when it ran an "80s retro synthwave" prompt and Gemini picked 2010 with a "synthwave's resurgence" rationale.

**LLM training bias (new).** Gemini's mappings of qualitative cues like "calm," "upbeat," or "cinematic" to specific genres and numeric targets reflect Western, English-language music culture. Users describing musical preferences grounded in other traditions may see interpretations that do not match their intent.

**Free-tier data use (new).** Google's Gemini free tier allows inputs and outputs to be used to improve the model. A user typing emotionally specific context ("I just got dumped and want something to cry to") should know that the text is being sent to Google and may be used in training. The dashboard includes a small disclosure note next to the natural-language input.

**Rate limit as an operational constraint (new).** The Gemini 2.5 Flash free tier is capped at 5 requests per minute. This shaped the evaluation harness design (13-second pacing between calls) and would limit any production use without upgrading to a paid tier.

**No personalization loop.** Every session is stateless. The system cannot learn that a particular user prefers folk more than the catalog leads with, so biases compound for users whose tastes sit outside the majority distribution.

**Architecture pattern risk.** The "LLM translator plus deterministic engine" pattern is easy to copy into higher-stakes domains such as loan triage or content moderation. The same design can cause real harm if the transparency layer (the rationale panel, the feature-importance charts, the reliability report) is stripped out. The defense against misuse is the transparency, not the pattern itself.

---

## 7. Evaluation

### Preset profile testing

To check whether the recommender was working as intended, seven user profiles were tested: four realistic ones (Chill Lofi Student, Melancholic Explorer, Festival Headliner, Late Night Jazz) and three adversarial ones designed to stress-test the system (Impossible Ideal, Genre Orphan, Flat Numeric Strong Categorical).

For each profile, the goal was to check whether the top results felt like a reasonable match: the genre and mood lined up where expected, the scores made sense given how close each song's features were to the target values, and the reasons printed alongside each result told an honest story about why a song was recommended.

The most surprising result came from the Flat Numeric Strong Categorical profile, where all numeric targets were set to a neutral midpoint of 0.5. Even without strong numeric preferences, the system still confidently ranked lofi songs at the top purely because of the genre label weight. This revealed that category labels carry enough scoring power to override the numeric features entirely when preferences are vague.

### Unit tests

Twelve automated tests run in under a second with no live API calls. Eight cover the scoring engine, including `test_feature_weights_sum_to_total`, which guarantees that the per-feature weighted contributions on every chart sum to the displayed total score. Four cover the LLM parser using mocked API responses, so they run in continuous integration without needing a Gemini API key.

### LLM evaluation harness

The reliability harness at `scripts/evaluate_parser.py` runs 8 hand-written natural-language prompts through live Gemini and checks each parsed profile against falsifiable assertions (for example, "for the prompt 'late-night studying, chill but focused', target_energy must be less than 0.55 and favorite_genre must be in the set of calm genres"). The latest run passed 18 of 18 assertions. The full report is at `assets/reliability_report.md` and is also embedded inside the dashboard's Reliability tab.

Two findings from the live runs are worth highlighting. First, the 80s retro synthwave case described in Section 6. Second, an adversarial contradiction case with the prompt "I want something both extremely calm and extremely loud at the same time." Rather than returning generic mid-range values or refusing the request, Gemini named the contradiction explicitly in its rationale and reasoned its way to ambient music by redefining "loud" as "rich, immersive soundscape" rather than "high energy or aggression."

---

## 8. Future Work

The explanation and transparency asks in the original future-work list are partially addressed in 2.0 through per-feature importance charts, the rationale panel, and the reliability report. Items still open include:

- Replace the binary genre match with a genre similarity score. For example, lofi and ambient could be treated as closer to each other than lofi and metal.
- Add a diversity rule so the top-k results cannot all come from the same genre or artist, which would make recommendations feel less repetitive and would address the catalog-density bias more directly.
- Expand the catalog, especially to pre-1990 decades, so prompts like "80s retro" have literal matches rather than inferred substitutes.
- Add a user feedback loop so the system can adjust its interpretation of qualitative cues over time (with explicit user consent and a reset option).
- Add an LLM-as-judge layer on top of the golden set to evaluate subtler quality properties (tone, creativity, whether the rationale reads naturally) that hand-written assertions cannot check.

---

## 9. Personal Reflection

Before this project I assumed recommendation systems were mostly about finding songs that sound similar. Building this made me realise they are actually about a lot of math, where you turn preferences into numbers and measure distance. That shift in thinking was the biggest thing I took away. The most unexpected moment from the 1.0 work was running the Flat Numeric Strong Categorical profile. I set all the numeric targets to 0.5 expecting the results to feel random, but the system confidently returned lofi songs at the top. It was a clear reminder that the weights you choose shape the output just as much as the user's actual preferences do. A system can look like it's working when it's really just defaulting to whatever the data has the most of.

Building 2.0 on top of that foundation taught me a second lesson about where to put the language model in the pipeline. I could have handed the whole recommendation task to Gemini, but I chose to scope it to a single job: turning English into a structured profile. That constraint meant every ranking decision still lived in code I could read and test, and it made the per-feature importance charts possible at all. The other surprise was how cheaply the evaluation harness paid off. The first live run caught a real catalog-bias issue (the decade gap) that no unit test would have found. That convinced me that falsifiable assertions against a living LLM are worth building even for a small project, because they shift "I think the model works" into "here is the evidence that it does."

It also changed how I think about apps like Spotify. I used to assume the recommendations were deep and personalised. Now I think about what the catalog looks like behind the scenes, how genres are labelled, and whether the system actually knows what I want or just what songs have features closest to my listening history. There is a lot of room between "the algorithm picked this" and "this is genuinely a good match."
