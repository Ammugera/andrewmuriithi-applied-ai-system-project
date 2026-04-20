# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name

**VibeMatch 1.0**

---

## 2. Intended Use

VibeMatch is designed to suggest songs from a small catalog based on a user's taste profile. It is built for classroom exploration, not for real users or production apps.

It is meant for: learning how content-based recommendation works, testing scoring logic, and exploring how small changes in weights affect results.

It is not meant for: real music apps, large catalogs, or users with complex or shifting tastes. It should not be used to make decisions that affect real people.

---

## 3. How the Model Works

Each song has a genre, a mood, and five numeric features: energy, valence, danceability, acousticness, and tempo.

Each user has a favorite genre, a favorite mood, and target values for those five numeric features.

The system scores every song in the catalog against the user profile. Genre and mood are worth bonus points if they match exactly. For the numeric features, the closer a song's value is to the user's target, the higher it scores, but scores drop off quickly if the values are far apart. This uses a bell-curve style formula called Gaussian decay.

All the individual scores are combined into one total using weighted averaging, with energy and acousticness counting more than valence, danceability, and tempo. Genre counts the most overall. Songs are then ranked from highest to lowest score and the top results are returned.

---

## 4. Data

The catalog has 20 songs stored in a CSV file. Each song has 10 fields: id, title, artist, genre, mood, energy, tempo, valence, danceability, and acousticness.

Genres represented: lofi, pop, rock, ambient, jazz, synthwave, indie pop, hip-hop, classical, country, metal, r&b, reggae, electronic, blues, folk, latin.

Lofi has 3 songs. Most other genres have 1. This imbalance affects results for users outside the lofi cluster.

Missing from the data: lyrics, language, release year, artist popularity, and listening history. The features were assigned manually, not measured from real audio.

---

## 5. Strengths

The system works well for users whose taste matches a well-represented genre. Lofi, jazz, electronic, and folk listeners all received results that matched expectations during testing.

The explanation output is a strength: every recommendation shows exactly why each song was chosen, which makes the logic transparent and easy to check.

The soft scoring approach means no songs are completely excluded. A chill ambient song can still rank for a lofi user if its numeric features are close enough.

---

## 6. Limitations and Bias

The most significant weakness discovered during experimentation is the catalog density bias toward lofi. With three lofi songs in a twenty-song catalog compared to one song for most other genres, the system structurally favors lofi listeners, not because the algorithm is better tuned for them, but simply because there are more candidates competing for top spots. This was confirmed by the Genre Orphan adversarial profile, where a reggae listener received a perfect score for the only matching song but had almost no meaningful second or third result. In contrast, a lofi listener consistently received three strong, differentiated recommendations. In a real-world system this type of catalog imbalance would quietly disadvantage users whose tastes fall outside the majority genre distribution, making the recommender appear broken for those users even though the scoring logic itself is working correctly.

---

## 7. Evaluation

To check whether the recommender was working as intended, seven user profiles were tested: four realistic ones (Chill Lofi Student, Melancholic Explorer, Festival Headliner, Late Night Jazz) and three adversarial ones designed to stress-test the system (Impossible Ideal, Genre Orphan, Flat Numeric Strong Categorical).

For each profile, the goal was to check whether the top results felt like a reasonable match, meaning the genre and mood lined up where expected, the scores made sense given how close each song's features were to the target values, and the reasons printed alongside each result told an honest story about why a song was recommended.

The most surprising result came from the Flat Numeric Strong Categorical profile, where all numeric targets were set to a neutral midpoint of 0.5. Even without strong numeric preferences, the system still confidently ranked lofi songs at the top purely because of the genre label weight. This revealed that category labels carry enough scoring power to override the numeric features entirely when preferences are vague.

A deliberate comparison was also run by doubling the weight of energy and halving the weight of genre. The song rankings mostly stayed the same, but the score gaps between the first and second results widened noticeably, meaning the system became more confident in its top pick and less forgiving of songs that were close but not quite right on energy.

---

## 8. Future Work

Add more songs per genre so every user type has real competition among candidates, not just one obvious winner.

Replace the binary genre match with a genre similarity score. For example, lofi and ambient could be treated as closer to each other than lofi and metal.

Add a diversity rule so the top-k results cannot all come from the same genre or artist, which would make the recommendations feel less repetitive.

---

## 9. Personal Reflection

Before this project I assumed recommendation systems were mostly about finding songs that sound similar. Building this made me realise they are actually about a lot of math, where you turn preferences into numbers and measuring distance. That shift in thinking was the biggest thing I took away.

The most unexpected moment was running the Flat Numeric Strong Categorical profile. I set all the numeric targets to 0.5 expecting the results to feel random, but the system confidently returned lofi songs at the top. It was a clear reminder that the weights you choose shape the output just as much as the user's actual preferences do. It was also evident that a system can look like it's working when it's really just defaulting to whatever the data has the most of.

It also changed how I think about apps like Spotify. I used to assume the recommendations were deep and personalised. Now I think about what the catalog looks like behind the scenes, how genres are labelled, and whether the system actually knows what I want or just what songs have features closest to my listening history. There is a lot of room between "the algorithm picked this" and "this is genuinely a good match."

---

## Screenshots

![image](image.png)

![Profile: Flat Numeric Strong Categorical](PROFILE Plat Numeric Strona Categorica.png)

![Profile: Genre Orphan](PROFILE Genre Orphan.png)

![Profile: Impossible Ideal](PROFILE Inpossible Ideal.png)

![Blue](BLUE.png)
