import json, os, re, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import generate_cards as g

LOGIN = os.environ.get("GH_LOGIN") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "shakibdev2-source"
PAGE_ID = os.environ.get("VISITOR_PAGE_ID", f"{LOGIN}.{LOGIN}")
BADGE = f"https://visitor-badge.laobi.icu/badge?page_id={PAGE_ID}"
ASSETS = os.path.join(HERE, "..", "assets")
STATE = os.path.join(ASSETS, "visitors.json")
OUTFILE = os.path.join(ASSETS, "visitors.svg")

def read_badge():
    if os.environ.get("VISITOR_TEST_COUNT"):
        return int(os.environ["VISITOR_TEST_COUNT"])
    req = urllib.request.Request(BADGE, headers={"User-Agent": "Mozilla/5.0 (visitor-card)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        svg = r.read().decode("utf-8", "ignore")
    nums = re.findall(r">\s*([\d,]+)\s*<", svg)
    if not nums:
        raise RuntimeError("badge e number pai ni")
    return int(nums[-1].replace(",", ""))

def card(count, gain):
    # Advanced Sci-Fi Eye & Cyber Portal Animation
    eye = '''<g transform="translate(62,52)">
  <!-- Outer Pulse Wave -->
  <circle r="42" fill="#a855f7" opacity=".08">
    <animate attributeName="r" values="32;46;32" dur="3s" repeatCount="indefinite"/>
    <animate attributeName="opacity" values=".15;.02;.15" dur="3s" repeatCount="indefinite"/>
  </circle>
  <!-- Rotating Sci-Fi Rings -->
  <circle r="37" fill="none" stroke="#00ffff" stroke-opacity=".6" stroke-width="2" stroke-dasharray="4 6">
    <animateTransform attributeName="transform" type="rotate" from="0" to="360" dur="10s" repeatCount="indefinite"/>
  </circle>
  <circle r="31" fill="none" stroke="#a855f7" stroke-opacity=".4" stroke-width="1.5" stroke-dasharray="2 4">
    <animateTransform attributeName="transform" type="rotate" from="360" to="0" dur="8s" repeatCount="indefinite"/>
  </circle>
  <!-- Core Pulsing Eye Group -->
  <g>
    <animateTransform attributeName="transform" type="scale" values="1;1.05;1;0.92;1" keyTimes="0;.3;.6;.85;1" dur="4s" repeatCount="indefinite"/>
    <path d="M-28,0 Q0,-26 28,0 Q0,26 -28,0Z" fill="#010308" stroke="url(#rg)" stroke-width="3" filter="url(#gl)"/>
    <g>
      <animateTransform attributeName="transform" type="translate" values="0 0;-5 0;5 -1;0 0" keyTimes="0;.3;.7;1" dur="4.5s" repeatCount="indefinite"/>
      <circle r="11" fill="url(#bd)"/>
      <circle r="4.5" fill="#010308"/>
      <circle cx="-3.5" cy="-3.5" r="2" fill="#fff"/>
      <circle cx="2" cy="2" r="0.8" fill="#00ffff" opacity=".8"/>
    </g>
  </g>
</g>'''

    # Advanced Equalizer Bars with Smooth Wave Sync
    bars = "".join(
        f'<rect x="{362 + i * 8}" y="58" width="5" height="26" rx="2.5" fill="url(#rg)" filter="url(#gl)">'
        f'<animate attributeName="height" values="4;{h};8;{h-5};4" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'<animate attributeName="y" values="84;{84-h};80;{84-(h-5)};84" dur="{d}s" begin="{b}s" repeatCount="indefinite"/>'
        f'</rect>'
        for i, (h, d, b) in enumerate(((18, 1.2, 0), (28, 0.9, 0.15), (12, 1.4, 0.3), (24, 1.1, 0.1), (20, 1.3, 0.25), (15, 1.0, 0.4)))
    )

    # Glowing Live Indicator
    live = (
        '<g transform="translate(346,36)">'
        '<circle r="4" fill="#4ade80" filter="url(#gl)">'
        '<animate attributeName="opacity" values="1;0.2;1" dur="1.2s" repeatCount="indefinite"/>'
        '<animate attributeName="r" values="3;6;3" dur="1.2s" repeatCount="indefinite"/>'
        '</circle>'
        '<text x="12" y="4" font-size="10" font-weight="800" letter-spacing="2.5" fill="#4ade80">LIVE</text>'
        '</g>'
    )

    chip = ""
    if gain > 0:
        chip = f'<text x="116" y="98" font-size="10" font-weight="700" fill="#4ade80">▲ +{gain:,} new visits</text>'

    body = (
        eye
        + '<text x="116" y="36" font-size="13" font-weight="800" letter-spacing="3" fill="#00ffff">TOTAL VISITORS</text>'
        + g.cu(116, 78, g.seq(count), 36, 800, "url(#bd)", "start", 0.3, 1.8)
        + chip
        + live
        + bars
    )
    return g.svg(420, 104, body, 21)

def main():
    os.makedirs(ASSETS, exist_ok=True)
    state = {"self_hits": 0, "last": 0}
    if os.path.exists(STATE):
        try:
            state.update(json.load(open(STATE)))
        except Exception:
            pass
    try:
        shown = read_badge()
    except Exception as e:
        print("badge read fail:", e)
        if not os.path.exists(OUTFILE):
            open(OUTFILE, "w", encoding="utf-8").write(card(state["last"], 0))
        return
    state["self_hits"] += 1
    visitors = max(state["last"], shown - state["self_hits"])
    gain = visitors - state["last"]
    state["last"] = visitors
    json.dump(state, open(STATE, "w"))
    open(OUTFILE, "w", encoding="utf-8").write(card(visitors, gain))
    print("visitors:", visitors, "(badge:", shown, "self hits:", state["self_hits"], ")")

if __name__ == "__main__":
    main()

