import requests
import os
import datetime

GITHUB_USERNAME = "thethinkmachine"
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")

HF_USERNAME     = "thethinkmachine"

# ── Styling ───────────────────────────────────────────────────────────────────
FONT      = "monospace"
BG        = "#0a0e16"   # near-black navy
BORDER    = "#262b3a"   # cool slate border
ROW_ALT   = "#11151f"   # alternating row bg
ACCENT1   = "#cdfa4e"   # lime green — section headers / keys (Marathon wordmark)
ACCENT2   = "#5fd4f0"   # cyan       — username / highlight
DIM       = "#7c8696"   # cool grey  — secondary text
FG        = "#dde3ec"   # cool white — values

W         = 920
PAD       = 24
HEADER_H  = 50

ROW_H     = 24          # table row height
HDR_H     = 26          # section header row height
FS        = 12          # table font size
KEY_W     = 100         # width of key column inside each table

POEM_FS   = 12          # poem line font size
POEM_LH   = 19          # poem line height

POEM_TITLE  = "Ozymandias"
POEM_AUTHOR = "Percy Bysshe Shelley"
POEM_LINES  = [
    "I met a traveller from an antique land",
    "Who said: Two vast and trunkless legs of stone",
    "Stand in the desert. Near them, on the sand,",
    "Half sunk, a shattered visage lies, whose frown,",
    "And wrinkled lip, and sneer of cold command,",
    "Tell that its sculptor well those passions read",
    "Which yet survive, stamped on these lifeless things,",
    "The hand that mocked them, and the heart that fed:",
    "And on the pedestal these words appear:",
    "‘My name is Ozymandias, king of kings:",
    "Look on my works, ye Mighty, and despair!’",
    "Nothing beside remains. Round the decay",
    "Of that colossal wreck, boundless and bare",
    "The lone and level sands stretch far away.",
]


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def relative_time(iso_ts):
    try:
        dt = datetime.datetime.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
    except (ValueError, TypeError):
        return "?"
    days = (datetime.datetime.now(datetime.timezone.utc) - dt).days
    if days < 1:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days}d ago"
    months = days // 30
    if months < 12:
        return f"{months}mo ago"
    return f"{months // 12}y ago"


def fetch_stats():
    headers = {"Accept": "application/vnd.github+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    def gh(url):
        r = requests.get(url, headers=headers)
        return r.json() if r.ok else {}

    user = gh(f"https://api.github.com/users/{GITHUB_USERNAME}")
    repos, page = [], 1
    while True:
        batch = gh(f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100&page={page}")
        if not batch or not isinstance(batch, list):
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    search = gh(f"https://api.github.com/search/commits?q=author:{GITHUB_USERNAME}&per_page=1")

    # Skip the profile-readme repo itself (named after the user, pushed daily by this script)
    candidates = [r for r in repos if r.get("name") != GITHUB_USERNAME] or repos
    latest = max(candidates, key=lambda r: r.get("pushed_at", ""), default={})

    return dict(
        repos        = user.get("public_repos", "?"),
        stars        = sum(r.get("stargazers_count", 0) for r in repos),
        forks        = sum(r.get("forks_count", 0) for r in repos),
        commits      = search.get("total_count", "?"),
        latest_repo  = latest.get("name", "?"),
        latest_lang  = latest.get("language") or "—",
        latest_stars = latest.get("stargazers_count", 0),
        latest_pushed= relative_time(latest.get("pushed_at")),
    )


def fetch_hf_stats():
    def count(repo_type):
        r = requests.get(f"https://huggingface.co/api/{repo_type}?author={HF_USERNAME}&limit=100")
        return len(r.json()) if r.ok else "?"

    return dict(
        hf_models   = count("models"),
        hf_datasets = count("datasets"),
        hf_spaces   = count("spaces"),
    )


def build_table(els, x, y, table_w, sections):
    """
    Draw a bordered table with section headers and key/value rows.
    sections = [("Section Name", [("Key", "Value"), ...]), ...]
    Returns the y coordinate of the table's bottom edge.
    """
    total_h = sum(HDR_H + ROW_H * len(rows) for _, rows in sections)

    els.append(f'<rect x="{x}" y="{y}" width="{table_w}" height="{total_h}" '
               f'rx="4" fill="none" stroke="{BORDER}" stroke-width="1"/>')

    cy = y
    for sec_name, rows in sections:
        els.append(f'<rect x="{x}" y="{cy}" width="{table_w}" height="{HDR_H}" fill="{ROW_ALT}"/>')
        els.append(f'<line x1="{x}" y1="{cy+HDR_H}" x2="{x+table_w}" y2="{cy+HDR_H}" '
                   f'stroke="{BORDER}" stroke-width="1"/>')
        els.append(
            f'<text x="{x+10}" y="{cy+HDR_H-8}" font-family="{FONT}" font-size="{FS}" '
            f'fill="{ACCENT2}" font-weight="bold" xml:space="preserve">{esc(sec_name)}</text>'
        )
        cy += HDR_H

        for idx_r, (key, val) in enumerate(rows):
            row_bg = BG if idx_r % 2 == 0 else ROW_ALT
            els.append(f'<rect x="{x}" y="{cy}" width="{table_w}" height="{ROW_H}" fill="{row_bg}"/>')
            els.append(f'<line x1="{x}" y1="{cy+ROW_H}" x2="{x+table_w}" y2="{cy+ROW_H}" '
                       f'stroke="{BORDER}" stroke-width="0.5"/>')
            els.append(f'<line x1="{x+KEY_W}" y1="{cy}" x2="{x+KEY_W}" y2="{cy+ROW_H}" '
                       f'stroke="{BORDER}" stroke-width="0.5"/>')
            els.append(
                f'<text x="{x+10}" y="{cy+ROW_H-7}" font-family="{FONT}" font-size="{FS}" '
                f'fill="{ACCENT1}" xml:space="preserve">{esc(key)}</text>'
            )
            els.append(
                f'<text x="{x+KEY_W+10}" y="{cy+ROW_H-7}" font-family="{FONT}" font-size="{FS}" '
                f'fill="{FG}" xml:space="preserve">{esc(val)}</text>'
            )
            cy += ROW_H

    return cy


def build_svg(stats):
    els = []

    left_sections = [
        ("Stack", [
            ("Frameworks", "PyTorch, Transformers, LangChain"),
            ("Tooling",    "scikit-learn, NumPy, Pandas"),
        ]),
        ("Contact", [
            ("Email",  "shreyan(dot)chaubey@gmail(dot)com"),
            ("GitHub", f"github.com/{GITHUB_USERNAME}"),
        ]),
        ("Hugging Face", [
            ("Models",   str(stats["hf_models"])),
            ("Datasets", str(stats["hf_datasets"])),
            ("Spaces",   str(stats["hf_spaces"])),
        ]),
    ]

    right_sections = [
        ("Currently working on", [
            ("Repo",     stats["latest_repo"]),
            ("Language", stats["latest_lang"]),
            ("Stars",    str(stats["latest_stars"])),
            ("Pushed",   stats["latest_pushed"]),
        ]),
        ("GitHub Stats", [
            ("Repos",   str(stats["repos"])),
            ("Stars",   str(stats["stars"])),
            ("Forks",   str(stats["forks"])),
            ("Commits", str(stats["commits"])),
        ]),
    ]

    col_gap = PAD
    table_w = (W - PAD * 2 - col_gap) // 2
    col1_x  = PAD
    col2_x  = PAD + table_w + col_gap
    table_y = HEADER_H + PAD

    def table_h(sections):
        return sum(HDR_H + ROW_H * len(rows) for _, rows in sections)

    tables_bottom = table_y + max(table_h(left_sections), table_h(right_sections))
    poem_divider_y = tables_bottom + PAD
    poem_top = poem_divider_y + PAD
    poem_rows = 3 + len(POEM_LINES)   # title, author, blank gap, then each line
    H = poem_top + poem_rows * POEM_LH + PAD

    # Background + outer border
    els.append(f'<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>')
    els.append(f'<rect width="{W}" height="{H}" rx="10" fill="none" stroke="{BORDER}" stroke-width="1.5"/>')

    # Header: username + sync timestamp, divider below
    els.append(
        f'<text x="{PAD}" y="{PAD+18}" font-family="{FONT}" font-size="16" xml:space="preserve">'
        f'<tspan fill="{ACCENT2}" font-weight="bold">{esc(GITHUB_USERNAME)}</tspan>'
        f'<tspan fill="{DIM}">@github</tspan></text>'
    )
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    els.append(
        f'<text x="{W-PAD}" y="{PAD+18}" font-family="{FONT}" font-size="12" '
        f'fill="{DIM}" text-anchor="end" xml:space="preserve">synced {esc(ts)}</text>'
    )
    els.append(f'<line x1="{PAD}" y1="{HEADER_H}" x2="{W-PAD}" y2="{HEADER_H}" stroke="{BORDER}" stroke-width="1"/>')

    build_table(els, col1_x, table_y, table_w, left_sections)
    build_table(els, col2_x, table_y, table_w, right_sections)

    # Poem section: centered, below the tables
    els.append(f'<line x1="{PAD}" y1="{poem_divider_y}" x2="{W-PAD}" y2="{poem_divider_y}" '
               f'stroke="{BORDER}" stroke-width="1"/>')

    cx = W // 2

    def poem_baseline(row_idx):
        return poem_top + row_idx * POEM_LH + (POEM_LH - 6)

    els.append(
        f'<text x="{cx}" y="{poem_baseline(0)}" font-family="{FONT}" font-size="15" '
        f'fill="{ACCENT2}" font-weight="bold" text-anchor="middle" xml:space="preserve">{esc(POEM_TITLE)}</text>'
    )
    els.append(
        f'<text x="{cx}" y="{poem_baseline(1)}" font-family="{FONT}" font-size="11" '
        f'fill="{DIM}" font-style="italic" text-anchor="middle" xml:space="preserve">{esc(POEM_AUTHOR)}</text>'
    )
    for i, line in enumerate(POEM_LINES):
        els.append(
            f'<text x="{cx}" y="{poem_baseline(3 + i)}" font-family="{FONT}" font-size="{POEM_FS}" '
            f'fill="{FG}" font-style="italic" text-anchor="middle" xml:space="preserve">{esc(line)}</text>'
        )

    inner = "\n  ".join(els)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n  {inner}\n</svg>'


if __name__ == "__main__":
    print("Fetching stats...")
    stats = fetch_stats()
    stats.update(fetch_hf_stats())
    print(stats)
    svg = build_svg(stats)
    os.makedirs("assets", exist_ok=True)
    with open("assets/profile.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("Written -> assets/profile.svg")
