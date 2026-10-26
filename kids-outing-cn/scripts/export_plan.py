#!/usr/bin/env python3
"""把一份方案 JSON 渲染成一张竖长 JPG。不依赖浏览器。

用法:
    python3 scripts/export_plan.py <plan.json> <out.jpg> [--style neon|cartoon|line] [--width 1080]

设计取向与 export_card.py 一致：同一套皮肤。卡片是 4:5 封面，本脚本是整份方案的长图。
"""

import argparse
import io
import json
import os
import sys

from export_card import esc, pick_font

W = 1080
M = 64  # 页边距


_FONT_FILE = None
_FONT_CACHE = {}


def font_file(family):
    """用 fontconfig 查字体文件，供精确量宽。查不到返回 None。"""
    global _FONT_FILE
    if _FONT_FILE is not None:
        return _FONT_FILE or None
    import subprocess

    try:
        out = subprocess.run(
            ["fc-match", "-f", "%{file}", family], capture_output=True, text=True, timeout=10
        )
        _FONT_FILE = out.stdout.strip() if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        _FONT_FILE = ""
    return _FONT_FILE or None


def text_width(s, font_px, family):
    """精确量宽。量不到就按中文字宽估算。"""
    path = font_file(family)
    if path:
        try:
            from PIL import ImageFont

            key = (path, font_px)
            f = _FONT_CACHE.get(key)
            if f is None:
                f = ImageFont.truetype(path, font_px)
                _FONT_CACHE[key] = f
            return f.getlength(s)
        except Exception:
            pass
    return len(s) * font_px * 1.05


def est_chars(px, font_px):
    """兜底估算：中文按 1 字约等于 1 个 font_px 宽。"""
    return max(6, int(px / (font_px * 1.05)))


NO_LINE_START = "，。？！：；、）」』%·…—"


def wrap_text(text, px, font_px, family=None):
    """按实际字宽断行，标点不落行首。"""
    out = []
    for para in str(text).split("\n"):
        if not para:
            out.append("")
            continue
        line = ""
        for ch in para:
            trial = line + ch
            if line and text_width(trial, font_px, family) > px:
                # 标点允许溢出 8% 以内，避免整句拖出画布
                if ch in NO_LINE_START and text_width(trial, font_px, family) <= px * 1.08:
                    out.append(trial)
                    line = ""
                    continue
                if ch in NO_LINE_START and len(line) > 1:
                    out.append(line[:-1])
                    line = line[-1] + ch
                    continue
                out.append(line)
                line = ch
            else:
                line = trial
        if line:
            out.append(line)
    return out


def balance(lines, px, font_px, family):
    """末行太短就把前一行末尾的字挪下来，直到两行长度接近。"""
    if len(lines) < 2:
        return lines
    for _ in range(40):
        last = text_width(lines[-1], font_px, family)
        prev = text_width(lines[-2], font_px, family)
        if last < prev * 0.55 and len(lines[-2]) > 2:
            lines[-2], lines[-1] = lines[-2][:-1], lines[-2][-1] + lines[-1]
            if text_width(lines[-1], font_px, family) > px:
                lines[-2], lines[-1] = lines[-2] + lines[-1][0], lines[-1][1:]
                break
        else:
            break
    return lines


def wrap_title(title, px, font_px, family=None):
    """标题优先在中文冒号或分号处断开，其次按实际字宽。"""
    for sep in ("：", "；"):
        if sep in title:
            head, _, tail = title.partition(sep)
            head_line = head + sep
            if text_width(head_line, font_px, family) <= px:
                return balance([head_line] + wrap_text(tail, px, font_px, family), px, font_px, family)
    return balance(wrap_text(title, px, font_px, family), px, font_px, family)


class Canvas:
    def __init__(self):
        self.parts = []
        self.y = 0

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size, fill, font, weight=None, anchor=None, spacing=None, opacity=None):
        a = ""
        if weight:
            a += f' font-weight="{weight}"'
        if anchor:
            a += f' text-anchor="{anchor}"'
        if spacing:
            a += f' letter-spacing="{spacing}"'
        if opacity:
            a += f' opacity="{opacity}"'
        self.add(
            f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{fill}"{a}>{esc(s)}</text>'
        )

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=1, rx=0, opacity=None):
        a = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}"'
        a += f' fill="{fill}"' if fill else ' fill="none"'
        if stroke:
            a += f' stroke="{stroke}" stroke-width="{sw}"'
        if opacity is not None:
            a += f' opacity="{opacity}"'
        self.add(a + "/>")

    def line(self, x1, y1, x2, y2, stroke, sw=1, opacity=None, dash=None):
        a = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"'
        if opacity is not None:
            a += f' opacity="{opacity}"'
        if dash:
            a += f' stroke-dasharray="{dash}"'
        self.add(a + "/>")


THEMES = {
    "neon": {
        "bg": "#0B0F14",
        "panel": "#0F151C",
        "ink": "#E8F1F8",
        "dim": "#7C8E9E",
        "faint": "#4A5A68",
        "accent": "#38E8D0",
        "accent2": "#FF4D8D",
        "amber": "#FFC24B",
        "rule": "rgba(56,232,208,0.20)",
        "grid": "rgba(56,232,208,0.05)",
        "radius": 2,
    },
    "cartoon": {
        "bg": "#FFF8E7",
        "panel": "#FFECC9",
        "ink": "#241B13",
        "dim": "#5C4A38",
        "faint": "#8A7560",
        "accent": "#E8735A",
        "accent2": "#9B7EDE",
        "amber": "#FFC53D",
        "rule": "rgba(36,27,19,0.55)",
        "grid": "rgba(36,27,19,0.05)",
        "radius": 18,
    },
    "line": {
        "bg": "#FCFCFA",
        "panel": "#F4F4F0",
        "ink": "#1A1A1A",
        "dim": "#6B6B6B",
        "faint": "#9A9A9A",
        "accent": "#2F6B5A",
        "accent2": "#C2703A",
        "amber": "#C2703A",
        "rule": "rgba(26,26,26,0.45)",
        "grid": "rgba(26,26,26,0.04)",
        "radius": 0,
    },
}


def render(plan, font, T, width):
    cw = width - 2 * M
    c = Canvas()
    c.y = 0

    # 顶栏
    c.y = 108
    c.text(M, c.y, plan.get("kicker", ""), 22, T["accent"], font, spacing=6)
    c.text(width - M, c.y, plan.get("date", ""), 22, T["dim"], font, anchor="end", spacing=3)
    c.line(M, c.y + 26, width - M, c.y + 26, T["rule"])

    # 标题
    c.y += 92
    for line in wrap_title(plan["title"], cw, 62, font):
        c.text(M, c.y, line, 62, T["ink"], font, weight="700")
        c.y += 82
    if plan.get("route"):
        c.y += 12
        c.text(M, c.y, plan["route"], 25, T["accent"], font, spacing=1)
        c.y += 44

    # 摘要三行（右上角信息改为正文块）
    for m in plan.get("meta", []):
        c.text(M, c.y, m, 24, T["dim"], font)
        c.y += 38

    # 四格
    c.y += 40
    strip = plan.get("strip", [])[:4]
    if strip:
        gap = 14
        cw4 = (cw - gap * 3) / 4
        top = c.y
        for i, (k, v, s) in enumerate(strip):
            x = M + i * (cw4 + gap)
            c.rect(x, top, cw4, 118, fill=T["panel"], stroke=T["rule"], sw=1, rx=T["radius"])
            c.text(x + 16, top + 30, k, 18, T["faint"], font, spacing=2)
            c.text(x + 16, top + 72, v, 34, T["ink"], font, weight="600")
            c.text(x + 16, top + 101, s, 17, T["dim"], font)
        c.y = top + 118 + 46

    # 分节标题
    def sec(title, note=""):
        c.text(M, c.y, title, 20, T["accent"], font, spacing=5)
        if note:
            c.text(M + 240, c.y, note, 19, T["faint"], font, spacing=1)
        c.line(M, c.y + 16, width - M, c.y + 16, T["rule"])
        c.y += 52

    # 时间轴
    if plan.get("timeline"):
        sec("TIMELINE", "照着走，勿跳步")
        for row in plan["timeline"]:
            t, w, sub, src = (row + ["", "", "", ""])[:4]
            c.text(M, c.y, t, 24, T["accent"], font)
            c.text(M + 120, c.y, w, 25, T["ink"], font, weight="500")
            if src:
                c.text(width - M, c.y, src, 18, T["faint"], font, anchor="end")
            c.y += 34
            if sub:
                for line in wrap_text(sub, cw - 120, 21, font):
                    c.text(M + 120, c.y, line, 21, T["dim"], font)
                    c.y += 30
            c.line(M, c.y - 8, width - M, c.y - 8, T["rule"], opacity=0.5)
            c.y += 16

    # 顺序选项
    if plan.get("orders"):
        c.y += 26
        sec("ROUTES", "可换顺序，换了就重算")
        for o in plan["orders"]:
            lines_t = wrap_text(o["title"], cw - 40, 27, font)
            lines_d = wrap_text(o.get("desc", ""), cw - 40, 22, font)
            h = 26 + len(lines_t) * 36 + len(lines_d) * 31 + 26
            c.rect(M, c.y, cw, h, fill=T["panel"], stroke=T["accent"] if o.get("on") else T["rule"],
                   sw=2 if o.get("on") else 1, rx=T["radius"])
            if o.get("on"):
                c.rect(M, c.y, 3, h, fill=T["accent"])
            yy = c.y + 30
            c.text(M + 20, yy, o["n"], 20, T["accent"], font, spacing=3)
            c.text(width - M - 20, yy, o.get("cost", ""), 19, T["faint"], font, anchor="end")
            yy += 38
            for line in lines_t:
                c.text(M + 20, yy, line, 27, T["ink"], font, weight="600")
                yy += 36
            yy += 4
            for line in lines_d:
                c.text(M + 20, yy, line, 22, T["dim"], font)
                yy += 31
            c.y += h + 14

    # 议题
    if plan.get("issues"):
        c.y += 26
        sec("QUESTIONS", "带一个回家，不用现在答")
        for q, hint in plan["issues"]:
            c.line(M, c.y - 18, M, c.y + 16, T["accent2"], sw=3)
            for line in wrap_text(q, cw - 34, 25, font):
                c.text(M + 20, c.y, line, 25, T["ink"], font)
                c.y += 36
            if hint:
                c.text(M + 20, c.y + 2, hint, 19, T["faint"], font)
                c.y += 30
            c.y += 26

    # 侧栏信息转成正文块
    if plan.get("side"):
        c.y += 14
        sec("DETAILS")
        for head, items in plan["side"]:
            c.text(M, c.y, head, 21, T["accent"], font, spacing=2)
            c.y += 34
            for it in items:
                for line in wrap_text("· " + it, cw - 24, 22, font):
                    c.text(M + 8, c.y, line, 22, T["dim"], font)
                    c.y += 32
            c.y += 14

    # 结论
    if plan.get("verdict"):
        c.y += 26
        sec("VERDICT")
        for head, body in plan["verdict"]:
            c.text(M, c.y, head, 19, T["faint"], font, spacing=3)
            c.y += 32
            for line in wrap_text(body, cw, 22, font):
                c.text(M, c.y, line, 22, T["dim"], font)
                c.y += 32
            c.y += 22

    # 页脚
    c.y += 18
    c.line(M, c.y, width - M, c.y, T["rule"])
    c.y += 36
    f = plan.get("footer", ["", ""])
    c.text(M, c.y, f[0] if f else "", 19, T["faint"], font, spacing=3)
    if len(f) > 1:
        c.text(width - M, c.y, f[1], 19, T["faint"], font, anchor="end", spacing=2)
    c.y += 58

    height = int(c.y)

    # 网格底纹与外框
    bg = [
        f'<rect width="{width}" height="{height}" fill="{T["bg"]}"/>',
        '<defs><pattern id="pg" width="54" height="54" patternUnits="userSpaceOnUse">'
        f'<path d="M54 0H0V54" fill="none" stroke="{T["accent"]}" stroke-width="1" opacity="0.05"/>'
        "</pattern></defs>",
        f'<rect width="{width}" height="{height}" fill="url(#pg)"/>',
    ]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        + "".join(bg)
        + "".join(c.parts)
        + "</svg>"
    )
    return svg, height


def main():
    ap = argparse.ArgumentParser(description="把方案 JSON 渲染成长图 JPG")
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--style", choices=["neon", "cartoon", "line"], default=None)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--quality", type=int, default=92)
    ap.add_argument("--scale", type=float, default=2)
    ap.add_argument("--font", default=None)
    args = ap.parse_args()

    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)
    style = args.style or plan.get("style", "neon")
    T = THEMES[style]
    font = pick_font(prefer_serif=False, requested=args.font)

    try:
        import cairosvg
        from PIL import Image
    except ImportError:
        print("[error] 缺依赖：pip install cairosvg pillow --break-system-packages", file=sys.stderr)
        return 2

    svg, height = render(plan, font, T, args.width)
    png = cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        output_width=int(args.width * args.scale),
        output_height=int(height * args.scale),
    )
    im = Image.open(io.BytesIO(png)).convert("RGB")
    im = im.resize((args.width, height), Image.LANCZOS)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    im.save(args.out, "JPEG", quality=args.quality, optimize=True)
    print(f"已导出 {args.out}（{args.width}x{height}，{style}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
