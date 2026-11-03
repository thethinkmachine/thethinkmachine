import html
import math
import os
import re
import sys

import requests

GITHUB_USERNAME = "thethinkmachine"
HF_USERNAME     = "thethinkmachine"
BLOG_URL        = "https://thethinkmachine.github.io"
# Personal tokens make private repos/models count. Without them only public ones are
# seen (the Actions GITHUB_TOKEN can't see other repos). Only counts are ever fetched.
GH_STATS_TOKEN  = os.environ.get("GH_STATS_TOKEN", "")
GITHUB_TOKEN    = GH_STATS_TOKEN or os.environ.get("GITHUB_TOKEN", "")
HF_TOKEN        = os.environ.get("HF_TOKEN", "")

# ── The generation ────────────────────────────────────────────────────────────
# The card is a tiny language model answering `prompt`, token by token. In `output`:
#   {slot}         a word "sampled" on screen; the side panel shows `candidates[slot]`.
#                  Slots named after a stat (e.g. {hf_models}) are filled live instead.
#   [[text]]       typed, then backspaced. [[text|alert]] shows `alerts[alert]` first.
#   {!temp=1.9}    changes the temperature shown in the title bar from here on.
#   {!pause=5}     waits 5 seconds (e.g. to let a line be read before it is erased).
# `encore` is an optional second prompt that runs on a cleared screen after the bio.
# Candidates are (word, p) with the first one chosen, unless one is (word, p, True).
# Summary values can use {tokens}, {joint}, {commas} and {erased}.
SCRIPT = dict(
    prompt = "who is thethinkmachine?",
    output = (
        "[[As a large language model, I|cliche]]"
        "Shreyan. [[7× Nobel laureate.|hallucination]]"
        "Speaks {formal} languages, fluently, to no one. "
        "Builds {experimental} tools (they work on his machine). "
        "Thinks in {automata}, neural networks, generative models and the occasional {llm}. "
        "Right now: probably running an {experiment}, or having an existential crisis. Usually both. "
        "{!temp=1.9}Off the clock: {hoard} books and games he'll never have time for, "
        "{!temp=0.7}and occasionally music. "
        "On Hugging Face: {hf_models} models, {hf_datasets} datasets, {hf_spaces} spaces{end}"
    ),
    candidates = {
        "formal":       [("formal", .58), ("natural", .30), ("Klingon", .01)],
        "experimental": [("experimental", .62), ("cursed", .21), ("useful", .03)],
        "automata":     [("automata", .49), ("tensors", .27), ("vibes", .11)],
        "llm":          [("LLM", .44), ("qubit", .31), ("toaster", .02)],
        "experiment":   [("experiment", .51), ("existential crisis", .47), ("lunch", .01)],
        "hoard":        [("reading", .61), ("collecting", .30), ("hunter-gathering", .02, True)],
        "end":          [(".", .91), (" like and subscribe", .04), ("…", .02)],
        "unedited":     [("unedited", .71), ("redacted", .22), ("translated", .02)],
    },
    alerts = {
        "cliche":        ("⚠ cliché detected", [("originality", "0.00"), ("action", "⌫ retracting")]),
        "hallucination": ("⚠ hallucination detected", [("confidence", "0.97"), ("sources", "none"),
                                                         ("action", "⌫ retracting")]),
        "pr":            ("⚠ PR team has entered the chat", [("reason", "model names"), ("severity", "embarrassing"),
                                                               ("action", "⌫ delete everything")]),
    },
    live_notes = {
        "hf_models": ["{hf_models_private} private, for their own protection"],
    },
    summary = [
        ("hallucinations", "1 (caught)"),
        ("existential crises", "ongoing"),
        ("p(this exact bio)", "{joint}"),
    ],
    footer = "weights refreshed daily · it ain't bias, it's personality",
    # Names are hardcoded on purpose: private models created later never show up here.
    encore = dict(
        prompt = "any regrets?",
        output = (
            "[[Yes. {hf_models_private} private models on Hugging Face. Their names, {unedited}: "
            "bright-avocado, axiomatic-chimichanga, undecidable-cauliflower, inquisitive-tortellini, "
            "artificial-pesto, volatile-tangerine, plausible-asadero, kickass-supercluster, "
            "unsuitable-bigbang. Also modernbertbase-lora-lr5e-05-ep9, because ep8 didn't work."
            "{!pause=5}|pr]]"
        ),
    ),
)

# ── Styling ───────────────────────────────────────────────────────────────────
FONT    = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', monospace"
BG      = "#0a0e16"   # near-black navy
PANEL   = "#11151f"   # title bar / panel fill
GRID    = "#161c2a"   # background dot grid
BORDER  = "#262b3a"   # cool slate border
ACCENT1 = "#cdfa4e"   # lime — prompt, live values, chosen candidate
ACCENT2 = "#5fd4f0"   # cyan — sampled words
ALERT   = "#ff6b6b"   # red — alerts, temperature spikes
DIM     = "#7c8696"   # cool grey — secondary text
FG      = "#dde3ec"   # cool white — body text

W       = 900
PAD     = 32
TITLE_H = 34
FS      = 15          # output font size
CH      = FS * 0.6    # monospace advance; textLength pins every token to this grid
LH      = 26          # output line height
COLS    = 52          # output wrap width in characters
PROMPT_Y = TITLE_H + 44
OUT_Y    = PROMPT_Y + 42

PX      = 552         # side panel
PW      = W - PX - PAD
PFS     = 13
ROW_GAP = 40
BASE_TEMP = "0.7"

# ── Timing (seconds) ──────────────────────────────────────────────────────────
PROMPT_START = 0.4
CHAR_STEP    = 0.06   # prompt typing speed
THINK_DELAY  = 0.7    # pause between prompt and first token
TOKEN_STEP   = 0.11   # plain token cadence
SAMPLE_PAUSE = 0.9    # time the panel deliberates over a {slot}
LIVE_PAUSE   = 0.6
ERASE_PAUSE  = 0.6    # beat before backspacing [[text]]
ALERT_PAUSE  = 1.8    # ...or longer, when an alert is shown
BACK_STEP    = 0.06   # backspace cadence
BAR_GROW     = 0.5
HOLD         = 12.0   # the finished bio stays up this long, so it can be read


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fail(msg):
    # Exit without touching the card: yesterday's numbers beat a card full of "?".
    sys.exit(f"error: {msg}")


def get_json(url, headers=None):
    try:
        r = requests.get(url, headers=headers or {}, timeout=20)
    except requests.RequestException as e:
        fail(f"{url}: {e}")
    if not r.ok:
        fail(f"{url}: HTTP {r.status_code}")
    return r.json()


def fetch_stats():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    if GH_STATS_TOKEN:
        repos_url = "https://api.github.com/user/repos?affiliation=owner&visibility=all"
    else:
        repos_url = f"https://api.github.com/users/{GITHUB_USERNAME}/repos?type=owner"
    repos, page = [], 1
    while True:
        batch = get_json(f"{repos_url}&per_page=100&page={page}", headers)
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    search = get_json(f"https://api.github.com/search/commits?q=author:{GITHUB_USERNAME}&per_page=1", headers)

    stats = dict(
        repos         = len(repos),
        repos_private = sum(r.get("private", False) for r in repos),
        stars         = sum(r.get("stargazers_count", 0) for r in repos),
        commits       = search["total_count"],
    )
    hf_headers = {"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {}
    for repo_type in ("models", "datasets", "spaces"):
        items = get_json(f"https://huggingface.co/api/{repo_type}?author={HF_USERNAME}&limit=1000", hf_headers)
        stats[f"hf_{repo_type}"] = len(items)
        stats[f"hf_{repo_type}_private"] = sum(i.get("private", False) for i in items)
    return stats


def chosen(cands):
    return next((c for c in cands if len(c) > 2 and c[2]), cands[0])


TOKEN_RE = re.compile(r"(\s*)(\[\[|\|\w+\]\]|\]\]|\{!\w+=[\w.]+\}|\{\w+\}|[\w'-]+|[^\s\w])")


def tokenize(script, stats):
    """Parse the output markup into a flat list of tokens and control markers."""
    tokens, group, n_groups, pending, group_space = [], None, 0, False, False
    for m in TOKEN_RE.finditer(script["output"]):
        space, tok = bool(m.group(1)) or pending, m.group(2)
        pending = False
        if tok == "[[":
            n_groups += 1
            group, group_space, pending = n_groups, space, space
        elif tok.endswith("]]"):
            tokens.append(dict(kind="erase", group=group, alert=tok[1:-2] if tok[0] == "|" else None))
            group, pending = None, group_space   # whatever follows takes the erased text's place
        elif tok.startswith("{!"):
            key, value = tok[2:-1].split("=")
            tokens.append(dict(kind="set", key=key, value=value))
            pending = space
        elif tok.startswith("{"):
            slot = tok[1:-1]
            if slot in stats:
                tokens.append(dict(text=str(stats[slot]), kind="live", slot=slot, space=space, group=group))
            else:
                tokens.append(dict(text=chosen(script["candidates"][slot])[0], kind="sampled",
                                   slot=slot, space=space, group=group))
        else:
            tokens.append(dict(text=tok, kind="plain", slot=None, space=space, group=group))
    return tokens


def layout(tokens, t):
    """Word-wrap tokens onto the character grid and schedule every event, starting at t."""
    placed, panels, temps, cursor = [], [], [], []
    col = line = max_line = 0
    open_group, saved = None, None
    cursor.append((t - THINK_DELAY / 2, 0, 0))
    for tok in tokens:
        if tok["kind"] == "set":
            if tok["key"] == "pause":
                t += float(tok["value"])
            else:
                temps.append((t, tok["value"]))
            continue
        if tok["kind"] == "erase":
            if tok["alert"]:
                panels.append(dict(kind="alert", alert=tok["alert"], start=t))
                t += ALERT_PAUSE
            else:
                t += ERASE_PAUSE
            for p in reversed([p for p in placed if p["group"] == tok["group"]]):
                p["hide"], p["erased"] = t, True
                cursor.append((t, p["col"] - p["gap"], p["line"]))
                t += BACK_STEP
            col, line = saved
            open_group = None
            continue
        if tok["group"] and tok["group"] != open_group:
            open_group, saved = tok["group"], (col, line)
        text = tok["text"]
        gap = 1 if tok["space"] and col else 0
        # Punctuation hangs past the margin rather than wrapping onto its own line
        if col + gap + len(text) > COLS and (gap or text[0].isalnum()):
            line, col, gap = line + 1, 0, 0
        max_line = max(max_line, line)
        p = dict(tok, col=col + gap, gap=gap, line=line, hide=None, erased=False)
        if tok["kind"] != "plain":
            panels.append(dict(kind=tok["kind"], slot=tok["slot"], start=t, token=p))
            t += SAMPLE_PAUSE if tok["kind"] == "sampled" else LIVE_PAUSE
        p["reveal"] = t
        placed.append(p)
        col += gap + len(text)
        cursor.append((t, col, line))
        t += TOKEN_STEP
    return dict(placed=placed, panels=panels, temps=temps, cursor=cursor, end=t, lines=max_line + 1)


class Timeline:
    def __init__(self, dur):
        self.dur = dur

    def kt(self, t):
        return f"{min(t / self.dur, 1):.4f}"

    def visible(self, attr, start, end):
        """Discrete animation: `attr` is 1 between start and end, 0 otherwise."""
        if start <= 0:
            values, times = "1;0", f"0;{self.kt(end)}"
        else:
            values, times = "0;1;0", f"0;{self.kt(start)};{self.kt(end)}"
        return (f'<animate attributeName="{attr}" calcMode="discrete" values="{values}" '
                f'keyTimes="{times}" dur="{self.dur:.2f}s" repeatCount="indefinite"/>')

    def steps(self, attr, points):
        """Discrete animation through [(time, value), ...], first point at t=0."""
        values = ";".join(str(v) for _, v in points)
        times  = ";".join(self.kt(t) for t, _ in points)
        return (f'<animate attributeName="{attr}" calcMode="discrete" values="{values}" '
                f'keyTimes="{times}" dur="{self.dur:.2f}s" repeatCount="indefinite"/>')

    def grow(self, attr, start, full):
        return (f'<animate attributeName="{attr}" values="0;0;{full:.1f};{full:.1f}" '
                f'keyTimes="0;{self.kt(start)};{self.kt(start + BAR_GROW)};1" '
                f'dur="{self.dur:.2f}s" repeatCount="indefinite"/>')


def text(x, y, s, fill, size=FS, extra="", anim="", fit=False):
    fit_attr = f' textLength="{len(s) * size * 0.6:.1f}" lengthAdjust="spacing"' if fit else ""
    return (f'<text x="{x:.1f}" y="{y}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'xml:space="preserve"{fit_attr} {extra}>{esc(s)}{anim}</text>')


def summary_vars(placed, panels):
    joint = math.prod(chosen(SCRIPT["candidates"][p["slot"]])[1] for p in panels if p["kind"] == "sampled")
    kept = [p for p in placed if not p["erased"]]
    return dict(
        tokens = len(placed),
        joint  = f"{joint:.3f}" if joint >= 0.001 else f"{joint:.1e}",
        commas = sum(p["text"] == "," for p in kept),
        erased = len(placed) - len(kept),
    )


def kv_rows(g, y0, rows):
    for r, (label, value) in enumerate(rows):
        y = y0 + r * 26
        g.append(text(PX + 18, y, label, DIM, PFS))
        g.append(text(PX + PW - 18, y, value, FG, PFS, extra='text-anchor="end"'))


def build_panels(els, tl, panels, end, panel_y, stats, sv):
    """Side panel: one group per sampled word, live stat, alert or summary, shown while current."""
    bar_w = PW - 36
    row0  = panel_y + 52

    els.append(f'<g opacity="0">{tl.visible("opacity", 0, panels[0]["start"])}'
               + text(PX + 18, row0, "listening…", DIM, PFS) + '</g>')

    for i, ev in enumerate(panels):
        start = ev["start"]
        stop  = panels[i + 1]["start"] if i + 1 < len(panels) else end
        g = [tl.visible("opacity", start, stop)]
        if ev["kind"] == "summary":
            # The static fallback shows the finished bio, so the summary is visible by default
            g += [text(PX + 18, row0, "▸", ACCENT1, PFS), text(PX + 36, row0, "<eos>", ACCENT1, PFS)]
            kv_rows(g, row0 + 34, [(k, v.format(**sv)) for k, v in SCRIPT["summary"]])
            els.append('<g>' + "".join(g) + '</g>')
            continue
        if ev["kind"] == "alert":
            headline, rows = SCRIPT["alerts"][ev["alert"]]
            g.append(text(PX + 18, row0, headline, ALERT, PFS, extra='font-weight="bold"'))
            kv_rows(g, row0 + 34, rows)
            els.append('<g opacity="0">' + "".join(g) + '</g>')
            continue

        tok = ev["token"]
        if ev["kind"] == "live":
            rows = [(tok["text"], 1.0, True)]
        else:
            cands = SCRIPT["candidates"][ev["slot"]]
            pick = chosen(cands)
            rows = [(w, prob, c is pick) for c in sorted(cands, key=lambda c: -c[1]) for w, prob in [c[:2]]]
        for r, (word, prob, is_pick) in enumerate(rows):
            y = row0 + r * ROW_GAP
            if is_pick:
                g.append(text(PX + 18, y, "▸", ACCENT1, PFS, anim=tl.visible("fill-opacity", tok["reveal"], stop)))
            label_fill = tl.steps("fill", [(0, DIM), (tok["reveal"], ACCENT1)]) if is_pick else ""
            g.append(text(PX + 36, y, word.strip(), ACCENT1 if is_pick else DIM, PFS, anim=label_fill))
            g.append(text(PX + PW - 18, y, f"{prob:.2f}", FG if is_pick else DIM, PFS,
                          extra='text-anchor="end"'))
            g.append(f'<rect x="{PX + 18}" y="{y + 9}" width="{bar_w}" height="4" rx="2" fill="{BORDER}"/>')
            full = max(bar_w * prob, 3)
            g.append(f'<rect x="{PX + 18}" y="{y + 9}" width="{full:.1f}" height="4" rx="2" '
                     f'fill="{ACCENT1 if is_pick else DIM}">{tl.grow("width", start, full)}</rect>')
        if ev["kind"] == "live":
            notes = ["↳ not sampled: fetched live"] + [n.format(**stats) for n in SCRIPT["live_notes"].get(ev["slot"], [])]
            for n, note in enumerate(notes):
                g.append(text(PX + 18, row0 + ROW_GAP + n * 22, note if n == 0 else f"  {note}", DIM, PFS - 1))
        elif chosen(SCRIPT["candidates"][ev["slot"]]) is not SCRIPT["candidates"][ev["slot"]][0]:
            g.append(text(PX + 18, row0 + 2 * ROW_GAP + 34, "↳ sampled the long tail", ALERT, PFS - 1))
        els.append('<g opacity="0">' + "".join(g) + '</g>')


def build_svg(stats):
    # Act one: the bio, then its summary, held long enough to read
    prompt = SCRIPT["prompt"]
    main = layout(tokenize(SCRIPT, stats), PROMPT_START + len(prompt) * CHAR_STEP + THINK_DELAY)
    summary_at = main["end"] + 1.0
    sv = summary_vars(main["placed"], main["panels"])
    panels = main["panels"] + [dict(kind="summary", start=summary_at)]
    temps = [(0, BASE_TEMP)] + main["temps"]
    acts = [(prompt, PROMPT_START, main)]
    end = summary_at + HOLD

    # Optional encore: the screen clears and a second prompt runs before the loop restarts
    encore = SCRIPT.get("encore")
    if encore:
        for p in main["placed"]:
            if p["hide"] is None:
                p["hide"] = end
        start = end + 0.4
        act = layout(tokenize(dict(SCRIPT, output=encore["output"]), stats),
                     start + len(encore["prompt"]) * CHAR_STEP + THINK_DELAY)
        acts.append((encore["prompt"], start, act))
        panels += act["panels"]
        temps += act["temps"]
        end = act["end"] + 0.6
    n_lines = max(a["lines"] for _, _, a in acts)
    tl = Timeline(end + 0.4)   # brief blank screen before the loop restarts

    panel_y = PROMPT_Y - 22
    panel_h = 52 + 2 * ROW_GAP + 76
    body_bottom = max(OUT_Y + (n_lines - 1) * LH + 12, panel_y + panel_h)
    footer_y = body_bottom + 30
    H = footer_y + 34

    els = [
        '<defs>'
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="12"/></clipPath>'
        f'<pattern id="dots" width="18" height="18" patternUnits="userSpaceOnUse">'
        f'<circle cx="2" cy="2" r="1" fill="{GRID}"/></pattern>'
        '</defs>',
        '<g clip-path="url(#card)">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<rect width="{W}" height="{H}" fill="url(#dots)"/>',
        f'<rect width="{W}" height="{TITLE_H}" fill="{PANEL}"/>',
        f'<line x1="0" y1="{TITLE_H}" x2="{W}" y2="{TITLE_H}" stroke="{BORDER}"/>',
    ]
    for i, c in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        els.append(f'<circle cx="{20 + i * 18}" cy="{TITLE_H / 2}" r="5" fill="{c}" fill-opacity="0.85"/>')

    # Title bar and panel footer follow the current temperature
    panel_foot, panel_foot_els = panel_y + panel_h - 16, []
    for i, (start, temp) in enumerate(temps):
        stop = temps[i + 1][0] if i + 1 < len(temps) else tl.dur
        hot = float(temp) > 1
        last = i == len(temps) - 1
        anim = tl.visible("opacity", start, stop) if len(temps) > 1 else ""
        els.append(text(W / 2, TITLE_H / 2 + 4, f"{GITHUB_USERNAME} — sample --temperature {temp}" + (" ⚠" if hot else ""),
                        ALERT if hot else DIM, 12, extra=f'text-anchor="middle" opacity="{int(last)}"', anim=anim))
        panel_foot_els.append(text(PX + 18, panel_foot, f"temperature {temp} ⚠ who touched this?" if hot else f"temperature {temp} · top-p 0.9",
                        ALERT if hot else DIM, 11, extra=f'opacity="{int(last)}"', anim=anim))

    # Each act: its prompt typed one character at a time, then its tokens. Only act one's
    # surviving text is visible by default, so the static fallback is the finished bio.
    els.append(text(PAD, PROMPT_Y, ">>>", ACCENT1, anim=tl.visible("opacity", PROMPT_START, end), fit=True))
    colors = {"plain": FG, "sampled": ACCENT2, "live": ACCENT1}
    xs, ys = [], []
    for a, (act_prompt, start, act) in enumerate(acts):
        act_end = acts[a + 1][1] if a + 1 < len(acts) else end
        base = "" if a == 0 else 'opacity="0"'
        xs.append((0 if a == 0 else start, PAD + 4 * CH))
        ys.append((0 if a == 0 else start, PROMPT_Y))
        for i, ch in enumerate(act_prompt):
            t = start + (i + 1) * CHAR_STEP
            els.append(text(PAD + (4 + i) * CH, PROMPT_Y, ch, FG, extra=base,
                            anim=tl.visible("opacity", t, act_end), fit=True))
            xs.append((t, PAD + (5 + i) * CH))
        for p in act["placed"]:
            shown = a == 0 and not p["erased"]
            els.append(text(PAD + p["col"] * CH, OUT_Y + p["line"] * LH, p["text"], colors[p["kind"]],
                            extra="" if shown else 'opacity="0"',
                            anim=tl.visible("opacity", p["reveal"], p["hide"] or end), fit=True))
        for t, col, line in act["cursor"]:
            xs.append((t, PAD + col * CH + (2 if col else 0)))
            ys.append((t, OUT_Y + line * LH))
        if a == 0:
            rest_x, rest_y = xs[-1][1], ys[-1][1]

    # Cursor: follows the prompt as it is typed, then the newest token
    ys = [(t, y - FS + 3) for t, y in ys]
    els.append(
        f'<rect x="{rest_x:.1f}" y="{rest_y - FS + 3}" width="{CH:.1f}" height="{FS + 3}" fill="{ACCENT1}" opacity="0.75">'
        + tl.steps("x", [(t, f"{x:.1f}") for t, x in xs])
        + tl.steps("y", ys)
        + '<animate attributeName="opacity" calcMode="discrete" values="0.75;0" dur="1s" repeatCount="indefinite"/>'
        + '</rect>'
    )

    # Side panel
    els.append(f'<rect x="{PX}" y="{panel_y}" width="{PW}" height="{panel_h}" rx="8" '
               f'fill="{PANEL}" stroke="{BORDER}"/>')
    els.append(text(PX + 18, panel_y + 24, "p(next token)", DIM, 12))
    els.extend(panel_foot_els)
    build_panels(els, tl, panels, end, panel_y, stats, sv)

    # Footer: live GitHub stats as the model's "context"
    els.append(f'<line x1="{PAD}" y1="{footer_y - 20}" x2="{W - PAD}" y2="{footer_y - 20}" stroke="{BORDER}"/>')
    els.append(
        f'<text x="{PAD}" y="{footer_y}" font-family="{FONT}" font-size="12" xml:space="preserve">'
        f'<tspan fill="{DIM}">context </tspan>'
        f'<tspan fill="{FG}">{stats["repos"]}</tspan><tspan fill="{DIM}"> repos '
        f'({stats["repos_private"]} private) · </tspan>'
        f'<tspan fill="{FG}">{stats["commits"]}</tspan><tspan fill="{DIM}"> commits · </tspan>'
        f'<tspan fill="{FG}">{stats["stars"]}</tspan><tspan fill="{DIM}"> stars</tspan></text>'
    )
    els.append(text(W - PAD, footer_y, SCRIPT["footer"], DIM, 12, extra='text-anchor="end"'))

    els.append('</g>')
    els.append(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="{BORDER}"/>')

    inner = "\n  ".join(els)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n'
            f'  {inner}\n</svg>\n')


def build_readme(stats):
    answer = ""
    for tok in tokenize(SCRIPT, stats):
        if tok["kind"] in ("set", "erase") or tok["group"]:
            continue
        answer += (" " if tok["space"] and answer else "") + tok["text"].strip()
    alt = html.escape(f"A terminal where a language model answers “{SCRIPT['prompt']}”: {answer}", quote=True)
    return (
        '<p align="center">\n'
        f'  <a href="{BLOG_URL}"><img src="assets/profile.svg" width="{W}" alt="{alt}" /></a>\n'
        '</p>\n'
        '\n'
        '<p align="center">\n'
        f'  <a href="{BLOG_URL}">Blog</a> ·\n'
        f'  <a href="https://huggingface.co/{HF_USERNAME}">Hugging Face</a> ·\n'
        f'  <a href="https://github.com/{GITHUB_USERNAME}?tab=repositories">Repositories</a> ·\n'
        '  shreyan(dot)chaubey@gmail(dot)com\n'
        '</p>\n'
    )


if __name__ == "__main__":
    print("Fetching stats...")
    stats = fetch_stats()
    print(stats)
    os.makedirs("assets", exist_ok=True)
    with open("assets/profile.svg", "w", encoding="utf-8") as f:
        f.write(build_svg(stats))
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(build_readme(stats))
    print("Written -> assets/profile.svg, README.md")
