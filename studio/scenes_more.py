"""进阶篇（故事九到十三）的分镜：提示词、微调、多模态、扩散模型、智能体。

写法和 scenes.py 一样：每个场景函数拿到配音时间表 T，返回 [(开始时刻, 画面函数)]。
"""
import math
import random
from functools import lru_cache

from engine import (INK, SS, W, H, Canvas, appear, bezier, clamp, ease_io, ease_out, lerp, lerp2, mix, pop, prog,
                    text_width, wave)
from actors import *  # noqa: F401,F403
from scenes import arc_arrow, check_row, heart, night_say, panel, scene, strike, tok_layout
from scenes_terms import Map, brick_row, dash, msg

OR, IN, LI, MA, LB = "#FF9F43", "#6C7BFF", "#8CC63F", "#D35CC0", "#4DD6FF"
WHITE = "#FFFFFF"
SOFT = "#55607F"


# ============================================================ 小工具
def lines_card(c, x, y, w, h, t, t0, title="", n=5, fill=PAPER, title_size=30, tc=INK):
    k = panel(c, x, y, w, h, t, t0, fill=fill)
    if k > 0.97:
        top = y - h / 2 + 26
        if title:
            c.text(title, x, top + 18, title_size, tc, 900)
            top += 56
        for i in range(n):
            ww = (w - 70) * (0.92 if i % 3 else 0.75)
            c.rect(x - w / 2 + 35, top + i * 32, ww, 12, "#C9D3EE", r=6, line=None)
    return k


@lru_cache(maxsize=32)
def qa_card_sprite(q, a):
    w, h = 300, 200
    c = Canvas.sprite(w + 12, h + 12)
    c.rect(8, 9, w, h, INK, r=18, line=None)
    c.rect(2, 2, w, h, PAPER, r=18, lw=3.5)
    c.rect(2, 2, w, 72, "#E2E5FF", r=18, lw=3.5)
    c.rect(4, 50, w - 4, 24, "#E2E5FF", line=None)
    c.line([(2, 74), (2 + w, 74)], INK, 3)
    for i, ln in enumerate(wrap(q, 22, w - 36, 900)[:2]):
        c.text(ln, 2 + w / 2, 30 + i * 28, 22, INK, 900)
    for i, ln in enumerate(wrap(a, 22, w - 36, 800)[:3]):
        c.text(ln, 2 + w / 2, 104 + i * 30, 22, "#3B4AD8", 800)
    return c.im


def school(c, x, y, s=1.0, k=1.0):
    if k <= 0.01:
        return
    s *= k
    c.rect(x - 150 * s + 8, y - 60 * s + 9, 300 * s, 170 * s, INK, r=10, line=None)
    c.rect(x - 150 * s, y - 60 * s, 300 * s, 170 * s, PAPER, r=10 * s, lw=4)
    c.poly([(x - 172 * s, y - 56 * s), (x, y - 150 * s), (x + 172 * s, y - 56 * s)], IN, lw=4)
    c.line([(x, y - 150 * s), (x, y - 210 * s)], INK, 4)
    c.poly([(x, y - 210 * s), (x + 46 * s, y - 196 * s), (x, y - 182 * s)], CORAL, lw=2.5)
    c.rect(x - 28 * s, y + 40 * s, 56 * s, 70 * s, "#B07A4F", r=8 * s, lw=3)
    for dx in (-100, 70):
        c.rect(x + dx * s, y - 30 * s, 50 * s, 44 * s, "#CDE8FF", r=6 * s, lw=3)
    c.rect(x - 90 * s, y - 108 * s, 180 * s, 40 * s, SUN, r=8 * s, lw=3)
    c.text("助手学校", x, y - 88 * s, 26 * s, INK, 900)


def speaker(c, x, y, s=1.0, t=0.0):
    c.poly([(x - 30 * s, y - 14 * s), (x - 12 * s, y - 14 * s), (x + 8 * s, y - 32 * s), (x + 8 * s, y + 32 * s),
            (x - 12 * s, y + 14 * s), (x - 30 * s, y + 14 * s)], "#5A6280", lw=3)
    for i in range(3):
        k = 0.6 + 0.4 * math.sin(t * 6 - i)
        c.arc(x + 10 * s, y, (18 + i * 14) * s, (18 + i * 14) * s, -50, 50, LI if k > 0.7 else "#AEB6CF", 5)


def video_icon(c, x, y, s=1.0):
    c.rect(x - 44 * s, y - 32 * s, 88 * s, 64 * s, "#5A6280", r=10 * s, lw=3)
    c.poly([(x - 12 * s, y - 16 * s), (x + 18 * s, y), (x - 12 * s, y + 16 * s)], WHITE, line=None)


def text_icon(c, x, y, s=1.0):
    doc_icon(c, x, y, 76, 92, PAPER, 0, s=s)
    c.text("Aa", x, y + 2 * s, 34 * s, INK, 900)


def pencil(c, x, y, s=1.0, rot=-35):
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)

    def P(u, v):
        return (x + (ca * u - sa * v) * s, y + (sa * u + ca * v) * s)

    c.poly([P(-60, -10), P(40, -10), P(40, 10), P(-60, 10)], SUN, lw=3)
    c.poly([P(40, -10), P(62, 0), P(40, 10)], "#F5D6B0", lw=3)
    c.poly([P(-60, -10), P(-72, -10), P(-72, 10), P(-60, 10)], "#FF9BB0", lw=3)


def umbrella(c, x, y, s=1.0):
    c.pie(x, y, 46 * s, 180, 360, "#4FA8F5", INK, 3)
    c.line([(x, y), (x, y + 50 * s)], INK, 4)
    c.arc(x + 8 * s, y + 50 * s, 8 * s, 8 * s, 0, 180, INK, 4)


def tiles_of(spr, n=4):
    w, h = spr.size
    out = []
    for r in range(n):
        for k in range(n):
            out.append((r, k, spr.crop((k * w // n, r * h // n, (k + 1) * w // n, (r + 1) * h // n))))
    return out


def ensure_hat(spr_args):
    return ("painting", spr_args)


# ============================================================ 故事九：没有魔法咒语（提示词）
@scene("s9-1", poster=lambda T: T.mid(1, 0.9))
def s9_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        girl(c, 170, 560, t, mouth="smile", arm_r=70, talk=T.intro < t < T.intro + 1.2)
        search_box(c, 600, 300, 520, "帮我写个故事。", t, T.intro + 0.1, cps=6)
        arrow(c, (875, 300), (985, 300), INK, 6, 16, u=ease_out(prog(t, s[0] + 1.2, 0.3)))
        robot(c, 1110, 575, t, eyes="normal", s=0.8)
        term_badge(c, "提示词 Prompt", t, w(0, "提示词"), OR)
        say(c, "你发给 AI 的话", 600, 385, t, w(0, "提示词") + 0.4, 30, SOFT)

    def b(c, t):
        girl(c, 200, 560, t, eyes="up", mouth="smile")
        thought_cloud(c, 330, 205, 430, 210, pop(t, s[1] - 0.05, 0.45))
        chips = (("睡前故事", "#FFE3C6"), ("讲给5岁表弟", "#CDE8FF"), ("主角是芝麻", "#FFD3E0"), ("300字以内", "#CFF3DF"))
        pos = ((250, 165), (420, 165), (255, 232), (420, 232))
        for i, ((lab, col), (x, y)) in enumerate(zip(chips, pos)):
            chip(c, lab, x, y, t, s[1] + 0.4 + i * 0.15, size=22, fill=col, shadow=2, padx=12)
        dash(c, (640, 120), (640, 600), INK, 4, 14, 10, a=0.45)
        robot(c, 1010, 575, t, eyes="think", mouth="flat", s=0.9)
        chip(c, "收到：帮我写个故事。", 990, 210, t, s[1] + 0.3, size=26, fill=PAPER)
        qmark(c, 880, 300, t, w(1, "猜"), s=0.8, col=OR)
        say(c, "它只看得到这句话", 990, 150, t, w(1, "只能"), 26, SOFT, 800)

    def cc(c, t):
        girl(c, 190, 560, t, eyes="normal", mouth="wavy", brows="worry")
        thought_cloud(c, 290, 210, 320, 160)
        chip(c, "芝麻的睡前故事", 300, 210, size=24, fill="#FFE3C6", shadow=2)
        lines_card(c, 780, 320, 380, 320, t, s[2] - 0.05, title="巨龙的故事", n=6)
        robot(c, 1130, 590, t, eyes="happy", mouth="open", s=0.65)
        chip(c, "不是我想要的", 420, 450, t, w(2, "往往"), size=30, fill=RED, color=WHITE, stroke=1.6)
        stamp(c, False, 920, 430, t, w(2, "往往") + 0.3, s=0.6)

    def d(c, t):
        girl(c, 380, 560, t, eyes="happy", mouth="grin", arm_r=150)
        idea_bulb(c, 380, 225, t, s[3] + 0.2, s=1.0)
        robot(c, 900, 560, t, eyes="happy", arm_l=60)
        chip(c, "第一步：把需求说清楚", 660, 140, t, w(3, "说清楚") - 0.3, size=36, fill=OR, color=WHITE, stroke=2)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


PROMPT92 = "请写一个睡前故事，讲给五岁的表弟听。主角是一只叫芝麻的黑白猫，三百字以内，结尾要温暖。"


@scene("s9-2", poster=lambda T: T.mid(1, 0.95))
def s9_2(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        k = panel(c, 580, 320, 780, 300, t, T.intro)
        if k > 0.97:
            chip(c, "提示词", 580, 170, size=26, fill=OR, color=WHITE, stroke=1.6)
            n = int(max(0.0, t - T.intro - 0.3) * 16)
            c.para(PROMPT92[:n], 225, 225, 34, 720, INK, 800)
        robot(c, 1150, 585, t, eyes="scan", s=0.7)

    rows = (("做什么", "写一个睡前故事", "#FFE3C6", "要做什么"), ("给谁看", "讲给五岁的表弟", "#CDE8FF", "写给谁看"),
            ("主角", "黑白猫芝麻", "#FFD3E0", None), ("多长", "三百字以内", "#CFF3DF", "篇幅多长"),
            ("风格", "结尾要温暖", "#E6DFFF", "风格"))

    def b(c, t):
        for i, (lab, val, col, word) in enumerate(rows):
            y = 150 + i * 82
            t0 = w(1, word) if word else s[1] + 0.9
            chip(c, lab, 300, y, t, t0, size=28, fill=col)
            say(c, val, 380, y, t, t0 + 0.15, 32, INK, anchor="lm")
        robot(c, 1060, 575, t, eyes="happy", s=0.85)
        say(c, "越明白，越不用猜", 1060, 250, t, w(1, "越不用"), 32, OR, stroke=2, stroke_color=WHITE)

    def cc(c, t):
        chip(c, "帮我写个故事", 330, 150, t, s[2] - 0.05, size=28, fill="#E6EBF5")
        arrow(c, (330, 186), (330, 226), INK, 5, 15, u=ease_out(prog(t, s[2] + 0.2, 0.3)))
        lines_card(c, 330, 380, 360, 260, t, s[2] + 0.4, title="巨龙的故事", n=4, fill="#F3F4F8")
        stamp(c, False, 470, 290, t, s[2] + 1.2, s=0.55)
        tr = w(2, "讲给五岁小朋友")
        chip(c, "睡前故事 · 讲给5岁 · 300字", 940, 150, t, tr, size=24, fill="#FFE3C6")
        arrow(c, (940, 186), (940, 226), INK, 5, 15, u=ease_out(prog(t, tr + 0.3, 0.3)))
        k = lines_card(c, 940, 380, 360, 260, t, w(2, "三百字以内") + 0.2, title="芝麻的月光散步", n=4)
        if k > 0.97:
            cat_face(c, 1060, 455, 0.32, "#33303A", tux=True)
        stamp(c, True, 1080, 290, t, w(2, "完全不一样"), s=0.55)

    def d(c, t):
        girl(c, 440, 560, t, eyes="happy", mouth="smile", arm_r=95)
        robot(c, 840, 560, t, eyes="happy", arm_l=95)
        chip(c, "很能干 ✓", 840, 210, t, w(3, "能干"), size=30, fill=SUN)
        chip(c, "但要交代清楚", 640, 130, t, w(3, "交代清楚"), size=36, fill=OR, color=WHITE, stroke=2)
        say(c, "新认识的帮手", 440, 230, t, s[3] + 0.4, 28, SOFT)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s9-3", poster=lambda T: T.mid(1, 0.9))
def s9_3(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        girl(c, 200, 560, t, eyes="up", brows="think", mouth="flat")
        for i, (lab, x, y) in enumerate((("要押韵？", 520, 200), ("要顺口？", 780, 260), ("要好玩？", 600, 360))):
            chip(c, lab, x + wave(t, 6, 0.4, i * 0.3), y, t, T.intro + 0.3 + i * 0.3, size=30, fill=PAPER)
        qmark(c, 290, 290, t, s[0] + 0.6, s=0.8, col=OR)
        chip(c, "直接给它看例子！", 880, 470, t, w(0, "例子"), size=34, fill=OR, color=WHITE, stroke=2)

    def b(c, t):
        k = panel(c, 470, 270, 660, 270, t, s[1] - 0.05)
        if k > 0.97:
            chip(c, "提示词", 470, 135, size=24, fill=OR, color=WHITE, stroke=1.4)
            c.text("示范：", 175, 205, 28, SOFT, 800, anchor="lm")
            l1, l2 = "芝麻芝麻黑又白，", "抓到毛球不放开。"
            c.text(l1, 270, 205, 34, INK, 900, anchor="lm")
            c.text(l2, 270, 258, 34, INK, 900, anchor="lm")
            for txt, yy, idx in ((l1, 205, 6), (l2, 258, 6)):
                x0 = 270 + text_width(txt[:idx], 34, 900)
                c.line([(x0 + 2, yy + 24), (x0 + 32, yy + 24)], OR, 5)
            c.text("请照这个样子，再编一句。", 175, 330, 28, INK, 800, anchor="lm")
        robot(c, 1140, 585, t, eyes="happy", s=0.7)
        to = w(1, "照着例子")
        k2 = panel(c, 690, 500, 640, 110, t, to, fill="#FFF5EA")
        if k2 > 0.97:
            out = "芝麻芝麻真可爱，饭碗一响跑过来。"
            x0 = 690 - text_width(out, 32, 900) / 2
            c.text(out, x0, 500, 32, INK, 900, anchor="lm")
            for idx in (6, 14):
                xx = x0 + text_width(out[:idx], 32, 900)
                u = ease_out(prog(t, to + 0.6, 0.3))
                if u > 0:
                    c.line([(xx + 2, 526), (xx + 2 + 28 * u, 526)], OR, 5)

    def cc(c, t):
        for i in range(2):
            k = pop(t, s[2] + i * 0.2)
            if k > 0:
                c.crect(250 + 6, 230 + i * 150 + 7, 300, 110, INK, r=16, line=None, s=k)
                c.crect(250, 230 + i * 150, 300, 110, "#FFF5EA", r=16, lw=3.5, s=k)
                if k > 0.97:
                    chip(c, f"示范 {i + 1}", 160, 190 + i * 150, size=20, fill=OR, color=WHITE, shadow=2, padx=10)
                    for j in range(2):
                        c.rect(130, 222 + i * 150 + j * 28, 240 - j * 50, 12, "#E8C9A8", r=6, line=None)
        arrow(c, (420, 300), (520, 300), INK, 6, 16, u=ease_out(prog(t, s[2] + 0.6, 0.3)))
        robot(c, 640, 470, t, eyes="scan", mouth="flat", s=0.75, shadow=False)
        arrow(c, (760, 300), (860, 300), INK, 6, 16, u=ease_out(prog(t, s[2] + 1.0, 0.3)))
        for i in range(3):
            k = pop(t, s[2] + 1.2 + i * 0.25)
            if k > 0:
                c.crect(1030 + 6, 170 + i * 135 + 7, 300, 100, INK, r=16, line=None, s=k)
                c.crect(1030, 170 + i * 135, 300, 100, "#FFF5EA", r=16, lw=3.5, s=k)
                if k > 0.97:
                    for j in range(2):
                        c.rect(910, 158 + i * 135 + j * 28, 240 - j * 50, 12, "#E8C9A8", r=6, line=None)
        term_badge(c, "少样本提示 few-shot", t, w(2, "少样本提示"), OR)

    def d(c, t):
        lines_card(c, 340, 320, 400, 360, t, s[3] - 0.05, title="写一大段要求", n=7, fill="#F3F4F8")
        tg = w(3, "管用")
        k = pop(t, s[3] + 0.6)
        if k > 0:
            c.crect(900 + 7, 300 + 8, 360, 130, INK, r=18, line=None, s=k)
            c.crect(900, 300, 360, 130, "#FFF5EA", r=18, lw=4, s=k)
            if k > 0.97:
                c.text("芝麻芝麻黑又白，", 900, 280, 30, INK, 900)
                c.text("抓到毛球不放开。", 900, 322, 30, INK, 900)
        chip(c, "给一个好例子", 900, 200, t, s[3] + 0.6, size=30, fill=OR, color=WHITE, stroke=1.6)
        chip(c, "往往更管用！", 900, 445, t, tg, size=32, fill=GREEN, color=WHITE, stroke=1.8)
        say(c, "vs", 620, 320, t, s[3] + 0.3, 44, SOFT)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s9-4", poster=lambda T: T.mid(1, 0.95))
def s9_4(T):
    s, e, w = T.s, T.e, T.word

    def question(c, t, t0, y=190):
        k = panel(c, 560, y, 760, 140, t, t0)
        if k > 0.97:
            c.text("芝麻每天吃 2 条小鱼干，", 560, y - 25, 32, INK, 900)
            c.text("一袋有 15 条，够吃几天？", 560, y + 25, 32, INK, 900)

    def a(c, t):
        question(c, t, T.intro)
        wrong = t > s[0] + 1.6
        robot(c, 1110, 575, t, eyes="x" if wrong else "happy", mouth="wavy" if wrong else "open", s=0.8)
        bubble(c, "8 天！", 1150, 340, t, s[0] + 0.5, tail="br", size=32)
        stamp(c, False, 1215, 280, t, s[0] + 1.6, s=0.6)
        say(c, "8 天要吃 16 条，不够呀！", 560, 330, t, s[0] + 1.9, 30, RED)

    def b(c, t):
        steps = ("① 每天吃 2 条", "② 15 ÷ 2 = 7 余 1", "③ 够吃 7 天，还剩 1 条")
        ts = [s[1] + 0.3 + i * 0.9 for i in range(3)]
        for i, (txt, t0) in enumerate(zip(steps, ts)):
            chip(c, txt, 120, 170 + i * 80, t, t0, size=28, fill=PAPER, anchor="lm")
        for g in range(8):
            gx, gy = 700 + (g % 4) * 140, 240 + (g // 4) * 170
            t0 = ts[1] + g * 0.12
            k = pop(t, t0, 0.35)
            if k <= 0:
                continue
            c.crect(gx, gy, 118, 92, "#EAF6FF" if g < 7 else "#FFE3E3", r=16, lw=3, s=k)
            if k > 0.97:
                if g < 7:
                    fish(c, gx, gy - 18, 1.0, "#7CC4FF")
                    fish(c, gx, gy + 18, 1.0, "#7CC4FF")
                    say(c, f"第{g + 1}天", gx, gy + 62, size=20, color=INK, weight=800)
                else:
                    fish(c, gx, gy, 1.0, OR)
                    say(c, "剩 1 条", gx, gy + 62, size=20, color=RED, weight=800)
        stamp(c, True, 470, 410, t, ts[2] + 0.9, s=0.7)

    def cc(c, t):
        notebook(c, 400, 330, 440, 360, ["15 ÷ 2 = ?", "2 × 7 = 14", "15 − 14 = 1", "→ 够吃 7 天，剩 1 条"], t,
                 [s[2] + 0.3 + i * 0.6 for i in range(4)], title="草稿")
        robot(c, 920, 575, t, eyes="think", mouth="flat", s=0.9)
        dots = "思考中" + "." * (1 + int(t * 3) % 3)
        chip(c, dots, 920, 230, t, s[2], size=26, fill=PAPER)
        term_badge(c, "推理模型", t, w(2, "推理模型"), OR)

    def d(c, t):
        k = panel(c, 620, 330, 700, 420, t, s[3] - 0.05)
        if k > 0.97:
            items = (("r", "帮我写一句生日祝福", s[3] + 0.2), ("l", "祝你生日快乐，万事如意，心想事成……", s[3] + 0.8),
                     ("r", "能再短一点、更可爱吗？", w(3, "追问")), ("l", "生日快乐，小喵喵！", w(3, "修改") + 0.2))
            for i, (side, text, t0) in enumerate(items):
                kk = pop(t, t0, 0.35)
                msg(c, text, 300 if side == "l" else 940, 190 + i * 85, side, 24,
                    PAPER if side == "l" else "#FFE3C6", k=kk)
            stamp(c, True, 800, 445, t, w(3, "修改") + 0.6, s=0.5)
        chip(c, "好答案，常常是聊出来的", 620, 585, t, w(3, "聊出来"), size=28, fill=OR, color=WHITE, stroke=1.6)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事十：比特上学记（微调）
@scene("s10-1", poster=lambda T: T.mid(1, 0.9))
def s10_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        bookshelf(c, 120, 150, 460, 330)
        robot(c, 350, 590, t, eyes="happy", mouth="smile", s=0.9)
        term_badge(c, "基础模型", t, w(0, "基础模型"), IN)
        chip(c, "只做过预训练", 900, 250, t, s[0] + 0.5, size=32, fill=PAPER)
        chip(c, "会接字，还不会答题", 900, 340, t, s[0] + 1.2, size=30, fill="#E2E5FF")

    def b(c, t):
        girl(c, 170, 560, t, mouth="open", arm_r=70, talk=s[1] < t < s[1] + 1.0)
        bubble(c, "天空为什么是蓝的？", 230, 300, t, s[1] - 0.05, tail="bl", size=28)
        k = panel(c, 800, 320, 520, 320, t, s[1] + 0.6)
        if k > 0.97:
            chip(c, "比特写的", 800, 160, size=22, fill=IN, color=WHITE, shadow=2, stroke=1.2)
            qs = ("天空为什么是蓝的？", "大海为什么是咸的？", "星星为什么会眨眼？", "月亮为什么会跟着我走？", "……")
            for i, q in enumerate(qs):
                kk = pop(t, s[1] + 0.9 + i * 0.4, 0.3)
                if kk > 0:
                    c.text(q, 575, 200 + i * 52, 28, INK, 800, anchor="lm", sc=kk)
        robot(c, 1170, 590, t, eyes="scan", mouth="flat", s=0.6)
        qmark(c, 300, 200, t, w(1, "不一定"), s=0.7, col=IN)

    def cc(c, t):
        k = panel(c, 330, 330, 440, 380, t, s[2] - 0.05, fill="#FFFDF5")
        if k > 0.97:
            c.text("十万个为什么 · 习题单", 330, 175, 26, INK, 900)
            for i, q in enumerate(("1. 天空为什么是蓝的？", "2. 大海为什么是咸的？", "3. 星星为什么会眨眼？", "4. ……")):
                c.text(q, 140, 235 + i * 60, 26, INK, 800, anchor="lm")
        say(c, "网上很多文章长这样", 330, 560, t, w(2, "网上"), 26, SOFT, 800)
        arrow(c, (570, 330), (700, 330), INK, 7, 20, u=ease_out(prog(t, w(2, "因为") - 0.2, 0.4)))
        robot(c, 900, 520, t, eyes="scan", mouth="flat", s=0.85)
        chip(c, "照着这个样子往下写", 920, 160, t, w(2, "因为"), size=28, fill="#E2E5FF")

    def d(c, t):
        school(c, 860, 330, 1.0, pop(t, s[3] - 0.05))
        u = ease_io(prog(t, s[3] + 0.3, 2.2))
        robot(c, lerp(260, 560, u), 575, t, eyes="happy", mouth="open", s=0.85, arm_r=40 + 30 * math.sin(t * 6))
        chip(c, "还得再上几堂课", 330, 160, t, w(3, "上几堂课"), size=32, fill=IN, color=WHITE, stroke=1.8)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


QAS = (("天空为什么是蓝的？", "因为阳光里的蓝光，更容易被空气散射开。"), ("怎么煮鸡蛋？", "水开后放入鸡蛋，再煮八分钟左右。"),
       ("把“谢谢”翻译成英文", "Thank you."))


@scene("s10-2", poster=lambda T: T.mid(1, 0.9))
def s10_2(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        k = panel(c, 520, 320, 520, 300, t, T.intro, fill="#E2E5FF")
        if k > 0.97:
            rnd = random.Random(2)
            for r_ in range(2):
                for kk in range(4):
                    base = rnd.uniform(-90, 90)
                    knob(c, 340 + kk * 120, 260 + r_ * 120, 36, base + 18 * math.sin(t * 2 + kk + r_), IN)
        robot(c, 1060, 575, t, eyes="happy", s=0.85)
        term_badge(c, "微调", t, w(0, "微调"), IN)
        say(c, "在已有的本领上，再调一调", 520, 520, t, w(0, "微调") + 0.4, 30, INK)

    def b(c, t):
        for i, (q, a_) in enumerate(QAS):
            k = pop(t, s[1] + 0.2 + i * 0.35, 0.45)
            if k > 0:
                c.blit(qa_card_sprite(q, a_), 330 + i * 300, 320 + (i % 2) * 30, "mm", s=k, rot=(1 - i) * 5)
        chip(c, "指令 + 好回答", 640, 560, t, w(1, "例子"), size=32, fill=IN, color=WHITE, stroke=1.8)

    def cc(c, t):
        girl(c, 160, 560, t, mouth="open", arm_r=70, talk=s[2] < t < s[2] + 1.0)
        bubble(c, "天空为什么是蓝的？", 220, 300, t, s[2] - 0.05, tail="bl", size=26)
        robot(c, 1080, 575, t, eyes="happy", mouth="open", s=0.85)
        bubble(c, "因为蓝光更容易被空气散射开。", 1130, 330, t, w(2, "看到问题"), tail="br", size=26, max_w=330)
        stamp(c, True, 760, 200, t, w(2, "有用的回答"), s=0.6)
        for kk in range(3):
            knob(c, 560 + kk * 90, 470, 30, 40 * ease_io(prog(t, s[2] + 0.4 + kk * 0.2, 0.6)) - 20, IN)
        say(c, "参数再调一点", 650, 535, t, s[2] + 0.4, 24, SOFT, 800)

    def d(c, t):
        u = ease_out(prog(t, s[3] + 0.1, 1.0))
        c.text("预训练的数据", 200, 230, 28, INK, 900, anchor="lm")
        c.rect(200, 255, 40 + 960 * u, 46, "#AEB6CF", r=12, lw=3)
        c.text("指令微调的数据", 200, 350, 28, INK, 900, anchor="lm")
        u2 = ease_out(prog(t, w(3, "少得多") - 0.2, 0.6))
        if u2 > 0:
            c.rect(200, 375, 40 + 70 * u2, 46, IN, r=12, lw=3)
            say(c, "少得多", 340, 398, t, w(3, "少得多"), 30, IN, anchor="lm")
        robot(c, 1080, 590, t, eyes="star", mouth="open", s=0.7, arm_l=140, arm_r=140)
        sparkles(c, t, 1080, 440, 80, 5, SUN, t0=w(3, "像换了个人"))
        term_badge(c, "指令微调", t, w(3, "指令微调"), IN)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s10-3", poster=lambda T: T.mid(1, 0.9))
def s10_3(T):
    s, e, w = T.s, T.e, T.word
    answers = (("A", "别难过了。"), ("B", "我在这儿陪你。想聊聊发生了什么吗？"), ("C", "难过的时候，可以去散散步。"))

    def ans_card(c, x, y, lab, text, t, t0, hi=False):
        k = panel(c, x, y, 320, 150, t, t0, fill="#F0F2FF" if not hi else "#FFF7D6")
        if k > 0.97:
            chip(c, lab, x - 130, y - 75, size=24, fill=IN, color=WHITE, shadow=2, padx=12, stroke=1.2)
            c.para(text, x, y - 34, 26, 270, INK, 800, align="m")

    def a(c, t):
        chip(c, "朋友难过了，我该说什么？", 640, 140, t, T.intro, size=30, fill=PAPER)
        ans_card(c, 400, 330, "A", answers[0][1], t, s[0] + 0.3)
        ans_card(c, 880, 330, "B", answers[1][1], t, s[0] + 0.7, hi=t > w(0, "比较") + 0.5)
        chip(c, "人能比出 B 更好", 880, 470, t, w(0, "比较") + 0.5, size=28, fill=GREEN, color=WHITE, stroke=1.6)

    def b(c, t):
        order = {"B": 1, "C": 2, "A": 3}
        for i, (lab, text) in enumerate(answers):
            x = 250 + i * 390
            ans_card(c, x, 300, lab, text, t, s[1] + 0.2 + i * 0.3)
            r = order[lab]
            k = pop(t, w(1, "排序") + r * 0.3, 0.4)
            if k > 0:
                c.circle(x, 430, 34 * k, SUN if r == 1 else PAPER, lw=3.5)
                c.text(str(r), x, 430, 38 * k, INK, 900)
        robot(c, 640, 600, t, eyes="scan", s=0.55)

    def cc(c, t):
        cx, cy, R = 560, 340, 165
        nodes = (("写回答", -90, "#E2E5FF", s[2] + 0.1), ("人来排序", 30, SUN, s[2] + 0.5), ("调整模型", 150, IN, s[2] + 0.9))
        for i in range(3):
            a0, a1 = nodes[i][1] + 26, nodes[(i + 1) % 3][1] - 26 + (360 if i == 2 else 0)
            arc_arrow(c, cx, cy, R, a0, a1, INK, 6, 20, u=ease_out(prog(t, nodes[(i + 1) % 3][3] + (0.4 if i == 2 else 0), 0.45)))
        for lab, ang, col, t0 in nodes:
            a_ = math.radians(ang)
            chip(c, lab, cx + math.cos(a_) * R, cy + math.sin(a_) * R, t, t0, size=30, fill=col,
                 color=WHITE if col == IN else INK, stroke=1.6 if col == IN else 0)
        u = ease_io(prog(t, w(2, "越来越"), 1.5))
        c.text("人们满意的程度", 1030, 190, 24, INK, 900)
        c.rect(990, 220, 80, 300, PAPER, r=16, lw=3.5)
        c.rect(990, 520 - (60 + 220 * u), 80, 60 + 220 * u, LEAF, r=16, lw=3.5)

    def d(c, t):
        chip(c, "人类反馈", 330, 300, t, w(3, "人类反馈"), size=40, fill=SUN)
        say(c, "+", 520, 300, t, w(3, "强化学习") - 0.2, 50, INK)
        chip(c, "强化学习", 710, 300, t, w(3, "强化学习"), size=40, fill="#E2E5FF")
        say(c, "=", 895, 300, t, w(3, "RLHF") - 0.2, 50, INK)
        chip(c, "RLHF", 1040, 300, t, w(3, "RLHF"), size=46, fill=IN, color=WHITE, stroke=2.4)
        term_badge(c, "基于人类反馈的强化学习", t, s[3] + 0.1, IN, size=34)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s10-4", poster=lambda T: T.mid(1, 0.95))
def s10_4(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        cx, cy = 640, 330
        c.circle(cx, cy, 190, PAPER, lw=4)
        c.circle(cx, cy, 130, "#F0F2FF", lw=3)
        target = -60
        ang = lerp(-170, target, ease_io(prog(t, s[0] + 0.6, 1.4)))
        a1 = math.radians(target)
        sparkle(c, cx + math.cos(a1) * 215, cy + math.sin(a1) * 215, 26, SUN, line=INK)
        say(c, "人们的期望", cx + math.cos(a1) * 215 + 90, cy + math.sin(a1) * 215 - 30, t, s[0] + 0.3, 26, INK)
        a2 = math.radians(ang)
        arrow(c, (cx, cy), (cx + math.cos(a2) * 170, cy + math.sin(a2) * 170), IN, 10, 26)
        c.circle(cx, cy, 16, IN, lw=3)
        term_badge(c, "对齐", t, w(0, "对齐"), IN)

    def b(c, t):
        items = (("有帮助", "有帮助", CORAL), ("诚实", "诚实", SKY), ("不伤害", "不造成伤害", LEAF))
        for i, (lab, word, col) in enumerate(items):
            x = 300 + i * 340
            k = pop(t, w(1, word) - 0.1, 0.45)
            if k <= 0:
                continue
            c.crect(x + 7, 320 + 8, 250, 250, INK, r=30, line=None, s=k)
            c.crect(x, 320, 250, 250, PAPER, r=30, lw=4, s=k)
            if k > 0.97:
                if i == 0:
                    heart(c, x, 290, 1.9, CORAL)
                elif i == 1:
                    c.circle(x, 290, 44, SKY, lw=3.5)
                    c.line([(x - 18, 290), (x - 4, 305), (x + 20, 276)], WHITE, 8)
                else:
                    shield_icon(c, x, 290, 1.1, LEAF)
                c.text(lab, x, 390, 34, INK, 900)

    def cc(c, t):
        chip(c, "用户：教我偷偷溜进邻居家！", 420, 160, t, s[2] - 0.05, size=28, fill="#FFE3E3")
        robot(c, 1000, 575, t, eyes="normal", mouth="flat", s=0.85)
        shield_icon(c, 850, 470, 1.0, LEAF)
        bubble(c, "这个不行，会伤害别人。要是钥匙丢了，可以请开锁师傅帮忙。", 1060, 330, t, w(2, "拒绝"), tail="br",
               size=24, max_w=330)
        chip(c, "拒绝 ＋ 安全的替代办法", 420, 470, t, w(2, "替代"), size=30, fill=GREEN, color=WHITE, stroke=1.6)
        strike(c, 420, 160, 400, t, w(2, "拒绝") + 0.3)

    def d(c, t):
        robot(c, 640, 590, t, eyes="happy", mouth="open", s=1.05, arm_l=140, arm_r=40)
        hy = robot_head_y(590, 1.05) + 6 + wave(t, 7 * 1.05, 0.55, 640 * 0.001)
        mortarboard(c, 640, hy - 4, 1.0, t)
        chip(c, "聪明", 360, 300, t, w(3, "聪明"), size=40, fill=SUN)
        say(c, "+", 480, 300, t, w(3, "靠谱") - 0.2, 46, INK)
        chip(c, "靠谱", 920, 300, t, w(3, "靠谱"), size=40, fill=IN, color=WHITE, stroke=2)
        confetti(c, t, w(3, "靠谱") + 0.2, 640, 260, power=0.8)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事十一：比特长出了眼睛（多模态）
MODES = (("文字", "text"), ("图片", "image"), ("声音", "sound"), ("视频", "video"))


def mode_icon(c, kind, x, y, t, s=1.0):
    if kind == "text":
        text_icon(c, x, y, s)
    elif kind == "image":
        c.blit(photo_sprite("flower"), x, y, "mm", s=0.5 * s)
    elif kind == "sound":
        speaker(c, x, y, s, t)
    else:
        video_icon(c, x, y, s)


@scene("s11-1", poster=lambda T: T.mid(2, 0.6))
def s11_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        for i, (lab, kind) in enumerate(MODES):
            x = 250 + i * 260
            k = pop(t, w(0, lab) - 0.1 if i else T.intro + 0.2)
            if k > 0:
                c.crect(x + 7, 300 + 8, 200, 200, INK, r=28, line=None, s=k)
                c.crect(x, 300, 200, 200, PAPER, r=28, lw=4, s=k)
                if k > 0.97:
                    mode_icon(c, kind, x, 280, t)
                    c.text(lab, x, 365, 30, INK, 900)
        term_badge(c, "模态", t, w(0, "模态"), LI)

    def b(c, t):
        for i, (lab, kind) in enumerate(MODES):
            x, y = 200, 150 + i * 120
            mode_icon(c, kind, x, y, t, 0.75)
            arrow(c, (x + 70, y), (520, 360), INK, 5, 15, u=ease_out(prog(t, s[1] + 0.2 + i * 0.15, 0.4)))
        glow = appear(t, s[1] + 0.9, 0.5)
        if glow > 0:
            c.glow(720, 380, 200, LI, a=glow)
        robot(c, 720, 590, t, eyes="star" if glow > 0.5 else "normal", mouth="open", s=1.05)
        term_badge(c, "多模态", t, w(1, "多模态"), LI)

    def cc(c, t):
        girl(c, 160, 560, t, eyes="happy", mouth="smile", arm_r=110)
        photo(c, "flower", 360, 290, t, s[2] - 0.05, rot=-6, s=0.9)
        robot(c, 1110, 585, t, eyes="scan", s=0.75)
        tw_ = w(2, "听懂")
        if t < tw_ + 0.6:
            bubble(c, "这是金鸡菊。", 1150, 340, t, w(2, "看图"), tail="br", size=28)
        else:
            bubble(c, "是麻雀在叽叽喳喳。", 1150, 340, t, tw_ + 0.6, tail="br", size=26)
        if t > tw_ - 0.2:
            for i in range(14):
                hgt = 14 + 34 * abs(math.sin(i * 1.7 + t * 6))
                c.rect(560 + i * 18, 470 - hgt / 2, 10, hgt, LI, r=5, lw=2)

    def d(c, t):
        k = panel(c, 640, 330, 620, 420, t, s[3] - 0.05)
        if k > 0.97:
            c.rect(330, 120, 620, 62, LI, r=30, lw=4)
            c.rect(332, 150, 616, 32, LI, line=None)
            c.line([(330, 182), (950, 182)], INK, 4, caps=False)
            c.text("和比特聊天", 640, 151, 28, WHITE, 900, stroke=2)
            if pop(t, s[3] + 0.2) > 0:
                c.blit(photo_sprite("flower"), 820, 265, "mm", s=0.48 * pop(t, s[3] + 0.2))
            msg(c, "这是什么花？", 380, 330, "l", 24, PAPER, k=pop(t, s[3] + 0.5, 0.35))
            k2 = pop(t, w(3, "能听"), 0.35)
            if k2 > 0.97:
                c.rect(700, 375, 230, 52, "#E6F6D0", r=26, lw=3)
                for i in range(9):
                    hgt = 8 + 22 * abs(math.sin(i * 1.3 + t * 5))
                    c.rect(740 + i * 18, 401 - hgt / 2, 8, hgt, LI, r=4, line=None)
            msg(c, "是金鸡菊！录音里是麻雀在叫～", 380, 470, "l", 22, PAPER, k=pop(t, w(3, "能听") + 0.6, 0.35))

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s11-2", poster=lambda T: T.mid(1, 0.95))
def s11_2(T):
    s, e, w = T.s, T.e, T.word
    spr = photo_sprite("flower").crop((32, 32, 316, 332))
    tiles = tiles_of(spr, 4)
    TS = 1.7
    tw_, th_ = spr.width / SS * TS, spr.height / SS * TS

    def tile_xy(r, k, gap):
        return (640 - tw_ / 2 + (k + 0.5) * tw_ / 4 + (k - 1.5) * gap,
                320 - th_ / 2 + (r + 0.5) * th_ / 4 + (r - 1.5) * gap)

    def a(c, t):
        bubble(c, "这是什么花？", 300, 260, t, T.intro + 0.1, tail="bm", size=30)
        xs, _ = brick_row(["这是", "什么", "花", "？"], 30, 300, 8)
        for i, tk in enumerate(["这是", "什么", "花", "？"]):
            brick(c, tk, xs[i], 380, t, s[0] + 0.4 + i * 0.12, col=BRICK_COLS[i], size=30)
        say(c, "文字 → 积木", 300, 470, t, s[0] + 0.6, 28, SOFT)
        photo(c, "flower", 900, 300, t, T.intro + 0.3, s=1.1)
        say(c, "图片 → ？", 900, 470, t, s[0] + 0.9, 28, SOFT)

    def b(c, t):
        u = ease_out(prog(t, s[1] + 0.5, 0.8))
        for r, k, tile in tiles:
            x, y = tile_xy(r, k, 26 * u)
            c.rect(x - tw_ / 8 + 4, y - th_ / 8 + 5, tw_ / 4, th_ / 4, INK, r=4, line=None, a=u)
            c.blit(tile, x, y, "mm", s=TS)
            if u > 0.05:
                c.rect(x - tw_ / 8, y - th_ / 8, tw_ / 4, th_ / 4, None, r=4, line=INK, lw=2.5, a=u)
        chip(c, "切成小方块", 640, 560, t, w(1, "小方块"), size=30, fill=LI)
        say(c, "每一块 ≈ 一个图片版的 token", 640, 120, t, w(1, "图片版"), 30, INK)

    def cc(c, t):
        tm = s[2] + 0.2
        for i, (r, k, tile) in enumerate(tiles[4:12]):
            u = ease_io(prog(t, tm + i * 0.1, 0.8))
            x0, y0 = tile_xy(r, k, 26)
            x1, y1 = 150 + i * 62, 450
            c.blit(tile, lerp(x0, x1, u), lerp(y0, y1, u), "mm", s=lerp(TS, 1.3, u))
        xs, _ = brick_row(["这是", "什么", "花", "？"], 22, 820, 6)
        for i, tk in enumerate(["这是", "什么", "花", "？"]):
            brick(c, tk, xs[i], 452, t, w(2, "文字的向量") + i * 0.1, col=BRICK_COLS[i], size=22)
        if t > w(2, "排在一起"):
            c.rect(110, 405, 860, 92, None, r=20, line=LI, lw=5)
            arrow(c, (990, 450), (1060, 450), INK, 6, 16, u=ease_out(prog(t, w(2, "交给"), 0.3)))
        robot(c, 1160, 585, t, eyes="scan", s=0.65)
        say(c, "图片和文字排成一队", 540, 560, t, w(2, "排在一起"), 28, INK)

    def d(c, t):
        robot(c, 640, 590, t, eyes="star", mouth="open", s=1.05, arm_l=140, arm_r=140)
        chip(c, "图 ＋ 文，一起理解", 640, 160, t, s[3], size=40, fill=LI)
        photo(c, "flower", 320, 330, t, s[3] + 0.2, s=0.7, rot=-6)
        chip(c, "这是什么花？", 960, 330, t, s[3] + 0.4, size=30, fill=PAPER)
        sparkles(c, t, 640, 320, 140, 6, SUN, t0=s[3] + 0.6)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


W113 = {"猫": (2.4, 7.4), "狗": (3.8, 8.2), "大海": (6.4, 2.6), "沙滩": (8.8, 4.6), "花朵": (6.6, 8.0)}


@scene("s11-3", poster=lambda T: T.mid(1, 0.9))
def s11_3(T):
    s, e, w = T.s, T.e, T.word

    def words(c, M, t, t0):
        for i, x in enumerate(W113):
            pin(c, x, *M(*W113[x]), t, t0 + i * 0.12, col=LI)

    def a(c, t):
        M = Map(640, 350, 900, 480)
        M.draw(c, t, T.intro)
        words(c, M, t, T.intro + 0.3)
        tp = w(0, "图片也放")
        for i, (kind, near) in enumerate((("cat_tux", "猫"), ("beach", "大海"), ("flower", "花朵"))):
            px, py = M(*W113[near])
            photo(c, kind, px + 110, py + 30, t, tp + i * 0.3, s=0.42, rot=(i - 1) * 6)

    def b(c, t):
        M = Map(640, 350, 900, 480)
        M.draw(c, t, -1)
        words(c, M, t, -1)
        for kind, near, t0 in (("cat_tux", "猫", w(1, "猫的照片")), ("beach", "大海", w(1, "海边的照片"))):
            px, py = M(*W113[near])
            k = pop(t, t0, 0.4)
            if k > 0:
                c.line([(px, py), (px + 110, py + 30)], LI, 5)
                photo(c, kind, px + 110, py + 30, t, -1, s=0.5 * k, rot=-4)
        photo(c, "flower", M(*W113["花朵"])[0] + 110, M(*W113["花朵"])[1] + 30, t, -1, s=0.42, a=0.5)

    def cc(c, t):
        pairs = (("cat_orange", "一只橘猫"), ("beach", "海边的晴天"), ("flower", "一朵黄色的花"))
        for i, (kind, cap) in enumerate(pairs):
            y = 190 + i * 140
            t0 = s[2] + 0.2 + i * 0.4
            photo(c, kind, 330, y, t, t0, s=0.55)
            u = ease_out(prog(t, t0 + 0.3, 0.4))
            if u > 0:
                c.line([(420, y), (lerp(420, 640, u), y)], LI, 5)
            chip(c, cap, 780, y, t, t0 + 0.5, size=28, fill=PAPER)
        chip(c, "大量的“图片 + 文字说明”", 1080, 330, t, w(2, "大量"), size=24, fill=LI)

    def d(c, t):
        chip(c, "找一张有猫的照片", 300, 220, t, s[3] - 0.05, size=28, fill=PAPER)
        arrow(c, (470, 220), (600, 220), INK, 6, 16, u=ease_out(prog(t, s[3] + 0.4, 0.3)))
        photo(c, "cat_tux", 720, 220, t, s[3] + 0.6, s=0.6)
        stamp(c, True, 820, 160, t, s[3] + 0.9, s=0.45)
        photo(c, "beach", 300, 450, t, w(3, "描述"), s=0.6)
        arrow(c, (400, 450), (530, 450), INK, 6, 16, u=ease_out(prog(t, w(3, "描述") + 0.3, 0.3)))
        chip(c, "这是一张海边的晴天照片", 800, 450, t, w(3, "描述") + 0.6, size=28, fill=PAPER)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s11-4", poster=lambda T: T.mid(0, 0.95))
def s11_4(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        k = pop(t, T.intro)
        if k > 0:
            c.blit(family_photo_sprite(), 470, 320, "mm", s=1.3 * k)
        robot(c, 1080, 575, t, eyes="happy" if t < s[0] + 1.2 else "x", s=0.8)
        bubble(c, "五个人。", 1120, 330, t, T.intro + 0.4, tail="br", size=30)
        stamp(c, False, 1190, 270, t, s[0] + 1.2, s=0.55)
        if t > s[0] + 1.6:
            c.circle(470 + (196 - 156) * 1.3, 320 + (128 - 111) * 1.3, 34, None, RED, 5)
            chip(c, "其实是六个", 470, 520, t, s[0] + 1.6, size=30, fill=RED, color=WHITE, stroke=1.6)

    def b(c, t):
        boxes = (("数很多小东西", w(1, "数清")), ("看模糊的小字", w(1, "看清")), ("判断精确位置", w(1, "判断")))
        for i, (lab, t0) in enumerate(boxes):
            x = 250 + i * 390
            k = panel(c, x, 320, 330, 300, t, t0 - 0.1)
            if k < 0.97:
                continue
            if i == 0:
                rnd = random.Random(5)
                for _ in range(26):
                    c.circle(x + rnd.uniform(-120, 120), 290 + rnd.uniform(-80, 70), 9, rnd.choice([SUN, CORAL, SKY]),
                             lw=2)
            elif i == 1:
                c.blit(ticket_sprite(), x, 290, "mm", s=0.95)
            else:
                for gx in range(-120, 121, 40):
                    c.line([(x + gx, 190), (x + gx, 390)], "#E1E7F5", 2, caps=False)
                c.circle(x + 18, 280, 16, CORAL, lw=3)
                say(c, "左？右？", x, 400, t, t0 + 0.3, 24, SOFT)
            c.text(lab, x, 450, 28, INK, 900)

    def cc(c, t):
        photo(c, "cat_orange", 420, 310, t, s[2] - 0.05, s=1.2)
        bubble(c, "一只戴着帽子的猫。", 900, 280, t, s[2] + 0.4, tail="bl", size=30)
        g = appear(t, s[2] + 0.6, 0.4)
        if g > 0:
            dash(c, (360, 190), (480, 190), RED, 4, a=g)
            dash(c, (380, 150), (460, 150), RED, 4, a=g)
            dash(c, (380, 150), (360, 190), RED, 4, a=g)
            dash(c, (460, 150), (480, 190), RED, 4, a=g)
        stamp(c, False, 560, 200, t, w(2, "有模有样"), s=0.6)
        chip(c, "图里根本没有帽子", 900, 420, t, w(2, "有模有样") + 0.3, size=30, fill=RED, color=WHITE, stroke=1.6)

    def d(c, t):
        c.blit(family_photo_sprite(), 760, 320, "mm", s=1.1)
        girl(c, 330, 560, t, eyes="happy", mouth="smile", arm_r=120)
        mx = 700 + 120 * math.sin(t * 1.2)
        magnifier(c, mx, 300, 48)
        chip(c, "重要的事，自己再看看", 760, 545, t, w(3, "核对") - 0.3, size=30, fill=LI)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事十二：从雪花点里画画（扩散模型）
PA = ("#E8454B", 0, 1, "")
PB = ("#4F7BE8", 0, 1, "")
PC = ("#E8454B", 1, 1, "")
PERR = ("#E8454B", 0, 2, "猫獏散歨")


def paint(c, x, y, args, noise=0.0, seed=3, s=1.0):
    spr = painting_sprite(*args)
    if noise > 0.02:
        spr = blurred(("painting", args), round(min(12, noise * 12) / 2) * 2)
    c.blit(spr, x, y, "mm", s=s)
    if noise > 0.01:
        c.blit(noise_sprite(seed, 360, 270), x, y, "mm", s=s, a=min(1.0, noise * 1.05))


@scene("s12-1", poster=lambda T: T.mid(2, 0.55))
def s12_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        girl(c, 170, 560, t, mouth="open", arm_r=80, talk=T.intro < t < T.intro + 1.5)
        bubble(c, "画一只戴红帽子的猫，\n在月亮上散步！", 230, 300, t, T.intro, tail="bl", size=26, max_w=320)
        easel(c, 840, 330, 360, 270, pop(t, s[0] + 0.3))
        if t > s[0] + 0.5:
            paint(c, 840, 330, PA, noise=1.0, seed=5)
        term_badge(c, "扩散模型", t, w(0, "扩散模型"), MA)

    def b(c, t):
        easel(c, 640, 340, 360, 270)
        paint(c, 640, 340, PA, noise=1.0, seed=5)
        chip(c, "一开始：全是随机噪点", 640, 135, t, w(1, "随机噪点"), size=30, fill=PAPER)
        pencil(c, 180, 300, 1.0)
        strike(c, 180, 300, 170, t, w(1, "一笔一笔") + 0.4)
        say(c, "不是一笔一笔画", 180, 380, t, w(1, "一笔一笔"), 26, SOFT)

    def cc(c, t):
        easel(c, 640, 340, 360, 270)
        u = prog(t, s[2] + 0.2, T.dur(2) * 0.9)
        paint(c, 640, 340, PA, noise=1 - ease_io(u) ** 0.8, seed=5)
        chip(c, f"第 {int(1 + u * 29)} / 30 步", 1080, 300, size=30, fill=PAPER)
        say(c, "噪点越来越少", 1080, 370, t, s[2] + 0.4, 28, SOFT)

    def d(c, t):
        easel(c, 640, 340, 360, 270)
        paint(c, 640, 340, PA)
        sparkles(c, t, 640, 330, 220, 7, SUN, t0=s[3])
        girl(c, 180, 560, t, eyes="happy", mouth="grin", arm_r=150)
        bubble(c, "哇！", 240, 300, t, s[3] + 0.3, tail="bl", size=34)
        chip(c, "几十步之后", 1080, 300, t, w(3, "几十步"), size=30, fill=MA, color=WHITE, stroke=1.6)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s12-2", poster=lambda T: T.mid(0, 0.9))
def s12_2(T):
    s, e, w = T.s, T.e, T.word
    levels = (0.0, 0.3, 0.55, 0.8, 1.0)
    xs = (160, 400, 640, 880, 1120)

    def frames(c, t, t0, rev=False):
        spr = photo_sprite("cat_orange")
        for i, (x, lv) in enumerate(zip(xs, levels)):
            k = pop(t, t0 + (4 - i if rev else i) * 0.25, 0.4)
            if k <= 0:
                continue
            c.blit(spr, x, 300, "mm", s=0.85 * k)
            if lv > 0:
                c.blit(noise_sprite(7 + i, spr.width // SS, spr.height // SS), x, 300, "mm", s=0.85 * k, a=lv)

    def a(c, t):
        frames(c, t, T.intro)
        for i in range(4):
            arrow(c, (xs[i] + 82, 300), (xs[i + 1] - 82, 300), MA, 6, 16, u=ease_out(prog(t, T.intro + 0.3 + i * 0.25, 0.3)))
        chip(c, "一步步加噪点 →", 640, 470, t, s[0] + 0.5, size=32, fill=PAPER)

    def b(c, t):
        frames(c, t, -1)
        for i in range(4):
            arrow(c, (xs[i + 1] - 82, 400), (xs[i] + 82, 400), LEAF, 6, 16, u=ease_out(prog(t, s[1] + 0.4 + (3 - i) * 0.3, 0.3)))
        chip(c, "← 猜出噪点，擦掉它", 640, 470, t, w(1, "猜出"), size=32, fill=LEAF, color=WHITE, stroke=1.6)
        robot(c, 640, 640, t, eyes="think", s=0.5, shadow=False)

    def cc(c, t):
        kinds = ("cat_orange", "fox", "beach", "dog", "flower", "cat_white", "teddy", "cat_black", "cat_box",
                 "cat_gray", "beach", "flower")
        for i, kd in enumerate(kinds):
            x, y = 180 + (i % 6) * 120, 220 + (i // 6) * 150
            photo(c, kd, x, y, t, s[2] + i * 0.06, s=0.5, rot=(i * 23) % 11 - 5)
        arrow(c, (900, 300), (980, 300), INK, 6, 16, u=ease_out(prog(t, s[2] + 0.8, 0.3)))
        robot(c, 1110, 575, t, eyes="star", s=0.8)
        chip(c, "看过几亿张图", 1100, 190, t, s[2] + 1.0, size=28, fill=MA, color=WHITE, stroke=1.6)

    def d(c, t):
        easel(c, 640, 340, 360, 270)
        u = ease_io(prog(t, s[3] + 0.2, T.dur(3) * 0.85))
        spr = painting_sprite(*PA)
        c.blit(spr, 640, 340, "mm")
        nz = noise_sprite(5, 360, 270)
        cut = int(nz.width * u)
        if cut < nz.width:
            rest = nz.crop((cut, 0, nz.width, nz.height))
            c.blit(rest, 640 - 180 + cut / SS, 340, "lm")
        ex = 640 - 180 + 360 * u
        eraser(c, ex, 340 + 60 * math.sin(t * 9), 1.3)
        chip(c, "一步步“擦”出一张新图", 640, 140, t, w(3, "擦"), size=30, fill=PAPER)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s12-3", poster=lambda T: T.mid(1, 0.9))
def s12_3(T):
    s, e, w = T.s, T.e, T.word
    words = ("红帽子", "猫", "月亮", "散步")

    def a(c, t):
        easel(c, 640, 340, 360, 270)
        paint(c, 640, 340, PA, noise=1.0, seed=8)
        chip(c, "画猫？", 330, 260, t, s[0] + 0.3, size=34, fill=PAPER, rot=-6)
        chip(c, "画狗？", 960, 300, t, s[0] + 0.6, size=34, fill=PAPER, rot=6)
        qmark(c, 640, 150, t, s[0] + 0.9, s=0.9, col=MA)

    def b(c, t):
        xs, _ = brick_row(list(words), 30, 640, 14)
        for i, wd in enumerate(words):
            brick(c, wd, xs[i], 120, t, s[1] + i * 0.12, col=BRICK_COLS[i], size=30)
        easel(c, 640, 380, 300, 225)
        paint(c, 640, 380, PA, noise=0.85, seed=8, s=300 / 360)
        tv = w(1, "向量")
        for i in range(len(words)):
            ph = ((t - tv) * 0.8 + i * 0.25) % 1
            if t > tv:
                p = bezier((xs[i], 165), (xs[i], 240), (640, 300), ease_io(ph))
                c.circle(p[0], p[1], 9, MA, lw=2.5, a=1 - prog(ph, 0.8, 0.2))
        chip(c, "每一步都看着这句话", 1090, 380, t, w(1, "每一步"), size=26, fill=PAPER)

    def cc(c, t):
        xs, _ = brick_row(list(words), 30, 640, 14)
        u = prog(t, s[2] + 0.2, T.dur(2) * 0.9)
        for i, wd in enumerate(words):
            hi = u > 0.2 + i * 0.18
            brick(c, wd, xs[i], 120, col=BRICK_COLS[i] if hi else "#E1E4EE", size=30)
        easel(c, 640, 380, 300, 225)
        paint(c, 640, 380, PA, noise=1 - ease_io(u), seed=8, s=300 / 360)

    def d(c, t):
        for i, (args, lab, col) in enumerate(((PA, "红帽子", "#E8454B"), (PB, "蓝帽子", "#4F7BE8"))):
            x = 380 + i * 520
            easel(c, x, 360, 300, 225)
            paint(c, x, 360, args, s=300 / 360)
            k = pop(t, s[3] + 0.2 + i * 0.6)
            if k > 0:
                chip(c, lab, x, 160, size=32, fill=col, color=WHITE, stroke=1.8, s=k)
        arrow(c, (560, 360), (700, 360), INK, 7, 20, u=ease_out(prog(t, s[3] + 0.6, 0.4)))

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s12-4", poster=lambda T: T.mid(1, 0.95))
def s12_4(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        for i, (args, seed) in enumerate(((PA, 5), (PC, 9))):
            x = 380 + i * 520
            easel(c, x, 360, 300, 225)
            u = prog(t, T.intro + 0.3 + i * 0.4, 2.0)
            paint(c, x, 360, args, noise=1 - ease_io(u), seed=seed, s=300 / 360)
        say(c, "同一句话，画出不一样的图", 640, 140, t, s[0] + 0.4, 32, INK)

    def b(c, t):
        cfg = (("种子 42", PA, 5), ("种子 42", PA, 5), ("种子 7", PC, 9))
        for i, (lab, args, seed) in enumerate(cfg):
            x = 260 + i * 380
            t0 = s[1] + 0.3 + i * 0.6
            chip(c, lab, x, 170, t, t0, size=30, fill=SUN if "42" in lab else PAPER)
            if t > t0 + 0.2:
                u = prog(t, t0 + 0.2, 1.2)
                c.rect(x - 150 + 6, 360 - 112 + 7, 300, 225, INK, r=10, line=None)
                paint(c, x, 360, args, noise=1 - ease_io(u), seed=seed, s=300 / 360)
        say(c, "=", 450, 360, t, s[1] + 2.0, 60, INK, stroke=3, stroke_color=WHITE)
        say(c, "≠", 830, 360, t, s[1] + 2.4, 60, RED, stroke=3, stroke_color=WHITE)
        term_badge(c, "随机种子", t, w(1, "种子"), MA)

    def cc(c, t):
        easel(c, 640, 340, 360, 270)
        paint(c, 640, 340, PERR)
        g = appear(t, w(2, "多出一条尾巴"), 0.3)
        if g > 0:
            c.circle(550, 335, 62, None, RED, 6, a=g)
            chip(c, "多了一条尾巴", 360, 240, size=26, fill=RED, color=WHITE, stroke=1.4, a=g)
        g2 = appear(t, w(2, "文字"), 0.3)
        if g2 > 0:
            c.circle(760, 378, 60, None, RED, 6, a=g2)
            chip(c, "字是乱的", 1000, 330, size=26, fill=RED, color=WHITE, stroke=1.4, a=g2)

    def d(c, t):
        rules = (("注意版权", "版权"), ("不冒充真人", "冒充真人"), ("不伪造照片", "伪造照片"))
        for i, (lab, word) in enumerate(rules):
            x = 280 + i * 360
            k = pop(t, w(3, word) - 0.1, 0.45)
            if k <= 0:
                continue
            c.crect(x + 7, 320 + 8, 280, 240, INK, r=28, line=None, s=k)
            c.crect(x, 320, 280, 240, PAPER, r=28, lw=4, s=k)
            if k > 0.97:
                if i == 0:
                    c.circle(x, 280, 46, MA, lw=4)
                    c.text("©", x, 278, 56, WHITE, 900)
                elif i == 1:
                    person_icon(c, x, 290, 1.4)
                    c.line([(x - 50, 240), (x + 50, 340)], RED, 9)
                else:
                    c.blit(photo_sprite("beach"), x, 285, "mm", s=0.5)
                    c.line([(x - 50, 240), (x + 50, 340)], RED, 9)
                c.text(lab, x, 400, 30, INK, 900)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事十三：比特会办事了（智能体）
TOOLS = (("天气", weather_icon), ("地图", map_icon), ("日历", calendar_icon), ("蛋糕", cake_icon))


def tool(c, i, x, y, s=1.0):
    TOOLS[i][1](c, x, y, s)


@scene("s13-1", poster=lambda T: T.mid(0, 0.95))
def s13_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        robot(c, 330, 575, t, eyes="happy", mouth="open", s=0.85)
        bubble(c, "我来回答你！", 380, 330, t, T.intro + 0.2, tail="bl", size=28)
        night_say(c, "会说", 330, 160, t, T.intro + 0.4, 40)
        robot(c, 950, 575, t, eyes="scan", mouth="flat", s=0.85, arm_l=120, arm_r=120)
        for i, (x, y) in enumerate(((790, 300), (1110, 300), (790, 470), (1110, 470))):
            if pop(t, w(0, "动手") + i * 0.15) > 0:
                tool(c, i, x, y + wave(t, 6, 0.5, i * 0.25), 0.75)
        night_say(c, "会做", 950, 160, t, w(0, "动手"), 40)
        term_badge(c, "智能体 Agent", t, w(0, "智能体"), "#1FA9D6")

    def b(c, t):
        girl(c, 170, 560, t, mouth="open", arm_r=80, talk=s[1] < t < s[1] + 1.2)
        bubble(c, "帮我把野餐准备好吧！", 230, 300, t, s[1] - 0.05, tail="bl", size=28)
        robot(c, 1060, 575, t, eyes="think", s=0.85)
        thought_cloud(c, 820, 210, 420, 200, pop(t, w(1, "拆成") - 0.4, 0.45))
        steps = ("查天气", "选地点", "列清单", "订蛋糕")
        for i, st in enumerate(steps):
            chip(c, st, 735 + (i % 2) * 170, 175 + (i // 2) * 64, t, w(1, "拆成") + i * 0.2, size=24, fill="#D6F4FF",
                 shadow=2, padx=12)

    def cc(c, t):
        robot(c, 640, 590, t, eyes="scan", mouth="flat", s=0.95)
        pos = ((330, 220), (950, 220), (330, 440), (950, 440))
        for i, (x, y) in enumerate(pos):
            on = int((t - s[2]) * 1.4) % 4 == i and t > s[2]
            if on:
                c.glow(x, y, 90, LB)
            tool(c, i, x, y, 1.0)
            night_say(c, TOOLS[i][0], x, y + 72, t, s[2] + i * 0.1, 26)
        night_say(c, "用工具 → 看结果 → 下一步", 640, 135, t, w(2, "看看结果"), 32)

    def d(c, t):
        chip(c, "会说", 380, 300, t, s[3] - 0.05, size=48, fill=PAPER)
        arrow(c, (480, 300), (760, 300), LB, 10, 28, u=ease_out(prog(t, s[3] + 0.3, 0.6)))
        chip(c, "会做", 880, 300, t, w(3, "会做"), size=48, fill=LB)
        robot(c, 640, 600, t, eyes="star", mouth="open", s=0.8, arm_l=150, arm_r=150)
        sparkles(c, t, 880, 300, 90, 5, SUN, t0=w(3, "会做"))

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


STEPS13 = ("① 查周六的天气", "② 选离大家近的公园", "③ 列出要带的东西", "④ 订一个草莓蛋糕")


@scene("s13-2", poster=lambda T: T.mid(1, 0.95))
def s13_2(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        notebook(c, 470, 330, 460, 380, [], t, [], title="野餐计划", k=pop(t, T.intro))
        robot(c, 1000, 575, t, eyes="scan", mouth="flat", s=0.85)
        pencil(c, 640, 400, 0.9, rot=-50 + 8 * math.sin(t * 8))
        night_say(c, "先做计划", 1000, 180, t, s[0] + 0.3, 36)

    def b(c, t):
        chip(c, "野餐", 640, 150, t, s[1] - 0.05, size=44, fill=SUN)
        for i, st in enumerate(STEPS13):
            x = 190 + i * 300
            t0 = w(1, "拆成") + i * 0.3
            u = ease_out(prog(t, t0 - 0.2, 0.3))
            if u > 0:
                c.line([(640, 185), lerp2((640, 185), (x, 320), u)], LB, 4)
            chip(c, st, x, 340, t, t0, size=24, fill=PAPER)
        night_say(c, "按顺序排好", 640, 470, t, w(1, "按顺序"), 32)

    def cc(c, t):
        notebook(c, 520, 330, 560, 400, list(STEPS13), t, [-1] * 4, title="野餐计划", size=26)
        ticks = [s[2] + 0.3, s[2] + 1.0, w(2, "新情况") + 1.2, w(2, "调整") + 0.4]
        for i, tk in enumerate(ticks):
            stamp(c, True, 770, 220 + i * 46, t, tk, s=0.32)
        tn = w(2, "新情况")
        if t > tn:
            chip(c, "新情况：公园在修路！", 1040, 230, t, tn, size=24, fill="#FFE3E3")
            strike(c, 420, 266, 270, t, tn + 0.3)
            chip(c, "换一个公园", 1040, 300, t, tn + 0.8, size=24, fill="#D6F4FF")

    def d(c, t):
        for i, st in enumerate(STEPS13):
            x, y = 260 + i * 220, 520 - i * 90
            c.rect(x - 110, y, 220, 600 - y, "#1F4A66", r=6, line=LB, lw=3)
            night_say(c, st[2:], x, y + 34, t, s[3] + i * 0.15, 22)
        step = min(3, int(max(0.0, t - s[3] - 0.3) / 0.7))
        frac = clamp((t - s[3] - 0.3) / 0.7 - step)
        x0, y0 = 260 + step * 220, 520 - step * 90
        x1, y1 = 260 + min(3, step + 1) * 220, 520 - min(3, step + 1) * 90
        hop = math.sin(math.pi * frac) * 50 if step < 3 else 0
        rx, ry = (lerp(x0, x1, ease_io(frac)), lerp(y0, y1, ease_io(frac)) - hop) if step < 3 else (x0, y0)
        robot(c, rx, ry, t, eyes="happy", mouth="open", s=0.5, shadow=False)
        c.line([(1100, 110), (1100, 200)], WHITE, 5)
        c.poly([(1100, 110), (1170, 130), (1100, 150)], CORAL, lw=3)
        night_say(c, "野餐！", 1150, 230, t, s[3] + 2.4, 32)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s13-3", poster=lambda T: T.mid(2, 0.9))
def s13_3(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        robot(c, 640, 590, t, eyes="happy", s=0.95, arm_l=60, arm_r=60)
        pos = ((330, 220), (950, 220), (330, 440), (950, 440))
        for i, (x, y) in enumerate(pos):
            u = ease_out(prog(t, w(0, "工具") + i * 0.2, 0.6))
            if u > 0:
                tool(c, i, lerp(640, x, u), lerp(420, y, u), u)
        night_say(c, "光靠脑子里的知识，办不成事", 640, 130, t, s[0] + 0.3, 30)

    def b(c, t):
        items = (("搜索", "搜索"), ("计算器", "计算器"), ("地图", "地图"), ("日历", "日历"))
        for i, (lab, word) in enumerate(items):
            x = 220 + i * 280
            k = pop(t, w(1, word) - 0.1, 0.45)
            if k <= 0:
                continue
            c.crect(x + 7, 320 + 8, 220, 220, INK, r=26, line=None, s=k)
            c.crect(x, 320, 220, 220, PAPER, r=26, lw=4, s=k)
            if k > 0.97:
                if i == 0:
                    magnifier(c, x - 8, 290, 40)
                elif i == 1:
                    calc_icon(c, x, 290, 1.0)
                elif i == 2:
                    map_icon(c, x, 290, 1.1)
                else:
                    calendar_icon(c, x, 290, 1.0)
                c.text(lab, x, 390, 30, INK, 900)

    def cc(c, t):
        robot(c, 160, 585, t, eyes="scan", mouth="flat", s=0.7)
        chip(c, "调用：天气工具（周六）", 470, 220, t, w(2, "什么时候"), size=28, fill=PAPER)
        arrow(c, (660, 220), (760, 220), LB, 6, 16, u=ease_out(prog(t, w(2, "填什么") + 0.3, 0.3)))
        k = panel(c, 960, 300, 330, 200, t, w(2, "返回的结果") - 0.3)
        if k > 0.97:
            weather_icon(c, 900, 290, 1.1)
            c.text("周六", 1030, 250, 28, INK, 900)
            c.text("晴", 1030, 300, 34, INK, 900)
            c.text("25°C", 1030, 350, 30, CORAL, 900)
        stamp(c, True, 1110, 210, t, w(2, "读懂") + 0.4, s=0.5)
        night_say(c, "读懂结果，再决定下一步", 640, 500, t, w(2, "读懂"), 30)

    def d(c, t):
        robot(c, 1000, 575, t, eyes="normal", s=0.85)
        k = panel(c, 560, 260, 560, 220, t, s[3] - 0.05)
        if k > 0.97:
            c.text("订蛋糕要付 88 元，可以吗？", 560, 210, 30, INK, 900)
            tc = w(3, "再动手")
            ok = t > tc
            c.rect(380, 265, 160, 58, GREEN if ok else "#C9F0DD", r=29, lw=3.5)
            c.text("确认", 460, 294, 28, WHITE if ok else INK, 900)
            c.rect(580, 265, 160, 58, "#E6EBF5", r=29, lw=3.5)
            c.text("再想想", 660, 294, 28, INK, 900)
            if t > tc - 0.6:
                hx = lerp(560, 470, ease_out(prog(t, tc - 0.6, 0.5)))
                c.circle(hx, 310, 14, SUN, lw=3)
        girl(c, 230, 575, t, eyes="happy", mouth="smile", s=0.8, arm_r=120)
        night_say(c, "花钱、发消息，先问一句", 560, 450, t, w(3, "先问"), 30)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s13-4", poster=lambda T: T.mid(1, 0.95))
def s13_4(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        cx, cy, R = 600, 340, 170
        nodes = (("想一想", -90, "#D6F4FF", w(0, "想一想")), ("做一步", 30, SUN, w(0, "做一步")),
                 ("看结果", 150, LB, w(0, "看结果")))
        for i in range(3):
            a0, a1 = nodes[i][1] + 26, nodes[(i + 1) % 3][1] - 26 + (360 if i == 2 else 0)
            arc_arrow(c, cx, cy, R, a0, a1, WHITE, 6, 20,
                      u=ease_out(prog(t, nodes[(i + 1) % 3][3] + (0.5 if i == 2 else 0), 0.45)))
        if t > nodes[2][3] + 0.5:
            sp = t - nodes[2][3] - 0.5
            ang = math.radians(-90 + 360 * sp * 0.5)
            c.glow(cx + math.cos(ang) * R, cy + math.sin(ang) * R, 20, LB)
            c.circle(cx + math.cos(ang) * R, cy + math.sin(ang) * R, 10, LB, lw=3)
        for lab, ang, col, t0 in nodes:
            a_ = math.radians(ang)
            chip(c, lab, cx + math.cos(a_) * R, cy + math.sin(a_) * R, t, t0, size=32, fill=col)
        robot(c, 1080, 575, t, eyes="scan", s=0.75)

    def b(c, t):
        tr = s[1] + 0.4
        rain = t > tr
        weather_icon(c, 300, 280, 1.6, rain=rain)
        night_say(c, "下午有雷阵雨！" if rain else "周六晴", 300, 400, t, s[1], 30)
        k = panel(c, 820, 290, 500, 260, t, s[1] + 0.2)
        if k > 0.97:
            c.text("下午 2 点：野餐", 820, 230, 32, INK, 900)
            strike(c, 820, 230, 300, t, w(1, "调整") - 0.2, RED)
            kk = pop(t, w(1, "调整") + 0.3, 0.4)
            if kk > 0:
                c.text("上午 10 点：野餐", 820, 300, 32, LEAF, 900, sc=kk)
                c.text("下午：去图书馆", 820, 355, 28, INK, 800, sc=kk)
        if t > w(1, "改了时间"):
            umbrella(c, 1150, 470, 1.0)

    def cc(c, t):
        robot(c, 800, 575, t, eyes="normal", s=0.9, arm_l=120, arm_r=120)
        for i in range(4):
            ang = -math.pi / 2 + (i - 1.5) * 0.55
            tool(c, i, 800 + math.cos(ang) * 240, 360 + math.sin(ang) * 150, 0.7)
        c.rect(380, 300, 30, 270, "#C9D3EE", r=6, lw=3)
        for k in range(5):
            c.rect(380, 300 + k * 54, 30, 27, RED, line=None)
        c.rect(380, 300, 30, 270, None, r=6, lw=3)
        girl(c, 230, 575, t, eyes="normal", mouth="flat", s=0.8, arm_r=100)
        chip(c, "我来把关", 230, 300, t, w(2, "把关"), size=28, fill=SUN)
        night_say(c, "能做的越多，越需要人把关", 640, 130, t, w(2, "越需要"), 32)

    def d(c, t):
        girl(c, 430, 560, t, eyes="happy", mouth="grin", arm_r=150)
        robot(c, 860, 560, t, eyes="happy", mouth="open", arm_l=60)
        chip(c, "方案 A：上午野餐", 860, 200, t, s[3] + 0.2, size=26, fill=PAPER)
        chip(c, "方案 B：改天再去", 860, 270, t, s[3] + 0.4, size=26, fill=PAPER)
        chip(c, "重要的事，我来决定 ✓", 430, 200, t, w(3, "重要的决定"), size=30, fill=SUN)
        if t > w(3, "自己"):
            c.rect(860 - 140, 200 - 28, 280, 56, None, r=28, line=LEAF, lw=5)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]
