"""名词篇（故事五到八）的分镜：token、向量、注意力、上下文窗口。

写法和 scenes.py 一样：每个场景函数拿到配音时间表 T，返回 [(开始时刻, 画面函数)]。
"""
import math
import random
from functools import lru_cache

from engine import (INK, W, H, appear, bezier, clamp, ease_io, ease_out, lerp, lerp2, mix, pop, prog,
                    text_width, wave)
from actors import *  # noqa: F401,F403
from scenes import (check_row, night_say, panel, scene, strike, tok_layout)

AZ, RO, AM, TE = "#4FA8F5", "#FF7FA6", "#FFB547", "#22B3A3"
WHITE = "#FFFFFF"
SOFT = "#55607F"


# ============================================================ 小工具
def brick_row(toks, size, x_center, gap=16):
    ws = [brick_w(tk, size) for tk in toks]
    total = sum(ws) + gap * (len(toks) - 1)
    x = x_center - total / 2
    xs = []
    for wd in ws:
        xs.append(x + wd / 2)
        x += wd + gap
    return xs, ws


def dash(c, p0, p1, col=INK, lw=3, seg=12, gap=9, a=1.0):
    L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    if L < 1:
        return
    n = int(L // (seg + gap)) + 1
    for i in range(n):
        u0 = i * (seg + gap) / L
        u1 = min(1.0, (i * (seg + gap) + seg) / L)
        if u0 >= 1:
            break
        c.line([lerp2(p0, p1, u0), lerp2(p0, p1, u1)], col, lw, a=a, caps=False)


def flip_chip(c, text, x, y, sx, size=34, fill=INK, color=WHITE):
    c.blit(chip_sprite(text, size, fill, color, 900, 18, 9, 3.5, 4, None, 0.0), x, y, "mm", sx=max(0.02, sx))


class Map:
    """词语地图：坐标 (u, v) 都在 0~10 之间"""

    def __init__(self, cx, cy, w, h, pad=56):
        self.cx, self.cy, self.w, self.h = cx, cy, w, h
        self.x0, self.x1 = cx - w / 2 + pad, cx + w / 2 - pad
        self.y0, self.y1 = cy + h / 2 - pad, cy - h / 2 + pad

    def __call__(self, u, v):
        return (lerp(self.x0, self.x1, u / 10), lerp(self.y0, self.y1, v / 10))

    def draw(self, c, t, t0, axes=False):
        k = pop(t, t0, 0.45)
        if k <= 0:
            return 0
        c.crect(self.cx + 8, self.cy + 9, self.w, self.h, INK, r=24, line=None, s=k)
        c.crect(self.cx, self.cy, self.w, self.h, "#FFFCF6", r=24, lw=4, s=k)
        if k < 0.97:
            return k
        for i in range(11):
            x = lerp(self.x0, self.x1, i / 10)
            c.line([(x, self.y1 - 22), (x, self.y0 + 22)], "#F5E4EA", 2, caps=False)
            y = lerp(self.y0, self.y1, i / 10)
            c.line([(self.x0 - 22, y), (self.x1 + 22, y)], "#F5E4EA", 2, caps=False)
        if axes:
            arrow(c, (self.x0, self.y0), (self.x1 + 30, self.y0), INK, 4, 14)
            arrow(c, (self.x0, self.y0), (self.x0, self.y1 - 30), INK, 4, 14)
        return k


def open_book(c, x, y, w, h, k=1.0, cover=AZ, page="#FFFDF5"):
    if k <= 0.01:
        return
    c.crect(x + 8, y + 10, w + 28, h + 28, INK, r=22, line=None, s=k)
    c.crect(x, y, w + 28, h + 28, cover, r=22, lw=4, s=k)
    c.crect(x - w / 4 * k, y, w / 2, h, page, r=14, lw=3.5, s=k)
    c.crect(x + w / 4 * k, y, w / 2, h, page, r=14, lw=3.5, s=k)
    if k > 0.97:
        c.line([(x, y - h / 2 + 10), (x, y + h / 2 - 10)], INK, 3)


def receipt(c, x, y, w, h, k=1.0):
    if k <= 0.01:
        return
    w, h = w * k, h * k
    x0, y0, x1, y1 = x - w / 2, y - h / 2, x + w / 2, y + h / 2
    zig = []
    n = 12
    for i in range(n + 1):
        zig.append((x1 - (x1 - x0) * i / n, y1 - (0 if i % 2 == 0 else 14 * k)))
    pts = [(x0, y0), (x1, y0)] + zig
    c.poly([(px + 7, py + 8) for px, py in pts], INK, line=None)
    c.poly(pts, PAPER, lw=3.5)


def hop_arc(c, x0, x1, y, h, col=WHITE, lw=3, a=1.0, head=False):
    pts = [bezier((x0, y), ((x0 + x1) / 2, y - h * 2), (x1, y), i / 24) for i in range(25)]
    c.line(pts, col, lw, a=a)
    if head:
        end, prev = pts[-1], pts[-3]
        ang = math.atan2(end[1] - prev[1], end[0] - prev[0])
        L = 14
        c.poly([end, (end[0] - math.cos(ang - 0.5) * L, end[1] - math.sin(ang - 0.5) * L),
                (end[0] - math.cos(ang + 0.5) * L, end[1] - math.sin(ang + 0.5) * L)], col, line=None, a=a)


def msg(c, text, x, y, side="l", size=22, fill=PAPER, a=1.0, k=1.0):
    """聊天记录里的一条消息"""
    if k <= 0.01:
        return
    tw = text_width(text, size, 800)
    w, h = (tw + 32) * k, (size * 1.3 + 16) * k
    x0 = x if side == "l" else x - w
    c.rect(x0 + 4, y - h / 2 + 5, w, h, INK, r=h / 2, line=None, a=a)
    c.rect(x0, y - h / 2, w, h, fill, r=h / 2, lw=3, a=a)
    if k > 0.97:
        c.text(text, x0 + w / 2, y + 1, size, INK, 800, a=a)


def mini_map(c, x, y, k=1.0):
    if k <= 0.01:
        return
    c.crect(x + 6, y + 7, 130, 104, INK, r=14, line=None, s=k)
    c.crect(x, y, 130, 104, "#FFFCF6", r=14, lw=3.5, s=k)
    if k > 0.97:
        for i in range(1, 4):
            c.line([(x - 65 + i * 32, y - 44), (x - 65 + i * 32, y + 44)], "#F5E4EA", 2, caps=False)
            c.line([(x - 57, y - 52 + i * 26), (x + 57, y - 52 + i * 26)], "#F5E4EA", 2, caps=False)
        for px, py, col in ((-30, 18, RO), (-6, -16, SUN), (32, 10, SKY)):
            c.circle(x + px, y + py, 8, col, lw=2.5)


def q_icon(c, x, y, s=1.0):
    c.poly([(x - 16 * s, y + 32 * s), (x - 30 * s, y + 52 * s), (x + 2 * s, y + 38 * s)], SKY, lw=3)
    c.circle(x, y, 46 * s, SKY, lw=3.5)
    c.text("?", x, y - 2 * s, 56 * s, WHITE, 900, stroke=3)


def k_icon(c, x, y, label="", s=1.0):
    w, h = 132 * s, 74 * s
    c.line([(x - w / 2 + 18 * s, y - h / 2 + 10 * s), (x - w / 2 - 4 * s, y - h / 2 - 22 * s)], INK, 3)
    c.rect(x - w / 2 + 6 * s, y - h / 2 + 7 * s, w, h, INK, r=14 * s, line=None)
    c.rect(x - w / 2, y - h / 2, w, h, SUN, r=14 * s, lw=3.5)
    c.circle(x - w / 2 + 18 * s, y - h / 2 + 16 * s, 7 * s, PAPER, lw=2.5)
    if label:
        c.text(label, x + 6 * s, y + 4 * s, 24 * s, INK, 900)


def v_icon(c, x, y, s=1.0):
    w, h = 104 * s, 86 * s
    c.rect(x - w / 2 + 6 * s, y - h / 2 + 7 * s, w, h, INK, r=10 * s, line=None)
    c.rect(x - w / 2, y - h / 2, w, h, "#D9A066", r=10 * s, lw=3.5)
    c.rect(x - 12 * s, y - h / 2, 24 * s, h, CORAL, line=None)
    c.line([(x - w / 2, y - h * 0.18), (x + w / 2, y - h * 0.18)], INK, 3, caps=False)
    c.line([(x - w / 2, y - h * 0.18), (x - w / 2, y - h / 2)], INK, 3, caps=False)


TOKS5 = ["我", "爱", "吃", "草莓", "蛋糕"]
TCOLS5 = [SKY, SUN, CORAL, "#FF9BB0", LEAF]
IDS5 = ["25110", "23460", "10172", "31415", "2718"]


# ============================================================ 故事五：文字积木（Token）
@scene("s5-1", poster=lambda T: T.mid(1, 0.92))
def s5_1(T):
    s, e, w = T.s, T.e, T.word
    sent, SZ = "我爱吃草莓蛋糕", 58

    def a(c, t):
        t_cut, t_split = s[0] + 0.9, s[0] + 2.1
        tw = text_width(sent, SZ, 900)
        x0 = 640 - tw / 2
        orig, acc = [], 0
        for tk in TOKS5:
            orig.append(x0 + text_width(sent[:acc], SZ, 900) + text_width(tk, SZ, 900) / 2)
            acc += len(tk)
        xs, _ = brick_row(TOKS5, 42, 640, 22)
        if t < t_split:
            k = pop(t, T.intro + 0.05)
            if k > 0:
                c.crect(646, 237, tw + 80, 112, INK, r=28, line=None, s=k)
                c.crect(640, 230, tw + 80, 112, PAPER, r=28, lw=4, s=k)
                if k > 0.97:
                    c.text(sent, 640, 233, SZ, INK, 900)
            acc = 0
            for i, tk in enumerate(TOKS5[:-1]):
                acc += len(tk)
                bx = x0 + text_width(sent[:acc], SZ, 900)
                u = ease_out(prog(t, t_cut + i * 0.18, 0.3))
                if u > 0:
                    dash(c, (bx, 168), (bx, lerp(168, 292, u)), CORAL, 4.5, 10, 7)
        else:
            for i, tk in enumerate(TOKS5):
                u = ease_out(prog(t, t_split + i * 0.09, 0.7))
                x = lerp(orig[i], xs[i], u)
                y = lerp(233, 400, u) - 70 * math.sin(math.pi * u)
                brick(c, tk, x, y, col=TCOLS5[i], size=42)
        robot(c, 1160, 585, t, eyes="scan", mouth="flat", s=0.7)
        term_badge(c, "Token（词元）", t, w(0, "token"), AZ)

    def side(c, t, x, title, col, word, pieces, pcols, label, t0):
        k = panel(c, x, 345, 470, 350, t, t0)
        if k < 0.97:
            return
        chip(c, title, x, 170, size=28, fill=col, color=WHITE, stroke=1.6)
        chip(c, word, x, 250, t, t0 + 0.2, size=38, fill=PAPER)
        arrow(c, (x, 290), (x, 338), INK, 5, 15, u=ease_out(prog(t, t0 + 0.5, 0.3)))
        xs, _ = brick_row(pieces, 36, x, 12)
        for i, (p, pc) in enumerate(zip(pieces, pcols)):
            brick(c, p, xs[i], 388, t, t0 + 0.7 + i * 0.18, col=pc, size=36)
        say(c, label, x, 470, t, t0 + 0.8 + len(pieces) * 0.18, 30, col if col != SKY else "#2A7FC9")

    def b(c, t):
        side(c, t, 330, "常见的词", SKY, "草莓", ["草莓"], ["#FF9BB0"], "整个就是 1 块", s[1] - 0.05)
        side(c, t, 950, "少见的词", CORAL, "喵喵拳", ["喵", "喵", "拳"], [SUN, SUN, CORAL], "拆成好几块",
             w(1, "少见") - 0.3)

    def cc(c, t):
        girl(c, 170, 560, t, eyes="happy", mouth="grin", arm_r=125, talk=s[2] < t < s[2] + 1.0)
        bubble(c, "我新编的词：喵喵拳！", 230, 300, t, s[2] - 0.05, tail="bl", size=28)
        photo(c, "cat_tux", 590, 300, t, s[2] + 0.2, rot=-6)
        if t > s[2] + 0.4:
            for i in range(3):
                ph = (t * 2.2 + i * 0.33) % 1
                x = 690 + 40 * ph
                c.line([(x, 250 + i * 34), (x + 34, 250 + i * 34)], WHITE, 6, a=1 - ph)
            sparkles(c, t, 690, 290, 40, 3, SUN, seed=4, t0=s[2] + 0.4)
        robot(c, 1150, 585, t, eyes="scan", mouth="flat", s=0.7)
        t1, t2 = w(2, "草莓"), w(2, "喵喵拳")
        brick(c, "草莓", 860, 225, t, t1, col="#FF9BB0", size=34)
        chip(c, "= 1 块", 985, 230, t, t1 + 0.3, size=26, fill=PAPER)
        xs, _ = brick_row(["喵", "喵", "拳"], 34, 860, 10)
        for i, p in enumerate(["喵", "喵", "拳"]):
            brick(c, p, xs[i], 355, t, t2 + 0.3 + i * 0.2, col=SUN if p == "喵" else CORAL, size=34)
        chip(c, "= 3 块", 1035, 360, t, t2 + 1.0, size=26, fill=PAPER)

    def d(c, t):
        t0 = s[3] - 0.05
        machine(c, 600, 330, 250, 230, "分词器", t, col=AZ)
        u = ease_io(prog(t, t0 + 0.1, 0.9))
        if u < 1:
            chip(c, "我爱吃草莓蛋糕", lerp(200, 470, u), 330, size=30, fill=PAPER, a=1 - prog(u, 0.8, 0.2),
                 s=lerp(1, 0.7, u))
        xs, _ = brick_row(TOKS5, 28, 1010, 10)
        for i, tk in enumerate(TOKS5):
            v = ease_out(prog(t, t0 + 0.9 + i * 0.22, 0.45))
            if v > 0:
                brick(c, tk, lerp(735, xs[i], v), 330, col=TCOLS5[i], size=28, s=lerp(0.5, 1, v))
        term_badge(c, "分词", t, w(3, "分词"), AZ)
        say(c, "文字 → token", 640, 520, t, w(3, "分词") + 0.3, 34, INK)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s5-2", poster=lambda T: T.mid(1, 0.85))
def s5_2(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        xs, _ = tok_layout(IDS5, 34, x_center=600, gap=26, padx=18)
        for i, tk in enumerate(TOKS5):
            tf = s[0] + 0.4 + i * 0.3
            u = prog(t, tf, 0.45)
            k = pop(t, T.intro + i * 0.08)
            if u < 0.5:
                if k > 0:
                    c.blit(brick_sprite(tk, TCOLS5[i], 44), xs[i], 296, "mm", s=k, sx=max(0.02, 1 - 2 * u))
            else:
                flip_chip(c, IDS5[i], xs[i], 300, 2 * u - 1, size=34)
                say(c, tk, xs[i], 372, t, tf + 0.3, 30, SOFT)
        chip(c, "每块积木都有自己的号码", 600, 470, t, s[0] + 1.8, size=30, fill=SUN)
        say(c, "（号码是举例）", 600, 530, t, s[0] + 2.0, 20, SOFT, 700)
        robot(c, 1160, 585, t, eyes="wide", mouth="o", s=0.7)

    def b(c, t):
        bk = pop(t, s[1] - 0.05, 0.45)
        open_book(c, 520, 330, 720, 400, bk)
        if bk > 0.97:
            c.text("积木目录", 340, 190, 36, INK, 900)
            brick(c, "草莓", 340, 290, col="#FF9BB0", size=40)
            c.text("我认识的所有积木", 340, 400, 24, SOFT, 800)
            rows = [("我", "25110"), ("爱", "23460"), ("吃", "10172"), ("草莓", "31415"), ("蛋糕", "2718"),
                    ("喵", "40712"), ("……", "……")]
            for i, (tk, n) in enumerate(rows):
                kk = pop(t, s[1] + 0.3 + i * 0.25, 0.3)
                if kk <= 0:
                    continue
                y = 172 + i * 50
                c.text(tk, 590, y, 28, INK, 900, anchor="lm", sc=kk)
                dash(c, (660, y + 4), (760, y + 4), "#C9D3EE", 2.5, 4, 6)
                c.text(n, 850, y, 26, "#2A7FC9", 900, anchor="rm", sc=kk)
        term_badge(c, "词表", t, w(1, "词表"), AZ)
        chip(c, "几万到二十多万个", 1090, 230, t, w(1, "几万"), size=26, fill=SUN)
        say(c, "token", 1090, 285, t, w(1, "几万") + 0.2, 28, INK)
        robot(c, 1100, 585, t, eyes="happy", s=0.7)

    def cc(c, t):
        xs, _ = tok_layout(IDS5, 28, x_center=560, gap=24, padx=18)
        for i, tk in enumerate(TOKS5):
            brick(c, tk, xs[i], 165, t, s[2] - 0.05 + i * 0.05, col=TCOLS5[i], size=38)
            ta = s[2] + 0.4 + i * 0.15
            arrow(c, (xs[i], 212), (xs[i], 266), INK, 5, 14, u=ease_out(prog(t, ta, 0.25)))
            chip(c, IDS5[i], xs[i], 305, t, ta + 0.2, size=28, fill=INK, color=WHITE)
        tm = w(2, "真正读进去")
        chip(c, "[ " + ", ".join(IDS5) + " ]", 560, 450, t, tm, size=30, fill=SUN)
        say(c, "模型真正读到的", 560, 395, t, tm, 26, SOFT, 800)
        robot(c, 1130, 585, t, eyes="scan", mouth="flat", s=0.75)
        if t > tm + 0.6:
            for j in range(5):
                ph = ((t - tm - 0.6) * 0.8 + j * 0.2) % 1
                p = bezier((860, 450), (990, 320), (1130, 430), ease_io(ph))
                chip(c, IDS5[j], p[0], p[1], size=18, fill=INK, color=WHITE, shadow=2, padx=8,
                     a=1 - prog(ph, 0.75, 0.25))

    def d(c, t):
        robot(c, 170, 585, t, eyes="happy", mouth="open", s=0.75, arm_r=100)
        y = 300
        tn, tb, tw_ = s[3] + 0.3, w(3, "查词表"), w(3, "变回文字")
        chip(c, "41027", 400, y - 36, t, tn, size=28, fill=INK, color=WHITE)
        chip(c, "9821", 400, y + 36, t, tn + 0.15, size=28, fill=INK, color=WHITE)
        arrow(c, (476, y), (560, y), INK, 6, 16, u=ease_out(prog(t, tb - 0.3, 0.3)))
        k = pop(t, tb - 0.1)
        if k > 0:
            book(c, 640, y, 120, 150, AZ, "词表", s=k)
        arrow(c, (720, y), (800, y), INK, 6, 16, u=ease_out(prog(t, tw_ - 0.3, 0.3)))
        brick(c, "好吃", 878, y - 30, t, tw_, col=SUN, size=32)
        brick(c, "！", 878, y + 50, t, tw_ + 0.15, col=CORAL, size=32)
        arrow(c, (940, y), (1010, y), INK, 6, 16, u=ease_out(prog(t, tw_ + 0.4, 0.3)))
        chip(c, "好吃！", 1110, y, t, tw_ + 0.6, size=40, fill=PAPER)
        chip(c, "编号 → 查词表 → 文字", 640, 480, t, s[3] + 0.6, size=30, fill=SUN)
        say(c, "反过来", 400, 180, t, s[3], 30, "#2A7FC9")

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s5-3", poster=lambda T: T.mid(2, 0.85))
def s5_3(T):
    s, e, w = T.s, T.e, T.word
    rtoks = ["我", "爱", "吃", "草莓", "蛋糕", "，", "真", "好吃"]

    def a(c, t):
        k = pop(t, T.intro + 0.05)
        if k > 0:
            c.crect(646, 407, 900, 70, INK, r=12, line=None, s=k)
            c.crect(640, 400, 900, 70, SUN, r=12, lw=4, s=k)
            if k > 0.97:
                for i in range(31):
                    x = 205 + i * 29
                    c.line([(x, 366), (x, 366 + (28 if i % 5 == 0 else 15))], INK, 3, caps=False)
        xs, _ = brick_row(rtoks, 30, 640, 6)
        for i, tk in enumerate(rtoks):
            brick(c, tk, xs[i], 330, t, T.intro + 0.4 + i * 0.16, col=BRICK_COLS[i % len(BRICK_COLS)], size=30)
        chip(c, "单位：token", 640, 200, t, s[0] + 0.3, size=40, fill=PAPER)
        term_badge(c, "计量单位", t, w(0, "计量单位"), AZ)

    def b(c, t):
        x0, y0, tw_, th = 170, 175, 340, 320
        k = pop(t, s[1] - 0.05)
        if k > 0:
            c.crect(x0 + tw_ / 2 + 7, y0 + th / 2 + 8, tw_, th, INK, r=20, line=None, s=k)
            c.crect(x0 + tw_ / 2, y0 + th / 2, tw_, th, "#EAF6FF", r=20, lw=4, s=k)
        if k > 0.97:
            u = ease_io(prog(t, s[1] + 0.3, 2.4))
            n = int(u * 20)
            for i in range(n):
                r_, cl = divmod(i, 4)
                brick(c, "", x0 + 50 + cl * 80, y0 + th - 42 - r_ * 56, col=BRICK_COLS[i % 7], size=22)
            c.text(f"{n * 1000:,} token" if n < 20 else "装满啦！", x0 + tw_ / 2, y0 - 24, 26, INK, 900)
        chip(c, "一次能读多少", x0 + tw_ / 2, 545, t, s[1] + 0.1, size=30, fill=AZ, color=WHITE, stroke=1.6)
        tv = w(1, "每秒")
        v = 0.15 + 0.62 * ease_io(prog(t, tv, 1.2)) + 0.03 * math.sin(t * 9)
        if pop(t, tv - 0.3) > 0:
            gauge(c, 920, 350, 150, v, lw=22, lo="慢", hi="快")
            c.text("token / 秒", 920, 440, 28, INK, 900)
        chip(c, "每秒能写多少", 920, 545, t, tv - 0.2, size=30, fill=AZ, color=WHITE, stroke=1.6)

    def cc(c, t):
        girl(c, 150, 560, t, mouth="smile", arm_r=80)
        robot(c, 1140, 575, t, eyes="happy", s=0.8)
        rk = pop(t, s[2] - 0.05)
        receipt(c, 640, 330, 420, 400, rk)
        ti, to_, ts = w(2, "你发进去的"), w(2, "它写出来的"), w(2, "都要算")
        if rk > 0.97:
            c.text("AI 服务账单", 640, 168, 32, INK, 900)
            c.line([(450, 200), (830, 200)], "#C9D3EE", 3, caps=False)
            for i, (lab, val, t0) in enumerate((("你发进去的", "1,200 token", ti), ("它写出来的", "800 token", to_))):
                kk = pop(t, t0, 0.3)
                if kk > 0:
                    c.text(lab, 460, 245 + i * 60, 28, INK, 800, anchor="lm", sc=kk)
                    c.text(val, 820, 245 + i * 60, 28, "#2A7FC9", 900, anchor="rm", sc=kk)
            if t >= ts:
                dash(c, (450, 350), (830, 350), INK, 3, 8, 6)
                c.text("合计", 460, 395, 32, INK, 900, anchor="lm", sc=pop(t, ts))
                c.text("2,000 token", 820, 395, 32, CORAL, 900, anchor="rm", sc=pop(t, ts))
                for i in range(3):
                    if pop(t, ts + 0.3 + i * 0.15) > 0:
                        coin(c, 590 + i * 50, 460 - (i % 2) * 6, 20)
        for src, t0, col in (((230, 420), ti, SKY), ((1060, 400), to_, SUN)):
            for j in range(4):
                u = prog(t, t0 + j * 0.15, 0.7)
                if 0 < u < 1:
                    p = bezier(src, ((src[0] + 640) / 2, 90), (640, 150), ease_io(u))
                    brick(c, "", p[0], p[1], col=col, size=18, a=1 - prog(u, 0.65, 0.3))

    def d(c, t):
        chip(c, "同样的意思", 640, 140, t, s[3] - 0.05, size=32, fill=PAPER)
        bubble(c, "那个……我想问一下，就是说，如果我想做一个草莓蛋糕的话，应该怎么做比较好呢？", 230, 410, t,
               s[3] + 0.2, size=26, max_w=380, tail="bl")
        chip(c, "约 30 个 token", 380, 470, t, s[3] + 0.6, size=26, fill="#C9D3EE")
        bubble(c, "草莓蛋糕怎么做？", 860, 410, t, w(3, "简洁"), size=34, tail="bl")
        chip(c, "约 8 个 token", 960, 470, t, w(3, "简洁") + 0.3, size=26, fill=GREEN, color=WHITE, stroke=1.4)
        chip(c, "省下不少！", 960, 540, t, w(3, "省下"), size=32, fill=SUN, rot=-4)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s5-4", poster=lambda T: T.mid(3, 0.85))
def s5_4(T):
    s, e, w = T.s, T.e, T.word
    pieces = ["str", "aw", "berry"]
    pcols = [SKY, SUN, "#FF9BB0"]

    def a(c, t):
        k = pop(t, T.intro + 0.05)
        if k > 0:
            c.crect(646, 217, 520, 120, INK, r=28, line=None, s=k)
            c.crect(640, 210, 520, 120, PAPER, r=28, lw=4, s=k)
            if k > 0.97:
                c.text("strawberry", 640, 206, 72, INK, 900)
        chip(c, "里面有几个字母 r？", 640, 330, t, s[0] + 0.3, size=34, fill=SUN)
        girl(c, 170, 560, t, mouth="smile", arm_r=70, talk=s[0] < t < s[0] + 1.0)
        wrong = t > s[0] + 1.9
        robot(c, 1100, 575, t, eyes="x" if wrong else "think", mouth="wavy" if wrong else "flat", s=0.85)
        bubble(c, "两个？", 1150, 335, t, s[0] + 1.0, tail="br", size=32)
        stamp(c, False, 1215, 270, t, s[0] + 1.9, s=0.6)
        chip(c, "其实是 3 个", 640, 430, t, s[0] + 2.3, size=30, fill=GREEN, color=WHITE, stroke=1.6)

    def b(c, t):
        xs, _ = brick_row(pieces, 50, 600, 18)
        for i, p in enumerate(pieces):
            brick(c, p, xs[i], 300, t, s[1] + 0.3 + i * 0.2, col=pcols[i], size=50)
        chip(c, "比特眼里的 strawberry", 600, 165, t, w(1, "在它眼里") - 0.2, size=30, fill=PAPER)
        say(c, "（不同模型的切法不一样）", 600, 420, t, s[1] + 1.2, 24, SOFT, 700)
        robot(c, 1150, 585, t, eyes="scan", mouth="flat", s=0.7)

    def cc(c, t):
        xs, ws = brick_row(pieces, 50, 600, 18)
        for i, p in enumerate(pieces):
            brick(c, p, xs[i], 300, col=pcols[i], size=50)
            fog = appear(t, s[2] + 0.1 + i * 0.15, 0.4)
            if fog > 0:
                c.rect(xs[i] - ws[i] / 2 + 8, 300 - 18, ws[i] - 16, 60, "#FFFFFF", r=10, line=None, a=0.82 * fog)
                say(c, "?", xs[i], 300 + 12, t, s[2] + 0.3 + i * 0.15, 44, AZ)
        magnifier(c, xs[2] + 20 + wave(t, 12, 0.7), 300 - 10, 46)
        robot(c, 1130, 585, t, eyes="confused", mouth="wavy", s=0.75)
        bubble(c, "1……2……？", 1170, 365, t, s[2] + 0.5, tail="br", size=28)
        say(c, "字母藏在积木里", 600, 450, t, w(2, "藏在"), 34, INK)

    def d(c, t):
        letters = list("strawberry")
        xs, _ = tok_layout(letters, 46, x_center=600, gap=10, padx=14)
        n = 0
        for i, ch in enumerate(letters):
            tl = s[3] + 0.3 + i * 0.22
            isr = ch == "r"
            chip(c, ch, xs[i], 310, t, tl, size=46, fill=SUN if isr else PAPER, padx=14)
            if isr:
                n += 1
                say(c, str(n), xs[i], 228, t, tl + 0.25, 44, CORAL, stroke=3, stroke_color=WHITE)
        t_done = s[3] + 0.3 + 10 * 0.22 + 0.3
        chip(c, "3 个 r ✓", 600, 440, t, t_done, size=42, fill=GREEN, color=WHITE, stroke=2)
        done = t > t_done
        robot(c, 1150, 585, t, eyes="happy" if done else "think", mouth="open" if done else "flat", s=0.7,
              arm_l=140 if done else 10, arm_r=140 if done else 10)
        say(c, "一个字母一个字母地数", 600, 160, t, s[3] + 0.1, 30, SOFT, 800)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事六：词语地图（向量）
W61 = {"猫": (3.2, 7.5), "狗": (4.3, 8.0), "兔子": (2.2, 5.8), "苹果": (7.1, 7.5), "香蕉": (8.3, 6.9),
       "草莓": (7.0, 6.2), "汽车": (8.4, 2.2), "火车": (7.0, 1.5)}


@scene("s6-1", poster=lambda T: T.mid(2, 0.95))
def s6_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        k = panel(c, 330, 330, 460, 340, t, T.intro)
        if k > 0.97:
            chip(c, "只有编号", 330, 160, size=28, fill="#AEB6CF")
            for i, (n, wd) in enumerate((("2718", "蛋糕"), ("2719", "恐龙"), ("2720", "开心"))):
                chip(c, n, 260, 238 + i * 78, t, T.intro + 0.3 + i * 0.2, size=28, fill=INK, color=WHITE)
                say(c, wd, 345, 238 + i * 78, t, T.intro + 0.4 + i * 0.2, 32, INK, anchor="lm")
            say(c, "号码挨着，意思不相干", 330, 470, t, s[0] + 1.4, 24, SOFT, 800)
            qmark(c, 500, 250, t, s[0] + 1.6, s=0.7, col=RO)
        tv = w(0, "于是")
        brick(c, "猫", 730, 330, t, tv, col=SUN, size=44)
        arrow(c, (792, 330), (862, 330), INK, 6, 18, u=ease_out(prog(t, tv + 0.4, 0.3)))
        chip(c, "( 3.2 , 7.5 )", 1035, 330, t, tv + 0.7, size=38, fill="#FFE3EC")
        say(c, "一串数字", 1035, 398, t, tv + 0.9, 26, SOFT, 800)
        term_badge(c, "向量", t, w(0, "向量"), RO)

    def b(c, t):
        M = Map(560, 350, 720, 480)
        if M.draw(c, t, s[1] - 0.05, axes=True) > 0.97:
            px, py = M(3.2, 7.5)
            u = ease_out(prog(t, s[1] + 0.5, 0.7))
            if u > 0:
                dash(c, (px, M.y0), (px, lerp(M.y0, py, u)), RO, 3.5)
                dash(c, (M.x0, py), (lerp(M.x0, px, u), py), RO, 3.5)
            chip(c, "3.2", px, M.y0 + 34, t, s[1] + 0.6, size=24, fill=PAPER)
            chip(c, "7.5", M.x0 - 2, py, t, s[1] + 0.8, size=24, fill=PAPER)
            pin(c, "猫", px, py, t, s[1] + 1.1, col=SUN)
        say(c, "两个数字", 1095, 290, t, w(1, "两个数字"), 34, INK)
        say(c, "＝ 一个位置", 1095, 345, t, w(1, "确定"), 34, RO, stroke=2, stroke_color=WHITE)

    def cc(c, t):
        M = Map(640, 350, 920, 480)
        M.draw(c, t, -1)
        clusters = (("动物", ["猫", "狗", "兔子"], "#FFE3A0", s[2] + 0.1),
                    ("水果", ["苹果", "香蕉", "草莓"], "#FFD3E0", s[2] + 0.8),
                    ("交通工具", ["汽车", "火车"], "#CDE8FF", w(2, "不相关") - 0.4))
        for name, words, col, t0 in clusters:
            pts = [M(*W61[x]) for x in words]
            cx = sum(p[0] for p in pts) / len(pts)
            cy = sum(p[1] for p in pts) / len(pts)
            aa = appear(t, t0, 0.4)
            if aa > 0:
                c.ellipse(cx, cy - 22, 150, 92, col, line=None, a=0.8 * aa)
                say(c, name, cx, cy + 62, t, t0, 22, SOFT, 900)
            for i, x in enumerate(words):
                pin(c, x, *M(*W61[x]), t, t0 + 0.15 * i, col=RO)
        tn, tf = w(2, "住得近"), w(2, "住得远")
        p, q, r = M(*W61["猫"]), M(*W61["狗"]), M(*W61["汽车"])
        u = ease_out(prog(t, tn, 0.4))
        if u > 0:
            c.line([p, lerp2(p, q, u)], GREEN, 6)
            chip(c, "近", (p[0] + q[0]) / 2, (p[1] + q[1]) / 2 + 26, t, tn + 0.3, size=24, fill=GREEN,
                 color=WHITE, stroke=1.4)
        u2 = ease_out(prog(t, tf, 0.6))
        if u2 > 0:
            dash(c, p, lerp2(p, r, u2), RED, 4)
            chip(c, "远", (p[0] + r[0]) / 2, (p[1] + r[1]) / 2, t, tf + 0.5, size=24, fill=RED, color=WHITE,
                 stroke=1.4)

    def d(c, t):
        words = (("猫", SUN), ("苹果", "#FF9BB0"), ("汽车", SKY))
        for i, (x, col) in enumerate(words):
            y = 215 + i * 115
            brick(c, x, 150, y, t, s[3] - 0.05 + i * 0.1, col=col, size=34)
            arrow(c, (205, y), (300, 330), INK, 4, 13, u=ease_out(prog(t, s[3] + 0.3, 0.3)))
        machine(c, 410, 330, 200, 200, "嵌入", t, col=RO)
        M = Map(900, 340, 560, 450)
        M.draw(c, t, s[3])
        for i, (x, col) in enumerate(words):
            tp = s[3] + 0.8 + i * 0.4
            u = prog(t, tp, 0.5)
            if 0 < u < 1:
                p = bezier((520, 330), (680, 140), M(*W61[x]), ease_io(u))
                c.circle(p[0], p[1], 9, RO, lw=3)
            if u >= 1:
                pin(c, x, *M(*W61[x]), t, tp + 0.5, col=RO)
        term_badge(c, "嵌入 Embedding", t, w(3, "嵌入"), RO)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


W62 = {"开心": (3.0, 6.6), "快乐": (4.4, 8.2), "高兴": (1.6, 7.6), "愉快": (3.6, 4.6), "难过": (8.2, 2.4),
       "生气": (7.0, 1.4)}


@scene("s6-2", poster=lambda T: T.mid(2, 0.95))
def s6_2(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        M = Map(640, 350, 920, 480)
        M.draw(c, t, T.intro)
        for i, x in enumerate(("开心", "快乐", "难过")):
            pin(c, x, *M(*W62[x]), t, T.intro + 0.3 + i * 0.2, col=SUN if x == "开心" else RO)
        p, q, r = M(*W62["开心"]), M(*W62["快乐"]), M(*W62["难过"])
        tl = s[0] + 0.9
        u = ease_out(prog(t, tl, 0.4))
        if u > 0:
            c.line([p, lerp2(p, q, u)], GREEN, 6)
            chip(c, "很近", (p[0] + q[0]) / 2 + 46, (p[1] + q[1]) / 2 + 18, t, tl + 0.3, size=24, fill=GREEN,
                 color=WHITE, stroke=1.4)
        u2 = ease_out(prog(t, tl + 0.6, 0.6))
        if u2 > 0:
            dash(c, p, lerp2(p, r, u2), RED, 4)
            chip(c, "很远", (p[0] + r[0]) / 2, (p[1] + r[1]) / 2, t, tl + 1.1, size=24, fill=RED, color=WHITE,
                 stroke=1.4)

    def b(c, t):
        M = Map(560, 350, 780, 480)
        M.draw(c, t, -1)
        cx, cy = M(*W62["开心"])
        u = ease_out(prog(t, s[1] + 0.1, 0.6))
        if u > 0:
            c.circle(cx, cy, 150 * u, "#FFE3EC", line=None, a=0.85)
            c.circle(cx, cy, 150 * u, None, RO, 4)
        tn = w(1, "快乐")
        for i, x in enumerate(("快乐", "高兴", "愉快")):
            pin(c, x, *M(*W62[x]), t, tn + i * 0.25, col=RO)
        for x in ("难过", "生气"):
            pin(c, x, *M(*W62[x]), col="#AEB6CF", a=0.55)
        pin(c, "开心", cx, cy, col=SUN)
        say(c, "离得越近", 1100, 280, t, s[1] + 0.2, 34, INK)
        say(c, "意思越像", 1100, 335, t, w(1, "意思越像"), 34, RO, stroke=2, stroke_color=WHITE)

    docs = [(1.6, 2.2), (2.4, 8.6), (5.0, 5.4), (6.2, 7.0), (6.8, 4.6), (8.8, 8.2), (8.6, 2.6), (3.4, 4.2),
            (4.4, 7.6)]
    q = (5.9, 5.9)

    def cc(c, t):
        M = Map(560, 350, 780, 480)
        M.draw(c, t, s[2] - 0.05)
        order = sorted(range(len(docs)), key=lambda i: math.hypot(docs[i][0] - q[0], docs[i][1] - q[1]))
        near = set(order[:3])
        tn = w(2, "最近")
        for i, d_ in enumerate(docs):
            p = M(*d_)
            hi = i in near and t >= tn
            doc_icon(c, p[0], p[1], 40, 50, PAPER, 3, s=pop(t, s[2] + 0.2 + i * 0.06), accent=RO if hi else SKY,
                     a=1.0 if (hi or t < tn) else 0.45)
        qp = M(*q)
        pin(c, "问题", qp[0], qp[1], t, w(2, "问题"), col=SUN)
        for n, i in enumerate(order[:3]):
            p = M(*docs[i])
            u = ease_out(prog(t, tn + n * 0.25, 0.35))
            if u > 0:
                c.line([qp, lerp2(qp, p, u)], RO, 5)
                if u >= 1:
                    chip(c, str(n + 1), p[0] + 28, p[1] - 30, size=20, fill=SUN, shadow=2, padx=9)
        say(c, "找离问题", 1095, 280, t, tn - 0.3, 32, INK)
        say(c, "最近的几段", 1095, 332, t, tn, 32, RO, stroke=2, stroke_color=WHITE)

    def d(c, t):
        y = 300
        ts = [s[3] - 0.05, s[3] + 0.4, w(3, "找资料") - 0.3, w(3, "向量检索")]
        chip(c, "问题", 170, y, t, ts[0], size=34, fill=SUN)
        arrow(c, (235, y), (330, y), INK, 6, 16, u=ease_out(prog(t, ts[1] - 0.2, 0.3)))
        mini_map(c, 430, y, pop(t, ts[1]))
        magnifier(c, 470, y - 20, 24, a=appear(t, ts[1] + 0.3))
        say(c, "向量检索", 430, y + 95, t, ts[1] + 0.2, 28, INK)
        arrow(c, (515, y), (610, y), INK, 6, 16, u=ease_out(prog(t, ts[2] - 0.2, 0.3)))
        stack_icon(c, 700, y - 6, pop(t, ts[2]))
        say(c, "最近的资料", 700, y + 95, t, ts[2] + 0.2, 28, INK)
        arrow(c, (790, y), (880, y), INK, 6, 16, u=ease_out(prog(t, ts[2] + 0.4, 0.3)))
        robot(c, 990, 395, t, eyes="scan", mouth="flat", s=0.6, shadow=False)
        say(c, "组织答案", 990, y + 140, t, ts[2] + 0.6, 26, SOFT, 800)
        term_badge(c, "向量检索", t, ts[3], RO)
        chip(c, "还记得 RAG 吗？", 640, 150, t, s[3] - 0.05, size=30, fill=PAPER)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


W63 = {"中国": (1.4, 2.2), "北京": (2.8, 5.2), "法国": (4.4, 1.6), "巴黎": (5.8, 4.6), "日本": (7.0, 3.2),
       "东京": (8.4, 6.2)}
D63 = (1.4, 3.0)


def cap_arrow(c, M, a_, b_, t, t0, col=RO):
    u = ease_out(prog(t, t0, 0.5))
    if u > 0:
        p, q = M(*a_), M(*b_)
        arrow(c, p, lerp2(p, q, u), col, 7, 20, u=1)


@scene("s6-3", poster=lambda T: T.mid(2, 0.95))
def s6_3(T):
    s, e, w = T.s, T.e, T.word

    def countries(c, M, t, t0, tokyo=False):
        for i, x in enumerate(("中国", "北京", "法国", "巴黎", "日本")):
            pin(c, x, *M(*W63[x]), t, t0 + i * 0.12, col=SUN if x in ("中国", "法国", "日本") else RO)
        if tokyo:
            pin(c, "东京", *M(*W63["东京"]), col=RO)

    def a(c, t):
        M = Map(560, 350, 800, 480)
        M.draw(c, t, T.intro)
        countries(c, M, t, T.intro + 0.3)
        k = pop(t, s[0] + 0.5)
        if k > 0:
            c.circle(1100, 300, 70 * k, PAPER, lw=4)
            c.poly([(1100, 300 - 52 * k), (1114, 300), (1100, 300 + 52 * k), (1086, 300)], RO, lw=2.5)
            c.text("N", 1100, 300 - 92 * k, 26, INK, 900)
        say(c, "方向也有意思", 1100, 440, t, s[0] + 0.8, 30, INK)

    def b(c, t):
        M = Map(560, 350, 800, 480)
        M.draw(c, t, -1)
        cap_arrow(c, M, W63["中国"], W63["北京"], t, w(1, "北京") - 0.2)
        cap_arrow(c, M, W63["法国"], W63["巴黎"], t, w(1, "巴黎") - 0.2)
        countries(c, M, t, -1)
        chip(c, "首都方向", 1100, 300, t, w(1, "首都"), size=32, fill=RO, color=WHITE, stroke=1.8)
        say(c, "方向一样", 1100, 370, t, w(1, "方向和距离"), 28, SOFT, 800)
        say(c, "距离也差不多", 1100, 412, t, w(1, "方向和距离") + 0.3, 28, SOFT, 800)

    def cc(c, t):
        M = Map(560, 380, 800, 420)
        M.draw(c, t, -1)
        cap_arrow(c, M, W63["中国"], W63["北京"], t, -1, "#F3A9C0")
        cap_arrow(c, M, W63["法国"], W63["巴黎"], t, -1, RO)
        countries(c, M, t, -1)
        tm, tj = w(2, "减去"), w(2, "加上")
        u = ease_io(prog(t, tj + 0.2, 0.9))
        if t >= tm:
            st = lerp2(W63["法国"], W63["日本"], u)
            en = (st[0] + D63[0], st[1] + D63[1])
            arrow(c, M(*st), M(*en), SUN, 7, 20, a=0.95)
        if u >= 1:
            pin(c, "东京", *M(*W63["东京"]), t, tj + 1.1, col=RO)
            sparkles(c, t, *M(*W63["东京"]), 60, 4, SUN, seed=6, t0=tj + 1.1)
        parts = [("巴黎", w(2, "巴黎")), ("− 法国", tm), ("+ 日本", tj), ("≈ 东京", w(2, "东京"))]
        xs, _ = tok_layout([p for p, _ in parts], 36, x_center=560, gap=18, padx=16)
        for (p, t0), x in zip(parts, xs):
            chip(c, p, x, 118, t, t0, size=36, fill=SUN if "东京" in p else PAPER)

    def d(c, t):
        M = Map(560, 350, 800, 480)
        M.draw(c, t, -1)
        for a_, b_ in (("中国", "北京"), ("法国", "巴黎"), ("日本", "东京")):
            cap_arrow(c, M, W63[a_], W63[b_], t, -1)
        countries(c, M, t, -1, tokyo=True)
        an = {"猫": (1.0, 9.0), "喵": (2.8, 8.0), "狗": (4.6, 9.2), "汪": (6.4, 8.2)}
        t0 = s[3] + 0.3
        for a_, b_ in (("猫", "喵"), ("狗", "汪")):
            cap_arrow(c, M, an[a_], an[b_], t, t0 + 0.4, SKY)
        for i, x in enumerate(an):
            pin(c, x, *M(*an[x]), t, t0 + i * 0.12, col=SKY)
        chip(c, "国家 → 首都", 1100, 270, t, s[3] + 0.1, size=28, fill=RO, color=WHITE, stroke=1.6)
        chip(c, "动物 → 叫声", 1100, 340, t, t0 + 0.4, size=28, fill=SKY)
        say(c, "关系藏在方向里", 1100, 420, t, w(3, "藏在"), 28, INK)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s6-4", poster=lambda T: T.mid(1, 0.85))
def s6_4(T):
    s, e, w = T.s, T.e, T.word
    rnd = random.Random(9)
    nums = [f"{rnd.uniform(-1, 1):.2f}" for _ in range(64)]

    def a(c, t):
        M = Map(250, 330, 300, 270, pad=40)
        if M.draw(c, t, T.intro, axes=True) > 0.97:
            pin(c, "猫", *M(4.5, 6.5), col=SUN, size=22)
        say(c, "我们的地图：2 个数字", 250, 500, t, T.intro + 0.3, 26, SOFT, 800)
        k = pop(t, s[0] + 0.6)
        if k > 0:
            c.crect(846, 337, 680, 96, INK, r=20, line=None, s=k)
            c.crect(840, 330, 680, 96, PAPER, r=20, lw=4, s=k)
        if k > 0.97:
            off = (t * 110) % 92
            for i in range(9):
                x = 525 + i * 92 - off + 46
                aa = clamp((x - 515) / 40) * clamp((1165 - x) / 40)
                if aa > 0:
                    c.text(nums[(i + int(t * 110 // 92)) % 64], x, 331, 28, INK, 800, a=aa)
            c.text("[", 512, 330, 48, RO, 900)
            c.text("]", 1168, 330, 48, RO, 900)
        stage = "几百个" if t < w(0, "几千") else ("几千个" if t < w(0, "上万") else "上万个")
        if t >= w(0, "几百"):
            chip(c, f"真正的向量：{stage}数字", 840, 210, size=30, fill=RO, color=WHITE, stroke=1.8)

    def b(c, t):
        cx, cy = 640, 320
        steps = [(s[1], 2), (s[1] + 0.9, 3), (w(1, "多一个方向"), 8), (w(1, "能分辨"), 24), (w(1, "更细"), 60)]
        n = 2
        for t0, k in steps:
            if t >= t0:
                n = k
        R = 200
        for i in range(n):
            if n == 2:
                ang = math.radians(0 if i == 0 else -90)
            elif n == 3:
                ang = math.radians([0, -90, -145][i])
            else:
                ang = math.radians(-90 + 360 * i / n)
            col = [RO, SKY, SUN, LEAF, GRAPE][i % 5]
            if n <= 3:
                arrow(c, (cx, cy), (cx + math.cos(ang) * R, cy + math.sin(ang) * R), col, 6, 18)
            else:
                c.line([(cx, cy), (cx + math.cos(ang) * R, cy + math.sin(ang) * R)], col, 3 if n > 20 else 5)
                c.circle(cx + math.cos(ang) * R, cy + math.sin(ang) * R, 5 if n > 20 else 8, col, lw=2)
        c.circle(cx, cy, 12, PAPER, lw=3.5)
        label = {2: "2 维", 3: "3 维", 8: "8 维", 24: "更多维……", 60: "几千维"}[n]
        chip(c, label, 640, 560, size=32, fill=PAPER)

    def cc(c, t):
        girl(c, 230, 560, t, eyes="normal", mouth="wavy", brows="worry", arm_r=60)
        sweat(c, 300, 300 + 20 * ((t * 1.3) % 1), 1.0, a=1 - ((t * 1.3) % 1) * 0.6)
        bubble(c, "这么多方向，画不出来呀……", 290, 290, t, s[2] - 0.05, tail="bl", size=26)
        robot(c, 1060, 570, t, eyes="happy", mouth="open", s=0.9, arm_r=120)
        bubble(c, "但我能算！", 1020, 300, t, w(2, "计算机"), tail="br", size=30)
        chip(c, "算距离 ✓", 640, 400, t, w(2, "算距离"), size=32, fill=GREEN, color=WHITE, stroke=1.8)
        chip(c, "算方向 ✓", 640, 480, t, w(2, "算方向"), size=32, fill=GREEN, color=WHITE, stroke=1.8)

    def d(c, t):
        rnd2 = random.Random(4)
        vals = [rnd2.uniform(-1, 1) for _ in range(28)]
        x0, y0, cw = 190, 280, 64
        for i, v in enumerate(vals):
            r_, k = divmod(i, 14)
            x, y = x0 + k * cw, y0 + r_ * 70
            col = mix("#FFFFFF", RO, v) if v > 0 else mix("#FFFFFF", SKY, -v)
            kk = pop(t, s[3] - 0.05 + i * 0.03, 0.3)
            if kk > 0:
                c.crect(x, y, 56, 56, col, r=8, lw=2.5, s=kk)
        labels = {2: "大小？", 7: "心情？", 11: "？", 4: "？", 9: "？", 13: "？"}
        for i, lab in labels.items():
            say(c, lab, x0 + i * cw, y0 - 52, t, s[3] + 0.8 + i * 0.05, 24, INK if len(lab) > 1 else SOFT, 900)
        chip(c, "意思分散在许多数字的组合里", 640, 470, t, w(3, "分散"), size=30, fill=RO, color=WHITE, stroke=1.6)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事七：谁是“它”（注意力机制）
SW = ["芝麻", "追着", "毛线球", "跑", "因为", "它", "太好玩了"]
SC = [0.20, 0.03, 0.62, 0.04, 0.02, 0.05, 0.04]
IT, BALL, CAT = 5, 2, 0
HUES = [SKY, "#9ED7FF", AM, "#C9D3EE", "#E6DFFF", "#FFD3E0", "#D5F5E3"]


def stage_row(words, size=34):
    return tok_layout(words, size, x_center=640, gap=16)


def word_cards(c, words, y, t, t0, size=34, hi=(IT,), a=1.0, lift=None):
    xs, ws = stage_row(words, size)
    for i, (wd, x) in enumerate(zip(words, xs)):
        dy = lift(i) if lift else 0
        chip(c, wd, x, y + dy, t, t0 + i * 0.06, size=size, fill=AM if i in hi else PAPER, a=a)
    return xs


@scene("s7-1", poster=lambda T: T.mid(0, 0.95))
def s7_1(T):
    s, e, w = T.s, T.e, T.word
    W2 = SW[:-1] + ["太无聊了"]

    def a(c, t):
        xs1 = word_cards(c, SW, 230, t, T.intro)
        xs2 = word_cards(c, W2, 430, t, T.intro + 0.4)
        u1 = ease_out(prog(t, s[0] + 0.9, 0.6))
        if u1 > 0:
            curve_arrow(c, (xs1[IT], 196), (xs1[BALL], 196), bend=70, col=AM, lw=6, u=u1)
        u2 = ease_out(prog(t, s[0] + 1.9, 0.6))
        if u2 > 0:
            curve_arrow(c, (xs2[IT], 396), (xs2[CAT], 396), bend=90, col=AM, lw=6, u=u2)
        chip(c, "它 = 毛线球", 640, 300, t, s[0] + 1.4, size=26, fill=SUN)
        chip(c, "它 = 芝麻", 640, 500, t, s[0] + 2.4, size=26, fill=SUN)

    def b(c, t):
        xs = word_cards(c, SW, 330, t, -1)
        ex = xs[IT]
        look = math.sin(t * 2.4)
        for sg in (-1, 1):
            c.circle(ex + sg * 26, 245, 22, PAPER, lw=3.5)
            c.circle(ex + sg * 26 + look * 9, 248, 9, INK, line=None)
        for i, x in enumerate(xs):
            if i == IT:
                continue
            u = ease_out(prog(t, s[1] + 0.3 + abs(i - IT) * 0.15, 0.4))
            if u > 0:
                dash(c, (ex, 300), lerp2((ex, 300), (x, 300), u), "#FFE9A8", 3, 8, 6, a=0.8)
        night_say(c, "看看周围的词", 640, 470, t, s[1] + 0.4, 34)

    def cc(c, t):
        xs = word_cards(c, SW, 300, t, -1)
        lx = xs[IT]
        lamp(c, lx, 150, (lx, 280))
        for i, x in enumerate(xs):
            if i != IT:
                beam(c, (lx, 165), (x, 300), 70, a=0.35 * appear(t, s[2] + 0.2 + i * 0.05))
        word_cards(c, SW, 300, t, -1)
        term_badge(c, "注意力机制", t, w(2, "注意力机制"), "#F2A900")
        night_say(c, "专门负责“看周围”的部件", 640, 450, t, w(2, "看周围"), 30)
        robot(c, 1150, 560, t, eyes="happy", s=0.6)

    def d(c, t):
        xs = word_cards(c, SW, 400, t, -1, a=0.95)
        y = 366
        for i in range(len(SW)):
            for j in range(i + 1, len(SW)):
                key = {i, j}
                strong = key == {IT, BALL}
                mid = key == {CAT, 1}
                t0 = s[3] + 0.2 + (i + j) * 0.05
                aa = appear(t, t0, 0.4)
                if aa <= 0:
                    continue
                h = abs(xs[j] - xs[i]) * 0.32
                if strong:
                    hop_arc(c, xs[i], xs[j], y, h, AM, 7, a=aa)
                elif mid:
                    hop_arc(c, xs[i], xs[j], y, h, SKY, 5, a=aa)
                else:
                    hop_arc(c, xs[i], xs[j], y, h, "#FFFFFF", 2, a=0.32 * aa)
        night_say(c, "每个词都去关注别的词", 640, 510, t, w(3, "关注"), 32)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s7-2", poster=lambda T: T.mid(2, 0.95))
def s7_2(T):
    s, e, w = T.s, T.e, T.word
    Y = 450

    def a(c, t):
        xs, _ = stage_row(SW)
        tx = 640 + 360 * math.sin((t - T.intro) * 1.1)
        lamp(c, 640, 92, (tx, Y))
        beam(c, (640, 108), (tx, Y), 120, a=0.8 * appear(t, T.intro + 0.2))
        word_cards(c, SW, Y, t, T.intro)
        chip(c, "注意力 ≈ 一盏聚光灯", 640, 250, t, s[0] + 0.3, size=34, fill=PAPER)

    def scores(c, t, xs, t0):
        for i, x in enumerate(xs):
            chip(c, f"{SC[i] * 100:.0f}%", x, 530, t, t0 + i * 0.12, size=22, fill=SUN if i == BALL else PAPER,
                 shadow=2, padx=10)

    def b(c, t):
        xs, _ = stage_row(SW)
        lift = lambda i: -18 * ease_out(prog(t, s[1], 0.4)) if i == IT else 0  # noqa: E731
        word_cards(c, SW, Y, t, -1, lift=lift)
        lamp(c, xs[IT], 330, (xs[IT] + 1, 420), s=0.9)
        scores(c, t, xs, w(1, "关注分"))
        night_say(c, "给每个词打一个关注分", 640, 200, t, s[1] + 0.3, 34)

    def cc(c, t):
        xs, _ = stage_row(SW)
        src = (xs[IT], 345)
        for i, x in enumerate(xs):
            if i == IT:
                continue
            aa = appear(t, s[2] + 0.1 + i * 0.08, 0.5)
            beam(c, src, (x, Y - 8), 60 + 70 * SC[i], a=aa * (0.12 + 1.3 * SC[i] ** 0.8))
        lamp(c, xs[IT], 330, (xs[BALL], Y), s=0.9)
        word_cards(c, SW, Y, t, -1, lift=lambda i: -18 if i == IT else 0)
        scores(c, t, xs, -1)
        tb = w(2, "毛线球")
        if t > tb:
            sparkles(c, t, xs[BALL], Y - 10, 70, 5, SUN, seed=8, t0=tb)
            night_say(c, "最亮：毛线球", xs[BALL], 300, t, tb, 32)

    def d(c, t):
        word_cards(c, SW, Y + 20, t, -1, a=0.55)
        x0, total = 180, 920
        x = x0
        tb = s[3] + 0.1
        u = ease_out(prog(t, tb, 1.2))
        for i, sc in enumerate(SC):
            wd = total * sc * u
            if wd > 1:
                c.rect(x, 220, wd, 70, HUES[i], r=8 if wd > 16 else 2, lw=3)
                if sc >= 0.2 and u > 0.95:
                    c.text(f"{SW[i]} {sc * 100:.0f}%", x + wd / 2, 255, 26, INK, 900)
            x += wd
        if u >= 1:
            chip(c, "加起来 = 100%", 640, 340, t, tb + 1.2, size=34, fill=SUN)
        term_badge(c, "注意力权重", t, w(3, "注意力权重"), "#F2A900")

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s7-3", poster=lambda T: T.mid(1, 0.9))
def s7_3(T):
    s, e, w = T.s, T.e, T.word
    tags = [("芝麻：一只猫", 0.20, 175), ("毛线球：会滚的玩具", 0.62, 315), ("跑：一个动作", 0.04, 455)]

    def a(c, t):
        chip(c, "毛线球", 640, 175, t, T.intro, size=46, fill=PAPER)
        items = ((380, "提问", w(0, "提问")), (640, "标签", w(0, "标签")), (900, "内容", w(0, "内容")))
        for x, lab, t0 in items:
            u = ease_out(prog(t, t0 - 0.3, 0.3))
            if u > 0:
                dash(c, (640, 215), lerp2((640, 215), (x, 300), u), "#FFE9A8", 3, 8, 6)
            k = pop(t, t0, 0.45)
            if k > 0:
                if lab == "提问":
                    q_icon(c, x, 360, k)
                elif lab == "标签":
                    k_icon(c, x, 360, "会滚的玩具", k)
                else:
                    v_icon(c, x, 360, k)
                night_say(c, lab, x, 455, t, t0 + 0.1, 32)

    def b(c, t):
        chip(c, "它", 230, 330, t, -1, size=46, fill=AM)
        bubble(c, "我指的是哪个好玩的东西？", 200, 280, t, s[1] - 0.05, size=24, max_w=300, tail="bl")
        tm = w(1, "比对")
        best = w(1, "越匹配")
        for i, (lab, sc, y) in enumerate(tags):
            chip(c, lab, 880, y, t, s[1] + 0.3 + i * 0.15, size=26, fill=SUN)
            u = ease_out(prog(t, tm + i * 0.35, 0.4))
            if u > 0:
                p0, p1 = (300, 330), (742, y)
                c.line([p0, lerp2(p0, p1, u)], AM if (i == 1 and t >= best) else "#FFE9A8",
                       8 if (i == 1 and t >= best) else 3)
                if u >= 1:
                    mx, my = lerp2(p0, p1, 0.55)
                    chip(c, f"{sc * 100:.0f}%", mx, my - 4, size=24, fill=SUN if i == 1 else PAPER, shadow=2,
                         padx=10)
        if t >= best:
            stamp(c, True, 1062, 290, t, best + 0.2, s=0.55)

    def cc(c, t):
        tf = s[2] + 0.2
        glow = appear(t, tf + 1.0, 0.5)
        if glow > 0:
            c.glow(230, 330, 120, AM, a=glow)
        chip(c, "它", 230, 330, t, -1, size=46, fill=AM)
        for i, (lab, sc, y) in enumerate(tags):
            k = 0.45 + sc * 1.2
            v_icon(c, 1000, y, k)
            c.text(lab.split("：")[0], 1000, y + 52 * k + 18, 22, WHITE, 900, stroke=2.5)
            for j in range(2):
                u = prog(t, tf + i * 0.25 + j * 0.5, 0.9)
                if 0 < u < 1:
                    p = bezier((960, y), (620, 120 + i * 120), (280, 330), ease_io(u))
                    v_icon(c, p[0], p[1], k * lerp(0.8, 0.45, u))
        chip(c, "它 ≈ 毛线球（大部分）＋ 芝麻（一点点）", 600, 545, t, w(2, "更新"), size=28, fill=SUN)

    def d(c, t):
        cards = (("Q", "Query", "提问", SKY, w(3, "Query")), ("K", "Key", "标签", SUN, w(3, "Key")),
                 ("V", "Value", "内容", CORAL, w(3, "Value")))
        for i, (L, en, zh, col, t0) in enumerate(cards):
            x = 330 + i * 310
            k = panel(c, x, 330, 250, 280, t, t0, fill=col)
            if k > 0.97:
                c.text(L, x, 265, 96, WHITE, 900, stroke=5)
                c.text(en, x, 365, 34, INK, 900)
                c.text(zh, x, 418, 30, INK, 800)
        term_badge(c, "QKV", t, w(3, "QKV"), "#F2A900")

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s7-4", poster=lambda T: T.mid(0, 0.95))
def s7_4(T):
    s, e, w = T.s, T.e, T.word
    Y = 460
    LCOL = [AM, SKY, "#FF9BB0", LEAF, GRAPE, "#FFE27A"]

    def a(c, t):
        xs, _ = stage_row(SW)
        targets = [BALL, CAT, 1, 3, 4, IT]
        for i in range(6):
            lx = 230 + i * 164
            tx = xs[targets[i]] + 30 * math.sin(t * 1.4 + i)
            aa = appear(t, T.intro + 0.2 + i * 0.15, 0.4)
            beam(c, (lx, 100), (tx, Y), 80, a=0.55 * aa, col=LCOL[i])
            lamp(c, lx, 86, (tx, Y), lens=LCOL[i])
        word_cards(c, SW, Y, t, T.intro)
        term_badge(c, "多头注意力", t, w(0, "多头注意力"), "#F2A900")

    def b(c, t):
        xs, _ = stage_row(SW)
        word_cards(c, SW, Y, t, -1)
        groups = ((360, AM, "找指代", w(1, "找指代"), [(IT, BALL)]),
                  (640, SKY, "看动作", w(1, "看动作"), [(CAT, 1)]),
                  (920, "#FF9BB0", "管顺序", w(1, "管顺序"), [(k, k + 1) for k in range(6)]))
        for lx, col, lab, t0, pairs in groups:
            aa = appear(t, t0 - 0.2, 0.4)
            if aa <= 0:
                continue
            for p, q in pairs:
                beam(c, (lx, 120), (xs[p], Y), 60, a=0.35 * aa, col=col)
                hop_arc(c, xs[p], xs[q], Y - 34, abs(xs[q] - xs[p]) * 0.25 + 10, col, 5, a=aa, head=True)
            lamp(c, lx, 106, (lx, Y), lens=col)
            chip(c, lab, lx, 175, t, t0, size=28, fill=col)

    def cc(c, t):
        base = 525
        n = 6
        for i in range(n):
            y = base - i * 60
            k = pop(t, s[2] + 0.1 + i * 0.25, 0.4)
            if k <= 0:
                continue
            c.crect(520, y, 230, 48, AM, r=14, lw=3.5, s=k)
            c.crect(760, y, 230, 48, SKY, r=14, lw=3.5, s=k)
            if k > 0.97:
                c.text("注意力", 520, y + 1, 24, INK, 900)
                c.text("其他计算", 760, y + 1, 24, INK, 900)
        if t > s[2] + 1.6:
            chip(c, "× 几十层", 1010, 360, t, s[2] + 1.6, size=34, fill=PAPER)
            arrow(c, (640, base - n * 60 + 20), (640, 152), WHITE, 6, 18, u=ease_out(prog(t, s[2] + 1.8, 0.4)),
                  outline=False)
            chip(c, "下一个词", 640, 132, t, s[2] + 2.0, size=28, fill=SUN)
        term_badge(c, "Transformer", t, w(2, "Transformer"), "#F2A900")

    def d(c, t):
        chip(c, "2017", 230, 210, t, w(3, "2017"), size=60, fill=AM)
        night_say(c, "这种结构被提出", 230, 290, t, w(3, "2017") + 0.3, 26)
        k = pop(t, s[3] + 0.4)
        if k > 0:
            c.crect(760, 480, 760, 70, AM, r=16, lw=4, s=k)
            if k > 0.97:
                c.text("Transformer", 760, 482, 36, INK, 900)
        for i, (lab, col) in enumerate((("聊天助手", SKY), ("翻译", LEAF), ("写代码", "#FF9BB0"), ("……", PAPER))):
            chip(c, lab, 520 + i * 160, 400, t, w(3, "几乎所有") + i * 0.2, size=28, fill=col)
        night_say(c, "几乎所有大语言模型都建在它上面", 760, 300, t, w(3, "建立在"), 30)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事八：比特的小黑板（上下文窗口）
CHAT8 = [("l", "芝麻的生日是 5 月 20 日"), ("r", "记住啦！"), ("l", "月亮为什么会变形状？"), ("r", "因为太阳照到的部分不同……"),
         ("l", "恐龙吃什么？"), ("r", "有的吃草，有的吃肉。"), ("l", "霸王龙跑得快吗？"), ("r", "比你想的慢一点！"),
         ("l", "翼龙会飞吗？"), ("r", "会滑翔，也会扑翅膀。"), ("l", "恐龙为什么灭绝了？"), ("r", "很可能是小行星撞地球。")]
BOARD8 = ["芝麻的生日：5 月 20 日", "月亮为什么会变形状？", "恐龙吃什么？", "霸王龙跑得快吗？", "翼龙会飞吗？", "恐龙为什么灭绝了？",
          "地球上还有恐龙的亲戚吗？"]


def chat_column(c, items, x_l, x_r, y_bottom, t, shift=0.0, a_fn=None):
    for i, (side, text) in enumerate(reversed(items)):
        y = y_bottom - i * 50 - shift
        aa = a_fn(y) if a_fn else 1.0
        if aa > 0.02:
            msg(c, text, x_l if side == "l" else x_r, y, side, 22, PAPER if side == "l" else "#C6F1E9", a=aa)


@scene("s8-1", poster=lambda T: T.mid(1, 0.9))
def s8_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        items = CHAT8[:6]
        for i, (side, text) in enumerate(items):
            k = pop(t, T.intro + i * 0.15, 0.35)
            msg(c, text, 380 if side == "l" else 900, 170 + i * 66, side, 24, PAPER if side == "l" else "#C6F1E9",
                k=k)
        if t > s[0] + 0.5:
            ph = ((t - s[0] - 0.5) * 0.55) % 1
            y = lerp(150, 520, ph)
            c.rect(360, y - 26, 560, 52, TE, r=14, line=None, a=0.22)
            c.line([(350, y), (930, y)], TE, 4, caps=False)
        robot(c, 1120, 585, t, eyes="scan", mouth="flat", s=0.75)
        girl(c, 160, 560, t, mouth="smile", s=0.85)
        say(c, "每次都从头看一遍", 640, 590, t, w(0, "重新看"), 30, INK)

    def b(c, t):
        top = 290
        off = 260 * (1 - ease_out(prog(t, s[1] - 0.1, 2.6)))

        def fade(y):
            if y > 600 or y < 140:
                return 0.0
            return 1.0 if y > top + 14 else 0.2

        for i, (side, text) in enumerate(reversed(CHAT8)):
            y = 560 - i * 50 + off
            aa = fade(y)
            if aa > 0:
                msg(c, text, 360 if side == "l" else 920, y, side, 22, PAPER if side == "l" else "#C6F1E9", a=aa)
        c.rect(330, top, 620, 300, None, r=24, line=TE, lw=8)
        chip(c, "窗口里的才看得见", 640, top - 4, size=24, fill=TE, color=WHITE, stroke=1.4)
        term_badge(c, "上下文窗口", t, w(1, "上下文窗口"), TE)
        say(c, "有上限", 1110, 330, t, w(1, "有限"), 34, INK)
        robot(c, 1110, 585, t, eyes="normal", s=0.6)

    def cc(c, t):
        cx, cy, bw, bh = 600, 300, 760, 360
        chalkboard(c, cx, cy, bw, bh, pop(t, s[2] - 0.05))
        t0, per = s[2] + 0.2, 0.5
        top, lh = cy - bh / 2 + 52, 64
        t_full = t0 + 5 * per
        erases = [t_full + 0.3 + k * 1.9 for k in range(2)]
        shifts = [x + 0.6 for x in erases]
        writes = [x + 0.4 for x in shifts]
        for i in range(7):
            tw_ = t0 + i * per if i < 5 else writes[i - 5]
            if t < tw_:
                continue
            r0 = i if i < 5 else 4
            moved = 0.0
            for k, sh in enumerate(shifts):
                if tw_ < sh and i != k:
                    moved += ease_io(prog(t, sh, 0.3))
            ea = 1.0
            y = top + (r0 - moved) * lh
            if i < 2:
                u = prog(t, erases[i], 0.6)
                if u >= 1:
                    continue
                ea = 1 - u
                if u > 0:
                    eraser(c, cx - bw / 2 + 70 + u * (bw - 140), y, 1.0)
            chalk(c, BOARD8[i], cx - bw / 2 + 40, y, 30, a=ea, n=int((t - tw_) * 18))
        chip(c, "写满了，最早的就被擦掉", 600, 560, t, t_full, size=28, fill=PAPER)

    def d(c, t):
        cx, cy, bw, bh = 700, 245, 540, 250
        chalkboard(c, cx, cy, bw, bh)
        chalk(c, BOARD8[0], cx - bw / 2 + 30, cy - bh / 2 + 40, 26, a=0.14)
        c.line([(cx - bw / 2 + 24, cy - bh / 2 + 40), (cx + 60, cy - bh / 2 + 40)], CHALK, 3, a=0.25)
        for i, ln in enumerate(BOARD8[3:6]):
            chalk(c, ln, cx - bw / 2 + 30, cy - bh / 2 + 95 + i * 52, 26)
        girl(c, 170, 560, t, eyes="normal", mouth="open", arm_r=70, talk=s[3] < t < s[3] + 1.2)
        bubble(c, "芝麻的生日是哪天？", 230, 330, t, s[3] - 0.05, tail="bl", size=26)
        robot(c, 1110, 575, t, eyes="confused", mouth="wavy", s=0.8)
        bubble(c, "你……说过吗？", 1150, 350, t, s[3] + 0.9, tail="br", size=26)
        qmark(c, 1220, 260, t, s[3] + 1.3, s=0.7, col=TE)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s8-2", poster=lambda T: T.mid(2, 0.95))
def s8_2(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        cx, cy, bw, bh = 640, 340, 700, 330
        chalkboard(c, cx, cy, bw, bh, pop(t, T.intro))
        n = int(max(0.0, t - T.intro - 0.4) * 9)
        per_row = 9
        for i in range(min(n, 36)):
            r_, k = divmod(i, per_row)
            brick(c, "", cx - bw / 2 + 52 + k * 75, cy - bh / 2 + 52 + r_ * 66, col=BRICK_COLS[i % 7], size=20)
        chip(c, "单位：token", 640, 125, t, s[0] + 0.3, size=34, fill=PAPER)

    def b(c, t):
        chalkboard(c, 480, 300, 300, 180, pop(t, s[1] - 0.05))
        for i in range(3):
            chalk(c, "……………", 480 - 120, 250 + i * 40, 24, n=int(max(0, t - s[1] - 0.3) * 10))
        chip(c, "几年前：几千个 token", 480, 470, t, w(1, "几千"), size=30, fill=PAPER)
        for i in range(3):
            doc_icon(c, 820 + i * 46, 300 + (i % 2) * 8, 70, 88, PAPER, 4, s=pop(t, w(1, "几页纸") + i * 0.12),
                     accent=TE)
        say(c, "≈ 几页纸", 866, 410, t, w(1, "几页纸") + 0.3, 30, INK)

    def cc(c, t):
        u = ease_io(prog(t, s[2] + 0.1, 1.0))
        bw, bh = lerp(300, 1000, u), lerp(180, 400, u)
        cx, cy = lerp(480, 640, u), lerp(300, 320, u)
        chalkboard(c, cx, cy, bw, bh)
        if u >= 1:
            cols = [CORAL, SUN, SKY, LEAF, GRAPE, "#FF9BB0", TE]
            for i in range(7):
                k = pop(t, w(2, "好几本书") + i * 0.12)
                if k > 0:
                    book(c, 260 + i * 128, 330, 96, 160, cols[i], "", s=k, rot=(i % 3 - 1) * 4)
        chip(c, "今天：几十万，甚至上百万个 token", 640, 568, t, w(2, "几十万"), size=28, fill=SUN)

    def d(c, t):
        heat = appear(t, w(3, "计算量"), 0.6)
        if heat > 0:
            c.glow(280, 290, 120, CORAL, a=heat * (0.7 + 0.3 * math.sin(t * 6)))
        gpu_icon(c, 280, 290, 1.4, a=appear(t, s[3] - 0.05))
        chip(c, "计算更多", 280, 450, t, w(3, "计算量"), size=30, fill=PAPER)
        if pop(t, w(3, "速度")) > 0:
            v = lerp(0.85, 0.2, ease_io(prog(t, w(3, "速度"), 1.0)))
            gauge(c, 640, 300, 110, v, lw=18, c0=CORAL, c1=LEAF, lo="慢", hi="快")
        chip(c, "速度变慢", 640, 450, t, w(3, "变慢"), size=30, fill=PAPER)
        tc = w(3, "费用")
        for i in range(7):
            if pop(t, tc + i * 0.12) > 0:
                coin(c, 1000 + (i % 2) * 8, 370 - i * 16, 26)
        chip(c, "费用增加", 1000, 450, t, w(3, "增加"), size=30, fill=PAPER)
        say(c, "窗口用得越满……", 640, 145, t, s[3], 32, INK)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


def scroll_strip(c, x0, x1, y, h, t, t0, mid_fog=0.0, n_pages=9):
    k = appear(t, t0, 0.4)
    if k <= 0:
        return []
    xe = lerp(x0, x1, k)
    c.rect(x0 + 6, y - h / 2 + 7, xe - x0, h, INK, r=14, line=None)
    c.rect(x0, y - h / 2, xe - x0, h, "#FFFDF5", r=14, lw=3.5)
    pw = (x1 - x0) / n_pages
    centers = []
    for i in range(n_pages):
        px = x0 + i * pw
        if px + pw > xe + 1:
            break
        if i:
            c.line([(px, y - h / 2 + 8), (px, y + h / 2 - 8)], "#E3D9C3", 2.5, caps=False)
        for j in range(4):
            c.rect(px + 14, y - h / 2 + 22 + j * 28, pw - 28 - (j % 2) * 16, 9, "#C9D3EE", r=4, line=None)
        centers.append(px + pw / 2)
    if mid_fog > 0:
        for i in range(n_pages):
            u = i / (n_pages - 1)
            f = math.sin(math.pi * u) ** 1.5 * mid_fog
            if f > 0.05:
                c.rect(x0 + i * pw + 2, y - h / 2 + 2, pw - 4, h - 4, "#FFFFFF", r=8, line=None, a=0.75 * f)
    return centers


@scene("s8-3", poster=lambda T: T.mid(2, 0.9))
def s8_3(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        scroll_strip(c, 70, 1210, 320, 150, t, T.intro, mid_fog=appear(t, s[0] + 0.8, 0.8))
        mx = 640 + 520 * math.sin((t - T.intro) * 1.6)
        magnifier(c, mx, 300, 40)
        say(c, "开头", 150, 430, t, s[0] + 1.2, 28, TE)
        say(c, "中间", 640, 430, t, s[0] + 1.4, 28, SOFT)
        say(c, "结尾", 1130, 430, t, s[0] + 1.6, 28, TE)

    def b(c, t):
        ox, oy, gw, gh = 140, 140, 780, 410
        c.rect(ox + 8, oy + 10, gw, gh, INK, r=22, line=None)
        c.rect(ox, oy, gw, gh, PAPER, r=22, lw=4)
        x0, x1, y0, y1 = ox + 90, ox + gw - 50, oy + gh - 70, oy + 50
        c.line([(x0, y1 - 10), (x0, y0), (x1 + 10, y0)], INK, 4)
        c.text("找到信息的成功率", x0 + 8, y1 - 26, 24, INK, 900, anchor="lm")
        for lab, u in (("开头", 0.0), ("中间", 0.5), ("结尾", 1.0)):
            c.text(lab, lerp(x0 + 20, x1 - 20, u), y0 + 32, 24, INK, 900)
        c.text("信息在资料里的位置", (x0 + x1) / 2, y0 + 64 - 4, 20, SOFT, 700)
        pr = prog(t, s[1] + 0.3, T.dur(1) * 0.75)
        n = max(2, int(60 * pr))

        def f(u):
            return 0.9 - 0.38 * math.sin(math.pi * u) ** 1.2

        pts = [(lerp(x0 + 20, x1 - 20, i / 60), lerp(y0, y1, f(i / 60))) for i in range(n)]
        if pr > 0.01:
            c.line(pts, TE, 7)
        chip(c, "研究发现", 1080, 200, t, s[1] - 0.05, size=30, fill=TE, color=WHITE, stroke=1.6)
        say(c, "两头牢", 1080, 290, t, w(1, "开头和结尾"), 32, INK)
        say(c, "中间容易漏", 1080, 345, t, w(1, "夹在中间"), 32, RED, stroke=2, stroke_color=WHITE)
        robot(c, 1080, 590, t, eyes="think", s=0.55)

    def cc(c, t):
        centers = scroll_strip(c, 240, 990, 400, 130, t, -1, n_pages=7)
        tq, tm = w(2, "直接告诉它"), w(2, "显眼")
        u = ease_io(prog(t, tm, 0.9))
        px, py = lerp(centers[3] if centers else 615, 300, u), lerp(400, 205, u)
        c.rect(px - 60 + 6, py - 60 + 7, 120, 120, INK, r=12, line=None)
        c.rect(px - 60, py - 60, 120, 120, SUN, r=12, lw=3.5)
        c.text("第37页", px, py - 26, 26, INK, 900)
        c.text("小兔子", px, py + 8, 22, INK, 800)
        c.text("棉花糖", px, py + 36, 22, CORAL, 900)
        chip(c, "请找：小兔子的名字", 660, 160, t, tq, size=30, fill=PAPER)
        robot(c, 1130, 585, t, eyes="happy" if t > e[2] - 0.8 else "scan", s=0.7)
        bubble(c, "叫“棉花糖”！", 1170, 360, t, e[2] - 0.8, tail="br", size=28)
        stamp(c, True, 1215, 250, t, e[2] - 0.5, s=0.55)
        girl(c, 120, 575, t, eyes="happy", mouth="smile", s=0.7, arm_r=110)

    def d(c, t):
        rnd = random.Random(12)
        chip(c, "一股脑全塞进去", 320, 150, t, s[3] - 0.05, size=30, fill="#C9D3EE")
        for i in range(11):
            x, y = 320 + rnd.uniform(-130, 130), 300 + rnd.uniform(-70, 60)
            doc_icon(c, x, y, 60, 76, PAPER, 3, s=pop(t, s[3] + i * 0.05), accent=SKY)
        robot(c, 320, 600, t, eyes="confused", mouth="wavy", s=0.6)
        tg = w(3, "真正需要")
        chip(c, "只给真正需要的", 940, 150, t, tg - 0.2, size=30, fill=GREEN, color=WHITE, stroke=1.6)
        for i in range(2):
            doc_icon(c, 900 + i * 80, 300, 70, 88, PAPER, 4, s=pop(t, tg + i * 0.15), accent=TE)
        robot(c, 940, 600, t, eyes="happy" if t > tg + 0.5 else "normal", mouth="open", s=0.6)
        stamp(c, True, 1060, 240, t, tg + 0.6, s=0.55)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


NOTES8 = ["芝麻的生日：5 月 20 日", "朵朵喜欢恐龙", "月亮的样子会变"]


@scene("s8-4", poster=lambda T: T.mid(1, 0.95))
def s8_4(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        k = panel(c, 320, 335, 360, 400, t, T.intro)
        if k > 0.97:
            c.text("一下午的聊天记录", 320, 172, 26, INK, 900)
            for i in range(9):
                side = i % 2
                c.rect(170 + side * 60, 210 + i * 34, 220 - side * 40, 18, "#C6F1E9" if side else "#E6EBF5", r=9,
                       lw=2)
        ts = w(0, "总结成")
        u = ease_out(prog(t, ts - 0.4, 0.5))
        arrow(c, (520, 335), (lerp(520, 650, u), 335), INK, 7, 20, u=1 if u > 0 else 0)
        nk = pop(t, ts - 0.3)
        notebook(c, 900, 335, 420, 340, NOTES8, t, [ts + i * 0.45 for i in range(3)], title="要点", k=nk)

    def b(c, t):
        chalkboard(c, 400, 290, 440, 270)
        for i, ln in enumerate(("恐龙吃什么？", "霸王龙跑得快吗？", "翼龙会飞吗？")):
            chalk(c, ln, 210, 210 + i * 58, 28)
        notebook(c, 1010, 320, 330, 360, NOTES8, t, [-1, -1, -1], title="记忆本", size=22,
                 k=pop(t, s[1] - 0.05))
        u1 = ease_out(prog(t, w(1, "存进"), 0.5))
        if u1 > 0:
            curve_arrow(c, (620, 190), (850, 190), bend=-60, col=TE, lw=6, u=u1)
            say(c, "存进去", 735, 120, t, w(1, "存进") + 0.3, 28, TE, stroke=2, stroke_color=WHITE)
        u2 = ease_out(prog(t, w(1, "查出来"), 0.5))
        if u2 > 0:
            curve_arrow(c, (850, 470), (620, 470), bend=-60, col=SUN, lw=6, u=u2)
            say(c, "需要时查出来", 735, 548, t, w(1, "查出来") + 0.3, 28, INK)
            magnifier(c, 960, 300, 30)

    def cc(c, t):
        notes = NOTES8 + ["喜欢吃草莓蛋糕", "家住在小河边", "最怕打雷", "想学画画"]
        tm = s[2] + 0.4
        nk = pop(t, s[2] - 0.05)
        notebook(c, 920, 330, 400, 420, notes, t, [-1] * len(notes), title="记忆本", size=22, k=nk)
        hl = [0, 1]
        th = w(2, "只拿出")
        if nk > 0.97:
            v = prog(t, tm, 1.4) * 6
            magnifier(c, 1010, 200 + 46 * min(6, v), 30)
            for j, i in enumerate(hl):
                if t >= th:
                    y = 330 - 210 + 76 + i * 46 + 14
                    c.rect(760, y - 18, 330, 36, SUN, r=8, line=None, a=0.45)
        chalkboard(c, 330, 300, 380, 230)
        for j, i in enumerate(hl):
            u = ease_io(prog(t, th + 0.3 + j * 0.3, 0.7))
            if u > 0:
                p = lerp2((900, 330 - 210 + 76 + i * 46 + 14), (180, 250 + j * 60), u)
                if u < 1:
                    chip(c, notes[i], p[0], p[1], size=20, fill=SUN, shadow=2, padx=10)
                else:
                    chalk(c, notes[i], 160, 250 + j * 60, 26)
        chip(c, "和 RAG 一个思路", 330, 120, t, w(2, "RAG"), size=28, fill=PAPER)
        say(c, "只拿眼下需要的几条", 330, 470, t, th + 0.6, 28, INK)

    def d(c, t):
        girl(c, 170, 560, t, eyes="happy", mouth="smile", arm_r=80, talk=s[3] < t < s[3] + 1.4)
        k = panel(c, 680, 330, 600, 400, t, s[3] - 0.05)
        if k > 0.97:
            c.rect(380, 130, 600, 64, TE, r=30, lw=4)
            c.rect(382, 162, 596, 32, TE, line=None)
            c.line([(380, 194), (980, 194)], INK, 4, caps=False)
            c.text("新的对话", 680, 162, 28, WHITE, 900, stroke=2)
            bubble(c, "先说几个要点：①芝麻的生日是 5 月 20 日 ②我喜欢恐龙", 940, 360, t, s[3] + 0.3, size=24,
                   max_w=400, tail="br", fill="#C6F1E9")
            bubble(c, "记住啦！", 470, 470, t, w(3, "要点") + 0.8, size=28, tail="bl")
        robot(c, 1150, 585, t, eyes="happy", mouth="open", s=0.7, arm_l=60)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]
