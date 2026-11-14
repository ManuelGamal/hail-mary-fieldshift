"""Build the 7-slide deck (deck.pptx) and its charts from real pipeline outputs.

Style follows the Meta-hackathon winners: navy title card, calm off-white content slides, one big full-sentence
headline per slide, a small uppercase kicker, a single accent colour, real data pictures only, generous margins.
Run: python docs/submission/build_deck.py   (needs kaggle/m2_hetero/out and kaggle/m2_visuals/out fetched)
"""

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ASSETS = os.path.join(HERE, "assets")
VIS = os.path.join(ROOT, "kaggle", "m2_visuals", "out", "visuals")
os.makedirs(ASSETS, exist_ok=True)

NAVY = "#0A2540"
INK = "#1B2430"
MUTED = "#6B7480"
PAPER = "#F7F6F2"
ACCENT = "#2E8FA3"  # rice teal
CLOVER = "#3A9D5D"
WHEAT = "#E0B341"
RED = "#C8553D"
FONT = "Segoe UI"
plt.rcParams.update(
    {
        "font.family": FONT,
        "font.size": 20,
        "axes.edgecolor": MUTED,
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": MUTED,
    }
)

wp = json.load(
    open(
        os.path.join(
            ROOT, "kaggle", "m2_hetero", "out", "hetero", "water_productivity.json"
        )
    )
)
E = {(r["site"], r["treat"], r["next_crop"], r["outcome"]): r for r in wp}


def bars(path, title_left, title_right, after_wheat, after_clover, note):
    fig, ax = plt.subplots(figsize=(9, 7), dpi=200)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    b = ax.bar(
        [title_left, title_right],
        [after_wheat, after_clover],
        color=[WHEAT, CLOVER],
        width=0.55,
    )
    for rect, v in zip(b, [after_wheat, after_clover]):
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            v + 0.15,
            f"{v:.1f}",
            ha="center",
            va="bottom",
            fontsize=30,
            fontweight="bold",
            color=INK,
        )
    ax.set_ylim(95, 104)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="x", labelsize=22, length=0)
    ax.text(0.0, 1.02, note, transform=ax.transAxes, fontsize=17, color=MUTED)
    fig.tight_layout()
    fig.savefig(path, facecolor=PAPER)
    plt.close(fig)


# slide 4: whole summer window (what a naive analysis sees), slide 6: rice-only window. Indexed: rice after wheat = 100
whole = E[("ZAN", "clover", "rice", "ndvi_auc")]
late = E[("ZAN", "clover", "rice", "ndvi_days_late")]
bars(
    os.path.join(ASSETS, "bars_naive.png"),
    "Rice after\nwheat",
    "Rice after\nclover",
    100,
    100 + whole["pct_of_ctrl"],
    "Rice greenness over the summer (after wheat = 100)",
)
bars(
    os.path.join(ASSETS, "bars_honest.png"),
    "Rice after\nwheat",
    "Rice after\nclover",
    100,
    100 + late["pct_of_ctrl"],
    "Only while the rice is in the field (after wheat = 100)",
)

# slide 5: real field calendar, Nov -> Oct, if the visuals kernel produced it
cal_png = os.path.join(ASSETS, "calendar.png")
if os.path.exists(os.path.join(VIS, "calendar.csv")):
    cal = pd.read_csv(os.path.join(VIS, "calendar.csv"))
    m = cal.groupby(["precrop", "step"]).ndvi.mean().unstack(0)
    days = [14 + 28 * k for k in range(7)] + [
        196 + 14 + 28 * k for k in range(6)
    ]  # days since Nov 1
    fig, ax = plt.subplots(figsize=(16, 6.2), dpi=200)
    fig.patch.set_facecolor(PAPER)
    ax.set_facecolor(PAPER)
    ax.axvspan(196, 252, color=RED, alpha=0.10, lw=0)
    ax.text(
        224,
        0.86,
        "Clover keeps the\nfield green (and\ndrinking) into June",
        ha="center",
        va="top",
        fontsize=16,
        color=RED,
    )
    ax.axvspan(252, 364, color=ACCENT, alpha=0.06, lw=0)
    ax.text(
        308, 0.86, "Rice in the field", ha="center", va="top", fontsize=16, color=ACCENT
    )
    ax.plot(days, m["wheat"], color=WHEAT, lw=5, label="Wheat, then rice")
    ax.plot(days, m["clover"], color=CLOVER, lw=5, label="Clover, then rice")
    ax.set_xticks([0, 30, 61, 92, 120, 151, 181, 212, 242, 273, 304, 334])
    ax.set_xticklabels(
        [
            "Nov",
            "Dec",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
        ]
    )
    ax.set_yticks([])
    ax.set_ylim(0.1, 0.9)
    ax.set_ylabel("How green, from space", fontsize=16, color=MUTED)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, loc="lower left", fontsize=17)
    fig.tight_layout()
    fig.savefig(cal_png, facecolor=PAPER)
    plt.close(fig)

from PIL import Image, ImageDraw, ImageFont


def legend(src, dst, items):
    if not os.path.exists(src):
        return
    im = Image.open(src).convert("RGB")
    W, H = im.size
    out = Image.new("RGB", (W, H + 90), PAPER)
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype("segoeui.ttf", 34)
    x = 10
    for name, col in items:
        d.rectangle([x, H + 28, x + 34, H + 62], fill=col)
        d.text((x + 46, H + 22), name, fill=INK, font=f)
        x += 60 + int(f.getlength(name)) + 30
    out.save(dst)


legend(
    os.path.join(VIS, "crop_flip", "W2024.png"),
    os.path.join(ASSETS, "map_W2024.png"),
    [
        ("Wheat", WHEAT),
        ("Clover", CLOVER),
        ("Sugar beet", "#8E6CC0"),
        ("Villages", "#EEECE6"),
    ],
)
legend(
    os.path.join(VIS, "crop_flip", "S2024.png"),
    os.path.join(ASSETS, "map_S2024.png"),
    [
        ("Rice", ACCENT),
        ("Maize", "#E07B39"),
        ("Cotton", "#D9A0B8"),
        ("Villages", "#EEECE6"),
    ],
)

# ---------------------------------------------------------------- deck
prs = Presentation()
prs.slide_width, prs.slide_height = Emu(12192000), Emu(6858000)  # 16:9
SW, SH = prs.slide_width, prs.slide_height
BLANK = prs.slide_layouts[6]
M = Emu(700000)  # margin


def rgb(h):
    return RGBColor.from_string(h.lstrip("#"))


def bg(slide, colour):
    f = slide.background.fill
    f.solid()
    f.fore_color.rgb = rgb(colour)


def text(slide, x, y, w, h, runs, size=20, colour=INK, bold=False, spacing=1.1):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(runs if isinstance(runs, list) else [runs]):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        r.font.name, r.font.size, r.font.bold = FONT, Pt(size), bold
        r.font.color.rgb = rgb(colour)
        p.space_after = Pt(size * 0.45)
    return tb


def content(kicker, headline, bullets=None, image=None, img_left=False, footer=None):
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    text(s, M, Emu(420000), Emu(8000000), Emu(400000), kicker.upper(), 13, MUTED, True)
    text(s, M, Emu(760000), SW - 2 * M, Emu(1300000), headline, 36, INK, True, 1.0)
    colw = Emu(int((SW - 2 * M) * 0.44))
    if image and os.path.exists(image):
        ix = M if img_left else M + colw + Emu(300000)
        iw = SW - 2 * M - colw - Emu(300000)
        pic = s.shapes.add_picture(image, ix, Emu(2150000), width=iw)
        if pic.top + pic.height > SH - Emu(750000):
            ratio = (SH - Emu(750000) - pic.top) / pic.height
            pic.height, pic.width = int(pic.height * ratio), int(pic.width * ratio)
    elif image:
        ph = s.shapes.add_textbox(
            M + colw + Emu(300000), Emu(2400000), Emu(5000000), Emu(800000)
        )
        ph.text_frame.text = f"[picture: {os.path.basename(image)}]"
    if bullets:
        bx = M + (SW - 2 * M - colw) if img_left else M
        text(s, bx, Emu(2250000), colw, Emu(3800000), bullets, 19, INK)
    if footer:
        text(s, M, SH - Emu(560000), SW - 2 * M, Emu(400000), footer, 10.5, MUTED)
    return s


# 1. title card (navy, like the winners' title cards)
s = prs.slides.add_slide(BLANK)
bg(s, NAVY)
text(
    s,
    M,
    Emu(700000),
    Emu(9000000),
    Emu(400000),
    "TEAM PROJECT: HAIL MARY  ·  NASA SPACE APPS CAIRO 2026  ·  FIELD SHIFT",
    13,
    "#9FB3C8",
    True,
)
text(
    s,
    M,
    Emu(1900000),
    Emu(10500000),
    Emu(1600000),
    "What should I plant next, to save water or earn more?",
    54,
    "#FFFFFF",
    True,
    1.0,
)
text(
    s,
    M,
    Emu(3750000),
    Emu(10500000),
    Emu(800000),
    "Advice for Nile Delta farmers from what really happened on fields like theirs, measured by NASA satellites.",
    26,
    "#DCE6F0",
)
text(
    s,
    M,
    Emu(5650000),
    Emu(10500000),
    Emu(400000),
    "Precrop Payoff Atlas",
    18,
    "#9FB3C8",
)

# 2. problem
content(
    "The problem",
    "Rotation advice is everywhere. Proof for your own field is nowhere.",
    [
        "Delta farmers grow clover, wheat or sugar beet in winter, then rice, maize or cotton in summer.",
        "Advice says some winter crops help the next one. Field trials are few, old and far from most villages.",
        "Choosing wrong costs a farmer a whole season.",
    ],
    image=os.path.join(ASSETS, "map_W2024.png"),
)

# 3. what we built
content(
    "What we built",
    "Ten years of every field's crops, read from space.",
    [
        "NASA HLS (Landsat + Sentinel-2) shows what grew in each field block, every season since 2016.",
        "NASA ECOSTRESS measures how much water each block used.",
        "Our AI crop map is right on 8 in 10 blocks, checked against FAO's official maps on years it never saw.",
        "About 100,000 field blocks in Kafr El-Sheikh and Sharqia.",
    ],
    image=os.path.join(ASSETS, "map_S2024.png"),
)

# 4-6: water cost of the winter crop choice (ZAN switcher FE on ECOSTRESS season ET, lead placebo passes)
et = E[("ZAN", "clover", "rice", "et_season_mm")]
fig, ax = plt.subplots(figsize=(9, 7), dpi=200)
fig.patch.set_facecolor(PAPER)
ax.set_facecolor(PAPER)
base = et["ctrl_mean"]
b = ax.bar(
    ["Wheat, then rice", "Clover, then rice"],
    [base, base + et["estimate"]],
    color=[WHEAT, CLOVER],
    width=0.55,
)
for rect, v in zip(b, [base, base + et["estimate"]]):
    ax.text(
        rect.get_x() + rect.get_width() / 2,
        v + 2,
        f"{v:.0f} mm",
        ha="center",
        va="bottom",
        fontsize=28,
        fontweight="bold",
        color=INK,
    )
ax.set_ylim(440, 540)
ax.set_yticks([])
for sp in ("top", "right", "left"):
    ax.spines[sp].set_visible(False)
ax.tick_params(axis="x", labelsize=22, length=0)
ax.text(
    0.0,
    1.02,
    "Water the field used over the summer season (NASA ECOSTRESS)",
    transform=ax.transAxes,
    fontsize=16,
    color=MUTED,
)
fig.tight_layout()
fig.savefig(os.path.join(ASSETS, "bars_water.png"), facecolor=PAPER)
plt.close(fig)

content(
    "Worked example · 1 of 3",
    "Example: should a Sharqia farmer plant clover or wheat before rice?",
    [
        "For each field, we compared summers after clover with summers after wheat, on the same field, year after year.",
        "This removes the soil, salinity and canal differences between fields.",
        "Then NASA ECOSTRESS tells us how much water the field used.",
    ],
    image=cal_png,
    img_left=False,
)

content(
    "Worked example · 2 of 3",
    "Clover before rice costs about 50 m³ more water per feddan, every season.",
    [
        f"+{et['estimate']:.0f} mm over the summer season (+{et['pct_of_ctrl']:.1f}%), measured on 17,371 fields in Sharqia; range {et['ci_low']:.0f}–{et['ci_high']:.0f} mm.",
        "Same result in Kafr El-Sheikh: +10 mm.",
        "Our check: next year's clover cannot change this year's water use, and our method correctly finds nothing.",
    ],
    image=os.path.join(ASSETS, "bars_water.png"),
)

content(
    "Worked example · 3 of 3",
    "In our Sharqia study area alone, that is about 0.6 million m³ of water a year.",
    [
        "About 6,100 field blocks grow rice after clover each year in our study area (0.5–0.65 million m³).",
        "Egypt caps rice area to save water. Our maps track rice from space within about 10% of FAO's official maps.",
        "Water planners can now see the water cost of each rotation, field by field, without a farm survey.",
    ],
    image=os.path.join(ASSETS, "map_S2024.png"),
)

# 7. why it matters
content(
    "Why it matters",
    "Next: advice for every field, to save water or raise income.",
    [
        "For any field, our pipeline finds about 10 fields like it (same salinity, water and history) and shows what really happened there.",
        "Honest by design: a claim is shown only if it passes the impossible-effect check.",
        "Next: the farmer advice screen, a revenue calculator using the farmer's own prices, then all of the Delta.",
    ],
    image=os.path.join(ASSETS, "history_grid.png"),
    footer="Data: NASA HLS, NASA ECOSTRESS, NASA POWER, NASADEM, FAO WaPOR, OpenStreetMap. Models: NASA/IBM Prithvi-EO-2.0, LightGBM. "
    "AI use: AI assistants helped write code and text; every number comes from our own pipeline.",
)

out = os.path.join(HERE, "deck_water.pptx")
prs.save(out)
print("saved", out, "slides:", len(prs.slides))
