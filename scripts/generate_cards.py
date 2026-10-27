import json, math, os, random, sys, time, urllib.request
from datetime import date, datetime, timedelta, timezone
from xml.sax.saxutils import escape

LOGIN = os.environ.get("GH_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "shakibdev2-source"
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
HIST = os.path.join(OUT, "history.json")
F = "font-family=\"'Segoe UI',Ubuntu,Arial,sans-serif\""
STAMP = "UPDATED " + datetime.now(timezone.utc).strftime("%d %b · %H:%M UTC").upper()


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    headers = {"Authorization": "bearer " + TOKEN, "Content-Type": "application/json", "User-Agent": "stats-cards"}
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request("https://api.github.com/graphql", data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as r:
                res = json.load(r)
            if res.get("errors") and not res.get("data"):
                raise RuntimeError(res["errors"])
            return res["data"]
        except Exception as e:
            last = e
            time.sleep(2 ** attempt)
    raise last

def fetch():
    q = """query($login:String!){user(login:$login){name login createdAt
      repositories(ownerAffiliations:OWNER,isFork:false,first:100){nodes{stargazerCount
        languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}
      pullRequests{totalCount} issues{totalCount}
      repositoriesContributedTo(first:1,contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){totalCount}
      contributionsCollection{totalCommitContributions restrictedContributionsCount}}}"""
    u = gql(q, {"login": LOGIN})["user"]
    stars, langs = 0, {}
    for repo in u["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            old = langs.get(n, (0, e["node"]["color"]))
            langs[n] = (old[0] + e["size"], e["node"]["color"] or old[1])
    langs = sorted(((n, s, c or "#8b949e") for n, (s, c) in langs.items()), key=lambda x: -x[1])
    cc = u["contributionsCollection"]
    created = datetime.fromisoformat(u["createdAt"].replace("Z", "+00:00")).date()
    days, now = {}, datetime.now(timezone.utc)
    cq = """query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){
      contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    for y in range(created.year, now.year + 1):
        frm = datetime(y, 1, 1, tzinfo=timezone.utc)
        to = min(datetime(y, 12, 31, 23, 59, 59, tzinfo=timezone.utc), now)
        d = gql(cq, {"login": LOGIN, "from": frm.isoformat(), "to": to.isoformat()})
        for w in d["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
            for day in w["contributionDays"]:
                days[day["date"]] = day["contributionCount"]
    return {
        "name": u["name"] or u["login"], "stars": stars,
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "prs": u["pullRequests"]["totalCount"], "issues": u["issues"]["totalCount"],
        "contrib_to": u["repositoriesContributedTo"]["totalCount"],
        "repos": len(u["repositories"]["nodes"]),
        "langs": langs, "days": days, "created": created,
    }

def demo():
    today = date.today()
    days = {(today - timedelta(d)).isoformat(): (3 if 0 < d < 6 else (7 if d == 9 else 0)) for d in range(60)}
    return {"name": "Md. Shakib Hossan", "stars": 25, "commits": 260, "prs": 12, "issues": 5, "contrib_to": 7, "repos": 9,
            "langs": [("Python", 1800000, "#3572A5"), ("JavaScript", 1200000, "#f1e05a"), ("HTML/CSS", 700000, "#e34c26"),
                      ("PHP", 400000, "#4F5D95"), ("Java", 250000, "#b07219")],
            "days": days, "created": today - timedelta(200)}

def streaks(days):
    today = date.today()
    items = sorted((date.fromisoformat(k), v) for k, v in days.items() if date.fromisoformat(k) <= today)
    total = sum(v for _, v in items)
    best = (0, None, None); run = 0; start = None
    for d, v in items:
        if v > 0:
            if run == 0: start = d
            run += 1
            if run > best[0]: best = (run, start, d)
        else:
            run = 0
    cur = (0, None, None)
    lookup = dict(items)
    d = today if lookup.get(today, 0) > 0 else today - timedelta(1)
    end = d
    while lookup.get(d, 0) > 0:
        d -= timedelta(1)
    n = (end - d).days
    if n > 0: cur = (n, d + timedelta(1), end)
    return total, cur, best

def activity(days):
    today = date.today()
    window = [(today - timedelta(29 - k), days.get((today - timedelta(29 - k)).isoformat(), 0)) for k in range(30)]
    avg = sum(v for _, v in window) / 30
    bd, bv = max(window, key=lambda x: x[1])
    return avg, bd, bv

def load_history():
    try:
        with open(HIST, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def snapshot(d):
    total = sum(v for k, v in d["days"].items() if date.fromisoformat(k) <= date.today())
    return {"stars": d["stars"], "commits": d["commits"], "prs": d["prs"], "issues": d["issues"],
            "contrib_to": d["contrib_to"], "total": total}

def apply_history(d):
    hist = load_history()
    today = date.today().isoformat()
    older = sorted(k for k in hist if k < today)
    d["prev"] = hist[older[-1]] if older else {}
    hist[today] = snapshot(d)
    for k in sorted(hist)[:-60]:
        del hist[k]
    return hist

def fd(d):
    if d is None: return "-"
    s = f"{d:%b} {d.day}"
    return s if d.year == date.today().year else s + f", {d.year}"

def rng(a, b): return "-" if a is None else f"{fd(a)} - {fd(b)}"

STATIC = bool(os.environ.get("STATIC"))

def num(n): return f"{n:,}"

def seq(v, fmt=num, steps=24):
    if v <= 0: return [fmt(0)]
    n = min(v, steps); vals = []
    for i in range(n + 1):
        x = round(v * (1 - (1 - i / n) ** 3))
        t = fmt(x)
        if not vals or vals[-1] != t: vals.append(t)
    if vals[-1] != fmt(v): vals.append(fmt(v))
    return vals

def cyc(s, e, attr, on, off, dur, begin):
    """Looping 'spotlight' window: attr = on during [s,e] of each cycle, else off (discrete)."""
    if s <= 0 and e >= 1: return ""
    if s <= 0: vals, kt = [on, off], [0, e]
    elif e >= 1: vals, kt = [off, on], [0, s]
    else: vals, kt = [off, on, off], [0, s, e]
    return (f'<animate attributeName="{attr}" values="{";".join(map(str, vals))}" keyTimes="{";".join(f"{k:.4f}" for k in kt)}" '
            f'calcMode="discrete" dur="{dur}s" begin="{begin}s" repeatCount="indefinite"/>')

def cu(x, y, frames, size, weight, fill, anchor, delay, dur=1.8):
    a = f'x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"'
    if STATIC or len(frames) == 1:
        return f'<text {a}>{frames[-1]}</text>'
    n = len(frames); dt = dur / n; out = ""
    for k, fr in enumerate(frames):
        t = delay + k * dt
        end = ' fill="freeze"' if k == n - 1 else f' dur="{dt:.2f}s"'
        out += f'<text {a} display="none"><set attributeName="display" to="inline" begin="{t:.2f}s"{end}/>{fr}</text>'
    return out

def fade(delay, inner, dx=-18):
    if STATIC: return f"<g>{inner}</g>"
    return (f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{delay}s" dur=".6s" fill="freeze"/>'
            f'<animateTransform attributeName="transform" type="translate" from="{dx} 0" to="0 0" begin="{delay}s" dur=".6s" fill="freeze"/>{inner}</g>')

def ring(cx, cy, r, frac, color, width, dur=2.0, delay=0):
    C = 2 * math.pi * r
    anim = "" if STATIC else f'<animate attributeName="stroke-dashoffset" from="{C:.1f}" to="{C*(1-frac):.1f}" begin="{delay}s" dur="{dur}s" fill="freeze"/>'
    start = C * (1 - frac) if STATIC else C
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" '
            f'stroke-dasharray="{C:.1f}" stroke-dashoffset="{start:.1f}" transform="rotate(-90 {cx} {cy})" filter="url(#gl)">{anim}</circle>')

def spin(cx, cy, dur, inner, rev=False):
    a, b = (360, 0) if rev else (0, 360)
    return f'<g><animateTransform attributeName="transform" type="rotate" from="{a} {cx} {cy}" to="{b} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/>{inner}</g>'

def underline():
    if STATIC: return ""
    return '<rect x="28" y="49" width="0" height="2.5" rx="1.25" fill="url(#bd)"><animate attributeName="width" from="0" to="160" dur="1.2s" fill="freeze"/></rect>'

def title_anim(text, raw):
    est = len(raw) * 9.6
    plain = f'<text x="28" y="42" font-size="18" font-weight="800" fill="url(#bd)">{text}</text>'
    if STATIC: return plain
    n = len(raw)
    ws = ";".join(f"{est * k / n:.1f}" for k in range(n + 1))
    xs = ";".join(f"{28 + est * k / n:.1f}" for k in range(n + 1))
    clip = (f'<clipPath id="tc"><rect x="26" y="18" width="0" height="34"><animate attributeName="width" values="{ws}" calcMode="discrete" dur="1.5s" fill="freeze"/></rect></clipPath>')
    caret = (f'<rect x="28" y="27" width="2" height="18" fill="#00ffff" filter="url(#gl)"><animate attributeName="x" values="{xs}" calcMode="discrete" dur="1.5s" fill="freeze"/>'
             '<animate attributeName="opacity" values="1;0;1" dur=".9s" repeatCount="indefinite"/></rect>')
    # periodic RGB-split glitch after typing finishes
    glitch = ""
    kt = "0;.86;.88;.9;.92;.94;1"
    for col, dx in (("#00ffff", -2), ("#f472b6", 2)):
        xv = f"28;28;{28+dx};{28-dx};{28+dx};28;28"
        glitch += (f'<text x="28" y="42" font-size="18" font-weight="800" fill="{col}" opacity="0">{text}'
                   f'<animate attributeName="opacity" values="0;0;.8;0;.6;0;0" keyTimes="{kt}" dur="6s" begin="2s" repeatCount="indefinite"/>'
                   f'<animate attributeName="x" values="{xv}" keyTimes="{kt}" dur="6s" begin="2s" repeatCount="indefinite"/></text>')
    return f'<defs>{clip}</defs><g clip-path="url(#tc)">{plain}</g>{caret}{glitch}'

def chip(cx, cy, text, w):
    return (f'<rect x="{cx-w/2:.1f}" y="{cy-10}" width="{w}" height="20" rx="8" fill="#020617" stroke="#00ffff" stroke-opacity=".35" stroke-width="1"/>'
            f'<text x="{cx}" y="{cy+3.5}" font-size="10.5" font-weight="600" fill="#38bdf8" text-anchor="middle">{text}</text>')

def delta(x, y, diff):
    if diff == 0: return ""
    up = diff > 0
    col = "#4ade80" if up else "#f87171"
    sym = "▲" if up else "▼"
    return (f'<text x="{x}" y="{y}" font-size="8.5" font-weight="800" fill="{col}">{sym}{abs(diff):,}'
            f'<animate attributeName="opacity" values="1;.45;1" dur="1.6s" repeatCount="indefinite"/></text>')

def brackets(w, h):
    p = 12; l = 14
    a = ".55"
    pulse = '<animate attributeName="opacity" values=".25;.9;.25" dur="3s" repeatCount="indefinite"/>'
    paths = [f"M{p},{p+l} V{p} H{p+l}", f"M{w-p-l},{p} H{w-p} V{p+l}", f"M{p},{h-p-l} V{h-p} H{p+l}", f"M{w-p-l},{h-p} H{w-p} V{h-p-l}"]
    return "".join(f'<path d="{d}" fill="none" stroke="#00ffff" stroke-width="1.6" stroke-linecap="round" opacity="{a}">{pulse}</path>' for d in paths)

def parts(w, h, rnd):
    bub = ""
    for _ in range(20):
        x = rnd.randint(6, w - 6); r = rnd.uniform(0.8, 3.0); d = rnd.uniform(3, 8); b = rnd.uniform(0, d)
        col = rnd.choice(["#00ffff", "#a855f7", "#38bdf8"])
        bub += (f'<circle cx="{x}" cy="{h+12}" r="{r:.1f}" fill="{col}" opacity="0">'
                f'<animate attributeName="cy" from="{h+12}" to="-14" dur="{d:.1f}s" begin="-{b:.1f}s" repeatCount="indefinite"/>'
                f'<animate attributeName="cx" values="{x};{x+rnd.randint(-14,14)};{x}" dur="{d:.1f}s" begin="-{b:.1f}s" repeatCount="indefinite"/>'
                f'<animate attributeName="opacity" values="0;.9;.9;0" dur="{d:.1f}s" begin="-{b:.1f}s" repeatCount="indefinite"/></circle>')
    # --- advanced ambient layer: twinkling stars, shooting stars, CRT scanlines, glitch bar, boot flash ---
    extra = flash = ""
    if not STATIC:
        stars = "".join(
            f'<circle cx="{rnd.randint(8, w-8)}" cy="{rnd.randint(8, h-8)}" r="{rnd.uniform(.5, 1.3):.1f}" fill="#fff" opacity="0">'
            f'<animate attributeName="opacity" values="0;.9;0" dur="{rnd.uniform(1.5, 4):.1f}s" begin="{rnd.uniform(0, 4):.1f}s" repeatCount="indefinite"/></circle>'
            for _ in range(26))
        shoot = ""
        for _ in range(3):
            sx = rnd.randint(0, int(w * .6)); sy = rnd.randint(0, int(h * .4)); d = rnd.uniform(7, 11); b0 = rnd.uniform(0, d)
            ex, ey = sx + w * .45, sy + w * .225
            shoot += (f'<g opacity="0"><line x1="0" y1="0" x2="-38" y2="-19" stroke="url(#ss)" stroke-width="1.6" stroke-linecap="round"/>'
                      f'<circle r="1.8" fill="#fff" filter="url(#gl)"/>'
                      f'<animateTransform attributeName="transform" type="translate" values="{sx},{sy};{ex:.0f},{ey:.0f};{ex:.0f},{ey:.0f}" keyTimes="0;.14;1" dur="{d:.1f}s" begin="-{b0:.1f}s" repeatCount="indefinite"/>'
                      f'<animate attributeName="opacity" values="0;1;1;0;0" keyTimes="0;.02;.12;.14;1" dur="{d:.1f}s" begin="-{b0:.1f}s" repeatCount="indefinite"/></g>')
        gb = (f'<rect x="0" y="{h*.3:.0f}" width="{w}" height="3" fill="#00ffff" opacity="0">'
              f'<animate attributeName="opacity" values="0;0;.25;0;0" keyTimes="0;.9;.92;.94;1" dur="7s" repeatCount="indefinite"/>'
              f'<animate attributeName="y" values="{h*.3:.0f};{h*.7:.0f};{h*.45:.0f}" calcMode="discrete" dur="7s" repeatCount="indefinite"/></rect>')
        extra = f'<rect width="{w}" height="{h}" fill="url(#sl)" opacity=".35"/>{stars}{shoot}{gb}'
        flash = f'<rect width="{w}" height="{h}" fill="#00ffff" opacity="0"><animate attributeName="opacity" values="0;.35;0;.2;0" dur=".7s" fill="freeze"/></rect>'
    orbs = (
        f'<ellipse cx="{w*.2}" cy="{h*.2}" rx="{w*.42}" ry="{h*.7}" fill="#0284c7" opacity=".24"><animate attributeName="cx" values="{w*.2};{w*.7};{w*.2}" dur="8s" repeatCount="indefinite"/><animate attributeName="cy" values="{h*.2};{h*.8};{h*.2}" dur="11s" repeatCount="indefinite"/></ellipse>'
        f'<ellipse cx="{w*.8}" cy="{h*.7}" rx="{w*.38}" ry="{h*.6}" fill="#7e22ce" opacity=".26"><animate attributeName="cx" values="{w*.8};{w*.3};{w*.8}" dur="10s" repeatCount="indefinite"/><animate attributeName="cy" values="{h*.7};{h*.2};{h*.7}" dur="13s" repeatCount="indefinite"/></ellipse>'
        f'<ellipse cx="{w*.5}" cy="{h*.5}" rx="{w*.2}" ry="{h*.3}" fill="#db2777" opacity=".12"><animate attributeName="cx" values="{w*.5};{w*.15};{w*.85};{w*.5}" dur="16s" repeatCount="indefinite"/></ellipse>')
    return f"""<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#010308"/><stop offset="1" stop-color="#0a0f1d"/></linearGradient>
<linearGradient id="bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00ffff"/><stop offset=".5" stop-color="#a855f7"/><stop offset="1" stop-color="#38bdf8"/>
<animateTransform attributeName="gradientTransform" type="rotate" from="0 .5 .5" to="360 .5 .5" dur="9s" repeatCount="indefinite"/></linearGradient>
<linearGradient id="rg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00ffff"/><stop offset="1" stop-color="#a855f7"/>
<animateTransform attributeName="gradientTransform" type="rotate" from="0 .5 .5" to="360 .5 .5" dur="7s" repeatCount="indefinite"/></linearGradient>
<linearGradient id="sh" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".26"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<linearGradient id="bm" x1="0" x2="1"><stop offset="0" stop-color="#00ffff" stop-opacity="0"/><stop offset=".5" stop-color="#00ffff" stop-opacity=".5"/><stop offset="1" stop-color="#00ffff" stop-opacity="0"/></linearGradient>
<linearGradient id="sc" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00ffff" stop-opacity=".35"/><stop offset="1" stop-color="#a855f7" stop-opacity="0"/></linearGradient>
<linearGradient id="ss" x1="1" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<pattern id="gr" width="14" height="14" patternUnits="userSpaceOnUse"><path d="M14 0H0V14" fill="none" stroke="#00ffff" stroke-opacity=".07"/>
<animateTransform attributeName="patternTransform" type="translate" from="0 0" to="14 14" dur="5s" repeatCount="indefinite"/></pattern>
<pattern id="sl" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".28"/>
<animateTransform attributeName="patternTransform" type="translate" from="0 0" to="0 4" dur=".8s" repeatCount="indefinite"/></pattern>
<filter id="gl" x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="bl"><feGaussianBlur stdDeviation="50"/></filter>
<clipPath id="cc"><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="24"/></clipPath>
</defs>
<g clip-path="url(#cc)">
<rect width="{w}" height="{h}" fill="url(#bg)"/>
<g filter="url(#bl)">{orbs}</g>
<rect width="{w}" height="{h}" fill="url(#gr)"/>
{extra}
{bub}
<rect x="-6" y="0" width="6" height="{h}" fill="url(#bm)"><animate attributeName="x" values="-6;{w+6};{w+6}" keyTimes="0;.6;1" dur="6s" repeatCount="indefinite"/></rect>
<rect x="0" y="-3" width="{w}" height="2" fill="#00ffff" opacity=".14"><animate attributeName="y" from="-4" to="{h+4}" dur="7s" repeatCount="indefinite"/></rect>
{flash}
</g>
{brackets(w, h)}
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="24" fill="none" stroke="#1e293b" stroke-width="1.5"/>
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="24" fill="none" stroke="url(#bd)" stroke-width="3" pathLength="1000" stroke-dasharray="200 800" filter="url(#gl)"><animate attributeName="stroke-dashoffset" from="0" to="-1000" dur="2.8s" repeatCount="indefinite"/></rect>
<rect x="1" y="1" width="{w-2}" height="{h-2}" rx="24" fill="none" stroke="#f472b6" stroke-width="2" pathLength="1000" stroke-dasharray="60 940" filter="url(#gl)"><animate attributeName="stroke-dashoffset" from="-500" to="-1500" dur="4.2s" repeatCount="indefinite"/></rect>"""

def shine(w, h):
    return (f'<g clip-path="url(#cc)"><g transform="skewX(-20)"><rect x="-180" y="-10" width="110" height="{h+20}" fill="url(#sh)">'
            f'<animate attributeName="x" values="-160;{w+160};{w+160}" keyTimes="0;.5;1" dur="4.5s" begin="0.5s" repeatCount="indefinite"/></rect></g></g>')

def svg(w, h, body, seed, stamp_y=None):
    rnd = random.Random(seed)
    sy = h - 12 if stamp_y is None else stamp_y
    stamp = f'<text x="{w-22}" y="{sy}" font-size="8.5" fill="#00ffff" text-anchor="end" opacity="0.9">⚡ {STAMP}</text>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" {F}>'
            f'{parts(w,h,rnd)}{body}{stamp}{shine(w,h)}</svg>')

ICONS = [
    '<polygon points="6,0.5 7.6,4 11.5,4.5 8.6,7.2 9.4,11.2 6,9.3 2.6,11.2 3.4,7.2 0.5,4.5 4.4,4" fill="none" stroke="#00ffff" stroke-width="1.7" stroke-linejoin="round"/>',
    '<circle cx="6" cy="6" r="3.2" fill="none" stroke="#00ffff" stroke-width="1.7"/><path d="M0.5 6H3M9 6H11.5" stroke="#00ffff" stroke-width="1.7" stroke-linecap="round"/>',
    '<circle cx="2.5" cy="2.5" r="1.8" fill="none" stroke="#00ffff" stroke-width="1.7"/><circle cx="9.5" cy="9.5" r="1.8" fill="none" stroke="#00ffff" stroke-width="1.7"/><path d="M2.5 4.3V11.5M9.5 7.7V3.5H5.5" fill="none" stroke="#00ffff" stroke-width="1.7" stroke-linecap="round"/>',
    '<circle cx="6" cy="6" r="5" fill="none" stroke="#00ffff" stroke-width="1.7"/><path d="M6 3V6.2M6 8.2V8.3" stroke="#00ffff" stroke-width="1.9" stroke-linecap="round"/>',
    '<rect x="1" y="1" width="10" height="10" rx="2" fill="none" stroke="#00ffff" stroke-width="1.7"/><path d="M3.5 4H8.5M3.5 7H8.5" stroke="#00ffff" stroke-width="1.6" stroke-linecap="round"/>',
]

def radar(cx, cy, R, norms, labels, delay=0.6):
    n = len(norms)
    ang = [math.radians(-90 + i * 360 / n) for i in range(n)]
    pt = lambda a, r: (cx + r * math.cos(a), cy + r * math.sin(a))
    out = ""
    for k, op in ((1, .32), (.66, .18), (.33, .14)):
        out += f'<polygon points="{" ".join("%.1f,%.1f" % pt(a, R * k) for a in ang)}" fill="none" stroke="#00ffff" stroke-opacity="{op}" stroke-width="1"/>'
    for a in ang:
        x, y = pt(a, R)
        out += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#00ffff" stroke-opacity=".2"/>'
    if not STATIC:
        out += spin(cx, cy, 5, f'<path d="M{cx},{cy} L{cx},{cy-R} A{R},{R} 0 0 1 {cx+R*math.sin(math.radians(40)):.1f},{cy-R*math.cos(math.radians(40)):.1f} Z" fill="#00ffff" opacity=".13"/>'
                                f'<line x1="{cx}" y1="{cy}" x2="{cx}" y2="{cy-R}" stroke="#00ffff" stroke-opacity=".6" stroke-width="1.2"/>')
        # sonar pings expanding from the centre
        for k in (0, 1.5):
            out += (f'<circle cx="{cx}" cy="{cy}" r="0" fill="none" stroke="#00ffff" stroke-width="1" opacity="0">'
                    f'<animate attributeName="r" from="0" to="{R+6}" dur="3s" begin="{k}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values=".55;0" dur="3s" begin="{k}s" repeatCount="indefinite"/></circle>')
    pts = [pt(a, R * max(.1, v)) for a, v in zip(ang, norms)]
    final = " ".join("%.1f,%.1f" % p for p in pts)
    start = " ".join(f"{cx},{cy}" for _ in ang)
    anim = "" if STATIC else f'<animate attributeName="points" from="{start}" to="{final}" begin="{delay}s" dur="1.6s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/>'
    out += f'<polygon points="{final if STATIC else start}" fill="url(#rg)" fill-opacity=".3" stroke="url(#bd)" stroke-width="2" stroke-linejoin="round" filter="url(#gl)">{anim}</polygon>'
    for (x, y), a, lab in zip(pts, ang, labels):
        op = "1" if STATIC else "0"
        pop = "" if STATIC else (f'<animate attributeName="opacity" from="0" to="1" begin="{delay+1.5}s" dur=".3s" fill="freeze"/>'
                                 f'<animate attributeName="r" values="2.6;4.2;2.6" dur="2.2s" begin="{delay+1.8}s" repeatCount="indefinite"/>')
        out += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#fff" opacity="{op}" filter="url(#gl)">{pop}</circle>'
        lx, ly = pt(a, R + 9)
        anchor = "middle" if abs(lx - cx) < 5 else ("start" if lx > cx else "end")
        out += f'<text x="{lx:.1f}" y="{ly+3:.1f}" font-size="7.5" font-weight="800" letter-spacing=".5" fill="#7dd3fc" text-anchor="{anchor}">{lab}</text>'
    return out

def smooth(pts, top, base):
    clamp = lambda y: max(top, min(base, y))
    dd = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]; p1 = pts[i]; p2 = pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, clamp(p1[1] + (p2[1] - p0[1]) / 6))
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, clamp(p2[1] - (p3[1] - p1[1]) / 6))
        dd += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return dd

def stats_card(d):
    prev = d.get("prev", {})
    raw = f"{d['name']}'s GitHub Stats"
    level = min(99, max(1, math.floor(d['commits'] / 12) + 1))
    xp_pct = min(100, int((d['commits'] % 12) / 12 * 100))
    tier = f"🔥 LVL {level} CYBER-DEV"
    rows = [("Total Stars Earned", "stars"), ("Total Commits (last year)", "commits"), ("Total PRs", "prs"),
            ("Total Issues", "issues"), ("Contributed to (last year)", "contrib_to")]
    b = title_anim(escape(raw), raw)
    for i, (l, k) in enumerate(rows):
        v = d[k]
        y = 82 + i * 26
        dl = .5 + i * .22
        inner = (f'<rect x="18" y="{y-14}" width="244" height="22" rx="8" fill="#fff" opacity=".045"/>'
                 f'<g transform="translate(26,{y-11})">{ICONS[i]}<animate attributeName="opacity" values="1;.3;1" dur="1.5s" begin="{i*.3}s" repeatCount="indefinite"/></g>'
                 f'<text x="48" y="{y}" font-size="12.5" font-weight="600" fill="#f8fafc">{l}:</text>'
                 + delta(266, y, v - prev.get(k, v)))
        b += fade(dl, inner) + cu(256, y, seq(v), 13, 700, "#00ffff", "end", dl + .2, 1.4)
    if not STATIC:
        # row scanner: a highlight that hops down the rows in a loop
        b += ('<g opacity="0"><set attributeName="opacity" to="1" begin="2.8s" fill="freeze"/>'
              '<animateTransform attributeName="transform" type="translate" values="0 0;0 26;0 52;0 78;0 104" keyTimes="0;.2;.4;.6;.8" calcMode="discrete" dur="6s" begin="2.8s" repeatCount="indefinite"/>'
              '<rect x="18" y="68" width="244" height="22" rx="8" fill="#00ffff" opacity=".08"/>'
              '<rect x="18" y="68" width="3" height="22" rx="1.5" fill="#00ffff" filter="url(#gl)"/></g>')
    b += f'<text x="28" y="202" font-size="9" fill="#94a3b8">XP Progress: {xp_pct}%</text>'
    b += f'<rect x="110" y="195" width="150" height="6" rx="3" fill="#1e293b"/>'
    b += f'<rect x="110" y="195" width="{150 * xp_pct / 100}" height="6" rx="3" fill="url(#rg)"><animate attributeName="width" from="0" to="{150 * xp_pct / 100}" dur="1.5s" fill="freeze"/></rect>'
    if not STATIC and xp_pct > 0:
        tipx = 110 + 150 * xp_pct / 100
        b += (f'<circle cx="{tipx}" cy="198" r="3" fill="#fff" filter="url(#gl)"><animate attributeName="cx" from="110" to="{tipx}" dur="1.5s" fill="freeze"/>'
              '<animate attributeName="r" values="2.5;4.5;2.5" dur="1.4s" begin="1.5s" repeatCount="indefinite"/></circle>')
    caps = {"stars": 50, "commits": 400, "prs": 40, "issues": 40, "contrib_to": 15}
    norms = [min(1, math.log1p(d[k]) / math.log1p(caps[k])) for k in ("stars", "commits", "prs", "issues", "contrib_to")]
    b += radar(352, 112, 38, norms, ["STAR", "CMT", "PR", "ISS", "REPO"])
    b += f'<rect x="292" y="168" width="116" height="22" rx="7" fill="#020617" stroke="#00ffff" stroke-width="1.3"/>'
    if not STATIC:
        b += ('<rect x="292" y="168" width="116" height="22" rx="7" fill="none" stroke="#a855f7" stroke-width="1.6" stroke-dasharray="8 12">'
              '<animate attributeName="stroke-dashoffset" from="0" to="-40" dur="1.5s" repeatCount="indefinite"/></rect>')
    b += (f'<text x="350" y="182.5" font-size="9" font-weight="700" fill="#38bdf8" text-anchor="middle">{tier}'
          + ('' if STATIC else '<animate attributeName="opacity" values=".7;1;.7" dur="2s" repeatCount="indefinite"/>') + '</text>')
    return svg(420, 215, b, 11)

def langs_card(d):
    L = d["langs"]
    total = sum(s for _, s, _ in L) or 1
    items = [(n, s / total, c) for n, s, c in L]
    if len(items) > 5:
        items = items[:4] + [("Other", sum(p for _, p, _ in items[4:]), "#64748b")]
    b = title_anim("Most Used Languages", "Most Used Languages")
    if not L:
        b += '<text x="28" y="90" font-size="14" fill="#94a3b8">No language data yet</text>'
        return svg(420, 215, b, 12)
    n_it = len(items); T = n_it * 2.4; CB = 2.2
    for i, (n, p, c) in enumerate(items):
        y = 80 + i * 24
        w = max(2, 190 * p)
        track = f'<rect x="48" y="{y+6}" width="190" height="3.5" rx="1.75" fill="#fff" opacity=".08"/>'
        fillbar = (f'<rect x="48" y="{y+6}" width="{w:.1f}" height="3.5" rx="1.75" fill="{c}" filter="url(#gl)"/>' if STATIC else
                   f'<rect x="48" y="{y+6}" width="0" height="3.5" rx="1.75" fill="{c}" filter="url(#gl)"><animate attributeName="width" from="0" to="{w:.1f}" begin="{.6+i*.25}s" dur="1.3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/></rect>')
        if not STATIC and n_it > 1:
            # spotlight row that follows the highlighted donut segment
            b += f'<rect x="20" y="{y-15}" width="232" height="24" rx="8" fill="{c}" opacity="0">{cyc(i/n_it, (i+1)/n_it, "opacity", .13, 0, T, CB)}</rect>'
        b += fade(.4 + i * .25, f'<circle cx="34" cy="{y-4}" r="4.5" fill="{c}" filter="url(#gl)"><animate attributeName="r" values="4;5.6;4" dur="2.4s" begin="{i*.3}s" repeatCount="indefinite"/></circle>'
                  f'<text x="48" y="{y}" font-size="12.5" font-weight="600" fill="#f8fafc">{escape(n)}</text>'
                  f'<text x="238" y="{y}" font-size="11.5" font-weight="800" fill="{c}" text-anchor="end">{p*100:.1f}%</text>' + track, dx=-14) + fillbar
        if not STATIC:
            b += (f'<circle cx="48" cy="{y+7.75}" r="2.6" fill="#fff" opacity="0" filter="url(#gl)"><set attributeName="opacity" to="1" begin="{.6+i*.25}s" fill="freeze"/>'
                  f'<animate attributeName="cx" from="48" to="{48+w:.1f}" begin="{.6+i*.25}s" dur="1.3s" fill="freeze" calcMode="spline" keyTimes="0;1" keySplines=".2 .8 .2 1"/>'
                  f'<animate attributeName="r" values="2;3.6;2" dur="1.8s" begin="{1.9+i*.25}s" repeatCount="indefinite"/></circle>')
    dx, dy, R = 328, 112, 38
    C = 2 * math.pi * R
    b += f'<circle cx="{dx}" cy="{dy}" r="{R}" fill="none" stroke="#1e293b" stroke-width="12"/>'
    b += spin(dx, dy, 26, f'<circle cx="{dx}" cy="{dy}" r="54" fill="none" stroke="#00ffff" stroke-opacity=".4" stroke-width="2" stroke-dasharray="1.6 7"/>', rev=True)
    cum = 0
    for i, (n, p, c) in enumerate(items):
        ln = max(.5, C * p - 2.2); rot = -90 + 360 * cum
        start = ln if STATIC else 0
        anim = "" if STATIC else (f'<animate attributeName="stroke-dasharray" from="0 {C:.1f}" to="{ln:.1f} {C:.1f}" begin="{i*.3}s" dur="1.1s" fill="freeze"/>'
                                  + (cyc(i/n_it, (i+1)/n_it, "stroke-width", 17, 12, T, CB) if n_it > 1 else
                                     f'<animate attributeName="stroke-width" values="12;15;12" dur="3.2s" begin="2.2s" repeatCount="indefinite"/>'))
        b += (f'<circle cx="{dx}" cy="{dy}" r="{R}" fill="none" stroke="{c}" stroke-width="12" stroke-dasharray="{start:.1f} {C:.1f}" '
              f'transform="rotate({rot:.1f} {dx} {dy})" filter="url(#gl)">{anim}</circle>')
        cum += p
    b += spin(dx, dy, 7, f'<circle cx="{dx}" cy="{dy-R-11}" r="3" fill="#f472b6" filter="url(#gl)"/>')
    # centre read-out cycles through every language in sync with the donut
    for i, (n, p, c) in enumerate(items):
        if STATIC and i > 0: continue
        sp = "" if (STATIC or n_it == 1) else cyc(i/n_it, (i+1)/n_it, "opacity", 1, 0, T, CB)
        b += (f'<g opacity="{1 if i == 0 else 0}">{sp}'
              f'<text x="{dx}" y="{dy-2}" font-size="12" font-weight="800" fill="#ffffff" text-anchor="middle">{escape(n[:9])}</text>'
              f'<text x="{dx}" y="{dy+13}" font-size="11.5" font-weight="800" fill="{c}" text-anchor="middle">{round(p*100)}%</text></g>')
    repos = d.get("repos")
    foot = f"{len(L)} languages" + (f" · {repos} repos" if repos else "")
    b += f'<text x="28" y="203" font-size="9" fill="#94a3b8">{foot}</text>'
    return svg(420, 215, b, 12)

def streak_card(d):
    total, cur, best = streaks(d["days"])
    prev = d.get("prev", {})
    avg, bd, bv = activity(d["days"])
    today = date.today()
    W, H = 860, 262
    def col(x, v, label, dt, dl):
        t = fade(dl, f'<text x="{x}" y="118" font-size="15" font-weight="600" fill="#00ffff" text-anchor="middle">{label}</text>'
                     f'<text x="{x}" y="142" font-size="12.5" fill="#94a3b8" text-anchor="middle">{dt}</text>', dx=0)
        return t + cu(x, 86, seq(v), 38, 900, "url(#bd)", "middle", dl, 1.8)
    b = col(145, total, "Total Contributions", f"{fd(d['created'])} - Present", .3) + col(715, best[0], "Longest Streak", rng(best[1], best[2]), .6)
    gain = total - prev.get("total", total)
    left = (f"▲ {gain:,} new · " if gain > 0 else "") + f"30d avg {avg:.1f}/day"
    b += fade(.9, chip(145, 164, left, 190 if gain > 0 else 140), dx=0)
    right = f"Best day {bv} · {bd:%b} {bd.day}" if bv > 0 else "No activity in 30 days"
    b += fade(1.1, chip(715, 164, right, 170), dx=0)
    off = 0 if STATIC else 120
    la = "" if STATIC else '<animate attributeName="stroke-dashoffset" to="0" dur="1s" fill="freeze"/>'
    for x in (287, 573):
        b += f'<line x1="{x}" y1="34" x2="{x}" y2="176" stroke="#1e293b" stroke-width="1.5" stroke-dasharray="150" stroke-dashoffset="{off}">{la}</line>'
    cx, cy, r = 430, 82, 38
    b += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#1e293b" stroke-width="6.5"/>'
    b += ring(cx, cy, r, 1, "url(#rg)", 6.5, 1.8)
    if not STATIC:
        Cc = 2 * math.pi * r
        # comet racing around the ring once it is drawn
        b += (f'<g opacity="0"><set attributeName="opacity" to="1" begin="1.9s" fill="freeze"/>'
              f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-dasharray="14 {Cc-14:.1f}" '
              f'transform="rotate(-90 {cx} {cy})" filter="url(#gl)" opacity=".8"><animate attributeName="stroke-dashoffset" from="0" to="-{Cc:.1f}" dur="2.6s" repeatCount="indefinite"/></circle></g>')
    b += spin(cx, cy, 30, f'<circle cx="{cx}" cy="{cy}" r="51" fill="none" stroke="#a855f7" stroke-opacity=".5" stroke-width="2.2" stroke-dasharray="1.5 7"/>', rev=True)
    b += spin(cx, cy, 5, f'<circle cx="{cx}" cy="{cy-r-8}" r="3" fill="#00ffff" filter="url(#gl)"/>')
    b += f'<circle cx="{cx}" cy="{cy}" r="26" fill="#a855f7" opacity=".12"><animate attributeName="r" values="22;29;22" dur="2.2s" repeatCount="indefinite"/></circle>'
    b += cu(cx, cy + 13, seq(cur[0]), 36, 900, "#c084fc", "middle", .3, 1.4)
    sparks = "".join(f'<circle cx="{sx}" cy="0" r="1.6" fill="#ffd9a0" opacity="0"><animate attributeName="cy" from="-6" to="-30" dur="{du}s" begin="{be}s" repeatCount="indefinite"/><animate attributeName="opacity" values="0;1;0" dur="{du}s" begin="{be}s" repeatCount="indefinite"/></circle>'
                     for sx, du, be in ((-5, 1.6, 0), (4, 1.3, .5), (0, 1.9, .9), (7, 1.5, 1.3)))
    b += (f'<g transform="translate({cx},{cy-r+2})" filter="url(#gl)">{sparks}<g><animateTransform attributeName="transform" type="scale" values="1;1.25;.95;1.2;1" dur="1.3s" repeatCount="indefinite"/>'
          '<path d="M0,-13 C7,-5 11,-1 9,7 C7,13 -7,13 -9,7 C-11,-1 -3,-5 0,-13Z" fill="#a855f7"/>'
          '<path d="M0,-6 C4,-1 6,3 4,8 C2,11 -2,11 -4,8 C-6,3 -2,-1 0,-6Z" fill="#f472b6" opacity=".9"/>'
          '<path d="M0,0 C3,3 4,6 0,9 C-4,6 -3,3 0,0Z" fill="#fff6d6"/></g></g>')
    b += f'<text x="{cx}" y="150" font-size="15" font-weight="800" fill="#c084fc" text-anchor="middle">Current Streak</text>'
    b += f'<text x="{cx}" y="168" font-size="12.5" fill="#94a3b8" text-anchor="middle">{rng(cur[1], cur[2])}</text>'
    if cur[0] > 0 and d["days"].get(today.isoformat(), 0) == 0:
        b += ('<g transform="translate(488,76)"><circle r="3.5" fill="#fbbf24" filter="url(#gl)"><animate attributeName="opacity" values="1;.2;1" dur="1.2s" repeatCount="indefinite"/></circle>'
              '<text x="10" y="3.5" font-size="9" font-weight="800" letter-spacing="1.5" fill="#fbbf24">TODAY PENDING</text>'
              '<text x="10" y="16" font-size="8.5" fill="#94a3b8">contribute to keep it alive</text></g>')
    n = 30
    vals = [d["days"].get((today - timedelta(n - 1 - k)).isoformat(), 0) for k in range(n)]
    x0, x1, top, base = 30, 830, 206, 246
    mx = max(max(vals), 3)
    pts = [(x0 + k * (x1 - x0) / (n - 1), base - (v / mx) * (base - top)) for k, v in enumerate(vals)]
    b += '<text x="30" y="194" font-size="9" font-weight="800" letter-spacing="2" fill="#475569">LAST 30 DAYS</text>'
    for gy in (top, (top + base) / 2, base):
        b += f'<line x1="{x0}" y1="{gy}" x2="{x1}" y2="{gy}" stroke="#fff" stroke-opacity=".06" stroke-dasharray="3 5"/>'
    line = smooth(pts, top, base)
    area = line + f" L{pts[-1][0]:.1f},{base} L{pts[0][0]:.1f},{base} Z"
    pk = vals.index(max(vals)) if max(vals) > 0 else -1
    if STATIC:
        b += f'<path d="{area}" fill="url(#sc)"/><path d="{line}" fill="none" stroke="url(#bd)" stroke-width="2.6" stroke-linecap="round"/>'
    else:
        b += (f'<path d="{area}" fill="url(#sc)" opacity="0"><animate attributeName="opacity" from="0" to="1" begin="2.2s" dur="1s" fill="freeze"/></path>'
              f'<path d="{line}" fill="none" stroke="url(#bd)" stroke-width="2.8" stroke-linecap="round" pathLength="1000" stroke-dasharray="1000" stroke-dashoffset="1000" filter="url(#gl)">'
              f'<animate attributeName="stroke-dashoffset" from="1000" to="0" begin="1.2s" dur="2.4s" fill="freeze"/></path>')
        for k, (px, py) in enumerate(pts):
            if vals[k] > 0:
                b += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="0" fill="#e0f2fe"><animate attributeName="r" from="0" to="2.6" begin="{1.2+2.4*k/(n-1):.2f}s" dur=".3s" fill="freeze"/></circle>'
        b += (f'<circle r="10" fill="#a855f7" opacity=".28"><animateMotion path="{line}" dur="7s" begin="3.8s" repeatCount="indefinite"/></circle>'
              f'<circle r="3.8" fill="#fff" filter="url(#gl)"><animateMotion path="{line}" dur="7s" begin="3.8s" repeatCount="indefinite"/></circle>')
    if pk >= 0:
        px, py = pts[pk]
        lx = max(60, min(800, px))
        op = "1" if STATIC else "0"
        ap = "" if STATIC else '<animate attributeName="opacity" from="0" to="1" begin="3.4s" dur=".5s" fill="freeze"/>'
        b += (f'<g opacity="{op}">{ap}<circle cx="{px:.1f}" cy="{py:.1f}" r="5" fill="none" stroke="#fbbf24" stroke-width="1.6" filter="url(#gl)">'
              '<animate attributeName="r" values="4;11;4" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values="1;.1;1" dur="2s" repeatCount="indefinite"/></circle>'
              f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="#fbbf24"/>'
              f'<text x="{lx:.1f}" y="{py-12:.1f}" font-size="9" font-weight="800" letter-spacing="1" fill="#fbbf24" text-anchor="middle">PEAK {vals[pk]}</text></g>')
    lx, ly = pts[-1]
    b += (f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="3.4" fill="#00ffff" filter="url(#gl)"><animate attributeName="r" values="3;6;3" dur="1.6s" repeatCount="indefinite"/></circle>'
          f'<text x="{lx-10:.1f}" y="{ly-10:.1f}" font-size="8.5" font-weight="800" letter-spacing="1.5" fill="#00ffff" text-anchor="end">TODAY</text>')
    if not STATIC:
        # data scanner: sweeps the 30-day graph and reads out each day's value
        T, SB = 9, 4.0
        b += (f'<g opacity="0"><set attributeName="opacity" to="1" begin="{SB}s" fill="freeze"/>'
              f'<line x1="{x0}" y1="{top-6}" x2="{x0}" y2="{base+2}" stroke="#00ffff" stroke-opacity=".5" stroke-dasharray="2 3">'
              f'<animate attributeName="x1" from="{x0}" to="{x1}" dur="{T}s" begin="{SB}s" repeatCount="indefinite"/>'
              f'<animate attributeName="x2" from="{x0}" to="{x1}" dur="{T}s" begin="{SB}s" repeatCount="indefinite"/></line></g>')
        for k, (px, py) in enumerate(pts):
            s = max(0, (k - .5) / (n - 1)); e = min(1, (k + .5) / (n - 1))
            dt = today - timedelta(n - 1 - k)
            hot = "#fbbf24" if vals[k] > 0 else "#64748b"
            b += (f'<g opacity="0">{cyc(s, e, "opacity", 1, 0, T, SB)}'
                  f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.8" fill="none" stroke="#fff" stroke-width="1.4" filter="url(#gl)"/>'
                  f'<text x="{x1}" y="194" font-size="10" font-weight="800" letter-spacing=".5" fill="{hot}" text-anchor="end">{dt:%b} {dt.day} · {vals[k]} contributions</text></g>')
    return svg(W, H, b, 13, stamp_y=26)

def heatmap_card(d):
    today = date.today()
    first = today - timedelta((today.weekday() + 1) % 7) - timedelta(weeks=52)
    cols = 53
    pal = ["#1a2236", "#0e4a63", "#0891b2", "#a855f7", "#00ffff"]
    cells = {}
    for c in range(cols):
        for r in range(7):
            dt = first + timedelta(days=c * 7 + r)
            if dt <= today:
                cells[(c, r)] = (dt, d["days"].get(dt.isoformat(), 0))
    mx = max([v for _, v in cells.values()] + [1])
    def level(v):
        if v <= 0: return 0
        q = v / mx
        return 1 if q <= .25 else 2 if q <= .5 else 3 if q <= .75 else 4
    names = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    wd = [0] * 7
    wk = [0] * cols
    active = 0
    for (c, r), (dt, v) in cells.items():
        wd[r] += v; wk[c] += v
        if v > 0: active += 1
    busiest = names[wd.index(max(wd))] if max(wd) > 0 else "-"
    W, H = 860, 252
    x0, y0, step, size = 32, 108, 15, 12
    b = title_anim("Contribution Activity", "Contribution Activity")
    b += fade(.6, chip(98, 70, f"{active} active days", 132), dx=0)
    b += fade(.8, chip(246, 70, f"Busiest day: {busiest}", 148), dx=0)
    b += fade(1.0, chip(386, 70, f"Best week: {max(wk)}", 124), dx=0)
    last_m = None
    for c in range(cols):
        dt = first + timedelta(days=c * 7)
        if dt.month != last_m and dt.day <= 7:
            b += f'<text x="{x0 + c * step}" y="{y0 - 8}" font-size="9" font-weight="700" fill="#64748b">{dt:%b}</text>'
            last_m = dt.month
    for c in range(cols):
        g = ""
        for r in range(7):
            if (c, r) not in cells: continue
            dt, v = cells[(c, r)]
            lv = level(v)
            extra = ""
            if lv > 0 and not STATIC:
                extra = f'<animate attributeName="opacity" values="1;.55;1" dur="{2 + (c % 5) * .4:.1f}s" begin="{3 + r * .2:.1f}s" repeatCount="indefinite"/>'
            flt = ' filter="url(#gl)"' if lv == 4 else ""
            g += f'<rect x="{x0 + c * step}" y="{y0 + r * step}" width="{size}" height="{size}" rx="3" fill="{pal[lv]}"{flt}>{extra}</rect>'
        if STATIC:
            b += f"<g>{g}</g>"
        else:
            t = .4 + c * .035
            b += (f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{t:.2f}s" dur=".45s" fill="freeze"/>'
                  f'<animateTransform attributeName="transform" type="translate" from="0 10" to="0 0" begin="{t:.2f}s" dur=".45s" fill="freeze"/>{g}</g>')
    gh = 7 * step
    b += (f'<defs><clipPath id="gc"><rect x="{x0-2}" y="{y0-2}" width="{cols*step+4}" height="{gh+4}"/></clipPath></defs>'
          f'<g clip-path="url(#gc)"><rect x="{x0-24}" y="{y0-2}" width="24" height="{gh+4}" fill="url(#bm)">'
          f'<animate attributeName="x" values="{x0-24};{x0+cols*step};{x0+cols*step}" keyTimes="0;.7;1" dur="5s" begin="3.2s" repeatCount="indefinite"/></rect></g>')
    tc, tr = cols - 1, (today.weekday() + 1) % 7
    if not STATIC:
        # gold shockwaves radiating from today's cell across the grid
        rx_, ry_ = x0 + tc * step + size / 2, y0 + tr * step + size / 2
        rip = ""
        for k in (0, 2):
            rip += (f'<circle cx="{rx_}" cy="{ry_}" r="0" fill="none" stroke="#fbbf24" stroke-width="1.5" opacity="0">'
                    f'<animate attributeName="r" from="0" to="{cols*step}" dur="4s" begin="{3.5+k}s" repeatCount="indefinite"/>'
                    f'<animate attributeName="opacity" values=".7;0" dur="4s" begin="{3.5+k}s" repeatCount="indefinite"/></circle>')
        b += f'<g clip-path="url(#gc)">{rip}</g>'
    b += (f'<rect x="{x0 + tc * step - 2}" y="{y0 + tr * step - 2}" width="{size + 4}" height="{size + 4}" rx="4.5" fill="none" stroke="#fbbf24" stroke-width="1.6" filter="url(#gl)">'
          '<animate attributeName="opacity" values="1;.2;1" dur="1.4s" repeatCount="indefinite"/></rect>')
    ly = H - 24
    b += f'<text x="{x0}" y="{ly + 9}" font-size="9" font-weight="700" fill="#64748b">LESS</text>'
    for i, col in enumerate(pal):
        b += f'<rect x="{x0 + 32 + i * 16}" y="{ly}" width="11" height="11" rx="3" fill="{col}"/>'
    b += f'<text x="{x0 + 32 + 5 * 16 + 4}" y="{ly + 9}" font-size="9" font-weight="700" fill="#64748b">MORE</text>'
    return svg(W, H, b, 17)

def main():
    hist = None
    if "--demo" in sys.argv:
        d = demo()
    else:
        if not TOKEN:
            sys.exit("GH_TOKEN / GITHUB_TOKEN nai")
        d = fetch()
        hist = apply_history(d)
    os.makedirs(OUT, exist_ok=True)
    for name, fn in (("stats", stats_card), ("langs", langs_card), ("streak", streak_card), ("heatmap", heatmap_card)):
        with open(os.path.join(OUT, f"{name}.svg"), "w", encoding="utf-8") as f:
            f.write(fn(d))
    if hist is not None:
        with open(HIST, "w", encoding="utf-8") as f:
            json.dump(hist, f, indent=1, sort_keys=True)
    print("done:", d["commits"], "commits,", len(d["langs"]), "languages")

if __name__ == "__main__":
    main()
