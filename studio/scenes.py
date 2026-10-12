"""每一段讲解视频的分镜。

场景函数接收配音时间表 T：
  T.s[i] / T.e[i]   第 i 句配音的开始 / 结束时刻（秒）
  T.word(i, "词")   第 i 句念到某个词的时刻
返回镜头列表 [(开始时刻, 画面函数)]，画面函数 f(c, t) 负责在画布 c 上画出 t 时刻的画面。
画面坐标是 1280x720；y > 630 留给字幕，顶部 y ≈ 74 留给名词徽章。
"""
import math
import random
from functools import lru_cache

from engine import (INK, SS, W, H, Canvas, appear, back, bezier, clamp, ease_io, ease_out, lerp, lerp2, mix,
                    pop, prog, smooth, text_sprite, text_width, wave, wrap)
from actors import *  # noqa: F401,F403

SCENES, POSTER = {}, {}
WHITE = "#FFFFFF"
NIGHT_EDGE = "#7F89CF"


def scene(sid, poster=None):
    def deco(fn):
        SCENES[sid] = fn
        if poster:
            POSTER[sid] = poster
        return fn
    return deco


# ============================================================ 通用小部件
def check_row(c, x, y, text, ok, t, t0, size=26, color=INK):
    k = pop(t, t0, 0.3)
    if k <= 0:
        return
    c.text(text, x, y, size, color, 800, anchor="lm", sc=k)
    ix = x + (text_width(text, size, 800) + 28) * k
    col = GREEN if ok else RED
    c.circle(ix, y, 15 * k, col, lw=2.5)
    if ok:
        c.line([(ix - 7 * k, y), (ix - 2 * k, y + 6 * k), (ix + 8 * k, y - 6 * k)], WHITE, 4)
    else:
        c.line([(ix - 6 * k, y - 6 * k), (ix + 6 * k, y + 6 * k)], WHITE, 4)
        c.line([(ix - 6 * k, y + 6 * k), (ix + 6 * k, y - 6 * k)], WHITE, 4)


def strike(c, x, y, w, t, t0, col=RED):
    u = ease_out(prog(t, t0, 0.3))
    if u > 0:
        c.line([(x - w / 2, y + 4), (x - w / 2 + w * u, y - 4)], col, 6)


def clipboard(c, x, y, w, h, title, rows, t, t0, row_t, size=30, row_h=52):
    k = pop(t, t0, 0.45)
    if k <= 0:
        return
    c.crect(x + 8, y + 10, w, h, INK, r=22, line=None, s=k)
    c.crect(x, y, w, h, "#C98A55", r=22, lw=4, s=k)
    c.crect(x, y + 12 * k, w - 36, h - 52, PAPER, r=10, lw=3, s=k)
    c.crect(x, y - (h / 2 - 6) * k, 120, 36, "#AEB6CF", r=12, lw=3.5, s=k)
    if k < 0.97:
        return
    c.text(title, x, y - h / 2 + 70, 32, INK, 900)
    c.line([(x - w / 2 + 50, y - h / 2 + 98), (x + w / 2 - 50, y - h / 2 + 98)], "#C9D3EE", 3)
    for i, (txt, rt) in enumerate(zip(rows, row_t)):
        kk = pop(t, rt, 0.35)
        if kk > 0:
            c.text(txt, x - w / 2 + 48, y - h / 2 + 134 + i * row_h, size, INK, 800, anchor="lm", sc=kk)


def monitor(c, x, y, s=1.0, t=0.0, eyes=True):
    w, h = 130 * s, 92 * s
    c.rect(x - 16 * s, y + h / 2 - 4 * s, 32 * s, 30 * s, "#C9D3EE", r=4, lw=3)
    c.rect(x - 46 * s, y + h / 2 + 22 * s, 92 * s, 14 * s, "#C9D3EE", r=7 * s, lw=3)
    c.rect(x - w / 2, y - h / 2, w, h, "#F6F8FF", r=14 * s, lw=3.5)
    c.rect(x - w / 2 + 10 * s, y - h / 2 + 10 * s, w - 20 * s, h - 20 * s, BIT["screen"], r=8 * s, line=None)
    if eyes:
        for sg in (-1, 1):
            c.rect(x + sg * 22 * s - 6 * s, y - 12 * s, 12 * s, 24 * s, BIT["eye"], r=6 * s, line=None)


def heart(c, x, y, s=1.0, col=CORAL, a=1.0):
    c.circle(x - 10 * s, y - 6 * s, 11 * s, col, line=None, a=a)
    c.circle(x + 10 * s, y - 6 * s, 11 * s, col, line=None, a=a)
    c.poly([(x - 20.5 * s, y - 2 * s), (x + 20.5 * s, y - 2 * s), (x, y + 21 * s)], col, line=None, a=a)


@lru_cache(maxsize=8)
def card_back_sprite(w=170, h=196):
    c = Canvas.sprite(w + 12, h + 12)
    c.rect(8, 9, w, h, INK, r=16, line=None)
    c.rect(2, 2, w, h, GRAPE, r=16, lw=3.5)
    c.rect(16, 16, w - 28, h - 28, mix(GRAPE, "#FFFFFF", 0.22), r=10, lw=2.5)
    c.text("?", 2 + w / 2, 2 + h / 2, 92, WHITE, 900, stroke=4)
    return c.im


@lru_cache(maxsize=64)
def strip_sprite(text, size, tile_w):
    tw = text_width(text, size, 900)
    w = tw + tile_w + 34 * 3
    h = size * 1.9
    c = Canvas.sprite(w + 14, h + 14)
    c.rect(10, 11, w, h, INK, r=26, line=None)
    c.rect(3, 3, w, h, PAPER, r=26, lw=4)
    c.text(text, 3 + 34, 3 + h / 2, size, INK, 900, anchor="lm")
    tx = 3 + 34 + tw + 34
    c.rect(tx, 3 + h * 0.14, tile_w, h * 0.72, "#EEF6FF", r=16, lw=3)
    return c.im, (tx + tile_w / 2, 3 + h / 2), (w + 14, h + 14)


def strip(c, x, y, text, ans, t, t0, t_fill, size=54, col=LEAF, cover=False, t_reveal=1e9):
    """一行大字加一个空格子；t_fill 时刻答案弹进格子（cover=True 时先盖着，t_reveal 掀开）"""
    tile_w = max(size * 1.45, text_width(ans, size, 900) + 40)
    spr, (tcx, tcy), (sw, sh) = strip_sprite(text, size, round(tile_w))
    k = pop(t, t0, 0.4)
    if k <= 0:
        return
    c.blit(spr, x, y, "mm", s=k)
    fx, fy = x + (tcx - sw / 2) * k, y + (tcy - sh / 2) * k
    if k < 0.97:
        return
    if t >= t_fill:
        c.text(ans, fx, fy, size, col, 900, sc=pop(t, t_fill, 0.4))
    elif not cover:
        c.text("?", fx, fy, size, "#AEB6CF", 900, a=0.6 + 0.4 * math.sin(t * 6))
    if cover:
        u = ease_io(prog(t, t_reveal, 0.5))
        if u < 1:
            cw, ch = tile_w + 10, size * 1.5
            cy = fy - u * 70
            c.rect(fx - cw / 2 + 5, cy - ch / 2 + 6, cw, ch, INK, r=14, line=None, a=1 - u)
            c.rect(fx - cw / 2, cy - ch / 2, cw, ch, GRAPE, r=14, lw=3.5, a=1 - u)
            c.text("?", fx, cy, size * 0.9, WHITE, 900, stroke=2.5, a=1 - u)
    return fx, fy


def tok_layout(toks, size, x_center=None, x_left=None, gap=12, padx=16):
    ws = [text_width(tk, size, 900) + padx * 2 + 7 for tk in toks]
    total = sum(ws) + gap * (len(toks) - 1)
    x = x_left if x_left is not None else x_center - total / 2
    out = []
    for wdt in ws:
        out.append(x + wdt / 2)
        x += wdt + gap
    return out, ws


def prob_bars(c, x, y, items, t, t0, w=380, row=58, hl=None, t_hl=1e9, size=30, grow=0.5, dark=False):
    """概率条。items = [(词, 概率)]，x 是条形起点"""
    tc = WHITE if dark else INK
    for i, (lab, p) in enumerate(items):
        u = ease_out(prog(t, t0 + i * 0.1, grow))
        if u <= 0:
            continue
        yy = y + i * row
        hi = hl is not None and i == hl and t >= t_hl
        col = SUN if hi else [SKY, "#9ED7FF", "#BFE4FF", "#D6EEFF", "#E6F4FF"][min(i, 4)]
        c.text(lab, x - 18, yy, size, tc, 900, anchor="rm", a=u, stroke=2.5 if dark else 0)
        c.rect(x, yy - 17, w, 34, PAPER, r=17, lw=3, a=u)
        c.rect(x, yy - 17, max(34, w * p * u), 34, col, r=17, lw=3, a=u)
        c.text(f"{p * 100:.0f}%", x + w + 16, yy, 26, tc, 800, anchor="lm", a=u, stroke=2.5 if dark else 0)
        if hi:
            c.rect(x - 130, yy - 27, w + 230, 54, None, r=27, line=CORAL, lw=4)


def softmax_t(ps, temp):
    lg = [math.log(p) / temp for p in ps]
    m = max(lg)
    ex = [math.exp(v - m) for v in lg]
    s = sum(ex)
    return [v / s for v in ex]


def pulse(phase, l, width=1.0):
    return clamp(1 - abs(phase - l) / width)


def net_nodes(xs, counts, y_mid=330, gap=66):
    nodes = []
    for x, n in zip(xs, counts):
        g = gap if n > 2 else 140
        span = g * (n - 1)
        nodes.append([(x, y_mid - span / 2 + g * i) for i in range(n)])
    return nodes


def draw_net(c, nodes, t, layer_t0=None, act=None, ew=None, ecol=None, r=22, col=SUN, ncol=None, edge_a=0.85,
             dots=None):
    """神经网络：nodes 为每层节点坐标；act(l, i) 亮度；ew(l, i, j) 线宽；ecol(l, i, j) 线色"""
    L = len(nodes)
    vis = [1.0 if layer_t0 is None else appear(t, layer_t0[l], 0.35) for l in range(L)]
    for l in range(L - 1):
        a = min(vis[l], vis[l + 1])
        if a <= 0:
            continue
        for i, p in enumerate(nodes[l]):
            for j, q in enumerate(nodes[l + 1]):
                c.line([p, q], ecol(l, i, j) if ecol else NIGHT_EDGE, ew(l, i, j) if ew else 2.5,
                       a=a * edge_a, caps=False)
    if dots is not None:
        for l, u in dots:
            if 0 <= l < L - 1 and 0 < u < 1:
                for i, p in enumerate(nodes[l]):
                    for j, q in enumerate(nodes[l + 1]):
                        if (i + j) % 2 == 0:
                            d = lerp2(p, q, u)
                            c.circle(d[0], d[1], 5, SUN, line=None)
    for l in range(L):
        if vis[l] <= 0:
            continue
        for i, p in enumerate(nodes[l]):
            k = pop(t, layer_t0[l] + i * 0.04, 0.35) if layer_t0 else 1.0
            if k <= 0:
                continue
            bulb(c, p[0], p[1], r * k, on=act(l, i) if act else 0.0, col=ncol(l, i) if ncol else col)


def night_say(c, text, x, y, t, t0, size=36, anchor="mm"):
    say(c, text, x, y, t, t0, size, WHITE, 900, anchor, stroke=3)


def arc_arrow(c, cx, cy, R, a0, a1, col=INK, lw=7, head=20, u=1.0, a=1.0):
    if u <= 0.01:
        return
    n = 30
    pts = []
    for i in range(n + 1):
        ang = math.radians(lerp(a0, lerp(a0, a1, u), i / n))
        pts.append((cx + math.cos(ang) * R, cy + math.sin(ang) * R))
    end, prev = pts[-1], pts[-3]
    ang = math.atan2(end[1] - prev[1], end[0] - prev[0])
    c.line(pts[:-2], col, lw, a=a)
    l = (end[0] - math.cos(ang) * head + math.cos(ang + math.pi / 2) * head * 0.65,
         end[1] - math.sin(ang) * head + math.sin(ang + math.pi / 2) * head * 0.65)
    r = (end[0] - math.cos(ang) * head + math.cos(ang - math.pi / 2) * head * 0.65,
         end[1] - math.sin(ang) * head + math.sin(ang - math.pi / 2) * head * 0.65)
    c.poly([end, l, r], col, line=None, a=a)


def panel(c, x, y, w, h, t, t0, fill=PAPER, r=26):
    k = pop(t, t0, 0.45)
    if k > 0:
        c.crect(x + 8, y + 9, w, h, INK, r=r, line=None, s=k)
        c.crect(x, y, w, h, fill, r=r, lw=4, s=k)
    return k


# ============================================================ 故事一：比特学认猫（机器学习）
@scene("s1-1", poster=lambda T: T.mid(2, 0.95))
def s1_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        tx = s[0] + 0.85
        wrong = t >= tx
        robot(c, 420, 560, t, eyes="x" if wrong else "happy", mouth="wavy" if wrong else "open",
              arm_r=125 + wave(t, 5, 1.2), arm_l=10)
        photo(c, "fox", 780, 320, t, T.intro + 0.05, rot=-6 + wave(t, 1.5, 0.4))
        bubble(c, "我找到一只猫！", 470, 300, t, T.intro + 0.25, tail="bl")
        stamp(c, False, 830, 380, t, tx, s=1.15)
        if wrong:
            qmark(c, 320, 300, t, tx + 0.25)

    def b(c, t):
        girl(c, 190, 560, t, mouth="smile", arm_r=70 + wave(t, 10, 2.0), talk=t < e[1])
        rules = ["① 有尖耳朵", "② 有胡子", "③ 有四条腿"]
        rt = [w(1, "规则") + 0.1 + i * 0.45 for i in range(3)]
        clipboard(c, 570, 330, 330, 360, "认猫规则", rules, t, s[1], rt)
        ta = w(1, "电脑")
        arrow(c, (760, 330), (890, 330), SKY, 9, 24, u=ease_out(prog(t, ta - 0.2, 0.4)))
        busy = t > ta
        robot(c, 1060, 560, t, eyes="scan" if busy else "normal", mouth="flat" if busy else "smile")
        term_badge(c, "传统编程", t, w(1, "传统编程"), CORAL)
        say(c, "人写规则，电脑照做", 640, 582, t, w(1, "照着执行"), 30)

    def cc(c, t):
        tf, tc = s[2] + 0.05, w(2, "睡着") - 0.1
        for x, kind, rows, t0, rot in ((360, "fox", [("尖耳朵", True), ("有胡子", True), ("四条腿", True)], tf, -4),
                                       (920, "cat_curled", [("尖耳朵", False), ("有胡子", True), ("四条腿", False)],
                                        tc, 4)):
            photo(c, kind, x, 235, t, t0, rot=rot)
            for i, (txt, ok) in enumerate(rows):
                check_row(c, x - 70, 380 + i * 44, txt, ok, t, t0 + 0.3 + i * 0.2)
            verdict = "结论：是猫" if kind == "fox" else "结论：不是猫"
            chip(c, verdict, x - 20, 540, t, t0 + 1.0, size=28)
            stamp(c, False, x + 125, 540, t, t0 + 1.35, s=0.62)

    def d(c, t):
        rules = ["① 有尖耳朵", "② 有胡子", "③ 有四条腿", "④ 但狐狸不算", "⑤ 睡着看不见腿也算", "⑥ 毛绒玩具不算",
                 "⑦ 照片太暗的时候……", "⑧ 只露出尾巴的时候……", "⑨ 戴着帽子的时候……", "⑩ 还有……", "⑪ ……",
                 "⑫ ……", "⑬ ……"]
        t0 = s[3] - 0.1
        nf = min(len(rules), 3 + max(0.0, (t - t0 - 0.2) / 0.4))
        n = int(nf)
        top, max_h, row_h, head = 92, 470, 44, 74
        content = head + nf * row_h + 18
        vis_h = min(content, max_h)
        off = max(0.0, content - max_h)
        x0, pw = 340, 520
        c.rect(x0 + 8, top + 10, pw, vis_h, INK, r=16, line=None)
        c.rect(x0, top, pw, vis_h, PAPER, r=16, lw=4)
        hy = top + 40 - off
        if hy > top + 18:
            c.text("认猫规则（还在加……）", x0 + pw / 2, hy, 30, INK, 900, a=clamp((hy - top - 18) / 24))
        for i in range(n):
            y = top + head + i * row_h + row_h / 2 - off
            if y < top + 16 or y > top + vis_h - 14:
                continue
            a = clamp((y - top - 16) / 34)
            kk = pop(t, t0 + 0.2 + (i - 3) * 0.4, 0.3) if i >= 3 else 1.0
            c.text(rules[i], x0 + 44, y, 28, INK if i < 3 else "#C2412F", 800, anchor="lm", a=a, sc=kk)
        girl(c, 170, 560, t, eyes="normal", mouth="wavy", brows="worry")
        robot(c, 1070, 560, t, eyes="x", mouth="wavy", arm_l=40, arm_r=40)
        sweat(c, 1168, 330 + 26 * ((t * 1.3) % 1), 1.0, a=1 - ((t * 1.3) % 1) * 0.6)
        say(c, "写不完！", 1070, 230, t, w(3, "写不完"), 46, CORAL, stroke=3.5)

    def ee(c, t):
        girl(c, 500, 560, t, eyes="happy", mouth="grin", arm_r=150, arm_l=12)
        idea_bulb(c, 500, 225, t, s[4] + 0.3, s=1.1)
        robot(c, 820, 560, t, eyes="wide" if t < w(4, "换") else "happy", look=-1, arm_l=40)
        say(c, "换个思路！", 700, 140, t, w(4, "换"), 56, WHITE, stroke=5)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d), (s[4] - 0.1, ee)]


def compare_panel(c, x, y, title, ins, out, t, t0, col, hot=False):
    k = panel(c, x, y, 540, 330, t, t0)
    if k < 0.97:
        return
    chip(c, title, x, y - 165, t, t0 + 0.05, size=32, fill=col, color=WHITE, stroke=2)
    for i, lab in enumerate(ins):
        chip(c, lab, x - 178, y - 54 + i * 108, t, t0 + 0.25 + i * 0.25, size=30)
    say(c, "+", x - 178, y, t, t0 + 0.4, 36)
    arrow(c, (x - 112, y), (x - 76, y), INK, 6, 16, u=ease_out(prog(t, t0 + 0.7, 0.3)))
    if t >= t0 + 0.6:
        monitor(c, x, y - 8, 0.62)
        say(c, "电脑", x, y + 72, t, t0 + 0.6, 22, "#55607F", 800)
    arrow(c, (x + 70, y), (x + 106, y), INK, 6, 16, u=ease_out(prog(t, t0 + 0.9, 0.3)))
    chip(c, out, x + 178, y, t, t0 + 1.1, size=34, fill=SUN if hot else PAPER)
    if hot:
        sparkles(c, t, x + 178, y, 64, 4, SUN, t0=t0 + 1.25)


@scene("s1-2", poster=lambda T: T.mid(1, 0.97))
def s1_2(T):
    s, e, w = T.s, T.e, T.word
    kinds = ["cat_orange", "fox", "cat_black", "dog", "cat_white", "teddy", "cat_tux", "cat_gray", "cat_box", "dog",
             "cat_curled", "fox"]
    rnd = random.Random(11)
    slots = [(x, y) for y in (190, 320, 450) for x in (530, 660, 790, 920)]
    rnd.shuffle(slots)
    targets = [(x + rnd.uniform(-22, 22), y + rnd.uniform(-16, 16), rnd.uniform(-16, 16)) for x, y in slots]

    def a(c, t):
        robot(c, 1120, 560, t, eyes="wide", mouth="o", arm_l=30, arm_r=30)
        girl(c, 190, 560, t, eyes="happy", mouth="open", arm_r=105 + 30 * math.sin(t * 6), arm_l=14)
        for i, k in enumerate(kinds):
            tl = T.intro + 0.05 + i * 0.27
            if t < tl:
                continue
            u = ease_out(prog(t, tl, 0.75))
            p0 = (262, 395)
            tx, ty, tr = targets[i]
            ctrl = ((p0[0] + tx) / 2, min(p0[1], ty) - 200)
            x, y = bezier(p0, ctrl, (tx, ty), u)
            c.blit(photo_sprite(k), x, y, "mm", s=lerp(0.3, 0.6, u), rot=lerp(-40, tr, u))
        sparkles(c, t, 1120, 280, 80, 4, SUN, t0=T.intro + 1.0)

    def b(c, t):
        items = [("cat_orange", "猫"), ("fox", "不是猫"), ("cat_black", "猫"), ("dog", "不是猫"), ("cat_white", "猫"),
                 ("teddy", "不是猫"), ("cat_tux", "猫"), ("cat_gray", "猫")]
        tt = w(1, "猫")
        for i, (k, lab) in enumerate(items):
            x, y = 245 + (i % 4) * 263, 222 + (i // 4) * 215
            photo(c, k, x, y, t, s[1] - 0.05 + i * 0.07, s=0.72, rot=(i * 37) % 7 - 3)
            chip(c, lab, x, y + 92, t, tt + i * 0.16, size=24, fill=GREEN if lab == "猫" else GRAY, color=WHITE,
                 stroke=1.5)
        term_badge(c, "训练数据", t, w(1, "训练数据"), CORAL)

    def cc(c, t):
        robot(c, 640, 570, t, eyes="think", mouth="flat", s=1.15, chest=0.5 + 0.5 * math.sin(t * 9))
        head = (640, 360)
        ks = ["cat_white", "fox", "cat_orange", "dog", "cat_black", "teddy", "cat_gray", "cat_tux", "cat_box", "dog",
              "cat_curled", "fox", "cat_orange", "cat_white", "teddy", "cat_black"]
        for i, k in enumerate(ks):
            tl = s[2] - 0.2 + i * 0.28
            u = prog(t, tl, 0.9)
            if u <= 0 or u >= 1:
                continue
            side = -1 if i % 2 == 0 else 1
            p0 = (640 + side * 720, 170 + (i * 53) % 280)
            ctrl = (640 + side * 340, 70)
            x, y = bezier(p0, ctrl, head, ease_io(u))
            c.blit(photo_sprite(k), x, y, "mm", s=lerp(0.55, 0.12, ease_io(u)), rot=side * lerp(30, 0, u),
                   a=1 - prog(u, 0.8, 0.2))
        bubble(c, "让我自己找找规律……", 770, 320, t, w(2, "自己"), tail="bl", size=28)

    def d(c, t):
        tl, tr = s[3] + 0.05, w(3, "让电脑") - 0.3
        compare_panel(c, 345, 345, "传统编程", ["规则", "数据"], "答案", t, tl, GRAY)
        compare_panel(c, 935, 345, "机器学习", ["数据", "答案"], "规律", t, tr, CORAL, hot=True)
        term_badge(c, "机器学习", t, w(3, "机器学习"), CORAL)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s1-3", poster=lambda T: T.mid(3, 0.75))
def s1_3(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        t1, t2 = T.intro + 0.05, s[0] + 1.75
        first = t < t2
        tx = t1 + 0.95 if first else t2 + 0.95
        robot(c, 360, 560, t, eyes="x" if t >= tx else "think", mouth="wavy" if t >= tx else "open", arm_r=60)
        if first:
            photo(c, "dog", 830, 320, t, t1, rot=5)
            bubble(c, "猫！", 440, 300, t, t1 + 0.35)
        else:
            photo(c, "cat_curled", 830, 320, t, t2, rot=-5)
            bubble(c, "不是猫！", 440, 300, t, t2 + 0.3)
        stamp(c, False, 900, 380, t, tx)

    def b(c, t):
        photo(c, "dog", 290, 320, t, s[1] - 0.05, rot=-4, s=1.1)
        r1, r2, tm = s[1] + 0.3, w(1, "答案"), w(1, "错了多少")
        say(c, "比特猜：", 660, 220, t, r1, 34, anchor="rm")
        chip(c, "猫", 680, 220, t, r1 + 0.15, size=34, fill=CORAL, color=WHITE, stroke=2, anchor="lm")
        say(c, "正确答案：", 660, 320, t, r2, 34, anchor="rm")
        chip(c, "不是猫", 680, 320, t, r2 + 0.15, size=34, fill=GREEN, color=WHITE, stroke=2, anchor="lm")
        if t >= tm:
            u = ease_out(prog(t, tm, 0.9))
            say(c, "错了多少：", 660, 440, t, tm, 32, anchor="rm")
            c.rect(680, 420, 380, 40, PAPER, r=20, lw=3.5)
            c.rect(680, 420, max(40, 380 * 0.86 * u), 40, RED, r=20, lw=3.5)
            c.text(f"{int(86 * u)}%", 1078, 440, 30, INK, 900, anchor="lm")

    def cc(c, t):
        px, py, pw, ph = 120, 150, 740, 380
        c.rect(px + 8, py + 10, pw, ph, INK, r=26, line=None)
        c.rect(px, py, pw, ph, "#DDE6FA", r=26, lw=4)
        chip(c, "成千上万个小旋钮", px + pw / 2, py, t, s[2], size=28, fill=SUN)
        rnd = random.Random(5)
        tq = w(2, "轻轻")
        cols = [SKY, CORAL, LEAF, SUN, GRAPE]
        for r_ in range(3):
            for k in range(6):
                x, y = px + 75 + k * 118, py + 88 + r_ * 112
                base = rnd.uniform(-100, 100)
                tk = tq + rnd.uniform(0, 1.6)
                delta = rnd.choice([-1, 1]) * rnd.uniform(20, 42)
                u = ease_io(prog(t, tk, 0.5))
                knob(c, x, y, 34, base + delta * u, cols[(r_ * 6 + k) % 5])
                if tk <= t < tk + 0.9:
                    say(c, "+" if delta > 0 else "−", x + 40, y - 40, t, tk, 30, LEAF if delta > 0 else CORAL)
        robot(c, 1070, 560, t, eyes="think", mouth="flat", arm_l=60 + wave(t, 12, 1.5))
        u = ease_io(prog(t, w(2, "错得少"), 1.0))
        val = lerp(0.86, 0.6, u)
        c.text("错了多少", 1070, 150, 26, INK, 800)
        c.rect(930, 172, 280, 32, PAPER, r=16, lw=3)
        c.rect(930, 172, 280 * val, 32, RED, r=16, lw=3)
        c.text(f"{int(val * 100)}%", 1070, 228, 26, INK, 900)

    def d(c, t):
        cx, cy, R = 640, 350, 172
        ts = [w(3, "猜一猜"), w(3, "对答案"), w(3, "调一调")]
        nodes = [("猜一猜", -90, SKY), ("对答案", 30, LEAF), ("调一调", 150, SUN)]
        ring = appear(t, ts[0] - 0.3, 0.4)
        if ring > 0:
            c.circle(cx, cy, R, None, "#FFFFFF", 16, a=ring * 0.7)
        for i in range(3):
            a0, a1 = nodes[i][1] + 26, nodes[(i + 1) % 3][1] - 26 + (360 if i == 2 else 0)
            arc_arrow(c, cx, cy, R, a0, a1, INK, 7, 22, u=ease_out(prog(t, ts[min(i + 1, 2)] - 0.1 + (0.5 if i == 2 else 0), 0.45)))
        if t >= ts[2] + 0.5:
            sp = t - ts[2] - 0.5
            ang = math.radians(-90 + 360 * (sp * 0.45 + 0.08 * sp * sp))
            c.glow(cx + math.cos(ang) * R, cy + math.sin(ang) * R, 22, SUN)
            c.circle(cx + math.cos(ang) * R, cy + math.sin(ang) * R, 11, SUN, lw=3)
        for (lab, ang, col), tn in zip(nodes, ts):
            a_ = math.radians(ang)
            chip(c, lab, cx + math.cos(a_) * R, cy + math.sin(a_) * R, t, tn, size=36, fill=col)
        kx, ky = cx + math.cos(math.radians(150)) * R - 30, cy + math.sin(math.radians(150)) * R + 70
        if t >= ts[2]:
            knob(c, kx, ky, 24 * pop(t, ts[2] + 0.1), wave(t, 40, 0.8), SUN)
        say(c, "反复循环", cx, cy, t, ts[2] + 0.3, 36, INK)
        tp, tt_ = w(3, "参数"), w(3, "训练")
        if t < tt_ - 0.05:
            term_badge(c, "参数", t, tp, CORAL)
        else:
            term_badge(c, "训练", t, tt_, CORAL)

    def ee(c, t):
        ox, oy, gw, gh = 160, 140, 720, 420
        c.rect(ox + 8, oy + 10, gw, gh, INK, r=22, line=None)
        c.rect(ox, oy, gw, gh, PAPER, r=22, lw=4)
        x0, x1, y0, y1 = ox + 90, ox + gw - 40, oy + gh - 70, oy + 50

        def Y(v):
            return y0 - (y1 - y0) * -1 * (v - 0.4) / 0.6

        for v in (0.5, 0.75, 1.0):
            c.line([(x0, Y(v)), (x1, Y(v))], "#E1E7F5", 2.5, caps=False)
            c.text(f"{int(v * 100)}%", x0 - 12, Y(v), 22, "#55607F", 700, anchor="rm")
        c.line([(x0, y1 - 10), (x0, y0), (x1 + 10, y0)], INK, 4)
        c.text("准确率", x0 + 8, y1 - 26, 24, INK, 900, anchor="lm")
        c.text("练习次数 →", x1, y0 + 32, 24, INK, 900, anchor="rm")
        u = prog(t, s[4] + 0.05, T.dur(4) * 0.85)

        def acc(v):
            return 0.5 + 0.46 * (1 - math.exp(-4.2 * v)) + 0.025 * math.sin(28 * v) * (1 - v)

        n = max(2, int(80 * u))
        pts = [(x0 + (x1 - x0) * (i / 80), Y(acc(i / 80))) for i in range(n)]
        if u > 0.01:
            c.line(pts, CORAL, 7)
            hx, hy = pts[-1]
            c.circle(hx, hy, 11, CORAL, lw=3.5)
            c.text(f"{acc(u) * 100:.0f}%", hx + 4, hy - 34, 28, CORAL, 900, stroke=2, stroke_color=WHITE)
        done = u > 0.92
        robot(c, 1060, 560, t, eyes="happy" if done else "normal", mouth="open" if done else "smile",
              arm_l=150 if done else 10, arm_r=150 if done else 10)
        if done:
            confetti(c, t, s[4] + 0.05 + T.dur(4) * 0.85 * 0.92, 1060, 300, power=0.8)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d), (s[4] - 0.1, ee)]


@scene("s1-4", poster=lambda T: T.mid(1, 0.3))
def s1_4(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        chip(c, "期末考试", 640, 135, t, T.intro, size=40, fill=CORAL, color=WHITE, stroke=2.5)
        girl(c, 270, 560, t, eyes="happy", mouth="smile", arm_r=95)
        robot(c, 1010, 560, t, eyes="wide", mouth="o")
        ph = (t * 1.3) % 1
        sweat(c, 1105, 330 + 26 * ph, 1.0, a=1 - ph * 0.6)
        tf = s[0] + 1.5
        u = prog(t, tf, 0.5)
        k = pop(t, T.intro + 0.15)
        if u < 0.5:
            c.blit(card_back_sprite(), 640, 350, "mm", s=1.15 * k, sx=max(0.02, 1 - 2 * u))
        else:
            c.blit(photo_sprite("cat_box"), 640, 350, "mm", s=1.15, sx=max(0.02, 2 * u - 1))

    def b(c, t):
        photo(c, "cat_box", 440, 320, t, -1, s=1.15)
        ok = t > s[1] + 1.0
        robot(c, 930, 560, t, eyes="happy" if ok else "normal", mouth="open",
              arm_l=150 if ok else 10, arm_r=150 if ok else 10)
        bubble(c, "猫！", 990, 300, t, s[1] + 0.3, tail="bl")
        stamp(c, True, 545, 410, t, s[1] + 1.0)
        confetti(c, t, s[1] + 1.0, 440, 300)
        tg, tj = w(1, "规律"), w(1, "死记硬背")
        chip(c, "学到了规律", 300, 565, t, tg, size=28, fill=GREEN, color=WHITE, stroke=1.5)
        chip(c, "死记硬背", 560, 565, t, tj, size=28, fill=PAPER, color="#8A93AE")
        strike(c, 560, 565, 140, t, tj + 0.35)
        term_badge(c, "泛化", t, w(1, "泛化"), CORAL)
        chip(c, "举一反三", 640, 145, t, w(1, "举一反三"), size=30, fill=SUN)

    def cc(c, t):
        photo(c, "cat_hairless", 290, 300, t, s[2] - 0.05, s=1.1)
        robot(c, 560, 575, t, eyes="confused", mouth="wavy", s=0.8)
        bubble(c, "不……不是猫？", 585, 372, t, s[2] + 0.35, tail="bl", size=26)
        stamp(c, False, 375, 385, t, s[2] + 1.1, s=0.9)
        px, py, pw, ph = 760, 150, 450, 390
        tp = w(2, "因为") - 0.2
        if panel(c, px + pw / 2, py + ph / 2, pw, ph, t, tp) > 0.97:
            chip(c, "训练数据", px + pw / 2, py, t, tp + 0.05, size=28, fill=CORAL, color=WHITE, stroke=1.6)
            ks = ["cat_orange", "fox", "cat_black", "dog", "cat_white", "teddy", "cat_tux", "cat_gray", "cat_box", "dog",
                  "cat_curled", "fox"]
            pos = []
            for i, k in enumerate(ks):
                x, y = px + 78 + (i % 4) * 98, py + 82 + (i // 4) * 104
                pos.append((x, y))
                c.blit(photo_sprite(k), x, y, "mm", s=0.38 * pop(t, tp + 0.15 + i * 0.03))
            tm = w(2, "训练数据")
            v = prog(t, tm, 1.6) * (len(pos) - 1)
            if t >= tm:
                i0 = int(v)
                p = lerp2(pos[i0], pos[min(i0 + 1, len(pos) - 1)], v - i0)
                magnifier(c, p[0] + 10, p[1] - 6, 34)
            chip(c, "无毛猫：0 张", px + pw / 2, py + ph - 26, t, w(2, "一只"), size=28, fill=RED, color=WHITE,
                 stroke=1.6)

    def d(c, t):
        tl, tr = s[3] + 0.05, w(3, "数据越丰富")
        chip(c, "见得少", 330, 130, t, tl, size=30, fill=GRAY, color=WHITE, stroke=1.6)
        for i, (k, dx, dy, r) in enumerate((("cat_orange", -46, 0, -8), ("cat_orange", 46, 10, 6))):
            photo(c, k, 330 + dx, 250 + dy, t, tl + 0.1 + i * 0.12, s=0.6, rot=r)
        robot(c, 330, 575, t, eyes="confused", mouth="wavy", s=0.78)
        chip(c, "见得多", 930, 130, t, tr, size=30, fill=GREEN, color=WHITE, stroke=1.6)
        kinds = ["cat_orange", "cat_black", "cat_white", "cat_hairless", "cat_tux", "cat_gray", "cat_box", "cat_curled",
                 "fox", "dog"]
        for i, k in enumerate(kinds):
            x = 930 + (i % 5 - 2) * 74
            y = 215 + (i // 5) * 92 + (i % 2) * 8
            photo(c, k, x, y, t, tr + 0.08 * i, s=0.5, rot=(i * 29) % 13 - 6)
        happy = t > tr + 0.9
        robot(c, 930, 575, t, eyes="star" if happy else "normal", mouth="open", s=0.78,
              arm_l=140 if happy else 10, arm_r=140 if happy else 10)
        arrow(c, (520, 400), (740, 400), CORAL, 9, 24, u=ease_out(prog(t, tr - 0.2, 0.5)))
        say(c, "更可靠", 630, 360, t, w(3, "越可靠"), 34, CORAL)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事二：灯泡小镇（神经网络）
@scene("s2-1", poster=lambda T: T.mid(3, 0.9))
def s2_1(T):
    s, e, w = T.s, T.e, T.word
    F = [(330, 200), (330, 340), (330, 480)]
    C = (760, 330)
    ins = [1, 0, 1]
    wts = [0.9, 0.2, 0.6]
    wid = [13, 3.5, 8.5]
    cl = [(800, 200), (950, 185), (720, 300), (880, 290), (1035, 300), (800, 405), (965, 400)]
    cl_e = [(0, 1), (0, 3), (1, 3), (2, 3), (3, 4), (2, 5), (3, 5), (3, 6), (4, 6), (5, 6), (1, 4), (0, 2)]

    def a(c, t):
        lid = ease_out(prog(t, T.intro + 0.1, 0.6))
        hx, hy = 360, robot_head_y(560, 1.1) + 14
        if lid > 0:
            c.poly([(hx - 60, hy), (hx + 60, hy), (hx + 180, hy - 280), (hx - 180, hy - 280)], "#FFE27A", line=None,
                   a=0.26 * lid)
            c.poly([(hx - 34, hy), (hx + 34, hy), (hx + 90, hy - 280), (hx - 90, hy - 280)], "#FFF3B8", line=None,
                   a=0.22 * lid)
        robot(c, 360, 560, t, eyes="happy", mouth="smile", s=1.1, lid=lid, arm_l=20, arm_r=40)
        arrive = []
        for i, p in enumerate(cl):
            tl = T.intro + 0.35 + i * 0.3
            u = prog(t, tl, 1.1)
            arrive.append(u >= 1)
            if 0 < u < 1:
                q = bezier((hx, hy - 20), (600, 60), p, ease_io(u))
                bulb(c, q[0], q[1], 14 + 8 * u, on=0.9)
        for i, j in cl_e:
            if arrive[i] and arrive[j]:
                c.line([cl[i], cl[j]], NIGHT_EDGE, 3, a=0.9)
        for i, p in enumerate(cl):
            if arrive[i]:
                bulb(c, p[0], p[1], 22, on=0.55 + 0.45 * math.sin(t * 3 + i * 1.7))
        night_say(c, "小灯泡 ≈ 神经元", 880, 520, t, w(0, "神经元"), 40)
        term_badge(c, "神经元", t, w(0, "神经元"), "#F2A900")

    def view(c, t, show_w=None, compute=None):
        t_in = s[1] - 0.05
        for i, p in enumerate(F):
            wv = 4
            if show_w is not None:
                wv = lerp(4, wid[i], ease_out(prog(t, show_w + i * 0.3, 0.5)))
            red = compute is not None and False
            c.line([p, C], NIGHT_EDGE, wv, a=appear(t, t_in + 0.3))
            if ins[i] and t > t_in + 0.6:
                ph = ((t - t_in - 0.6 - i * 0.25) % 1.2) / 1.2
                q = lerp2(p, C, ph)
                c.glow(q[0], q[1], 16, SUN, a=0.9)
                c.circle(q[0], q[1], 7, SUN, line=None)
        center_on = 0.0
        if compute is not None:
            center_on = ease_out(prog(t, compute["light"], 0.3))
            c.line([C, (1250, C[1])], NIGHT_EDGE, 4, a=appear(t, compute["light"]))
            if t > compute["out"]:
                ph = ((t - compute["out"]) % 1.0)
                q = lerp2(C, (1250, C[1]), ph)
                c.glow(q[0], q[1], 18, SUN)
                c.circle(q[0], q[1], 8, SUN, line=None)
        for i, p in enumerate(F):
            bulb(c, p[0], p[1], 34 * pop(t, t_in + i * 0.15), on=0.95 if ins[i] else 0.0)
            if compute is not None:
                chip(c, str(ins[i]), p[0] - 80, p[1], t, compute["in"] + i * 0.15, size=28,
                     fill=SUN if ins[i] else PAPER)
        bulb(c, C[0], C[1], 62 * pop(t, t_in), on=center_on, base=True)
        if show_w is not None:
            for i, p in enumerate(F):
                m = lerp2(p, C, 0.48)
                chip(c, f"×{wts[i]}", m[0], m[1] - 30, t, show_w + i * 0.3, size=26, fill=PAPER)

    def b(c, t):
        view(c, t)
        night_say(c, "朋友们", 330, 110, t, s[1] + 0.3, 32)
        night_say(c, "我", 760, 210, t, s[1] + 0.5, 32)

    def cc(c, t):
        view(c, t, show_w=w(2, "信任程度") - 0.2)
        term_badge(c, "权重", t, w(2, "权重"), "#F2A900")

    def d(c, t):
        tm, tsum, tl, to = w(3, "乘上权重"), w(3, "加在一起"), w(3, "亮起来"), w(3, "往下传")
        comp = dict(light=tl, out=to, **{"in": s[3]})
        view(c, t, show_w=-10, compute=comp)
        parts = ["1×0.9", "+", "0×0.2", "+", "1×0.6", "=", "1.5"]
        xs, ws = tok_layout(parts, 36, x_center=760, gap=10, padx=4)
        for i, (p, x) in enumerate(zip(parts, xs)):
            t0 = tm + i * 0.18 if i < 5 else tsum + (i - 5) * 0.25
            say(c, p, x, 130, t, t0, 36, SUN if p == "1.5" else WHITE, 900, stroke=3)
        bx, by, bw = 660, 470, 200
        u = ease_out(prog(t, tsum, 0.7))
        c.rect(bx, by - 15, bw, 30, "#2A3270", r=15, lw=3, a=appear(t, s[3]))
        if u > 0:
            c.rect(bx, by - 15, max(30, bw * 0.75 * u), 30, SUN, r=15, lw=3)
        if t > s[3]:
            c.line([(bx + bw / 2, by - 26), (bx + bw / 2, by + 26)], CORAL, 5)
            night_say(c, "门槛", bx + bw / 2, by + 50, t, s[3] + 0.2, 24)
            night_say(c, "总分", bx - 16, by, t, s[3] + 0.2, 26, anchor="rm")
        if t >= tl:
            say(c, "叮！", 870, 230, t, tl, 50, SUN, stroke=4, rot=-8)

    def ee(c, t):
        nodes = net_nodes([200, 420, 640, 860, 1080], [4, 6, 6, 5, 3], 320, gap=64)
        lt = [s[4] - 0.15 + l * 0.12 for l in range(5)]
        ph = ((t - s[4] - 0.5) * 2.4) % 7.0 - 1.0
        draw_net(c, nodes, t, lt, act=lambda l, i: 0.12 + 0.88 * pulse(ph, l, 1.1), r=20,
                 dots=[(int(math.floor(ph)), ph - math.floor(ph))])
        chip(c, "很多灯泡连在一起", 640, 585, t, w(4, "很多灯泡"), size=30, fill=SUN)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d), (s[4] - 0.1, ee)]


def big_net_nodes():
    X = [380, 590, 800, 1040]
    nodes = net_nodes(X, [6, 5, 4, 2], 320, gap=68)
    nodes[3] = [(1040, 255), (1040, 395)]
    return X, nodes


@scene("s2-2", poster=lambda T: T.mid(2, 0.95))
def s2_2(T):
    s, e, w = T.s, T.e, T.word
    X, nodes = big_net_nodes()

    def f(c, t):
        lt = [T.intro + 0.1 + l * 0.3 for l in range(4)]
        th = [s[1] + 0.1, w(1, "往后一层"), s[2] + 0.05, w(2, "最后一层")]
        c.blit(pixel_sprite("cat_orange"), 150, 320, "mm", s=pop(t, T.intro))
        arrow(c, (238, 320), (322, 320), SUN, 7, 20, u=ease_out(prog(t, T.intro + 0.3, 0.3)))
        night_say(c, "输入的照片", 150, 430, t, T.intro + 0.2, 24)
        deep = t >= s[3]

        def act(l, i):
            if deep:
                ph = ((t - s[3]) * 2.2) % 5.5 - 0.6
                return 0.1 + 0.9 * pulse(ph, l, 1.0)
            if t < th[l]:
                return 0.06
            if l == 3:
                return 1.0 if i == 0 else 0.15
            return 0.35 + 0.6 * pulse((t - th[l]) * 1.4, 0.0, 1.0) + 0.05

        for l in range(3):
            if t >= th[l] and not deep:
                a = appear(t, th[l], 0.3)
                ys = [p[1] for p in nodes[l]]
                c.rect(X[l] - 42, min(ys) - 42, 84, max(ys) - min(ys) + 84, SUN, r=42, line=None, a=0.14 * a)
        draw_net(c, nodes, t, lt, act=act, r=22)
        labs = [("像素小点", th[0]), ("边缘·线条", th[1]), ("耳朵·眼睛", th[2])]
        for l, (lab, tl_) in enumerate(labs):
            a_ = 1 - appear(t, s[3] - 0.1, 0.3)
            if a_ > 0:
                chip(c, lab, X[l], 560, t, tl_, size=26, fill=PAPER, a=a_)
        if t >= th[3]:
            chip(c, "是猫 92%", 1080, 255, t, th[3] + 0.2, size=26, fill=SUN, anchor="lm")
            chip(c, "不是猫 8%", 1080, 395, t, th[3] + 0.35, size=26, fill=PAPER, anchor="lm")
        if deep:
            u = ease_out(prog(t, w(3, "层数很多") - 0.2, 0.5))
            if u > 0:
                y = 545
                c.line([(X[0] - 30, y - 16), (X[0] - 30, y), (lerp(X[0] - 30, X[2] + 30, u), y)], WHITE, 5)
                if u >= 1:
                    c.line([(X[2] + 30, y), (X[2] + 30, y - 16)], WHITE, 5)
                night_say(c, "层数越多，网络越“深”", (X[0] + X[2]) / 2, 585, t, w(3, "层数很多"), 30)
        tdeep = w(3, "深度")
        if t < tdeep - 0.05:
            term_badge(c, "神经网络", t, w(0, "神经网络"), "#F2A900")
        else:
            term_badge(c, "深度学习", t, tdeep, "#F2A900")

    return [(0, f)]


@scene("s2-3", poster=lambda T: T.mid(1, 0.55))
def s2_3(T):
    s, e, w = T.s, T.e, T.word
    X, nodes = big_net_nodes()
    rnd = random.Random(23)
    base = {}
    for l in range(3):
        for i in range(len(nodes[l])):
            for j in range(len(nodes[l + 1])):
                base[(l, i, j)] = rnd.uniform(1.5, 6.0)
    keys = list(base)
    rnd.shuffle(keys)
    changes = {k: (rnd.choice([-1, 1]), s[2] + 0.2 + n * 0.32) for n, k in enumerate(keys[:12])}

    def f(c, t):
        tf = T.intro + 0.2
        tb0, tb1 = s[1] + 0.1, s[1] + 0.1 + T.dur(1) * 0.85
        tf2 = s[3] + 0.5
        c.blit(pixel_sprite("fox"), 150, 320, "mm", s=pop(t, T.intro))
        arrow(c, (238, 320), (322, 320), SUN, 7, 20, u=ease_out(prog(t, T.intro + 0.3, 0.3)))
        second = t >= tf2
        fwd = (t - (tf2 if second else tf)) * 2.6
        bwd = 3.4 - (t - tb0) / (tb1 - tb0) * 3.8 if tb0 <= t < s[2] - 0.1 else None

        def act(l, i):
            if bwd is not None:
                return 0.08
            v = 0.1 + 0.9 * pulse(fwd, l, 1.0)
            if l == 3 and fwd > 3:
                good = (i == 1) if second else (i == 0)
                return 1.0 if good else 0.12
            return v

        def ncol(l, i):
            if bwd is not None and abs(bwd - l) < 0.9:
                return RED
            return SUN

        def act2(l, i):
            if bwd is not None:
                return clamp(1 - abs(bwd - l) / 0.9)
            return act(l, i)

        def ew(l, i, j):
            b = base[(l, i, j)]
            if (l, i, j) in changes:
                sg, tc = changes[(l, i, j)]
                b = b + sg * 3.0 * ease_out(prog(t, tc, 0.4))
            return max(1.0, b)

        def ecol(l, i, j):
            if bwd is not None and bwd < l + 1:
                return "#FF7B72"
            if t >= s[2] and t < s[3] and (l, i, j) in changes and t >= changes[(l, i, j)][1]:
                return LEAF if changes[(l, i, j)][0] > 0 else "#FF9F5A"
            return NIGHT_EDGE

        draw_net(c, nodes, t, act=act2, ew=ew, ecol=ecol, r=22, ncol=ncol)
        for (l, i, j), (sg, tc) in changes.items():
            if s[2] <= t < s[3] + 0.2:
                m = lerp2(nodes[l][i], nodes[l + 1][j], 0.5)
                chip(c, "+" if sg > 0 else "−", m[0], m[1], t, tc, size=20, fill=LEAF if sg > 0 else "#FF9F5A",
                     color=WHITE, shadow=2, padx=10, stroke=1.2)
        chip(c, "是猫", 1080, 255, size=24, fill=PAPER, anchor="lm")
        chip(c, "不是猫", 1080, 395, size=24, fill=PAPER, anchor="lm")
        if not second:
            stamp(c, False, 1215, 255, t, tf + 1.3, s=0.6)
            night_say(c, "是狐狸！", 150, 430, t, tf + 1.5, 28)
            qmark(c, 690, 150, t, s[0] + 1.9, s=0.8)
        else:
            stamp(c, True, 1230, 395, t, tf2 + 1.25, s=0.6)
        if tb0 - 0.2 <= t < s[2] - 0.1:
            chip(c, "错误往回传", 690, 140, t, tb0 - 0.1, size=30, fill=RED, color=WHITE, stroke=1.8)
            arrow(c, (900, 140), (820, 140), WHITE, 6, 18, u=1, outline=False)
        if s[2] <= t < s[3]:
            night_say(c, "多信一点 +   少信一点 −", 690, 585, t, s[2] + 0.4, 28)
        term_badge(c, "反向传播", t, w(3, "反向传播"), "#F2A900")

    return [(0, f)]


@lru_cache(maxsize=1)
def city_points():
    rnd = random.Random(5)
    return [(rnd.uniform(-40, W + 40), rnd.uniform(110, 610), rnd.uniform(0.8, 2.4), rnd.random()) for _ in range(2400)]


@scene("s2-4", poster=lambda T: T.mid(3, 0.7))
def s2_4(T):
    s, e, w = T.s, T.e, T.word
    nodes = net_nodes([430, 640, 850], [3, 4, 2], 320, gap=110)
    vals = ["0.82", "-0.13", "1.70", "0.05", "-0.66", "0.31", "-1.20", "0.47", "0.09", "-0.38", "0.94", "-0.25"]
    edges = [(0, i, j) for i in range(3) for j in range(4)] + [(1, i, j) for i in range(4) for j in range(2)]

    def a(c, t):
        draw_net(c, nodes, t, act=lambda l, i: 0.5 + 0.3 * math.sin(t * 2 + l + i), r=30)
        path = [(0, 0), (1, 1), (2, 0), (1, 3)]
        tl = T.intro + 0.4
        k = (t - tl) / 0.95
        if k >= 0:
            i0 = min(int(k), len(path) - 1)
            p = nodes[path[i0][0]][path[i0][1]]
            magnifier(c, p[0] + 20, p[1] - 18, 40)
            for n in range(i0 + 1):
                q = nodes[path[n][0]][path[n][1]]
                qmark(c, q[0] + 34, q[1] - 70, t, tl + n * 0.95 + 0.4, s=0.6, col=SUN)
        chip(c, "知识不在某一个灯泡里", 640, 585, t, w(0, "并不"), size=30, fill=SUN)

    def b(c, t):
        draw_net(c, nodes, t, act=lambda l, i: 0.45, r=30, ew=lambda l, i, j: 2 + ((i * 3 + j * 5 + l) % 5) * 1.6)
        t0 = s[1] + 0.2
        for n, (l, i, j) in enumerate(edges[::2]):
            m = lerp2(nodes[l][i], nodes[l + 1][j], 0.5 + 0.12 * ((n % 3) - 1))
            chip(c, vals[n % len(vals)], m[0], m[1], t, t0 + n * 0.16, size=20, fill=PAPER, shadow=2, padx=10)
        term_badge(c, "参数", t, w(1, "参数"), "#F2A900")
        chip(c, "知识 = 连线上的数字", 640, 585, t, w(1, "这些数字"), size=30, fill=SUN)

    def cc(c, t):
        k = panel(c, 400, 320, 440, 380, t, s[2] - 0.05)
        if k > 0.97:
            mini = net_nodes([300, 400, 500], [3, 4, 2], 290, gap=56)
            for l in range(2):
                for p in mini[l]:
                    for q in mini[l + 1]:
                        c.line([p, q], "#AEB6CF", 2.5, caps=False)
            for l in range(3):
                for p in mini[l]:
                    c.circle(p[0], p[1], 15, SUN, lw=3)
            c.text("认图小网络", 400, 450, 30, INK, 900)
        bx, by = 760, 230
        c.text("参数个数", bx, by - 40, 28, WHITE, 900, anchor="lm", stroke=2.5)
        u = ease_out(prog(t, w(2, "几万"), 0.6))
        c.rect(bx, by, 420, 40, "#2A3270", r=20, lw=3)
        c.rect(bx, by, max(40, 22 * u), 40, SUN, r=20, lw=3)
        if u > 0:
            say(c, "几万个", bx + 70, by + 20, t, w(2, "几万"), 30, WHITE, 900, "lm", stroke=3)

    def d(c, t):
        zoom = lerp(2.6, 1.0, ease_out(prog(t, s[3] - 0.1, 1.8)))
        for x, y, r, ph in city_points():
            X = W / 2 + (x - W / 2) * zoom
            Y = 360 + (y - 360) * zoom
            if -10 < X < W + 10 and 90 < Y < 630:
                tw = 0.5 + 0.5 * math.sin(t * 2.4 + ph * 6.28)
                c.circle(X, Y, r * zoom ** 0.5, SUN if ph < 0.65 else WHITE, line=None, a=0.35 + 0.6 * tw)
        chip(c, "大语言模型", 640, 220, t, w(3, "大语言模型"), size=36, fill=SUN)
        say(c, "几千亿个参数", 640, 330, t, w(3, "几千亿"), 76, WHITE, 900, stroke=6)
        bx, by = 300, 450
        u = ease_out(prog(t, w(3, "几千亿") + 0.3, 1.0))
        if u > 0:
            c.rect(bx, by, 22, 34, SKY, r=10, lw=3)
            night_say(c, "认图小网络", bx - 14, by + 17, t, w(3, "几千亿") + 0.3, 22, anchor="rm")
            c.rect(bx, by + 52, 40 + 960 * u, 34, SUN, r=10, lw=3)
            night_say(c, "大语言模型", bx - 14, by + 69, t, w(3, "几千亿") + 0.3, 22, anchor="rm")
            if u > 0.95:
                say(c, "……", 1280 - 30, by + 69, t, w(3, "几千亿") + 1.3, 30, INK, 900, "rm")

    def ee(c, t):
        items = [(300, "参数更多", s[4] + 0.1), (640, "数据更多", w(4, "数据")), (980, "算力更多", w(4, "算力"))]
        for x, lab, t0 in items:
            k = panel(c, x, 300, 230, 230, t, t0)
            if k > 0.97:
                if lab == "参数更多":
                    for i in range(3):
                        for j in range(3):
                            c.circle(x - 40 + i * 40, 270 + j * 30 - 25, 12, SUN, lw=2.5)
                elif lab == "数据更多":
                    stack_icon(c, x, 260, 1.0)
                else:
                    gpu_icon(c, x, 262, 0.9)
                c.text(lab, x, 375, 30, INK, 900)
        for x, t0 in ((470, w(4, "数据") - 0.1), (810, w(4, "算力") - 0.1)):
            night_say(c, "+", x, 300, t, t0, 54)
        arrow(c, (640, 440), (640, 510), SUN, 8, 22, u=ease_out(prog(t, w(4, "训练") - 0.2, 0.4)))
        chip(c, "学会更多规律", 640, 560, t, w(4, "能学会"), size=32, fill=SUN)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d), (s[4] - 0.1, ee)]


# ============================================================ 故事三：接字高手（大语言模型）
def chat_panel(c, x, y, t, t0, q, ans, t_type, cps=4.5):
    w, h = 600, 400
    k = panel(c, x, y, w, h, t, t0, r=30)
    if k < 0.97:
        return
    x0, y0 = x - w / 2, y - h / 2
    c.rect(x0, y0, w, 64, LEAF, r=30, lw=4)
    c.rect(x0 + 2, y0 + 34, w - 4, 30, LEAF, line=None)
    c.line([(x0, y0 + 64), (x0 + w, y0 + 64)], INK, 4)
    c.text("和比特聊天", x, y0 + 33, 28, WHITE, 900, stroke=2)
    bubble(c, q, x0 + w - 70, y0 + 160, t, t0 + 0.3, size=26, tail="br", fill="#C6F1DA")
    n = int(max(0, t - t_type) * cps)
    shown = ans[:n]
    if t >= t_type - 0.2:
        c.circle(x0 + 52, y0 + 280, 28, BIT["screen"], lw=3.5)
        for sg in (-1, 1):
            c.rect(x0 + 52 + sg * 10 - 4, y0 + 270, 8, 16, BIT["eye"], r=4, line=None)
        bw = max(80, text_width(shown, 28, 800) + 50)
        c.rect(x0 + 96, y0 + 250, bw, 60, PAPER, r=24, lw=3.5)
        c.text(shown, x0 + 120, y0 + 280, 28, INK, 800, anchor="lm")
        if n < len(ans):
            cx_ = x0 + 122 + text_width(shown, 28, 800)
            if int(t * 4) % 2 == 0:
                c.rect(cx_, y0 + 264, 3.5, 32, INK, line=None)
            chip(c, "猜下一个字…", cx_ + 10, y0 + 352, size=20, fill=SUN, shadow=2, padx=10)


@scene("s3-1", poster=lambda T: T.mid(1, 0.95))
def s3_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        t1, t2 = T.intro + 0.05, s[0] + 2.6
        girl(c, 170, 560, t, mouth="smile", arm_r=60, talk=(t1 < t < t1 + 0.8) or (t2 < t < t2 + 0.7))
        robot(c, 1110, 560, t, eyes="happy", mouth="open")
        if t < t2 - 0.05:
            strip(c, 640, 250, "床前明月", "光", t, t1, t1 + 0.9)
        else:
            strip(c, 640, 250, "白日依山", "尽", t, t2, t2 + 0.8)
        term_badge(c, "大语言模型", t, w(0, "大语言模型"), LEAF)
        chip(c, "根据前文，预测下一个字", 640, 430, t, w(0, "根据前面"), size=32, fill=SUN)

    def b(c, t):
        strip(c, 640, 180, "今天的作业实在是太", "多了", t, s[1] - 0.05, w(1, "多了"), size=50)
        items = [("多了", 0.62), ("难了", 0.21), ("少了", 0.06), ("好玩了", 0.03)]
        prob_bars(c, 500, 330, items, t, w(1, "后面") - 0.4, w=420, row=62, hl=0, t_hl=w(1, "多了"))
        robot(c, 1150, 575, t, eyes="think" if t < w(1, "多了") else "happy", s=0.8)

    def cc(c, t):
        chat_panel(c, 640, 335, t, s[2] - 0.05, "今天做点什么好呢？", "我们去公园放风筝吧！", s[2] + 0.9, cps=4.2)

    def d(c, t):
        for i in range(9):
            y = 170 + i * 48
            ph = (t * 1.8 + i * 0.37) % 1
            x = lerp(1300, -200, ph)
            c.line([(x, y), (x + 160, y)], WHITE, 6, a=0.8)
        robot(c, 640, 575, t, eyes="star", mouth="open", s=1.15, arm_l=150, arm_r=150)
        chip(c, "又快", 380, 260, t, s[3] + 0.05, size=46, fill=SUN, rot=-6)
        chip(c, "又准", 900, 260, t, w(3, "准"), size=46, fill=LEAF, color=WHITE, stroke=2.5, rot=6)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s3-2", poster=lambda T: T.mid(1, 0.92))
def s3_2(T):
    s, e, w = T.s, T.e, T.word
    rnd = random.Random(31)
    flyers = [(rnd.uniform(210, 1070), rnd.uniform(150, 470), rnd.choice([CORAL, SUN, SKY, LEAF, GRAPE]),
               rnd.uniform(-1, 1)) for _ in range(18)]

    def a(c, t):
        bookshelf(c, 160, 110, 960, 400)
        robot(c, 640, 600, t, eyes="happy", mouth="open", arm_l=60, arm_r=60)
        head = (640, 450)
        for i, (x, y, col, sp) in enumerate(flyers):
            tl = T.intro + 0.1 + i * 0.22
            u = prog(t, tl, 0.8)
            if 0 < u < 1:
                p = bezier((x, y), ((x + 640) / 2, min(y, 300) - 120), head, ease_io(u))
                ang = sp * 6 * u * 3.14
                ca, sa = math.cos(ang), math.sin(ang)
                bw, bh = 16 * (1 - 0.5 * u), 40 * (1 - 0.5 * u)
                pts = [(p[0] + ca * dx - sa * dy, p[1] + sa * dx + ca * dy) for dx, dy in
                       ((-bw, -bh), (bw, -bh), (bw, bh), (-bw, bh))]
                c.poly(pts, col, lw=2.5)
        term_badge(c, "预训练", t, w(0, "预训练"), LEAF)

    def b(c, t):
        robot(c, 210, 560, t, eyes="think", mouth="flat")
        tc, tg, tr = w(1, "盖住"), w(1, "猜一猜"), w(1, "对照原文")
        strip(c, 720, 250, "小猫喜欢吃", "鱼", t, s[1] - 0.05, s[1], cover=True, t_reveal=tr)
        bubble(c, "是“鱼”吧？", 290, 310, t, tg, tail="bl")
        chip(c, "① 盖住下一个词", 590, 410, t, tc, size=28, fill=PAPER, anchor="lm")
        chip(c, "② 猜一猜", 590, 470, t, tg, size=28, fill=PAPER, anchor="lm")
        chip(c, "③ 掀开对答案", 590, 530, t, tr, size=28, fill=SUN, anchor="lm")
        stamp(c, True, 1010, 250, t, tr + 0.35, s=0.75)

    def cc(c, t):
        k = panel(c, 470, 330, 600, 330, t, s[2] - 0.05)
        if k > 0.97:
            chip(c, "原文", 470, 165, size=26, fill=LEAF, color=WHITE, stroke=1.5)
            pre, ans = "小猫喜欢吃", "鱼"
            sz = 56
            tw_pre, tw_ans = text_width(pre, sz, 900), text_width(ans, sz, 900)
            x0 = 470 - (tw_pre + tw_ans + text_width("。", sz, 900)) / 2
            th = w(2, "原文本身")
            u = appear(t, th, 0.3)
            if u > 0:
                c.rect(x0 - 8, 300, tw_pre + 16, 76, SKY, r=12, line=None, a=0.45 * u)
                c.rect(x0 + tw_pre - 2, 300, tw_ans + 12, 76, LEAF, r=12, line=None, a=0.55 * u)
                say(c, "题目", x0 + tw_pre / 2, 420, t, th, 28, "#2A7FC9")
                say(c, "答案", x0 + tw_pre + tw_ans / 2 + 4, 420, t, th + 0.2, 28, "#1E8A5E")
            c.text(pre + ans + "。", x0, 338, sz, INK, 900, anchor="lm")
        tp = s[2] + 0.2
        if pop(t, tp) > 0:
            person_icon(c, 1010, 290, 1.5 * pop(t, tp))
            c.rect(1035, 330, 14, 60, SUN, r=4, lw=2.5)
            u = ease_out(prog(t, w(2, "不需要") + 0.3, 0.3))
            if u > 0:
                c.line([(925, 205), (lerp(925, 1095, u), lerp(205, 395, u))], RED, 10)
        chip(c, "不用人来写答案", 1010, 470, t, w(2, "不需要") + 0.3, size=28, fill=PAPER)

    def d(c, t):
        tn = s[3] + 0.1
        c.text("猜词练习", 640, 150, 32, INK, 900, a=appear(t, tn))
        u = ease_out(prog(t, tn, 1.6))
        if t < tn + 1.7:
            if u > 0:
                n = int(12_000_000_000_000 * u ** 3)
                c.text(f"{n:,}", 640, 230, 64, LEAF, 900, stroke=4, stroke_color=WHITE)
        else:
            say(c, "几万亿次", 640, 230, t, tn + 1.7, 72, LEAF, stroke=5, stroke_color=WHITE)
        robot(c, 640, 600, t, eyes="happy", mouth="smile", chest=1.0)
        chip(c, "语法", 330, 380, t, w(3, "语法"), size=36, fill=SKY)
        chip(c, "常识", 330, 490, t, w(3, "常识"), size=36, fill=SUN)
        chip(c, "推理的套路", 960, 435, t, w(3, "推理"), size=36, fill=CORAL, color=WHITE, stroke=2)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


TOKS = ["月亮", "像", "一块", "被", "咬", "了", "一口", "的", "饼干", "。"]


def tok_chip(c, tk, x, y, t, t0, size=32, fill=PAPER):
    chip(c, tk, x, y, t, t0, size=size, fill=fill, padx=16, shadow=3)


@scene("s3-3", poster=lambda T: T.mid(2, 0.45))
def s3_3(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        girl(c, 160, 560, t, mouth="smile", arm_r=60, talk=T.intro < t < T.intro + 1.0)
        bubble(c, "写一句诗，夸夸月亮！", 215, 300, t, T.intro + 0.05, tail="bl", size=28)
        robot(c, 1160, 575, t, eyes="scan", mouth="flat", s=0.72)
        xs, _ = tok_layout(TOKS, 28, x_center=660, gap=8, padx=12)
        n = len(TOKS)
        for i, (tk, x) in enumerate(zip(TOKS, xs)):
            chip(c, tk, x, 450, t, s[0] + 0.3 + (T.dur(0) - 0.6) * i / (n - 1), size=28, padx=12, shadow=3)
        say(c, "一个词一个词往外写", 660, 375, t, s[0] + 0.6, 30, "#55607F", 800)

    def b(c, t):
        xs, _ = tok_layout(["月亮", "？？"], 36, x_left=440)
        tok_chip(c, "月亮", xs[0], 175, t, -1, size=36)
        c.rect(xs[1] - 46, 175 - 30, 92, 60, "#EEF6FF", r=16, lw=3, a=appear(t, s[1]))
        c.text("?", xs[1], 175, 36, "#AEB6CF", 900, a=appear(t, s[1]))
        items = [("像", .48), ("是", .26), ("在", .14), ("很", .08), ("好", .04)]
        prob_bars(c, 520, 280, items, t, s[1] + 0.3, w=440, row=60, hl=0, t_hl=e[1] - 0.5)
        term_badge(c, "概率表", t, w(1, "概率表"), LEAF)
        robot(c, 1150, 575, t, eyes="think", s=0.8)

    steps = [
        [("像", .48), ("是", .26), ("在", .14), ("很", .08)],
        [("一块", .41), ("一个", .23), ("天上", .12), ("那", .08)],
        [("被", .37), ("的", .21), ("刚", .12), ("会", .07)],
    ]

    def cc(c, t):
        d = (T.dur(2) - 0.4) / 3.6
        xs, ws = tok_layout(TOKS, 34, x_left=170)
        t_app = [-1]
        for k in range(3):
            t_app.append(s[2] + 0.15 + k * d + d * 0.9)
        for k in range(6):
            t_app.append(s[2] + 0.15 + 3 * d + 0.15 + k * 0.12)
        for i, tk in enumerate(TOKS):
            if t >= t_app[i]:
                tok_chip(c, tk, xs[i], 160, t, t_app[i], size=34, fill=SUN if i in (1, 2, 3) else PAPER)
        k = int(clamp((t - s[2] - 0.15) / d, 0, 2.999))
        if t < s[2] + 0.15 + 3 * d:
            tk0 = s[2] + 0.15 + k * d
            prob_bars(c, 520, 290, steps[k], t, tk0, w=420, row=60, hl=0, t_hl=tk0 + d * 0.45, grow=0.35)
            u = prog(t, tk0 + d * 0.55, d * 0.35)
            if 0 < u < 1:
                p = bezier((470, 290), (xs[k + 1], 320), (xs[k + 1], 160), ease_io(u))
                tok_chip(c, steps[k][0][0], p[0], p[1], t, -1, size=34, fill=SUN)
        else:
            say(c, "写完啦！", 640, 330, t, s[2] + 0.15 + 3 * d + 0.9, 50, LEAF, stroke=4, stroke_color=WHITE)
        chip(c, "预测 → 选一个 → 接上 → 再预测", 640, 575, t, w(2, "再预测"), size=28, fill=PAPER)

    def d(c, t):
        xs, ws = tok_layout(TOKS, 40, x_center=640, gap=6)
        cols = ["#FFE7A3", "#CDEBFF", "#D5F5E3", "#FFD9E1", "#E6DFFF"]
        for i, (tk, x) in enumerate(zip(TOKS, xs)):
            chip(c, tk, x, 270, t, s[3] + i * 0.08, size=40, fill=cols[i % 5], padx=14, shadow=3)
        tl = w(3, "可能是一个字")
        tw_ = w(3, "也可能是一个词")
        arrow(c, (xs[1], 400), (xs[1], 325), INK, 5, 16, u=ease_out(prog(t, tl, 0.3)))
        chip(c, "一个字", xs[1], 430, t, tl, size=28, fill=PAPER)
        arrow(c, (xs[0] - 40, 400), (xs[0], 325), INK, 5, 16, u=ease_out(prog(t, tw_, 0.3)))
        chip(c, "一个词", xs[0] - 60, 430, t, tw_, size=28, fill=PAPER)
        term_badge(c, "词元 token", t, w(3, "词元"), LEAF)
        say(c, "最小单位", 640, 160, t, w(3, "最小单位"), 34, INK)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


def answer_card(c, x, y, head, text, t, t0, col=SKY, w=330, h=180):
    k = panel(c, x, y, w, h, t, t0)
    if k > 0.97:
        chip(c, head, x, y - h / 2, size=24, fill=col, shadow=3)
        c.para(text, x, y - 30, 30, w - 50, INK, 800, align="m")


def temp_dial(c, x, y, r, v, lw=24):
    n = 30
    for i in range(n):
        a0, a1 = 150 + 240 * i / n, 150 + 240 * (i + 1) / n + 0.8
        c.arc(x, y, r, r, a0, a1, mix("#4FA3FF", "#FF5A4E", i / (n - 1)), lw)
    c.arc(x, y, r + lw / 2 + 1, r + lw / 2 + 1, 150, 390, INK, 3.5)
    c.arc(x, y, r - lw / 2 - 1, r - lw / 2 - 1, 150, 390, INK, 3.5)
    ang = math.radians(150 + 240 * clamp(v))
    tip = (x + math.cos(ang) * (r - lw - 6), y + math.sin(ang) * (r - lw - 6))
    c.line([(x, y), tip], INK, 9)
    c.circle(x, y, 17, PAPER, lw=4)
    c.text("低", x + math.cos(math.radians(150)) * (r + 4), y + math.sin(math.radians(150)) * (r + 4) + 34, 28,
           "#2F7FD6", 900)
    c.text("高", x + math.cos(math.radians(30)) * (r + 4), y + math.sin(math.radians(30)) * (r + 4) + 34, 28,
           "#E2433A", 900)


def wheel(c, x, y, r, items, cols, ang):
    st = -90
    for (lab, p), col in zip(items, cols):
        ext = 360 * p
        c.pie(x, y, r, st, st + ext, col, INK, 3)
        mid = math.radians(st + ext / 2)
        c.text(lab, x + math.cos(mid) * r * 0.64, y + math.sin(mid) * r * 0.64, 34, INK, 900)
        st += ext
    c.circle(x, y, r, None, INK, 4.5)
    a = math.radians(ang - 90)
    tip = (x + math.cos(a) * r * 0.86, y + math.sin(a) * r * 0.86)
    c.line([(x, y), tip], INK, 12)
    c.line([(x, y), tip], CORAL, 6)
    c.circle(x, y, 17, PAPER, lw=4)


@scene("s3-4", poster=lambda T: T.mid(3, 0.55))
def s3_4(T):
    s, e, w = T.s, T.e, T.word
    base = [("像", .48), ("是", .26), ("在", .14), ("很", .12)]
    cols = [SUN, SKY, LEAF, "#FF9BB0"]

    def a(c, t):
        chip(c, "问：用一句话形容月亮", 640, 140, t, T.intro, size=32, fill=PAPER)
        answer_card(c, 470, 330, "第一次问", "月亮像一盏夜灯。", t, T.intro + 0.4, SKY)
        answer_card(c, 830, 330, "第二次问", "月亮是夜空打的哈欠。", t, s[0] + 1.3, SUN)
        girl(c, 140, 560, t, eyes="up", brows="think", mouth="flat")
        qmark(c, 215, 290, t, s[0] + 1.8)
        robot(c, 1150, 575, t, eyes="normal", s=0.8)

    def b(c, t):
        t1, t2 = s[1] + 0.2, w(1, "抽签") - 0.5
        a1 = 86.4 + 720
        a2 = a1 + 720 + (219.6 - 86.4)
        if t < t2:
            ang = lerp(0, a1, ease_out(prog(t, t1, 1.6)))
        else:
            ang = lerp(a1, a2, ease_out(prog(t, t2, 1.6)))
        k = pop(t, s[1] - 0.05)
        if k > 0:
            wheel(c, 430, 345, 190 * k, base, cols, ang)
        chip(c, "按概率“抽签”", 960, 160, t, w(1, "按照概率"), size=32, fill=SUN)
        chip(c, "第一次抽到：像", 960, 280, t, t1 + 1.6, size=30, fill=PAPER)
        chip(c, "第二次抽到：是", 960, 380, t, t2 + 1.6, size=30, fill=PAPER)

    def cc(c, t):
        k = pop(t, s[2] - 0.05)
        if k > 0:
            temp_dial(c, 640, 380, 170 * k, 0.35 + 0.12 * math.sin(t * 2.2), lw=24 * k)
        term_badge(c, "温度", t, w(2, "温度"), LEAF)
        chip(c, "控制抽签有多随机", 640, 585, t, s[2] + 0.3, size=28, fill=PAPER)

    def d(c, t):
        tlo, thi, terr = w(3, "温度高") - 0.2, w(3, "更有创意"), w(3, "容易出错") + 0.3
        if t < tlo:
            temp = 0.3
        elif t < thi:
            temp = lerp(0.3, 1.25, ease_io(prog(t, tlo, thi - tlo)))
        else:
            temp = lerp(1.25, 2.6, ease_io(prog(t, thi + 0.3, terr - thi)))
        temp_dial(c, 250, 330, 120, (temp - 0.3) / 2.3, lw=20)
        c.text(f"温度 {temp:.1f}", 250, 470, 30, INK, 900)
        ps = softmax_t([p for _, p in base], temp)
        prob_bars(c, 610, 200, [(lab, p) for (lab, _), p in zip(base, ps)], t, s[3] - 0.1, w=380, row=58, grow=0.3)
        if temp < 0.7:
            out, lab, col = "月亮很圆。", "更稳定", SKY
        elif temp < 1.7:
            out, lab, col = "月亮是夜空打的哈欠。", "更有创意", SUN
        else:
            out, lab, col = "月亮蓝色跳舞饼干叮咚", "容易跑偏", RED
        c.rect(560, 470, 600, 74, PAPER, r=22, lw=3.5)
        c.text(out, 860, 507, 32, INK, 800)
        chip(c, lab, 860, 465, size=24, fill=col, color=WHITE if col == RED else INK, shadow=3, stroke=1.4 if col == RED else 0)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# ============================================================ 故事四：不存在的书（AI 幻觉）
BOOK_T = "月亮背面的灯塔"


def chain(c, toks, y, t, times, size=30, fill=PAPER, x_center=640, check=True):
    xs, ws = tok_layout(toks, size, x_center=x_center, gap=46)
    for i, (tk, x) in enumerate(zip(toks, xs)):
        if i > 0 and t >= times[i] - 0.1:
            arrow(c, (xs[i - 1] + ws[i - 1] / 2 + 4, y), (x - ws[i] / 2 - 4, y), INK, 4, 13, u=1)
        chip(c, tk, x, y, t, times[i], size=size, fill=fill)
        if check:
            u = appear(t, times[i] + 0.25)
            if u > 0:
                c.text("像样 ✓", x, y + 46, 20, "#1E8A5E", 900, a=u)
    return xs


@scene("s4-1", poster=lambda T: T.mid(1, 0.6))
def s4_1(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        robot(c, 330, 560, t, eyes="star", mouth="open", arm_r=120 + wave(t, 6, 1.2))
        k = pop(t, T.intro + 0.1)
        if k > 0:
            book(c, 720, 310, 240, 310, GRAPE, BOOK_T, "辛望舒 著 · 1998", s=k, rot=-3)
        sparkles(c, t, 720, 310, 180, 6, SUN, t0=T.intro + 0.3)
        tm = w(0, "有模有样")
        for i, (txt, ok) in enumerate((("有书名", True), ("有作者", True), ("有年份", True))):
            check_row(c, 900, 230 + i * 70, txt, ok, t, tm + i * 0.25, size=30)

    def b(c, t):
        search_box(c, 640, 150, 560, BOOK_T, t, s[1] - 0.15, cps=9)
        tg = s[1] + 1.0
        g = ease_io(prog(t, tg + 0.3, 0.7))
        if g < 1:
            book(c, 640, 370, 220, 280, GRAPE, BOOK_T, "辛望舒 著 · 1998", a=1 - g)
        if g > 0:
            book(c, 640, 370, 220, 280, GRAPE, BOOK_T, dashed=True, a=g)
        if t >= tg:
            chip(c, "查无此书", 860, 300, t, tg, size=40, fill=RED, color=WHITE, stroke=2.5, rot=-10)
        term_badge(c, "AI 幻觉", t, w(1, "AI幻觉"), GRAPE, y=74)
        chip(c, "看起来很合理", 270, 520, t, w(1, "看起来"), size=30, fill=GREEN, color=WHITE, stroke=1.6)
        chip(c, "其实是编的", 1010, 520, t, w(1, "编造"), size=30, fill=RED, color=WHITE, stroke=1.6)

    def cc(c, t):
        robot(c, 640, 575, t, eyes="normal", mouth="smile", blush=True, s=1.15)
        qmark(c, 790, 250, t, s[2] + 0.3, s=0.8, col=GRAPE)
        chip(c, "不是故意撒谎", 330, 300, t, s[2] + 0.1, size=32, fill=PAPER)
        chip(c, "不知道自己错了", 960, 390, t, w(2, "甚至"), size=32, fill=SUN)

    def d(c, t):
        k = pop(t, s[3] - 0.05, 0.5)
        if k > 0:
            warning_sign(c, 640, 235, s=1.3 * k)
        say(c, "最常见的毛病之一", 640, 365, t, w(3, "最常见"), 40, INK)
        for i, txt in enumerate(("不存在的书", "假的引用", "错误的数字")):
            chip(c, txt, 330 + i * 310, 480, t, w(3, "最常见") + 0.4 + i * 0.25, size=32, fill=PAPER)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@scene("s4-2", poster=lambda T: T.mid(1, 0.9))
def s4_2(T):
    s, e, w = T.s, T.e, T.word
    c1 = ["推荐", "《月亮", "背面的", "灯塔》"]
    c2 = ["作者", "辛望舒", "1998年", "出版"]

    def a(c, t):
        tw_ = w(0, "预测")
        times = [s[0] + 0.3 + i * 0.5 for i in range(4)]
        times = [max(x, tw_ - 0.8 + i * 0.45) for i, x in enumerate(times)]
        chain(c, c1, 280, t, times, size=34)
        robot(c, 1130, 575, t, eyes="scan", mouth="flat", s=0.8)
        chip(c, "每一步都挑最像样的词", 640, 470, t, w(0, "最像样"), size=30, fill=SUN)

    def b(c, t):
        chain(c, c1, 190, t, [-1] * 4, size=30, check=False)
        times = [s[1] + 0.4 + i * 0.6 for i in range(4)]
        chain(c, c2, 330, t, times, size=34)
        ts = w(1, "并不会")
        k = pop(t, ts)
        if k > 0:
            x, y, r = 640, 500, 50 * k
            pts = [(x + math.cos(math.radians(22.5 + 45 * i)) * r, y + math.sin(math.radians(22.5 + 45 * i)) * r)
                   for i in range(8)]
            c.poly(pts, "#E04848", lw=3.5)
            c.text("停", x, y, 40 * k, WHITE, 900)
            strike(c, x, y, 130, t, ts + 0.4, INK)
            say(c, "不知道也不会停下", 640 + 90, 500, t, ts + 0.3, 30, INK, anchor="lm")

    def cc(c, t):
        rows = [("书名：月亮背面的灯塔", w(2, "书名")), ("作者：辛望舒", w(2, "作者")), ("年份：1998", w(2, "年份"))]
        tj = w(2, "拼在一起")
        tf = w(2, "假的")
        for i, (txt, t0) in enumerate(rows):
            u = ease_io(prog(t, tj, 0.6))
            x = lerp(330, 900, u)
            y = lerp(230 + i * 110, 330, u)
            if u < 1:
                chip(c, txt, x, y, t, t0, size=30, fill=PAPER, a=1 - u * 0.9, s=1 - 0.5 * u)
                if u < 0.05:
                    check_row(c, 560, 230 + i * 110, "像真的", True, t, t0 + 0.3, size=24)
        k = pop(t, tj + 0.5, 0.45)
        if k > 0:
            book(c, 900, 330, 220, 290, GRAPE, BOOK_T, "辛望舒 著 · 1998", s=k, rot=4)
        stamp(c, False, 980, 420, t, tf, s=1.1)
        say(c, "拼起来是假的", 900, 540, t, tf + 0.2, 34, RED)

    def d(c, t):
        chip(c, "说得流利", 360, 320, t, w(3, "流利"), size=46, fill=SKY)
        say(c, "≠", 640, 316, t, w(3, "不代表"), 90, CORAL, stroke=4)
        chip(c, "说得正确", 920, 320, t, w(3, "正确"), size=46, fill=GREEN, color=WHITE, stroke=2.5)
        robot(c, 640, 600, t, eyes="happy", mouth="smile", s=0.7)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


def rag_pipeline(c, t, times, brackets=None):
    y = 310
    xs = [150, 380, 620, 860, 1110]
    labs = ["提问", "搜索", "找到资料", "模型", "回答"]
    for i in range(1, 5):
        u = ease_out(prog(t, times[i] - 0.25, 0.3))
        arrow(c, (xs[i - 1] + 72, y), (xs[i] - 72, y), INK, 6, 18, u=u)
    for i, (x, lab) in enumerate(zip(xs, labs)):
        k = pop(t, times[i], 0.4)
        if k <= 0:
            continue
        if i == 0:
            chip(c, "？", x, y, size=48, fill=PAPER, s=k)
        elif i == 1:
            magnifier(c, x - 8, y - 8, 36 * k)
        elif i == 2:
            stack_icon(c, x, y - 4, 1.0 * k)
        elif i == 3:
            robot(c, x, y + 92, t, eyes="scan", mouth="flat", s=0.5 * k, shadow=False)
        else:
            doc_icon(c, x, y, 80, 100, PAPER, 4, s=k, accent=LEAF)
            c.circle(x + 30 * k, y + 38 * k, 16 * k, GREEN, lw=3)
        say(c, lab, x, y + 110, t, times[i] + 0.1, 28, INK)
    if brackets:
        for (i0, i1, lab, col, t0) in brackets:
            u = ease_out(prog(t, t0, 0.4))
            if u <= 0:
                continue
            x0, x1 = xs[i0] - 80, xs[i1] + 80
            yy = 485
            c.line([(x0, yy - 14), (x0, yy), (lerp(x0, x1, u), yy)], col, 6)
            if u >= 1:
                c.line([(x1, yy), (x1, yy - 14)], col, 6)
            chip(c, lab, (x0 + x1) / 2, yy + 40, t, t0 + 0.2, size=30, fill=col, color=WHITE, stroke=1.8)


@scene("s4-3", poster=lambda T: T.mid(2, 0.8))
def s4_3(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        girl(c, 220, 560, t, eyes="happy", mouth="open", arm_r=95)
        tf = s[0] + 0.5
        arrive = tf + 1.0
        robot(c, 960, 560, t, eyes="scan" if t > arrive else "normal", mouth="flat" if t > arrive else "smile",
              arm_l=60)
        u = ease_io(prog(t, tf, 1.0))
        if u > 0:
            p = bezier((300, 430), (600, 180), (880, 420), u) if u < 1 else (880, 420)
            stack_icon(c, p[0], p[1], 1.0)
        chip(c, "可靠的资料", 640, 160, t, w(0, "可靠的资料"), size=36, fill=SUN)
        chip(c, "根据资料回答", 640, 240, t, w(0, "根据资料"), size=30, fill=PAPER)

    def b(c, t):
        times = [s[1] + 0.05, w(1, "搜索"), w(1, "找到的内容"), w(1, "交给模型"), w(1, "组织答案")]
        rag_pipeline(c, t, times)

    def cc(c, t):
        rag_pipeline(c, t, [-1] * 5, brackets=[(1, 2, "检索", SKY, w(2, "检索")), (3, 3, "增强", SUN, w(2, "增强")),
                                              (4, 4, "生成", LEAF, w(2, "生成"))])
        term_badge(c, "检索增强生成 RAG", t, w(2, "检索增强生成"), GRAPE)

    def d(c, t):
        k = panel(c, 470, 320, 640, 300, t, s[3] - 0.05)
        if k > 0.97:
            chip(c, "比特的回答", 470, 170, size=24, fill=GRAPE, color=WHITE, stroke=1.4, shadow=3)
            c.para("月亮总用同一面对着地球，因为它自转一圈的时间，正好等于绕地球转一圈的时间。", 190, 215, 30, 560,
                   INK, 800)
            hl = appear(t, w(3, "出处"), 0.3)
            if hl > 0:
                c.rect(178, 393, 450, 48, SUN, r=12, line=None, a=0.55 * hl)
            c.text("出处：《月亮的故事》第23页", 190, 417, 26, "#5B3FD1", 900, anchor="lm")
        tk = w(3, "核对")
        arrow(c, (640, 417), (870, 360), CORAL, 7, 20, u=ease_out(prog(t, tk - 0.3, 0.4)))
        k2 = pop(t, tk - 0.1)
        if k2 > 0:
            book(c, 980, 330, 200, 250, LEAF, "月亮的故事", "第23页", s=k2, rot=3)
        stamp(c, True, 1060, 450, t, tk + 0.4, s=0.8)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


@lru_cache(maxsize=16)
def note_sprite(w, h, text, col, size=30):
    c = Canvas.sprite(w + 14, h + 30)
    c.rect(10, 22, w, h, INK, r=10, line=None)
    c.rect(3, 14, w, h, col, r=10, lw=3.5)
    c.rect(3 + w / 2 - 42, 3, 84, 26, "#D8ECFF", r=4, line=None)
    lines = wrap(text, size, w - 44, 800)
    for i, ln in enumerate(lines):
        c.text(ln, 3 + w / 2, 14 + h / 2 + (i - (len(lines) - 1) / 2) * size * 1.38, size, INK, 800)
    return c.im


def board(c, t, t_notes):
    c.rect(150 + 9, 120 + 10, 980, 420, INK, r=24, line=None)
    c.rect(150, 120, 980, 420, "#D9A066", r=24, lw=4.5)
    c.rect(172, 142, 936, 376, "#E8B57B", r=14, lw=3)
    notes = [("① 重要的事，多找几个地方核实", "#FFF3A6", -4), ("② 请 AI 说出“从哪儿知道的”", "#CFF3DF", 2),
             ("③ 允许它说“不知道”", "#FFD9E1", -2)]
    for i, ((text, col, rot), t0) in enumerate(zip(notes, t_notes)):
        k = pop(t, t0, 0.45)
        if k > 0:
            x, y = 330 + i * 310, 335
            c.blit(note_sprite(250, 210, text, col), x, y, "mm", s=k, rot=rot)
            stamp(c, True, x + 100, y - 90, t, t0 + 0.45, s=0.42)


@scene("s4-4", poster=lambda T: T.mid(2, 0.95))
def s4_4(T):
    s, e, w = T.s, T.e, T.word

    def a(c, t):
        girl(c, 470, 560, t, eyes="happy", mouth="grin", arm_r=150)
        robot(c, 810, 560, t, eyes="happy", arm_l=60)
        term_badge(c, "聪明的提问者", t, w(0, "聪明"), GRAPE)
        sparkles(c, t, 640, 300, 260, 7, SUN, t0=w(0, "聪明"))

    def b(c, t):
        board(c, t, [s[1] + 0.2, 1e9, 1e9])

    def cc(c, t):
        board(c, t, [-1, w(2, "出处") - 0.2, w(2, "不知道") - 0.2])

    def d(c, t):
        th = s[3] + 0.5
        girl(c, 490, 560, t, eyes="happy", mouth="grin", arm_r=150, arm_l=14)
        robot(c, 800, 560, t, eyes="happy", mouth="open", arm_l=150, arm_r=10)
        if t >= th:
            u = prog(t, th, 1.4)
            for i in range(7):
                ang = -math.pi / 2 + (i - 3) * 0.42
                d_ = 30 + 130 * ease_out(u)
                heart(c, 645 + math.cos(ang) * d_, 400 + math.sin(ang) * d_, 0.85, [CORAL, "#FF9BB0", SUN][i % 3],
                      a=1 - prog(u, 0.65, 0.35))
            heart(c, 645, 400, 1.3 * pop(t, th, 0.5), CORAL)
            sparkles(c, t, 645, 380, 110, 5, SUN, t0=th)
        chip(c, "得力的助手", 300, 200, t, w(3, "得力的助手"), size=34, fill=GREEN, color=WHITE, stroke=2)
        chip(c, "不会出错的权威", 980, 200, t, w(3, "权威") - 0.3, size=34, fill=PAPER, color="#8A93AE")
        strike(c, 980, 200, 250, t, w(3, "权威") + 0.2)

    return [(0, a), (s[1] - 0.1, b), (s[2] - 0.1, cc), (s[3] - 0.1, d)]


# 名词篇（故事五到八）的分镜在另一个文件里，导入时自动登记
import scenes_terms  # noqa: E402,F401
import scenes_more  # noqa: E402,F401
