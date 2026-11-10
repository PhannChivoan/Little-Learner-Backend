import json
import os

SLUG_INFO = {
    "count-the-critters": {"skin": "sunny", "dark": False, "limit": 8, "layout": "grid", "mascot": "🐰"},
    "abc-safari": {"skin": "grape", "dark": False, "limit": 8, "layout": "grid"},
    "animals-of-cambodia": {"skin": "mint", "dark": False, "limit": 8, "layout": "grid"},
    "balloon-colors": {"skin": "sky", "dark": False, "limit": 8, "layout": "balloon"},
    "memory-farm": {"skin": "lime", "dark": False, "limit": 3, "layout": "grid"},
    "ocean-quiz": {"skin": "deepsea", "dark": True, "limit": 8, "layout": "grid"},
    "space-math-race": {"skin": "space", "dark": True, "limit": 8, "layout": "grid", "race": True},
    "shape-sorter": {"skin": "gold", "dark": False, "limit": 8, "layout": "grid"},
    "khmer-letters": {"skin": "coral", "dark": False, "limit": 8, "layout": "grid"},
    "dino-time": {"skin": "meadow", "dark": False, "limit": 8, "layout": "scene"},
}


def q(kind, text, img="", **extra):
    base = {"type": kind, "q": text, "qk": "", "img": img, "a": [], "ak": [], "c": 0, "t": 20, "p": 500}
    base.update(extra)
    return base


def choice(text, img, right, wrongs, t):
    options = [right] + [w for w in wrongs if w != right][:3]
    return q("quiz", text, img, a=options, ak=[""] * len(options), c=0, t=t)


def count_game(data, secs):
    animals = data["animals"]
    out = []
    for n in range(data["min"], data["max"] + 1):
        animal = animals[n % len(animals)]
        pool = [x for x in (n - 1, n + 1, n + 2, n - 2, n + 3, n + 4, n + 5) if 0 < x < 13 and x != n]
        out.append(choice(f"How many {animal} can you see?", animal * n, str(n), [str(x) for x in pool], secs))
    return out


def abc_game(data, secs):
    pairs = data["pairs"]
    out = []
    for i, (letter, emoji, name) in enumerate(pairs):
        others = [p for p in pairs if p[0] != letter]
        wrong = [f"{o[1]} {o[2]}" for o in (others[(i * 3 + k) % len(others)] for k in range(3))]
        out.append(choice(f"Which animal starts with the letter {letter}?", f"{letter} {letter.lower()}", f"{emoji} {name}", wrong, secs))
    return out


def facts_game(data, secs):
    out = []
    for prompt, right, wrongs, emoji in data["questions"]:
        out.append(choice(prompt, emoji, right, wrongs, secs))
    return out


def balloon_game(data, secs):
    colors = data["colors"]
    out = []
    for i, (name, _) in enumerate(colors):
        others = [c[0] for c in colors if c[0] != name]
        wrong = [others[(i + k) % len(others)] for k in range(4)]
        out.append(q("quiz", f"Pop the {name.upper()} balloon!", "🎈", a=[name] + wrong, ak=[""] * 5, c=0, t=secs))
    return out


def memory_game(data, secs):
    animals = data["animals"]
    return [q("memory", "Find the matching pairs!", "", cards=animals[:n], t=secs) for n in data["pairs"]]


def math_game(data, secs):
    out = []
    k = 0
    for a in range(data["aMin"], data["aMax"] + 1):
        b = data["bMin"] + (a * 3) % (data["bMax"] - data["bMin"] + 1)
        plus = k % 5 != 4
        k += 1
        r = a + b if plus else a
        text = f"{a} + {b} = ?" if plus else f"{a + b} − {b} = ?"
        pool = [x for x in (r - 1, r + 1, r + 2, r - 2, r + 10, r - 10) if x >= 0 and x != r]
        out.append(choice(text, text, str(r), [str(x) for x in pool], secs))
    return out


def shape_game(data, secs):
    shapes = data["shapes"]
    out = []
    for i, (name, emoji) in enumerate(shapes):
        others = [s for s in shapes if s[0] != name]
        pick = [others[(i + k) % len(others)] for k in range(3)]
        out.append(choice("What shape is this?", emoji, name, [s[0] for s in pick], secs))
        out.append(choice(f"Tap the {name.upper()}!", "❓", emoji, [s[1] for s in pick], secs))
    return out


def khmer_game(data, secs):
    letters = data["letters"]
    out = []
    for i, (ch, sound) in enumerate(letters):
        others = [x for x in letters if x[0] != ch]
        out.append(choice("Which sound does this letter make?", ch, sound, [others[(i * 3 + k) % len(others)][1] for k in range(3)], secs))
    return out


def dino_game(data, secs):
    items = data["items"]
    out = []
    for i, (emoji, name) in enumerate(items):
        others = [x for x in items if x[0] != emoji]
        pick = [others[(i + k) % len(others)] for k in range(5)]
        out.append(choice(f"Find the {name}!", "🔍", emoji, [p[0] for p in pick], secs))
        out[-1]["a"] = [emoji] + [p[0] for p in pick]
        out[-1]["ak"] = [""] * 6
    return out


BUILDERS = {
    "count-the-critters": count_game,
    "abc-safari": abc_game,
    "animals-of-cambodia": facts_game,
    "balloon-colors": balloon_game,
    "memory-farm": memory_game,
    "ocean-quiz": facts_game,
    "space-math-race": math_game,
    "shape-sorter": shape_game,
    "khmer-letters": khmer_game,
    "dino-time": dino_game,
}


def convert_builtin_games(conn):
    from .db import now

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "builtin_config.json")
    with open(path, encoding="utf-8") as f:
        defaults = json.load(f)
    owner = conn.execute("SELECT id FROM users ORDER BY id LIMIT 1").fetchone()
    rows = conn.execute("SELECT * FROM games WHERE builtin=1").fetchall()
    for row in rows:
        slug = row["slug"]
        if slug not in BUILDERS:
            continue
        cfg = json.loads(row["config"]) if row["config"] else defaults[slug]
        info = SLUG_INFO[slug]
        questions = BUILDERS[slug](cfg["data"], cfg["secs"])
        settings = {
            "shuffle": True,
            "shuffleAnswers": True,
            "speedBonus": True,
            "music": True,
            "track": "happy",
            "musicUrl": "",
            "layout": info["layout"],
            "race": bool(info.get("race")),
            "limit": info["limit"],
            "dark": info["dark"],
            "hint": cfg.get("hint", ""),
        }
        conn.execute(
            "UPDATE games SET builtin=0, engine='quiz', skin=?, questions=?, config=?, owner_id=?, updated=? WHERE id=?",
            (info["skin"], json.dumps(questions, ensure_ascii=False), json.dumps({"settings": settings}, ensure_ascii=False), owner["id"] if owner else None, now(), row["id"]),
        )
    conn.commit()
