# Status — Sims But Social (prototype)

A self-contained clone of the core loop from [Status – Sims But Social](https://socialai.app) (by WishRoll):
create a persona, drop into a fandom community, post to a feed, and get reactions
from AI-driven in-universe characters. Clout rises and falls with what you post,
and an energy system gates how often you can act.

This prototype does **not** call any external AI service — character replies come
from local template banks keyed by post "category" (hype / drama / cancel / snark /
neutral) and character archetype (mentor / rival / bestie), so it runs standalone
with no API keys. The "premium" and "buy coffee" actions are simulated demo
buttons — no real payment is processed anywhere.

## Run it

```bash
cd status_app
pip install -r requirements.txt
python app.py
```

Then open http://localhost:5050.

## What's implemented

- Persona creation (name, avatar, bio)
- 5 fandom communities, each with 3 recurring AI characters (mentor/rival/bestie)
- A post composer that costs energy and gets reactions (likes + in-character comments)
- A clout meter with tiers: Cancelled → Nobody → Rising → Viral → Famous
- An energy economy: passive cap, "watch an ad" for a random top-up, a demo
  "premium" toggle that raises the cap, and a demo "buy coffee" top-up
- Mobile-first UI, installable as a PWA (manifest + service worker) so it can be
  added to a phone home screen like an app today

## Path to a real mobile app

The backend is a plain JSON API (`/api/*`), decoupled from the HTML/CSS/JS
frontend, so there are two straightforward next steps once the concept is
validated here:

1. **Fastest**: wrap this same web app with [Capacitor](https://capacitorjs.com/)
   or [Cordova](https://cordovaphonegap.com/) to ship it in the app stores with
   minimal changes.
2. **Native-feeling**: rebuild the UI in React Native / Expo, calling the same
   Flask endpoints (`/api/persona`, `/api/fandom`, `/api/post`, `/api/energy/*`).
   The reaction/clout/energy logic in `app.py` would not need to change.

## Not implemented (out of scope for this prototype)

- Real user accounts / multiplayer rooms
- Real payments (premium + coffee purchases are simulated)
- An actual LLM behind character replies (template-based instead, see
  `ARCHETYPE_REPLIES` in `app.py` — swapping in a real model is a drop-in
  change to `react_to_post()`)
