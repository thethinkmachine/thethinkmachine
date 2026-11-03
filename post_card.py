"""The "latest post" card: the blog's notebook entry over its cellular-automaton substrate.

Mirrors thethinkmachine.github.io: same palettes, fonts (embedded, see assets/fonts/OFL.txt),
8px cell grid and the same cycle of automata (a Life-like 2D rule, a 1D elementary rule,
Brian's Brain), precomputed here and played back as SVG animation.
"""
import base64
import hashlib
import json
import pathlib
import random

FONT_DIR = pathlib.Path(__file__).parent / "assets" / "fonts"
METRICS  = json.loads((FONT_DIR / "metrics.json").read_text(encoding="utf-8"))

PALETTES = {  # from the blog's CSS custom properties; cell alphas nudged up for a small card
    "dark": dict(card="#15141a", ink="#ece4cd", ink2="#a9a08a", ink3="#978e79", ink4="#7c745f",
                 accent="#d0a02a", ink_rgb="232,223,200",
                 gold="208,160,42", gold_a=.26, blue="120,150,180", blue_a=.22),
    "light": dict(card="#f6f2e9", ink="#1c1a15", ink2="#5a5347", ink3="#6c6557", ink4="#948b78",
                  accent="#9a6a10", ink_rgb="28,26,21",
                  gold="154,106,16", gold_a=.18, blue="150,170,195", blue_a=.16),
}

W, PAD  = 900, 30             # as wide as the terminal card above it
TEXT_W  = W - 2 * PAD - 34     # leaves room for the arrow
CELL    = 8                    # the blog's grid: 8px pitch, 7px cells
STEP    = 0.115                # ...and its tick
STEPS   = 48                   # generations per automaton before moving on

# The blog also runs Day & Night, but from a sparse soup it dies out at once (and dense, it buries the text)
RULES_2D = {"Conway": ({3}, {2, 3}), "HighLife": ({3, 6}, {2, 3})}
RULES_1D = [18, 22, 30, 54, 60, 90, 102, 110, 150, 184]
ROMAN    = "I II III IV V VI VII VIII IX X XI XII".split()


# ── Automata ──────────────────────────────────────────────────────────────────
def neighbours(grid, cols, rows, x, y, state=1):
    return sum(grid[(y + dy) % rows][(x + dx) % cols] == state
               for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy)


def run_life(rng, cols, rows, born, survive):
    grid = [[int(rng.random() < .1) for _ in range(cols)] for _ in range(rows)]
    frames = []
    for _ in range(STEPS):
        frames.append(grid)
        grid = [[int(neighbours(grid, cols, rows, x, y) in (survive if grid[y][x] else born))
                 for x in range(cols)] for y in range(rows)]
    return frames


def run_brain(rng, cols, rows):
    # 1 = firing, 2 = refractory (drawn fainter), 0 = ready: fires with exactly two firing neighbours
    grid = [[int(rng.random() < .07) for _ in range(cols)] for _ in range(rows)]
    frames = []
    for _ in range(STEPS):
        frames.append(grid)
        grid = [[2 if c == 1 else 0 if c == 2 else int(neighbours(grid, cols, rows, x, y) == 2)
                 for x, c in enumerate(row)] for y, row in enumerate(grid)]
    return frames


def run_1d(rng, cols, rule):
    """Generations of an elementary rule. As on the blog, each new one enters at the top."""
    row = [int(rng.random() < .04) for _ in range(cols)]
    row[cols // 2] = 1
    gens = []
    for _ in range(STEPS):
        gens.append(row)
        row = [rule >> (row[x - 1] << 2 | row[x] << 1 | row[(x + 1) % cols]) & 1 for x in range(cols)]
    return gens


# ── Drawing ───────────────────────────────────────────────────────────────────
def cell_paths(cells, pal):
    """Cells as dashed strokes: one subpath per horizontal run, dashes 7 on / 1 off."""
    layers = {}
    for x, y, state in cells:
        blue = (x * 7 + y * 13) % 19 == 0   # the blog tints a sparse lattice of cells blue-grey
        layers.setdefault((blue, state), {}).setdefault(y, []).append(x)
    out = []
    for (blue, state), rows in sorted(layers.items()):
        d = []
        for y, xs in rows.items():
            xs.sort()
            start = prev = xs[0]
            for x in xs[1:] + [None]:
                if x is not None and x == prev + 1:
                    prev = x
                    continue
                d.append(f"M{start * CELL} {y * CELL}h{(prev - start + 1) * CELL}")
                if x is not None:
                    start = prev = x
        rgb, alpha = (pal["blue"], pal["blue_a"]) if blue else (pal["gold"], pal["gold_a"])
        alpha *= .45 if state == 2 else 1
        out.append(f'<path d="{"".join(d)}" stroke="rgba({rgb},{alpha:.3f})"/>')
    return "".join(out)


def grid_cells(grid):
    return [(x, y, c) for y, row in enumerate(grid) for x, c in enumerate(row) if c]


class Clock:
    def __init__(self, dur):
        self.dur = dur

    def kt(self, t):
        return f"{min(t / self.dur, 1):.4f}"

    def visible(self, start, end):
        values, times = ("1;0", f"0;{self.kt(end)}") if start <= 0 else ("0;1;0", f"0;{self.kt(start)};{self.kt(end)}")
        return (f'<animate attributeName="opacity" calcMode="discrete" values="{values}" '
                f'keyTimes="{times}" dur="{self.dur:.2f}s" repeatCount="indefinite"/>')


def text_width(s, font, size, tracking=0.0):
    adv = METRICS[font]
    return sum(adv.get(ch, .5) for ch in s) * size + tracking * size * len(s)


def wrap(s, font, size, width, max_lines):
    lines, line = [], ""
    for word in s.split():
        trial = f"{line} {word}".strip()
        if line and text_width(trial, font, size) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        while text_width(lines[-1] + "…", font, size) > width:
            lines[-1] = lines[-1].rsplit(" ", 1)[0]
        lines[-1] = lines[-1].rstrip(",.;:") + "…"
    return lines


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def font_faces():
    faces = []
    for name, family, style in [("cormorant-500", "Cormorant", "normal"), ("garamond-400", "Garamond", "normal"),
                                ("garamond-400-italic", "Garamond", "italic"), ("inter-500", "Inter", "normal")]:
        data = base64.b64encode((FONT_DIR / f"{name}.woff2").read_bytes()).decode()
        faces.append(f"@font-face{{font-family:'{family}';font-style:{style};"
                     f"src:url(data:font/woff2;base64,{data}) format('woff2')}}")
    return "".join(faces)


def build_post_card(post, theme):
    """post: title, description, topic, number, date (datetime), link. theme: 'dark' | 'light'."""
    pal = PALETTES[theme]
    # Seeded by the post, so the universe only changes when a new post does
    rng = random.Random(hashlib.sha256(post["link"].encode()).digest())

    # Text layout first: the card is as tall as its content
    title = wrap(post["title"], "cormorant-500", 30, TEXT_W, 2)
    desc  = wrap(post["description"], "garamond-400", 16, TEXT_W, 2)
    y_kicker = PAD + 14
    y_title  = y_kicker + 46
    y_desc   = y_title + (len(title) - 1) * 34 + 30
    y_foot   = y_desc + (len(desc) - 1) * 23 + 40
    H = y_foot + PAD - 2
    cols, rows = -(-W // CELL), -(-H // CELL)

    # Automata: a Life-like rule, then a 1D rule, then Brian's Brain, as on the blog
    rule_2d = rng.choice(list(RULES_2D))
    rule_1d = rng.choice(RULES_1D)
    modes = [
        (f"{rule_2d} · 2D", "frames", [grid_cells(g) for g in run_life(rng, cols, rows, *RULES_2D[rule_2d])]),
        (f"Rule {rule_1d} · 1D", "scroll", run_1d(rng, cols, rule_1d)),
        ("Brian's Brain · 2D", "frames", [grid_cells(g) for g in run_brain(rng, cols, rows)]),
    ]
    span = STEPS * STEP
    clock = Clock(span * len(modes))

    substrate, labels = [], []
    for m, (label, kind, data) in enumerate(modes):
        t0 = m * span
        if kind == "frames":
            for f, cells in enumerate(data):
                base = 1 if m == 0 and f == 0 else 0   # static fallback: the opening frame
                substrate.append(f'<g opacity="{base}">{clock.visible(t0 + f * STEP, t0 + (f + 1) * STEP)}'
                                 f'{cell_paths(cells, pal)}</g>')
        else:
            # Generation g is drawn g rows above the top edge; the sheet slides down one row per tick
            cells = [(x, -g, 1) for g, row in enumerate(data) for x, c in enumerate(row) if c]
            steps = ";".join(f"0 {f * CELL}" for f in range(STEPS))
            times = ";".join(clock.kt(t0 + f * STEP) for f in range(STEPS))
            substrate.append(
                f'<g opacity="0">{clock.visible(t0, t0 + span)}<g>'
                f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" '
                f'values="0 0;{steps}" keyTimes="0;{times}" dur="{clock.dur:.2f}s" repeatCount="indefinite"/>'
                f'{cell_paths(cells, pal)}</g></g>')
        labels.append((label, t0, t0 + span))

    ink_line = f"rgba({pal['ink_rgb']},.1)"
    meta_style = 'font-family="Inter" font-size="9.5" letter-spacing="1.14"'
    d = post["date"]
    date = f"{d.day}.{ROMAN[d.month - 1]}.{d.year}"

    els = [
        f'<style>{font_faces()}</style>',
        '<defs>'
        f'<clipPath id="c"><rect width="{W}" height="{H}" rx="8"/></clipPath>'
        f'<linearGradient id="scrim" x1="0" x2="1"><stop offset="0" stop-color="{pal["card"]}" stop-opacity=".6"/>'
        f'<stop offset=".7" stop-color="{pal["card"]}" stop-opacity=".15"/>'
        f'<stop offset="1" stop-color="{pal["card"]}" stop-opacity="0"/></linearGradient>'
        '</defs>',
        '<g clip-path="url(#c)">',
        f'<rect width="{W}" height="{H}" fill="{pal["card"]}"/>',
        f'<g fill="none" stroke-width="7" stroke-dasharray="7 1" transform="translate(0 3.5)">{"".join(substrate)}</g>',
        f'<rect width="{W}" height="{H}" fill="url(#scrim)"/>',
        f'<rect x="6.5" y="6.5" width="{W - 13}" height="{H - 13}" rx="3" fill="none" stroke="rgba({pal["ink_rgb"]},.07)"/>',

        # Header: kicker left, entry number / date / topic right
        f'<text x="{PAD}" y="{y_kicker}" font-family="Garamond" font-style="italic" font-size="15" '
        f'fill="{pal["ink3"]}">Latest from the notebook</text>',
        f'<text x="{W - PAD}" y="{y_kicker - 2}" text-anchor="end" {meta_style}>'
        f'<tspan fill="{pal["ink4"]}">Nº {post["number"]:03d}   ·   {esc(date.upper())}   ·   </tspan>'
        f'<tspan fill="{pal["accent"]}">{esc(post["topic"].upper())}</tspan></text>',

        # Title with the blog's accent rule, then the description
        f'<rect x="{PAD - 14}" y="{y_title - 26}" width="2" height="{(len(title) - 1) * 34 + 32}" fill="{pal["accent"]}"/>',
    ]
    for i, line in enumerate(title):
        els.append(f'<text x="{PAD}" y="{y_title + i * 34}" font-family="Cormorant" font-weight="500" '
                   f'font-size="30" fill="{pal["ink"]}">{esc(line)}</text>')
    for i, line in enumerate(desc):
        els.append(f'<text x="{PAD}" y="{y_desc + i * 23}" font-family="Garamond" font-size="16" '
                   f'fill="{pal["ink3"]}">{esc(line)}</text>')

    # Footer: the blog's "Now" field naming the automaton on screen; read link on the right
    els += [
        f'<line x1="{PAD}" y1="{y_foot - 22}" x2="{W - PAD}" y2="{y_foot - 22}" stroke="{ink_line}"/>',
        f'<circle cx="{PAD + 3}" cy="{y_foot - 3.5}" r="3" fill="{pal["accent"]}">'
        '<animate attributeName="opacity" values="1;.25;1" dur="2.4s" repeatCount="indefinite"/></circle>',
        f'<text x="{PAD + 14}" y="{y_foot}" {meta_style} fill="{pal["ink4"]}">NOW</text>',
    ]
    for i, (label, start, end) in enumerate(labels):
        els.append(f'<text x="{PAD + 50}" y="{y_foot}" {meta_style} fill="{pal["ink2"]}" opacity="{int(i == 0)}">'
                   f'{esc(label.upper())}{clock.visible(start, end)}</text>')
    els += [
        f'<text x="{W - PAD}" y="{y_foot + 1}" text-anchor="end" xml:space="preserve">'
        f'<tspan font-family="Garamond" font-style="italic" font-size="16" fill="{pal["ink2"]}">Read the note </tspan>'
        f'<tspan font-family="Cormorant" font-size="22" fill="{pal["accent"]}">→</tspan></text>',
        '</g>',
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="none" stroke="{ink_line}"/>',
    ]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n  '
            + "\n  ".join(els) + "\n</svg>\n")
