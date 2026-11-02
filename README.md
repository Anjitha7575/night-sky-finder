# Night Sky Finder

**Let AI check your sky camera clips.**

Sky cameras record anything that moves at night: meteors, but also planes, satellites, birds, insects, clouds, lightning and aurora. One camera can save hundreds of clips a night, and owners check them by hand.
Night Sky Finder measures each clip with Python, then **Meta's Muse Spark** investigates it like a detective, decides **"meteor or not"**, and explains why in plain words.

- **Live demo:** https://night-sky-finder.vercel.app (the first load can take up to a minute while the server wakes up)
- **Demo video:** _coming soon_

Built for the **Meta Global AI Developer Hackathon** (Indie track).

![Night Sky Finder](docs/screenshot.png)

## Results

Meteor or not, checked against experts. "Not sure" counts as not right.

| Test set | Night Sky Finder | Muse Spark watching the video | Muse Spark looking at 8 frames |
|---|---|---|---|
| **NightSkyUCP**: 200 clips (100 meteors, 100 not), each checked by 5 experts | **85% right**, 13% not sure, 3% wrong | 35% right | 40% right |
| **AllSky7**: 33 clips, named by the network | **70% right** | 48% right | 55% right |

- When Night Sky Finder says "meteor" on the expert set, it is right **76 of 79** times.
- Cost: about **$0.01 per clip**.
- Every row is in the **Results** tab of the live demo.
- The AllSky7 set is small, and some of its clips were also used while we improved the code, so it is not a blind test. See [LIMITATIONS.md](LIMITATIONS.md).

## How it works

```
sky clip ──► 1. Python measures ──► 2. Muse Spark investigates ──► 3. answer + reason
            speed, straightness,     looks at 2 pictures, picks       "Meteor / Not a meteor",
            time visible, blinking,  up to 3 checks, then decides     the type, and why
            whole-sky flash
```

**1. Our code measures (OpenCV + NumPy)**
- Finds what moved between frames and follows the main moving object.
- Measures speed (% of the screen per second), straightness (1 = perfectly straight), how long it is visible, and whether it blinks.
- Spots whole-sky flashes (lightning) and the whole sky getting brighter (a fireball lighting up the sky).
- Handles hard cases: faint objects on a bright sky, long videos, several satellites one after another.
- Makes 2 pictures for the AI: all frames stacked with the still sky removed, and one normal frame (to see clouds, aurora, daylight).

**2. Muse Spark investigates (Meta Model API, Responses API with tool calling)**

The AI gets the numbers and the 2 pictures. If it is not sure yet, it can call up to **3 tools**, and must say **why** for each one:

| Tool | What it shows |
|---|---|
| `zoom_in` | A close-up of the object's path: dotted (blinking plane), smooth (satellite), or with a tail (meteor) |
| `frames_over_time` | 4 close-up frames: how the object moved and changed |
| `brightness_curve` | Brightness in each frame: flare, fade, steady or blinking |
| `where_in_sky` | How far from the centre of the round camera picture (edge = horizon) |
| `watch_video` | 8 frames spread over the whole clip (costs the most, used last) |

Clear clips are decided after one look, so they stay cheap. Unclear clips get more checks.

**3. The answer**

"Meteor", "Maybe a meteor", "Not a meteor" or "Not sure", then the type (meteor, satellite, plane, bird, insect, cloud, sky flash, aurora, space junk burning up), a confidence level, a reason in plain words, and every check the AI made.

Nothing is saved: every click asks the AI again, live.

## Run it yourself

You need Python 3.12 and Node 20+.

**Backend**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Create a `.env` file in the main project folder:
```
META_API_KEY=your-key
META_MODEL=muse-spark-1.3
AI_MODE=meta
```
(`AI_MODE=mock` runs simple rules instead of the AI, with no key needed.)
```bash
uvicorn skyfinder.api:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. To use another backend, set `VITE_API_URL`.

**Tests**
```bash
cd backend
python -m pytest -q
```

**Re-run the comparison** (uses the Meta API, costs tokens)
```bash
cd backend
python scripts/compare_ai_alone.py --folder data/nightskyucp_test --name NightSkyUCP_results --run-ours --how video
python scripts/compare_ai_alone.py --folder data/nightskyucp_test --name NightSkyUCP_frames --how frames
python scripts/make_results.py
```

## Project layout

```
backend/
  skyfinder/
    measure.py    measuring the moving object (OpenCV)
    tools.py      the 5 tools the AI can call
    agent.py      the investigation loop with Muse Spark
    classify.py   the guide for the AI and the answer format
    api.py        FastAPI server
  scripts/        test runs, results, helpers
  tests/          pytest tests
  results/        saved test results
  data/sample/    demo clips
frontend/         React (Vite) app: Live demo and Results tabs
```

## Credits

**Videos**
- **NightSkyUCP dataset:** M. Hofmann, R. Sennlaub, M. Hankey, M. Ennes, T. Müller, P. Kroll, P. Mäder (2022), [doi.org/10.6084/m9.figshare.16451625](https://doi.org/10.6084/m9.figshare.16451625), licence [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Paper: [doi.org/10.1093/mnras/stac1948](https://doi.org/10.1093/mnras/stac1948). Clips were cut and processed for this project.
- **AllSky7 Fireball Network:** [allsky7.net](https://allsky7.net). Copyright: the camera owners, AllSky7 Fireball Network. Used for non-commercial purposes only.

  | Clip | Station (camera) | Place | Copyright |
  |---|---|---|---|
  | `2026_03_08_17_55_..._010763` | [AMS76](https://herkenrath.allsky7.net) (010763) | Herkenrath, Germany | Bernd Klemt, AllSky7 Fireball Network |
  | `2026_03_23_18_27_..._012661` | [AMS266](https://lindenberg.allsky7.net) (012661) | Lindenberg, Germany | André Knöfel, AllSky7 Fireball Network |
  | `2026_05_15_01_29_..._010091` | [AMS16](https://ketzuer.allsky7.net) (010091) | Ketzür, Germany | Sirko Molau, AllSky7 Fireball Network |
  | `non_meteor_2023_02_26_21_15_..._011195` | [AMS119](https://gaustatoppen.allsky7.net) (011195) | Gaustatoppen, Norway | Steinar Midtskogen, AllSky7 Fireball Network |
  | `non_m_2022_10_30_03_54_..._011193` | [AMS119](https://gaustatoppen.allsky7.net) (011193) | Gaustatoppen, Norway | Steinar Midtskogen, AllSky7 Fireball Network |
  | `non_m_2023_11_09_00_57_..._010885` | [AMS88](https://hoyerswerda.allsky7.net) (010885) | Hoyerswerda, Germany | Peter Lindner, AllSky7 Fireball Network |
- **IAC / STARS4ALL all-sky meteors 2016** (Teide, Tenerife), licence CC BY 4.0.
- **SkySentinel** network, Las Cruces, USA: [goskysentinel.com](https://goskysentinel.com).

**Other**
- AI: Meta Muse Spark (`muse-spark-1.3`) through the Meta Model API.
- Background picture made with ChatGPT.

## More

- [LIMITATIONS.md](LIMITATIONS.md): what it does not do well yet
- [ROADMAP.md](ROADMAP.md): what could come next

---

© 2026 Anjitha D. All rights reserved. The code is shared for viewing and judging only. The videos keep their own licences (see Credits).