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
    "Interests.Subjective" : "Quantum Computing, Deep Learning, Representation Learning, All things LLMs",
    "Interests.Other"      : "Mathematics, Physics and Economics",
    "Contact.Discord"      : "shreyan.c",
    "Contact.Steam"        : "ThinkMachine_",
    "Contact.Xbox"         : "ThinkMachine543",
    "Contact.Other"        : "[EMAIL_ADDRESS]",
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

FONT    = "monospace"
BG      = "#0d1117"
BORDER  = "#30363d"
ACCENT1 = "#e8943a"
ACCENT2 = "#57c464"
DIM     = "#8b949e"
FG      = "#c9d1d9"
ART_LH  = 13
ART_FS  = 10
INFO_LH = 20
INFO_FS = 13
W       = 1060
PAD     = 22

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def txt(x, y, content, fill=FG, size=INFO_FS, weight="normal"):
    return (f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" '
            f'fill="{fill}" font-weight="{weight}" xml:space="preserve">{content}</text>')

def kv(x, y, key, value, dot_total=36):
    k = f'<tspan fill="{ACCENT1}">{esc(key)}</tspan>'
    c = f'<tspan fill="{DIM}">: </tspan>'
    d = f'<tspan fill="{DIM}">{"." * max(2, dot_total - len(key) - len(str(value)))} </tspan>'
    v = f'<tspan fill="{FG}">{esc(value)}</tspan>'
    return txt(x, y, k+c+d+v)

def section(x, y, label):
    return txt(x, y,
        f'<tspan fill="{DIM}">- </tspan>'
        f'<tspan fill="{ACCENT1}" font-weight="bold">{esc(label)} </tspan>'
        f'<tspan fill="{DIM}">{"─"*3}</tspan>')

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

def build_svg(stats):
    els = []
    art_lines = ASCII_ART.split("\n")
    art_h     = len(art_lines) * ART_LH + PAD * 2

    # Info panel: col1 has System(4) + Languages(4) + Hobbies(3) + Interests(3) = 14 rows + 4 gaps
    # col2 has Contact(5) + Stats(4) = 9 rows + 2 gaps + swatch
    # Use whichever col is taller + padding
    info_rows = (1 + 14 + 4) * INFO_LH + PAD * 2 + 30  # col1 is taller
    H = art_h + info_rows

    els.append(f'<rect width="{W}" height="{H}" rx="10" fill="{BG}"/>')
    els.append(f'<rect width="{W}" height="{H}" rx="10" fill="none" stroke="{BORDER}" stroke-width="1.5"/>')
    els.append(f'<line x1="{PAD}" y1="{art_h}" x2="{W-PAD}" y2="{art_h}" stroke="{BORDER}" stroke-width="1"/>')

    # Art
    ay = PAD + ART_LH
    for line in art_lines:
        els.append(txt(PAD, ay, esc(line), fill=ACCENT1, size=ART_FS))
        ay += ART_LH

    # Info panel — two columns
    col1 = PAD
    col2 = W // 2 + PAD
    y    = art_h + PAD + INFO_LH

    # Title row
    els.append(txt(col1, y,
        f'<tspan fill="{ACCENT2}" font-weight="bold">{esc(GITHUB_USERNAME)}</tspan>'
        f'<tspan fill="{DIM}">@github</tspan>'))
    els.append(txt(col2, y,
        f'<tspan fill="{DIM}">synced: {datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}</tspan>'))
    y += INFO_LH + 4

    c1y, c2y = y, y

    # ── Col 1: System + Languages + Hobbies + Interests ──────────────────────
    els.append(section(col1, c1y, "System"));         c1y += INFO_LH
    for k, v in [("OS",   INFO["OS"]),
                 ("Host", INFO["Host"]),
                 ("IDE",  INFO["IDE"])]:
        els.append(kv(col1, c1y, k, v));              c1y += INFO_LH
    c1y += 6

    els.append(section(col1, c1y, "Languages"));      c1y += INFO_LH
    for k, v in [("Languages.Code",   INFO["Languages.Code"]),
                 ("Languages.Markup", INFO["Languages.Markup"]),
                 ("Languages.Real",   INFO["Languages.Real"])]:
        els.append(kv(col1, c1y, k, v));              c1y += INFO_LH
    c1y += 6

    els.append(section(col1, c1y, "Hobbies"));        c1y += INFO_LH
    for k, v in [("Hobbies.Software", INFO["Hobbies.Software"]),
                 ("Hobbies.Other",    INFO["Hobbies.Other"])]:
        els.append(kv(col1, c1y, k, v));              c1y += INFO_LH
    c1y += 6

    els.append(section(col1, c1y, "Interests"));      c1y += INFO_LH
    for k, v in [("Interests.Subjective", INFO["Interests.Subjective"]),
                 ("Interests.Other",      INFO["Interests.Other"])]:
        els.append(kv(col1, c1y, k, v));              c1y += INFO_LH

    # ── Col 2: Contact + GitHub Stats ─────────────────────────────────────────
    els.append(section(col2, c2y, "Contact"));        c2y += INFO_LH
    for k, v in [("Contact.Discord", INFO["Contact.Discord"]),
                 ("Contact.Steam",   INFO["Contact.Steam"]),
                 ("Contact.Xbox",    INFO["Contact.Xbox"]),
                 ("Contact.Other",   INFO["Contact.Other"])]:
        els.append(kv(col2, c2y, k, v));              c2y += INFO_LH
    c2y += 6

    els.append(section(col2, c2y, "GitHub Stats"));   c2y += INFO_LH
    for k, v in [
        ("Repos",     f'{stats["repos"]}  |  Stars: {stats["stars"]}  |  Forks: {stats["forks"]}'),
        ("Commits",   str(stats["commits"])),
        ("Followers", f'{stats["followers"]}  |  Following: {stats["following"]}'),
    ]:
        els.append(kv(col2, c2y, k, v));              c2y += INFO_LH
    c2y += 8

    # Colour swatch
    px = col2
    for color in ["#ff5f56","#ffbd2e","#27c93f","#1d76fd","#b479e8","#e8943a","#57c464","#8b949e"]:
        els.append(f'<rect x="{px}" y="{c2y}" width="22" height="14" rx="3" fill="{color}"/>')
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
