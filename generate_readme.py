import requests
import os
import datetime

GITHUB_USERNAME = "thethinkmachine"
GITHUB_TOKEN    = os.environ.get("GITHUB_TOKEN", "")

INFO = {
    "OS"                   : "Linux, Windows",
    "Host"                 : "Indian Institute of Technology, Madras (IIT-M)",
    "IDE"                  : "VSCode",
    "Languages.Code"       : "Java, Python, JavaScript, TypeScript",
    "Languages.Markup"     : "HTML, CSS, JSON, YAML, TOML, Markdown",
    "Languages.Real"       : "English, Hindi",
    "Hobbies.Software"     : "Building stuff that I find useful",
    "Hobbies.Other"        : "Gaming, Coding, Music",
    "Interests.Subjective" : "QC, DL, RL, LLMs",
    "Interests.Other"      : "Mathematics, Physics and Economics",
    "Contact.Discord"      : "shreyan.c",
    "Contact.Steam"        : "ThinkMachine_",
    "Contact.Xbox"         : "ThinkMachine543",
    "Contact.Other"        : "shreyan.chaubey@gmail(dot)com",
}

ASCII_ART = """      .:-*%@@@@@@@@@:::::::::... .    .......             ..:::::+#=#@@@@@
      ..............  ...........     ......:==:=:.....    ...::::-#@@@@@@
      ........ ...     ..   ..            ..=%@@@@@@@@@%%...:...:::::-@@@@   -@@@@@@@@@.:@@
      .......                           -:.:+@@@@@@@@@@%.:..:.....::.:-*@@       +@.     @@
      .......                       .-**--*@@@@@@@@@@@@%::-... ..:..::@=@@       +@.     @@. -@= :@   @@
      .....                       :+:....:-=+%@@@@@@@@@@@@*=+.   ...::@@@@       +@.     @@   @# @@
      ....                     :*+--===++=--=+-.:%@@@@@#=-:::::: ...::@@@@       +@:     @@   @%  @@@@@.
                              ...:-+%@@@@@@@@@@@=%@@@@+=======-    .:.:-#@
                     .##*    -###*-#@@:  *@@@@@@==**-=+::=%@@@+--: ..::#@@
                    -###*=   .###%+#@@@@@@@@@@#+*@@@@*@=-@@@@-::.  ..%:=@@
                    -####*+. .##%@@@*#@@@@@@@%+@@@@@@@@@@@@@@-+:   .*@=@@@   #@  %@= .@= @@       .*           *@:
                     =####*.  *##@@@@@@@@@@@@@@@@@@@@@@%####+.  ...*@@@@@@       +@.     @@ *@-   =*  .*-.%@   :@:  *-
                      .-*#*:  -##%@@@@@@@@@@@@@%%%%%%@@@@@@@%    ..:%@@@@@       +@.     @@   @*  @@   @%  #@  :@*%=
                         .+-  .:*#@@@@%-::.........:.:-=%@@@:  ..::-@@@@@@       +@.     @@   @#  @@   @#  *@  :@+@@
                         .*+.    .:#@=..*@@@@@@@@@@@@#-..@%:  . .::+@@@@@@      =@@@-   -@@- #@@ :@@* #@@ :@@#-@@@ =@@+
                         :=##.      ...+@@@@@@%###%@@@@-::.       *@@@@@@@
                       .#######*:     ..:-%#%-::.:+@@+-:..  .....:%@@@@@@@
                       -###########=.    ..........:...   ........:=@@@@@@                                    .        .
                          .+###########-..     . ..  :::.  ........:*@@@@@     @@@      @@@                  =@
      .....                    -+################@= .:---:..... ...::#@@@@     @ @@    @ @@   @@:@@   #@-@@  =@+@@@+  @@- :@@=@@@   -@-@@=
      ..............                .=+*#####%@@@= .-----: ..........-%@@@     @  @@ .@  @@    :-@@  @%      =@   @@  :@-  @@   @* #@+===-
      .....................               ......   ::-:-:..............:%@     @   @@@   @@  @@  *@  @@+  :+ =@   @@  :@-  @@   @# :@@   =
      ... ......................          .       .:::::: ........... ...-
      ..... ...  ...................  . ..    .. .::::::..................
      ......  .    ..  . .........     .:.#@%#*-:::::::-::-...-#...  ....."""

# ── Styling ───────────────────────────────────────────────────────────────────
FONT      = "monospace"
BG        = "#0d1117"
BORDER    = "#30363d"
ROW_ALT   = "#161b22"   # alternating row bg
ACCENT1   = "#e8943a"   # orange — section headers / keys
ACCENT2   = "#57c464"   # green  — username / highlight
DIM       = "#8b949e"   # grey   — secondary text
FG        = "#c9d1d9"   # white  — values

ART_LH    = 13
ART_FS    = 10
W         = 1060
PAD       = 22

ROW_H     = 24          # table row height
HDR_H     = 26          # section header row height
FS        = 12          # table font size
KEY_W     = 190         # width of key column inside each table
TITLE_H   = 30          # title bar height

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

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
        b = gh(f"https://api.github.com/users/{GITHUB_USERNAME}/repos?per_page=100&page={page}")
        if not b or not isinstance(b, list): break
        repos.extend(b)
        if len(b) < 100: break
        page += 1
    search = gh(f"https://api.github.com/search/commits?q=author:{GITHUB_USERNAME}&per_page=1")
    return dict(
        repos    = user.get("public_repos","?"),
        stars    = sum(r.get("stargazers_count",0) for r in repos),
        forks    = sum(r.get("forks_count",0)      for r in repos),
        followers= user.get("followers","?"),
        following= user.get("following","?"),
        commits  = search.get("total_count","?"),
    )

def build_table(els, x, y, table_w, sections):
    """
    Draw a bordered table with section headers and key/value rows.
    sections = [("Section Name", [("Key", "Value"), ...]), ...]
    Returns the final y after the table.
    """
    # Count total rows to know full height
    total_h = 0
    for (sec, rows) in sections:
        total_h += HDR_H
        total_h += ROW_H * len(rows)

    # Outer border
    els.append(f'<rect x="{x}" y="{y}" width="{table_w}" height="{total_h}" '
               f'rx="4" fill="none" stroke="{BORDER}" stroke-width="1"/>')

    cy = y
    for idx_s, (sec_name, rows) in enumerate(sections):
        # Section header row
        els.append(f'<rect x="{x}" y="{cy}" width="{table_w}" height="{HDR_H}" '
                   f'fill="{ROW_ALT}" rx="0"/>')
        # Section header border bottom
        els.append(f'<line x1="{x}" y1="{cy+HDR_H}" x2="{x+table_w}" y2="{cy+HDR_H}" '
                   f'stroke="{BORDER}" stroke-width="1"/>')
        els.append(
            f'<text x="{x+10}" y="{cy+HDR_H-8}" font-family="{FONT}" font-size="{FS}" '
            f'fill="{ACCENT1}" font-weight="bold" xml:space="preserve">{esc(sec_name)}</text>'
        )
        cy += HDR_H

        for idx_r, (key, val) in enumerate(rows):
            # Alternate row bg
            if idx_r % 2 == 0:
                els.append(f'<rect x="{x}" y="{cy}" width="{table_w}" height="{ROW_H}" fill="{BG}"/>')
            else:
                els.append(f'<rect x="{x}" y="{cy}" width="{table_w}" height="{ROW_H}" fill="{ROW_ALT}"/>')

            # Row bottom border
            els.append(f'<line x1="{x}" y1="{cy+ROW_H}" x2="{x+table_w}" y2="{cy+ROW_H}" '
                       f'stroke="{BORDER}" stroke-width="0.5"/>')

            # Key column divider
            els.append(f'<line x1="{x+KEY_W}" y1="{cy}" x2="{x+KEY_W}" y2="{cy+ROW_H}" '
                       f'stroke="{BORDER}" stroke-width="0.5"/>')

            # Key text
            els.append(
                f'<text x="{x+10}" y="{cy+ROW_H-7}" font-family="{FONT}" font-size="{FS}" '
                f'fill="{ACCENT1}" xml:space="preserve">{esc(key)}</text>'
            )
            # Value text
            els.append(
                f'<text x="{x+KEY_W+10}" y="{cy+ROW_H-7}" font-family="{FONT}" font-size="{FS}" '
                f'fill="{FG}" xml:space="preserve">{esc(val)}</text>'
            )
            cy += ROW_H

    return cy  # bottom of table

def build_svg(stats):
    els = []
    art_lines = ASCII_ART.split("\n")
    art_h     = len(art_lines) * ART_LH + PAD * 2

    # Tables data
    left_sections = [
        ("System", [
            ("OS",   INFO["OS"]),
            ("Host", INFO["Host"]),
            ("IDE",  INFO["IDE"]),
        ]),
        ("Languages", [
            ("Languages.Code",   INFO["Languages.Code"]),
            ("Languages.Markup", INFO["Languages.Markup"]),
            ("Languages.Real",   INFO["Languages.Real"]),
        ]),
        ("Hobbies", [
            ("Hobbies.Software", INFO["Hobbies.Software"]),
            ("Hobbies.Other",    INFO["Hobbies.Other"]),
        ]),
        ("Interests", [
            ("Interests.Subjective", INFO["Interests.Subjective"]),
            ("Interests.Other",      INFO["Interests.Other"]),
        ]),
    ]

    right_sections = [
        ("Contact", [
            ("Contact.Discord", INFO["Contact.Discord"]),
            ("Contact.Steam",   INFO["Contact.Steam"]),
            ("Contact.Xbox",    INFO["Contact.Xbox"]),
            ("Contact.Other",   INFO["Contact.Other"]),
        ]),
        ("GitHub Stats", [
            ("Repos",     str(stats["repos"])),
            ("Stars",     str(stats["stars"])),
            ("Forks",     str(stats["forks"])),
            ("Commits",   str(stats["commits"])),
            ("Followers", str(stats["followers"])),
            ("Following", str(stats["following"])),
        ]),
    ]

    # Geometry
    col_gap  = PAD
    table_y  = art_h + TITLE_H + PAD
    table_w  = (W - PAD * 2 - col_gap) // 2
    col1_x   = PAD
    col2_x   = PAD + table_w + col_gap

    # Estimate height
    def table_h(sections):
        h = 0
        for sec, rows in sections:
            h += HDR_H + ROW_H * len(rows)
        return h

    left_h  = table_h(left_sections)
    right_h = table_h(right_sections)
    swatch_h = 30
    H = art_h + TITLE_H + PAD + max(left_h, right_h) + swatch_h + PAD * 2

    # Background + outer border
    els.append(f'<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>')
    els.append(f'<rect width="{W}" height="{H}" rx="10" fill="none" stroke="{BORDER}" stroke-width="1.5"/>')

    # Divider between art and info
    els.append(f'<line x1="{PAD}" y1="{art_h}" x2="{W-PAD}" y2="{art_h}" stroke="{BORDER}" stroke-width="1"/>')

    # Art
    ay = PAD + ART_LH
    for line in art_lines:
        els.append(
            f'<text x="{PAD}" y="{ay}" font-family="{FONT}" font-size="{ART_FS}" '
            f'fill="{ACCENT1}" xml:space="preserve">{esc(line)}</text>'
        )
        ay += ART_LH

    # Title bar
    ty = art_h + PAD + 16
    els.append(
        f'<text x="{col1_x}" y="{ty}" font-family="{FONT}" font-size="13" xml:space="preserve">'
        f'<tspan fill="{ACCENT2}" font-weight="bold">{esc(GITHUB_USERNAME)}</tspan>'
        f'<tspan fill="{DIM}">@github</tspan></text>'
    )
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    els.append(
        f'<text x="{col2_x}" y="{ty}" font-family="{FONT}" font-size="12" '
        f'fill="{DIM}" xml:space="preserve">synced: {esc(ts)}</text>'
    )

    # Draw tables
    build_table(els, col1_x, table_y, table_w, left_sections)
    right_bottom = build_table(els, col2_x, table_y, table_w, right_sections)

    # Colour swatch under right table
    px = col2_x
    sw_y = right_bottom + 10
    for color in ["#ff5f56","#ffbd2e","#27c93f","#1d76fd","#b479e8","#e8943a","#57c464","#8b949e"]:
        els.append(f'<rect x="{px}" y="{sw_y}" width="22" height="14" rx="3" fill="{color}"/>')
        px += 26

    inner = "\n  ".join(els)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">\n  {inner}\n</svg>'

if __name__ == "__main__":
    print("Fetching stats...")
    stats = fetch_stats()
    print(stats)
    svg = build_svg(stats)
    os.makedirs("assets", exist_ok=True)
    with open("assets/profile.svg", "w", encoding="utf-8") as f:
        f.write(svg)
    print("Written -> assets/profile.svg")
