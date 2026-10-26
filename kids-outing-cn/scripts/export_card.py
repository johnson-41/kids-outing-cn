#!/usr/bin/env python3
"""把 card.json 渲染成 1080x1350 的 JPG。两种风格。

用法:
    python3 scripts/export_card.py <card.json> <out.jpg> [--style cartoon|neon|line] [--scale 2] [--quality 92] [--font 字体名]

风格（自选，与年龄无关）:
    cartoon  纸黄底、粗描边、硬阴影、贴纸感。
    neon     近黑底、细线网格、霓虹描边、等宽字。
    line     白底黑线、只描边不填色、速写本。
             未指定时依次取 card.json 的 style、再按 age_band 推断（under12→cartoon，teen→neon）。

退出码:
    0 成功
    1 参数错误或输入文件缺失
    2 渲染失败
"""

import argparse
import io
import json
import os
import subprocess
import sys

W, H = 1080, 1350
REQUIRED = ["date", "place", "companions", "title", "one_thing", "plan_id"]

SANS = [
    "Noto Sans CJK SC",
    "PingFang SC",
    "Hiragino Sans GB",
    "Source Han Sans SC",
    "Microsoft YaHei",
    "Noto Serif CJK SC",
]
SERIF = [
    "Noto Serif CJK SC",
    "Source Han Serif SC",
    "Songti SC",
    "SimSun",
]


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def installed_fonts():
    try:
        out = subprocess.run(
            ["fc-list", ":lang=zh", "family"], capture_output=True, text=True, timeout=10
        )
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def pick_font(prefer_serif, requested):
    if requested:
        return requested
    pool = installed_fonts()
    if pool:
        for name in (SERIF if prefer_serif else SANS):
            if name in pool:
                return name
        first = pool.splitlines()[0].split(",")[0].strip()
        if first:
            return first
    print("[warn] 未探测到中文字体，中文可能显示为方块。可用 --font 指定。", file=sys.stderr)
    return "sans-serif"


def card_tier(card):
    """simple：只有封面帧；full：加时间轴与最有反应；full_child：再加孩子原话。"""
    tier = card.get("tier")
    if tier in ("simple", "full", "full_child"):
        return tier
    if card.get("child_says"):
        return "full_child"
    return "full"


def quote_of(card):
    """优先用孩子的原话；没有就用家长的原话。"""
    child = card.get("child_says") or {}
    if child.get("text"):
        who = child.get("name") or "孩子"
        age = child.get("age")
        tag = f"{who}说的 · {age} 岁" if age else f"{who}说的"
        return child["text"], tag, True
    if card.get("quote"):
        return card["quote"], "", False
    return None, "", False


def wrap(text, per_line, max_lines):
    lines = [text[i : i + per_line] for i in range(0, len(text), per_line)]
    return lines[:max_lines]


# ---------------------------------------------------------------- cartoon


def svg_cartoon(card, font):
    C = dict(
        paper="#FFF8E7",
        paper2="#FFECC9",
        ink="#241B13",
        sun="#FFC53D",
        sky="#5BC8E8",
        coral="#FF7A59",
        grape="#9B7EDE",
        tape="#FFE9A8",
    )
    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    a(f'<rect width="{W}" height="{H}" fill="{C["paper"]}"/>')

    # 底纸斜纹
    a('<defs><pattern id="hatch" width="26" height="26" patternUnits="userSpaceOnUse" '
      'patternTransform="rotate(45)">'
      '<line x1="0" y1="0" x2="0" y2="26" stroke="rgba(36,27,19,0.07)" stroke-width="6"/>'
      "</pattern></defs>")
    a(f'<rect width="{W}" height="{H}" fill="url(#hatch)"/>')

    # 主卡：硬阴影 + 粗描边
    a(f'<rect x="80" y="76" width="920" height="1200" rx="34" fill="{C["ink"]}" opacity="0.22"/>')
    a(f'<rect x="66" y="62" width="920" height="1216" rx="34" fill="{C["paper2"]}" '
      f'stroke="{C["ink"]}" stroke-width="6"/>')

    # 顶部胶带
    a(f'<rect x="380" y="26" width="300" height="66" fill="{C["tape"]}" opacity="0.95" '
      f'transform="rotate(-2.5 530 59)"/>')

    # 日期胶囊
    a(f'<rect x="112" y="118" width="296" height="54" rx="27" fill="{C["sky"]}" '
      f'stroke="{C["ink"]}" stroke-width="4"/>')
    a(f'<text x="260" y="155" text-anchor="middle" font-family="{font}" font-size="26" '
      f'font-weight="700" fill="{C["ink"]}">{esc(card["date"])}</text>')

    # 地点与同行人
    a(f'<text x="112" y="230" font-family="{font}" font-size="38" font-weight="700" '
      f'fill="{C["ink"]}">{esc(card["place"])}</text>')
    a(f'<text x="112" y="274" font-family="{font}" font-size="26" fill="#5C4A38">'
      f'{esc(card["companions"])}</text>')

    # 标题：短题一行，长题两行，避开右上插画
    title = str(card["title"])
    if len(title) <= 9:
        lines = [title]
    else:
        half = (len(title) + 1) // 2
        lines = [title[:half], title[half:]]
    y = 392 if len(lines) == 1 else 360
    for line in lines[:2]:
        a(f'<text x="112" y="{y}" font-family="{font}" font-size="52" font-weight="800" '
          f'fill="{C["ink"]}">{esc(line)}</text>')
        y += 72

    # 铜钱插画
    cx, cy, r = 800, 352, 78
    a(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{C["sun"]}" stroke="{C["ink"]}" stroke-width="6"/>')
    a(f'<rect x="{cx - 28}" y="{cy - 28}" width="56" height="56" fill="{C["paper2"]}" '
      f'stroke="{C["ink"]}" stroke-width="6"/>')
    a(f'<circle cx="{cx}" cy="{cy}" r="{r + 13}" fill="none" stroke="{C["ink"]}" stroke-width="2" '
      f'stroke-dasharray="6 9" opacity="0.45"/>')

    a(f'<rect x="112" y="488" width="828" height="6" rx="3" fill="{C["ink"]}" opacity="0.16"/>')

    # 最有反应标签
    a(f'<rect x="112" y="524" width="190" height="44" rx="22" fill="{C["grape"]}" '
      f'stroke="{C["ink"]}" stroke-width="4"/>')
    a(f'<text x="207" y="554" text-anchor="middle" font-family="{font}" font-size="21" '
      f'font-weight="700" fill="#FFFFFF">最有反应</text>')
    a(f'<text x="112" y="650" font-family="{font}" font-size="52" font-weight="700" '
      f'fill="{C["ink"]}">{esc(card["one_thing"])}</text>')

    # 站点贴纸卡（simple 档不显示）
    tier = card_tier(card)
    stops = [] if tier == "simple" else card.get("stops", [])[:5]
    y = 700
    for i, s in enumerate(stops):
        col = C["coral"] if i == 0 else C["paper"]
        a(f'<rect x="112" y="{y}" width="828" height="56" rx="15" fill="{col}" '
          f'stroke="{C["ink"]}" stroke-width="4"/>')
        a(f'<text x="146" y="{y + 37}" font-family="{font}" font-size="26" font-weight="600" '
          f'fill="{C["ink"]}">{esc(s)}</text>')
        y += 66

    # 原话气泡：优先孩子的话，带署名
    qtext, qtag, from_child = quote_of(card)
    by = 1064 if tier != "simple" else 880
    if qtext:
        bubble = C["grape"] if from_child else "#FFFFFF"
        fg = "#FFFFFF" if from_child else C["ink"]
        a(f'<rect x="112" y="{by}" width="828" height="90" rx="24" fill="{bubble}" '
          f'stroke="{C["ink"]}" stroke-width="4"/>')
        a(f'<path d="M186,{by + 90} l0,28 l40,-28 z" fill="{bubble}" stroke="{C["ink"]}" '
          'stroke-width="4"/>')
        a(f'<rect x="188" y="{by + 86}" width="36" height="9" fill="{bubble}"/>')
        a(f'<text x="148" y="{by + 58}" font-family="{font}" font-size="31" fill="{fg}">'
          f'「{esc(qtext)}」</text>')
        if qtag:
            a(f'<text x="112" y="{by - 12}" font-family="{font}" font-size="20" '
              f'fill="#5B3E9E" letter-spacing="1">{esc(qtag)}</text>')

    # 页脚票根齿孔
    a(f'<line x1="112" y1="1192" x2="940" y2="1192" stroke="{C["ink"]}" stroke-width="5" '
      'stroke-dasharray="20 14" opacity="0.55"/>')
    a(f'<text x="112" y="1238" font-family="{font}" font-size="23" fill="#5C4A38">'
      f'{esc(card.get("next", ""))}</text>')
    a(f'<text x="940" y="1238" text-anchor="end" font-family="{font}" font-size="21" '
      f'fill="#8A7560">{esc(card["plan_id"])}</text>')
    a("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- neon


def svg_neon(card, font):
    C = dict(
        bg="#0B0F14",
        ink="#E8F1F8",
        dim="#7C8E9E",
        neon="#38E8D0",
        pink="#FF4D8D",
        amber="#FFC24B",
    )
    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    a(f'<rect width="{W}" height="{H}" fill="{C["bg"]}"/>')

    a('<defs><pattern id="g" width="54" height="54" patternUnits="userSpaceOnUse">'
      f'<path d="M54 0H0V54" fill="none" stroke="{C["neon"]}" stroke-width="1" opacity="0.10"/>'
      "</pattern></defs>")
    a(f'<rect width="{W}" height="{H}" fill="url(#g)"/>')

    a(f'<rect x="46" y="46" width="988" height="1258" fill="none" stroke="{C["neon"]}" '
      'stroke-width="1.5" opacity="0.55"/>')
    for x, y in [(46, 46), (1034, 46), (46, 1304), (1034, 1304)]:
        a(f'<path d="M{x - 22},{y} H{x + 22} M{x},{y - 22} V{y + 22}" stroke="{C["neon"]}" '
          'stroke-width="2"/>')

    a(f'<text x="86" y="104" font-family="{font}" font-size="22" fill="{C["neon"]}" '
      'letter-spacing="6">FIELD LOG / OUTING</text>')
    a(f'<text x="994" y="104" text-anchor="end" font-family="{font}" font-size="22" '
      f'fill="{C["dim"]}" letter-spacing="3">{esc(card["date"])}</text>')
    a(f'<line x1="86" y1="126" x2="994" y2="126" stroke="{C["neon"]}" stroke-width="1" opacity="0.35"/>')

    a(f'<text x="86" y="196" font-family="{font}" font-size="24" fill="{C["dim"]}" '
      'letter-spacing="4">SITE</text>')
    a(f'<text x="86" y="252" font-family="{font}" font-size="42" font-weight="700" '
      f'fill="{C["ink"]}">{esc(card["place"])}</text>')
    a(f'<text x="994" y="252" text-anchor="end" font-family="{font}" font-size="24" '
      f'fill="{C["amber"]}">{esc(card["companions"])}</text>')

    y = 356
    for line in wrap(str(card["title"]), 11, 2):
        a(f'<text x="86" y="{y}" font-family="{font}" font-size="64" font-weight="700" '
          f'fill="{C["ink"]}" letter-spacing="1">{esc(line)}</text>')
        y += 82

    pts = [(150, 726), (400, 646), (650, 736), (900, 636)]
    d = f"M{pts[0][0]},{pts[0][1]} " + " ".join(f"L{p[0]},{p[1]}" for p in pts[1:])
    a(f'<path d="{d}" fill="none" stroke="{C["neon"]}" stroke-width="16" opacity="0.10"/>')
    a(f'<path d="{d}" fill="none" stroke="{C["neon"]}" stroke-width="6" opacity="0.28"/>')
    a(f'<path d="{d}" fill="none" stroke="{C["neon"]}" stroke-width="2"/>')

    labels = [] if card_tier(card) == "simple" else card.get("stops", [])[:4]
    for i, (px, py) in enumerate(pts[: len(labels)]):
        a(f'<circle cx="{px}" cy="{py}" r="16" fill="{C["bg"]}" stroke="{C["neon"]}" stroke-width="2"/>')
        a(f'<circle cx="{px}" cy="{py}" r="6" fill="{C["neon"]}"/>')
        a(f'<text x="{px}" y="{py + 58}" text-anchor="middle" font-family="{font}" '
          f'font-size="21" fill="{C["ink"]}">{esc(labels[i])}</text>')

    a(f'<line x1="86" y1="898" x2="994" y2="898" stroke="{C["neon"]}" stroke-width="1" opacity="0.3"/>')
    a(f'<text x="86" y="958" font-family="{font}" font-size="22" fill="{C["dim"]}" '
      'letter-spacing="5">KEY MOMENT</text>')
    a(f'<text x="86" y="1032" font-family="{font}" font-size="50" font-weight="700" '
      f'fill="{C["ink"]}">{esc(card["one_thing"])}</text>')

    qtext, qtag, from_child = quote_of(card)
    if qtext:
        a(f'<rect x="86" y="1078" width="8" height="96" fill="{C["pink"]}"/>')
        a(f'<text x="118" y="1128" font-family="{font}" font-size="30" '
          f'fill="{"#E8F1F8" if from_child else C["dim"]}">{esc(qtext)}</text>')
        tagline = f"— {qtag} / VERBATIM" if from_child else "— QUOTED ON SITE"
        a(f'<text x="118" y="1180" font-family="{font}" font-size="20" '
          f'fill="{C["pink"] if from_child else C["dim"]}" letter-spacing="2">{esc(tagline)}</text>')

    a(f'<line x1="86" y1="1218" x2="994" y2="1218" stroke="{C["neon"]}" stroke-width="1" opacity="0.3"/>')
    a(f'<text x="86" y="1268" font-family="{font}" font-size="23" fill="{C["dim"]}">'
      f'{esc(card.get("next", ""))}</text>')
    a(f'<text x="994" y="1268" text-anchor="end" font-family="{font}" font-size="21" '
      f'fill="{C["neon"]}" letter-spacing="3">{esc(card["plan_id"])}</text>')
    a(f'<text x="994" y="1300" text-anchor="end" font-family="{font}" font-size="18" '
      f'fill="#4A5A68" letter-spacing="2">22.5431N 114.0579E / ILLUSTRATIVE</text>')
    a("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- line


def svg_line(card, font):
    """速写本：白底黑线，只描边不填色，斜线打暗部。"""
    C = dict(
        paper="#FCFCFA",
        ink="#1A1A1A",
        accent="#2F6B5A",
        accent2="#C2703A",
        dim="#6B6B6B",
    )
    out = []
    a = out.append
    a(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
    a(f'<rect width="{W}" height="{H}" fill="{C["paper"]}"/>')

    # 外框：双线
    a(f'<rect x="60" y="60" width="960" height="1230" fill="none" stroke="{C["ink"]}" stroke-width="2"/>')
    a(f'<rect x="72" y="72" width="936" height="1206" fill="none" stroke="{C["ink"]}" stroke-width="0.8" opacity="0.4"/>')

    # 页眉
    a(f'<text x="104" y="128" font-family="{font}" font-size="22" fill="{C["dim"]}" '
      'letter-spacing="4">出行记录 / 速写本</text>')
    a(f'<text x="976" y="128" text-anchor="end" font-family="{font}" font-size="22" '
      f'fill="{C["dim"]}" letter-spacing="2">{esc(card["date"])}</text>')
    a(f'<line x1="104" y1="152" x2="976" y2="152" stroke="{C["ink"]}" stroke-width="2"/>')

    # 地点
    a(f'<text x="104" y="220" font-family="{font}" font-size="34" font-weight="600" '
      f'fill="{C["ink"]}">{esc(card["place"])}</text>')
    a(f'<text x="976" y="220" text-anchor="end" font-family="{font}" font-size="23" '
      f'fill="{C["dim"]}">{esc(card["companions"])}</text>')

    # 标题：线稿风用细笔画，按内容均分成两行，避免末行单字
    title = str(card["title"])
    if len(title) <= 10:
        lines = [title]
    else:
        half = (len(title) + 1) // 2
        lines = [title[:half], title[half:]]
    y = 330 if len(lines) == 1 else 300
    for line in lines[:2]:
        a(f'<text x="104" y="{y}" font-family="{font}" font-size="58" font-weight="400" '
          f'fill="{C["ink"]}" letter-spacing="1">{esc(line)}</text>')
        y += 80

    # 线稿插画：铜钱（只描边）
    cx, cy, r = 872, 372, 64
    a(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{C["ink"]}" stroke-width="2.2"/>')
    a(f'<circle cx="{cx}" cy="{cy}" r="{r - 9}" fill="none" stroke="{C["ink"]}" stroke-width="0.9" opacity="0.55"/>')
    a(f'<rect x="{cx - 24}" y="{cy - 24}" width="48" height="48" fill="none" stroke="{C["ink"]}" stroke-width="2.2"/>')
    for i in range(7):
        a(f'<line x1="{cx - 70 + i * 20}" y1="{cy + 86}" x2="{cx - 46 + i * 20}" y2="{cy + 62}" '
          f'stroke="{C["ink"]}" stroke-width="0.8" opacity="0.35"/>')

    # 强调：最有反应
    a(f'<line x1="104" y1="466" x2="976" y2="466" stroke="{C["ink"]}" stroke-width="0.9" opacity="0.5"/>')
    a(f'<circle cx="116" cy="512" r="5" fill="{C["accent"]}"/>')
    a(f'<text x="136" y="521" font-family="{font}" font-size="21" fill="{C["dim"]}" '
      'letter-spacing="3">最有反应的一段</text>')
    a(f'<text x="104" y="600" font-family="{font}" font-size="48" font-weight="500" '
      f'fill="{C["ink"]}">{esc(card["one_thing"])}</text>')

    # 站点：编号圆圈 + 细线
    y = 686
    for i, s in enumerate(card.get("stops", [])[:5]):
        a(f'<circle cx="120" cy="{y - 9}" r="13" fill="none" stroke="{C["ink"]}" stroke-width="1.6"/>')
        a(f'<text x="120" y="{y - 3}" text-anchor="middle" font-family="{font}" font-size="13" '
          f'fill="{C["ink"]}">{i + 1}</text>')
        a(f'<text x="152" y="{y}" font-family="{font}" font-size="30" fill="{C["ink"]}">{esc(s)}</text>')
        a(f'<line x1="152" y1="{y + 16}" x2="976" y2="{y + 16}" stroke="{C["ink"]}" '
          'stroke-width="0.7" opacity="0.28"/>')
        y += 74

    # 原话
    if card.get("quote"):
        qy = 1120
        a(f'<line x1="104" y1="{qy}" x2="976" y2="{qy}" stroke="{C["accent"]}" stroke-width="1.4"/>')
        a(f'<text x="104" y="{qy + 56}" font-family="{font}" font-size="30" fill="{C["ink"]}" '
          f'font-style="italic">「{esc(card["quote"])}」</text>')

    # 页脚
    a(f'<line x1="104" y1="1216" x2="976" y2="1216" stroke="{C["ink"]}" stroke-width="1.6"/>')
    a(f'<text x="104" y="1258" font-family="{font}" font-size="22" fill="{C["dim"]}">'
      f'{esc(card.get("next", ""))}</text>')
    a(f'<text x="976" y="1258" text-anchor="end" font-family="{font}" font-size="20" '
      f'fill="{C["dim"]}" letter-spacing="2">{esc(card["plan_id"])}</text>')
    a("</svg>")
    return "".join(out)


def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base}-{n}{ext}"):
        n += 1
    return f"{base}-{n}{ext}"


def main():
    ap = argparse.ArgumentParser(description="把 card.json 渲染成 JPG")
    ap.add_argument("card")
    ap.add_argument("out")
    ap.add_argument("--style", choices=["cartoon", "neon", "line"], default=None)
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--quality", type=int, default=92)
    ap.add_argument("--font", default=None)
    args = ap.parse_args()

    if not os.path.isfile(args.card):
        print(f"[error] 找不到 {args.card}", file=sys.stderr)
        return 1
    try:
        with open(args.card, encoding="utf-8") as f:
            card = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[error] card.json 不是合法 JSON：{e}", file=sys.stderr)
        return 1

    missing = [k for k in REQUIRED if not card.get(k)]
    if missing:
        print(f"[error] 缺字段：{', '.join(missing)}", file=sys.stderr)
        return 1

    try:
        import cairosvg
        from PIL import Image
    except ImportError:
        print(
            "[error] 缺依赖。请运行：pip install cairosvg pillow --break-system-packages",
            file=sys.stderr,
        )
        return 2

    style = args.style or card.get("style") or (
        "neon" if card.get("age_band") == "teen" else "cartoon"
    )
    if style not in ("cartoon", "neon", "line"):
        style = "cartoon"
    font = pick_font(prefer_serif=(style == "neon"), requested=args.font)
    render = {"cartoon": svg_cartoon, "neon": svg_neon, "line": svg_line}[style]
    svg = render(card, font)

    try:
        png = cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            output_width=int(W * args.scale),
            output_height=int(H * args.scale),
        )
        im = Image.open(io.BytesIO(png)).convert("RGB")
        im = im.resize((W, H), Image.LANCZOS)
        out = unique_path(args.out)
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        im.save(out, "JPEG", quality=args.quality, optimize=True)
    except Exception as e:
        print(f"[error] 渲染失败：{e}", file=sys.stderr)
        return 2

    print(f"已导出 {out}（{W}x{H}，{style}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
