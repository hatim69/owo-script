"""
Status - Sims But Social (prototype)

A self-contained social-media simulator in the spirit of "Status" by WishRoll:
create a persona, drop it into a fandom community, post to a feed, and get
reactions from AI-driven in-universe characters. Clout rises and falls with
what you post, and an energy system gates how often you can act.

No external services or API keys are required - character reactions are
generated from local template banks, not a live LLM.
"""
import os
import random
import secrets
import time

from flask import Flask, jsonify, render_template, request, session, send_from_directory

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

MAX_POSTS_STORED = 15
POST_ENERGY_COST = 15
DEFAULT_MAX_ENERGY = 100
PREMIUM_MAX_ENERGY = 150

# --- FANDOM COMMUNITIES -----------------------------------------------------
# Each fandom has exactly one character per archetype so reply banks
# (ARCHETYPE_REPLIES) can be shared across every community.
FANDOMS = {
    "wizarding-academy": {
        "name": "Wizarding Academy",
        "emoji": "🪄",
        "desc": "A magic boarding school full of rivalries, secret spells, and prophecy drama.",
        "characters": [
            {"name": "Prof. Lyra Ashbourne", "avatar": "🧙‍♀️", "archetype": "mentor"},
            {"name": "Finch Holloway", "avatar": "😏", "archetype": "rival"},
            {"name": "Wren Sable", "avatar": "⭐", "archetype": "bestie"},
        ],
    },
    "galactic-uprising": {
        "name": "Galactic Uprising",
        "emoji": "🚀",
        "desc": "A rebellion against an empire, fought one viral broadcast at a time.",
        "characters": [
            {"name": "Commander Vex", "avatar": "🎖️", "archetype": "mentor"},
            {"name": "Nova Sarn", "avatar": "😎", "archetype": "rival"},
            {"name": "K-9RO", "avatar": "🤖", "archetype": "bestie"},
        ],
    },
    "neon-district": {
        "name": "Neon District",
        "emoji": "🌆",
        "desc": "Cyberpunk hackers, fixers, and streamers fighting for clout in the underground.",
        "characters": [
            {"name": "Ghost_Iri", "avatar": "👤", "archetype": "mentor"},
            {"name": "Dex Malone", "avatar": "🕶️", "archetype": "rival"},
            {"name": "Juno Cross", "avatar": "📡", "archetype": "bestie"},
        ],
    },
    "ever-after-high": {
        "name": "Ever After High",
        "emoji": "🦸",
        "desc": "A superhero teen drama where secret identities never stay secret for long.",
        "characters": [
            {"name": "Coach Blaze", "avatar": "🔥", "archetype": "mentor"},
            {"name": "Ivy Vane", "avatar": "🖤", "archetype": "rival"},
            {"name": "Milo Chen", "avatar": "😂", "archetype": "bestie"},
        ],
    },
    "undead-dawn": {
        "name": "Undead Dawn",
        "emoji": "🧟",
        "desc": "A zombie apocalypse survivor camp where every post could be your last.",
        "characters": [
            {"name": "Sarge Reyes", "avatar": "🪖", "archetype": "mentor"},
            {"name": "Raider Cole", "avatar": "🔪", "archetype": "rival"},
            {"name": "Pixel", "avatar": "🎮", "archetype": "bestie"},
        ],
    },
}

ARCHETYPE_REPLIES = {
    "mentor": {
        "hype": [
            "Proud of you, {name}. Keep that momentum.",
            "This is exactly the growth I hoped to see.",
            "Well done. The whole crew's talking about this.",
        ],
        "snark": [
            "Careful, {name} - confidence is good, recklessness isn't.",
            "Bold move. Hope you thought it through.",
            "Hm. Not what I would've done, but noted.",
        ],
        "drama": [
            "This changes things. We need to talk, {name}.",
            "That's going to have consequences, sooner or later.",
            "You've opened a door that's hard to close, {name}.",
        ],
        "cancel": [
            "I warned you about this, {name}. Damage control, now.",
            "This isn't a look I can defend right now.",
            "We'll get through this, but it's going to be rough.",
        ],
        "neutral": [
            "Noted, {name}.",
            "Keep us posted.",
            "Interesting update.",
        ],
    },
    "rival": {
        "hype": [
            "...okay fine, that was actually impressive, {name}.",
            "Don't let it go to your head. But nice.",
            "Lucky. Won't happen twice.",
        ],
        "snark": [
            "lol sure, {name}.",
            "That's... a choice.",
            "Big talk. We'll see.",
        ],
        "drama": [
            "Oh this is JUICY. Popcorn's out. 🍿",
            "Wait, WHAT. Say more.",
            "Screenshotting this for later, {name}.",
        ],
        "cancel": [
            "Called it. 💀",
            "Yikes. Even I feel bad for you, {name}.",
            "This is not the redemption arc you think it is.",
        ],
        "neutral": [
            "k.",
            "cool cool cool.",
            "noted, moving on.",
        ],
    },
    "bestie": {
        "hype": [
            "{name}!! YES. This is EVERYTHING. 😭✨",
            "I am SO proud of you right now.",
            "Screenshotting this, it's iconic.",
        ],
        "snark": [
            "{name}... we need to talk about your choices lol",
            "bestie no 😭",
            "I love you but what was that",
        ],
        "drama": [
            "WAIT. Explain. Right now.",
            "okay this is a whole storyline, I'm invested",
            "{name} the way my jaw DROPPED",
        ],
        "cancel": [
            "I've got your back no matter what, {name}. Always.",
            "People are wrong about you and I'll say it louder.",
            "We ride at dawn. Don't spiral, I'm here.",
        ],
        "neutral": [
            "saw this, love u",
            "okay noted lol",
            "👀👀👀",
        ],
    },
}

CANCEL_WORDS = ["cancel", "expose", "exposed", "toxic", "cheat", "cheated", "lied", "liar", "scam", "betray"]
DRAMA_WORDS = ["drama", "fight", "breakup", "secret", "affair", "rumor", "beef", "shocking", "twist"]
HYPE_WORDS = ["love", "amazing", "best", "proud", "excited", "blessed", "win", "grateful", "yay"]
SNARK_WORDS = ["boring", "meh", "whatever", "lame"]

TIERS = [
    (float("-inf"), 0, "Cancelled", "💀"),
    (0, 50, "Nobody", "🌱"),
    (50, 150, "Rising", "✨"),
    (150, 350, "Viral", "🔥"),
    (350, float("inf"), "Famous", "👑"),
]


def classify_post(text):
    t = text.lower()
    if any(w in t for w in CANCEL_WORDS):
        return "cancel"
    if any(w in t for w in DRAMA_WORDS):
        return "drama"
    if any(w in t for w in HYPE_WORDS):
        return "hype"
    if any(w in t for w in SNARK_WORDS):
        return "snark"
    return random.choice(["neutral", "neutral", "hype", "snark"])


def clout_delta(category):
    if category == "hype":
        return random.randint(8, 20)
    if category == "drama":
        # consequence-driven: could go viral or backfire
        return random.choice([random.randint(15, 35), -random.randint(5, 15)])
    if category == "cancel":
        return -random.randint(20, 40)
    if category == "snark":
        return random.randint(-5, 5)
    return random.randint(1, 8)


def tier_for(clout):
    for lo, hi, label, icon in TIERS:
        if lo <= clout < hi:
            return {"label": label, "icon": icon}
    return {"label": "Nobody", "icon": "🌱"}


def reactors_for_tier(tier_label, characters):
    counts = {"Nobody": 1, "Rising": 2, "Viral": 3, "Famous": 3, "Cancelled": 3}
    n = min(counts.get(tier_label, 1), len(characters))
    return random.sample(characters, n)


def react_to_post(fandom_id, persona_name, category, tier_label, exclude_name=None):
    fandom = FANDOMS[fandom_id]
    candidates = [c for c in fandom["characters"] if c["name"] != exclude_name]
    chosen = reactors_for_tier(tier_label, candidates)
    comments = []
    for char in chosen:
        pool = ARCHETYPE_REPLIES[char["archetype"]][category]
        text = random.choice(pool).format(name=persona_name)
        comments.append({"author": char["name"], "avatar": char["avatar"], "text": text})
    base_likes = {"hype": (20, 60), "drama": (10, 90), "cancel": (0, 15), "snark": (5, 25), "neutral": (5, 30)}
    lo, hi = base_likes.get(category, (5, 20))
    likes = random.randint(lo, hi)
    return comments, likes


def default_state():
    return {
        "persona": None,  # {name, avatar, bio}
        "fandom_id": None,
        "clout": 0,
        "energy": DEFAULT_MAX_ENERGY,
        "max_energy": DEFAULT_MAX_ENERGY,
        "premium": False,
        "posts": [],  # newest first
    }


def get_state():
    if "game" not in session:
        session["game"] = default_state()
    return session["game"]


def save_state(state):
    session["game"] = state
    session.modified = True


def public_state(state):
    tier = tier_for(state["clout"])
    fandom = FANDOMS.get(state["fandom_id"]) if state["fandom_id"] else None
    return {
        "persona": state["persona"],
        "fandom": {"id": state["fandom_id"], "name": fandom["name"], "emoji": fandom["emoji"]} if fandom else None,
        "clout": state["clout"],
        "tier": tier,
        "energy": state["energy"],
        "max_energy": state["max_energy"],
        "premium": state["premium"],
        "posts": state["posts"],
    }


def seed_posts(state):
    fandom = FANDOMS[state["fandom_id"]]
    seeds = [
        ("hype", "just hit a new record and I'm still shaking, let's gooo"),
        ("drama", "okay something happened at practice today and I can't stop thinking about it"),
        ("neutral", "quiet day around here, regrouping for what's next"),
    ]
    posts = []
    for category, text in seeds:
        char = random.choice(fandom["characters"])
        comments, likes = react_to_post(state["fandom_id"], char["name"], category, "Rising", exclude_name=char["name"])
        # seed posts are from NPCs, so reroll one comment to keep it varied
        posts.append(
            {
                "id": secrets.token_hex(6),
                "author": char["name"],
                "avatar": char["avatar"],
                "is_user": False,
                "text": text,
                "category": category,
                "likes": likes,
                "comments": comments[:2],
                "ts": time.time(),
            }
        )
    posts.reverse()
    state["posts"] = posts


# --- ROUTES ------------------------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sw.js")
def service_worker():
    return send_from_directory(app.static_folder, "sw.js")


@app.route("/api/fandoms")
def api_fandoms():
    return jsonify(
        [{"id": fid, "name": f["name"], "emoji": f["emoji"], "desc": f["desc"]} for fid, f in FANDOMS.items()]
    )


@app.route("/api/state")
def api_state():
    return jsonify(public_state(get_state()))


@app.route("/api/persona", methods=["POST"])
def api_persona():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()[:24]
    avatar = (data.get("avatar") or "🙂").strip()[:4]
    bio = (data.get("bio") or "").strip()[:120]
    if not name:
        return jsonify({"error": "Name is required."}), 400

    state = get_state()
    state["persona"] = {"name": name, "avatar": avatar, "bio": bio}
    save_state(state)
    return jsonify(public_state(state))


@app.route("/api/fandom", methods=["POST"])
def api_fandom():
    data = request.get_json(force=True) or {}
    fandom_id = data.get("fandom_id")
    if fandom_id not in FANDOMS:
        return jsonify({"error": "Unknown fandom."}), 400

    state = get_state()
    if not state["persona"]:
        return jsonify({"error": "Create a persona first."}), 400

    state["fandom_id"] = fandom_id
    seed_posts(state)
    save_state(state)
    return jsonify(public_state(state))


@app.route("/api/post", methods=["POST"])
def api_post():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()[:280]
    if not text:
        return jsonify({"error": "Post can't be empty."}), 400

    state = get_state()
    if not state["persona"] or not state["fandom_id"]:
        return jsonify({"error": "Finish onboarding first."}), 400
    if state["energy"] < POST_ENERGY_COST:
        return jsonify({"error": "Not enough energy.", "code": "no_energy"}), 400

    state["energy"] -= POST_ENERGY_COST
    category = classify_post(text)
    state["clout"] += clout_delta(category)

    tier = tier_for(state["clout"])
    comments, likes = react_to_post(state["fandom_id"], state["persona"]["name"], category, tier["label"])

    post = {
        "id": secrets.token_hex(6),
        "author": state["persona"]["name"],
        "avatar": state["persona"]["avatar"],
        "is_user": True,
        "text": text,
        "category": category,
        "likes": likes,
        "comments": comments,
        "ts": time.time(),
    }
    state["posts"].insert(0, post)
    state["posts"] = state["posts"][:MAX_POSTS_STORED]
    save_state(state)
    return jsonify(public_state(state))


@app.route("/api/energy/watch_ad", methods=["POST"])
def api_watch_ad():
    state = get_state()
    gained = random.randint(10, 25)
    state["energy"] = min(state["max_energy"], state["energy"] + gained)
    save_state(state)
    resp = public_state(state)
    resp["gained"] = gained
    return jsonify(resp)


@app.route("/api/energy/coffee", methods=["POST"])
def api_coffee():
    # Simulated in-app purchase - no real payment is processed anywhere here.
    state = get_state()
    state["energy"] = min(state["max_energy"], state["energy"] + 20)
    save_state(state)
    return jsonify(public_state(state))


@app.route("/api/premium", methods=["POST"])
def api_premium():
    data = request.get_json(force=True) or {}
    state = get_state()
    state["premium"] = bool(data.get("premium"))
    state["max_energy"] = PREMIUM_MAX_ENERGY if state["premium"] else DEFAULT_MAX_ENERGY
    state["energy"] = state["max_energy"]
    save_state(state)
    return jsonify(public_state(state))


@app.route("/api/reset", methods=["POST"])
def api_reset():
    session["game"] = default_state()
    session.modified = True
    return jsonify(public_state(session["game"]))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=True)
