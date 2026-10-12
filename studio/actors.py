"""角色、道具和背景。

主角：
  比特 —— 刚学东西的小机器人（会飘浮，屏幕脸）
  朵朵 —— 教比特认识世界的小女孩
  芝麻 —— 朵朵家的黑白奶牛猫
"""
import math
import random
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw

from engine import (INK, SS, W, H, Canvas, appear, clamp, ease_out, lerp, lerp2, mix, pop, prog, rgb,
                    text_sprite, text_width, wave, wrap)

# ---------------------------------------------------------------- 调色板
SKY = "#7CC4FF"
SUN = "#FFC83D"
CORAL = "#FF6F5E"
LEAF = "#2FB57E"
GRAPE = "#8A6CFF"
GREEN = "#2FB57E"
RED = "#F0524A"
GRAY = "#A3ABC4"
PAPER = "#FFFFFF"
CREAM = "#FFF7E3"

BIT = dict(shell="#F6F8FF", screen="#26335F", eye="#72F1FF", ant=CORAL, ear=SUN, body=SKY, chest=SUN,
           neck="#C9D3EE", blush="#FF8FB1")
DUO = dict(skin="#FFE0C9", hair="#3B2B3A", bow=CORAL, dress=SUN, collar="#FFFFFF", shoe=CORAL,
           blush="#FF9BB0", mouth="#B5404F")

THEMES = {
    "coral": dict(top="#FFEFE7", bot="#FFDCCD", accent=CORAL, floor="#FFCDB8", dark=False),
    "sun": dict(top="#1B2152", bot="#2D357A", accent=SUN, floor="#141943", dark=True),
    "leaf": dict(top="#E8F8EF", bot="#CCEFDC", accent=LEAF, floor="#B3E5CA", dark=False),
    "grape": dict(top="#F2EDFF", bot="#DFD6FF", accent=GRAPE, floor="#CDBFFF", dark=False),
    "azure": dict(top="#EAF5FF", bot="#D0E7FF", accent="#4FA8F5", floor="#BCDAF8", dark=False),
    "rose": dict(top="#FFF1F6", bot="#FFDDE9", accent="#FF7FA6", floor="#FFC8DA", dark=False),
    "amber": dict(top="#22183F", bot="#382862", accent="#FFB547", floor="#6B4430", dark=True, stage=True,
                  title="#3A2A66"),
    "teal": dict(top="#E7FAF6", bot="#C9EFE8", accent="#22B3A3", floor="#ADE3D9", dark=False),
}


# ---------------------------------------------------------------- 背景
@lru_cache(None)
def background(theme):
    th = THEMES[theme]
    w, h = W * SS, H * SS
    top, bot = np.array(rgb(th["top"]), np.float32), np.array(rgb(th["bot"]), np.float32)
    u = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    grad = top[None, None, :] * (1 - u[..., None]) + bot[None, None, :] * u[..., None]
    im = Image.fromarray(np.broadcast_to(grad, (h, w, 3)).astype(np.uint8), "RGB")
    c = Canvas(im)
    rnd = random.Random(7)
    if th.get("stage"):
        _stage(c, th)
        return im
    if th.get("grid"):
        for gx in range(0, W + 1, 48):
            c.line([(gx, 0), (gx, 560)], th["accent"], 1.5, a=0.07, caps=False)
        for gy in range(0, 561, 48):
            c.line([(0, gy), (W, gy)], th["accent"], 1.5, a=0.07, caps=False)
        for _ in range(30):
            c.circle(rnd.randrange(0, W + 1, 48), rnd.randrange(0, 561, 48), 3, th["accent"], line=None, a=0.35)
    elif th["dark"]:
        for _ in range(140):
            x, y = rnd.uniform(0, W), rnd.uniform(0, 520)
            r = rnd.choice([1.2, 1.5, 2.0, 2.6])
            c.circle(x, y, r, "#FFFFFF", line=None, a=rnd.uniform(0.25, 0.8))
    else:
        for x, y, r in ((90, 120, 120), (1190, 90, 150), (1130, 470, 90), (160, 520, 70)):
            c.circle(x, y, r, "#FFFFFF", line=None, a=0.28)
        for gx in range(0, W + 1, 64):
            for gy in range(32, 560, 64):
                c.circle(gx + (gy // 64 % 2) * 32, gy, 2.2, "#FFFFFF", line=None, a=0.55)
    c.ellipse(W / 2, H + 70, W * 0.78, 190, th["floor"], line=None)
    return im


def _stage(c, th):
    """剧场舞台：木地板、两侧红幕布、顶上的帷幔"""
    rnd = random.Random(3)
    for _ in range(60):
        c.circle(rnd.uniform(140, W - 140), rnd.uniform(60, 470), rnd.choice([1.2, 1.6, 2.0]), "#FFFFFF",
                 line=None, a=rnd.uniform(0.15, 0.45))
    c.poly([(0, 560), (W, 560), (W, H), (0, H)], th["floor"], line=None)
    for i in range(1, 6):
        y = 560 + i * 34
        c.line([(0, y), (W, y)], mix(th["floor"], INK, 0.35), 2.5, caps=False)
    c.rect(0, 552, W, 12, "#8A5A3C", line=None)
    c.line([(0, 552), (W, 552)], INK, 3, caps=False)
    red, fold = "#B23A48", "#8E2C3A"
    for side in (-1, 1):
        x0 = 0 if side < 0 else W
        pts = [(x0, 0)]
        for k in range(0, 13):
            pts.append((x0 - side * (118 + 16 * math.sin(k * 1.3)), k * 50))
        pts.append((x0, 600))
        c.poly(pts, red, lw=3.5)
        for f in (34, 70, 100):
            c.line([(x0 - side * f, 30), (x0 - side * (f + 6), 590)], fold, 7, caps=False)
    c.rect(0, 0, W, 40, red, line=None)
    for k in range(0, 17):
        c.circle(k * 80 + 40, 40, 40, red, line=None)
    c.line([(0, 2), (W, 2)], INK, 4, caps=False)


@lru_cache(None)
def title_background(theme):
    th = THEMES[theme]
    base = th.get("title") or (th["accent"] if not th["dark"] else "#2D357A")
    im = Image.new("RGB", (W * SS, H * SS), rgb(base))
    c = Canvas(im)
    for gx in range(-40, W + 80, 80):
        for gy in range(-40, H + 80, 80):
            c.circle(gx + (gy // 80 % 2) * 40, gy, 9, "#FFFFFF", line=None, a=0.16)
    return im


# ---------------------------------------------------------------- 小图形
def star_pts(x, y, r, k=0.3, n=4, rot=0.0):
    pts = []
    for i in range(n * 2):
        ang = math.pi / n * i + rot - math.pi / 2
        rr = r if i % 2 == 0 else r * k
        pts.append((x + math.cos(ang) * rr, y + math.sin(ang) * rr))
    return pts


def sparkle(c, x, y, r, col="#FFFFFF", a=1.0, line=None):
    if r > 0.5:
        c.poly(star_pts(x, y, r), col, line=line, lw=2.5, a=a)


def sparkles(c, t, x, y, spread=90, n=5, col=SUN, seed=1, t0=0.0, line=INK):
    rnd = random.Random(seed)
    for i in range(n):
        ox, oy = rnd.uniform(-spread, spread), rnd.uniform(-spread * 0.7, spread * 0.7)
        ph = rnd.uniform(0, 1)
        k = 0.5 + 0.5 * math.sin(2 * math.pi * (t * 1.3 + ph))
        sparkle(c, x + ox, y + oy, (7 + 7 * k) * appear(t, t0 + i * 0.07), col, line=line)


def confetti(c, t, t0, x, y, n=26, seed=3, power=1.0):
    if t < t0:
        return
    dt = t - t0
    if dt > 2.2:
        return
    rnd = random.Random(seed)
    cols = [CORAL, SUN, SKY, LEAF, GRAPE, "#FF9BB0"]
    for i in range(n):
        ang = rnd.uniform(-math.pi * 0.92, -math.pi * 0.08)
        sp = rnd.uniform(260, 560) * power
        vx, vy = math.cos(ang) * sp, math.sin(ang) * sp
        px = x + vx * dt
        py = y + vy * dt + 520 * dt * dt
        a = 1 - prog(dt, 1.4, 0.8)
        rot = rnd.uniform(0, 6) + dt * rnd.uniform(4, 10)
        w, h = rnd.uniform(7, 12), rnd.uniform(4, 7)
        ca, sa = math.cos(rot), math.sin(rot)
        pts = [(px + ca * dx - sa * dy, py + sa * dx + ca * dy) for dx, dy in
               ((-w, -h), (w, -h), (w, h), (-w, h))]
        c.poly(pts, rnd.choice(cols), line=None, a=a)


def sweat(c, x, y, s=1.0, a=1.0):
    c.poly([(x, y - 16 * s), (x + 9 * s, y), (x - 9 * s, y)], "#9ADCFF", line=None, a=a)
    c.circle(x, y + 2 * s, 9.5 * s, "#9ADCFF", lw=2.5, a=a)
    c.line([(x, y - 16 * s), (x + 9 * s, y - 1 * s)], INK, 2.5, a=a)
    c.line([(x, y - 16 * s), (x - 9 * s, y - 1 * s)], INK, 2.5, a=a)


def arrow(c, p0, p1, col=INK, lw=7, head=20, u=1.0, a=1.0, outline=True):
    """直箭头，u 控制从起点长出来的进度"""
    if u <= 0.01:
        return
    q = lerp2(p0, p1, u)
    ang = math.atan2(q[1] - p0[1], q[0] - p0[0])
    base = (q[0] - math.cos(ang) * head * 0.8, q[1] - math.sin(ang) * head * 0.8)
    l = (q[0] - math.cos(ang) * head + math.cos(ang + math.pi / 2) * head * 0.7,
         q[1] - math.sin(ang) * head + math.sin(ang + math.pi / 2) * head * 0.7)
    r = (q[0] - math.cos(ang) * head + math.cos(ang - math.pi / 2) * head * 0.7,
         q[1] - math.sin(ang) * head + math.sin(ang - math.pi / 2) * head * 0.7)
    if outline and col != INK:
        c.line([p0, base], INK, lw + 5, a=a)
        c.line([p0, base], col, lw, a=a)
        c.poly([q, l, r], col, line=INK, lw=2.5, a=a)
    else:
        c.line([p0, base], col, lw, a=a)
        c.poly([q, l, r], col, line=None, a=a)


def curve_arrow(c, p0, p1, bend=60, col=INK, lw=6, head=18, u=1.0, a=1.0):
    if u <= 0.01:
        return
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy) or 1
    ctrl = (mx - dy / L * bend, my + dx / L * bend)
    n = 24
    pts = []
    for i in range(n + 1):
        v = u * i / n
        a1 = lerp2(p0, ctrl, v)
        b1 = lerp2(ctrl, p1, v)
        pts.append(lerp2(a1, b1, v))
    end, prev = pts[-1], pts[-3]
    ang = math.atan2(end[1] - prev[1], end[0] - prev[0])
    c.line(pts[:-2], col, lw, a=a)
    l = (end[0] - math.cos(ang) * head + math.cos(ang + math.pi / 2) * head * 0.65,
         end[1] - math.sin(ang) * head + math.sin(ang + math.pi / 2) * head * 0.65)
    r = (end[0] - math.cos(ang) * head + math.cos(ang - math.pi / 2) * head * 0.65,
         end[1] - math.sin(ang) * head + math.sin(ang - math.pi / 2) * head * 0.65)
    c.poly([end, l, r], col, line=None, a=a)


# ---------------------------------------------------------------- 比特
def _bit_face(c, x, y, eyes, mouth, blush):
    E = BIT["eye"]
    lx, rx = x - 31, x + 31
    if eyes == "normal":
        for ex in (lx, rx):
            c.rect(ex - 8.5, y - 17, 17, 34, E, r=8.5, line=None)
            c.circle(ex + 2.5, y - 8, 3.2, "#FFFFFF", line=None)
    elif eyes == "blink":
        for ex in (lx, rx):
            c.rect(ex - 11, y - 3, 22, 6, E, r=3, line=None)
    elif eyes == "happy":
        for ex in (lx, rx):
            c.arc(ex, y + 7, 13, 13, 200, 340, E, 6.5)
    elif eyes == "wide":
        for ex in (lx, rx):
            c.circle(ex, y - 2, 15, E, line=None)
            c.circle(ex + 5, y - 7, 4.5, "#FFFFFF", line=None)
    elif eyes == "sad":
        for ex in (lx, rx):
            c.arc(ex, y - 8, 12, 11, 25, 155, E, 6)
    elif eyes == "x":
        for ex in (lx, rx):
            c.line([(ex - 9, y - 9), (ex + 9, y + 9)], "#FF8080", 6)
            c.line([(ex - 9, y + 9), (ex + 9, y - 9)], "#FF8080", 6)
    elif eyes == "star":
        for ex in (lx, rx):
            c.poly(star_pts(ex, y - 2, 17, 0.45, 5), SUN, line=None)
    elif eyes == "think":
        for ex in (lx, rx):
            c.rect(ex - 13.5, y - 23, 17, 30, E, r=8.5, line=None)
    elif eyes == "confused":
        c.rect(lx - 8.5, y - 17, 17, 34, E, r=8.5, line=None)
        c.rect(rx - 11, y - 3, 22, 6, E, r=3, line=None)
    elif eyes == "q":
        c.text("?", lx, y - 2, 40, E, 900)
        c.text("?", rx, y - 2, 40, E, 900)
    elif eyes == "scan":
        for k in range(3):
            c.rect(x - 46, y - 18 + k * 14, 92 - k * 22, 6, E, r=3, line=None)
    if blush:
        bc = mix(BIT["screen"], BIT["blush"], 0.55)
        c.ellipse(x - 54, y + 20, 10, 5.5, bc, line=None)
        c.ellipse(x + 54, y + 20, 10, 5.5, bc, line=None)
    my = y + 30
    if mouth == "smile":
        c.arc(x, my - 9, 12, 9, 25, 155, E, 4.5)
    elif mouth == "open":
        c.ellipse(x, my, 8.5, 7, E, line=None)
    elif mouth == "flat":
        c.line([(x - 9, my), (x + 9, my)], E, 4.5)
    elif mouth == "wavy":
        c.line([(x - 13, my), (x - 6.5, my - 4), (x, my), (x + 6.5, my - 4), (x + 13, my)], E, 4)
    elif mouth == "o":
        c.circle(x, my, 5.5, None, E, 3.5)
    elif mouth == "sad":
        c.arc(x, my + 6, 10, 7, 205, 335, E, 4.5)


@lru_cache(maxsize=2048)
def bit_sprite(eyes="normal", mouth="smile", arm_l=8, arm_r=8, lid=0.0, chest=0.0, blush=False, look=0):
    c = Canvas.sprite(300, 380)
    cx, oy = 150, 80
    for sign, ang in ((-1, arm_l), (1, arm_r)):
        sx, sy = cx + sign * 50, 206 + oy
        a = math.radians(ang)
        ex, ey = sx + sign * math.sin(a) * 56, sy + math.cos(a) * 56
        c.capsule((sx, sy), (ex, ey), 15, BIT["body"], lw=3.5)
        c.circle(ex, ey, 12.5, BIT["shell"], lw=3.5)
    c.rect(cx - 58, 178 + oy, 116, 96, BIT["body"], r=38, lw=4)
    c.rect(cx - 40, 188 + oy, 26, 10, mix(BIT["body"], "#FFFFFF", 0.45), r=5, line=None)
    c.circle(cx, 226 + oy, 14, mix(BIT["chest"], "#FFF8D8", chest), lw=3.5)
    c.rect(cx - 22, 166 + oy, 44, 18, BIT["neck"], r=7, lw=3.5)
    c.ellipse(cx - 92, 110 + oy, 15, 28, BIT["ear"], lw=3.5)
    c.ellipse(cx + 92, 110 + oy, 15, 28, BIT["ear"], lw=3.5)
    c.rect(cx - 88, 46 + oy, 176, 128, BIT["shell"], r=48, lw=4)
    c.rect(cx - 70, 66 + oy, 140, 90, BIT["screen"], r=32, line=None)
    c.rect(cx - 52, 74 + oy, 34, 7, mix(BIT["screen"], "#FFFFFF", 0.18), r=3.5, line=None)
    _bit_face(c, cx + look * 9, 110 + oy, eyes, mouth, blush)
    ly = 50 + oy - lid * 52
    if lid > 0:
        c.ellipse(cx, 50 + oy, 66, 11, "#FFF3A6", lw=3)
        c.rect(cx - 74, ly - 20, 148, 24, BIT["shell"], r=12, lw=4)
        ly -= 20
    c.line([(cx, ly + 2), (cx, ly - 24)], INK, 4.5)
    c.circle(cx, ly - 28, 11, BIT["ant"], lw=3.5)
    return c.im


def robot(c, x, y, t, eyes="normal", mouth="smile", arm_l=8, arm_r=8, s=1.0, sx=1.0, sy=1.0, lid=0.0,
          chest=None, blush=False, look=0, rot=0.0, a=1.0, float_amp=7.0, shadow=True, blink=True):
    """比特。(x, y) 是它下方地面的位置。"""
    dy = wave(t, float_amp, 0.55, x * 0.001)
    if blink and eyes == "normal" and ((t + x * 0.0031) % 3.3) < 0.13:
        eyes = "blink"
    if chest is None:
        chest = 0.5 + 0.5 * math.sin(t * 4.0)
    if shadow:
        k = 1 - dy / 70
        c.ellipse(x, y + 2, 64 * s * k * sx, 11 * s * k, INK, line=None, a=0.16 * a)
    spr = bit_sprite(eyes, mouth, int(round(arm_l / 3) * 3), int(round(arm_r / 3) * 3), round(lid, 2),
                     round(chest, 1), blush, look)
    c.blit(spr, x, y + 8 * s + dy * s, "mb", s=s, sx=sx, sy=sy, a=a, rot=rot)


def robot_head_y(y, s=1.0):
    """比特头顶（天线根部）的大概高度"""
    return y - 246 * s


# ---------------------------------------------------------------- 朵朵
@lru_cache(maxsize=2048)
def duo_sprite(eyes="normal", mouth="smile", arm_l=14, arm_r=14, brows="", blush=True):
    c = Canvas.sprite(240, 330)
    cx = 120
    D = DUO
    for lx in (cx - 15, cx + 15):
        c.capsule((lx, 262), (lx, 298), 13, D["skin"], lw=3.5)
        c.ellipse(lx + (-4 if lx < cx else 4), 304, 15, 9, D["shoe"], lw=3.5)
    for sign, ang in ((-1, arm_l), (1, arm_r)):
        sx, sy = cx + sign * 25, 214
        a = math.radians(ang)
        ex, ey = sx + sign * math.sin(a) * 50, sy + math.cos(a) * 50
        c.capsule((sx, sy), (ex, ey), 12, D["skin"], lw=3.5)
        c.circle(ex, ey, 9.5, D["skin"], lw=3.5)
    c.poly([(cx - 27, 196), (cx + 27, 196), (cx + 52, 274), (cx - 52, 274)], D["dress"], lw=3.5)
    c.rect(cx - 52, 258, 104, 16, mix(D["dress"], CORAL, 0.35), r=4, line=None)
    c.line([(cx - 52, 274), (cx + 52, 274)], INK, 3.5)
    c.poly([(cx - 17, 196), (cx, 214), (cx + 17, 196)], D["collar"], lw=3)
    for sg in (-1, 1):
        c.circle(cx + sg * 60, 80, 26, D["hair"], lw=3.5)
    c.circle(cx, 130, 70, D["hair"], lw=3.5)
    for sg in (-1, 1):
        bx, by = cx + sg * 44, 98
        c.poly([(bx, by), (bx + sg * 16, by - 12), (bx + sg * 16, by + 12)], D["bow"], lw=2.5)
        c.poly([(bx, by), (bx - sg * 14, by - 11), (bx - sg * 14, by + 11)], D["bow"], lw=2.5)
        c.circle(bx, by, 5, D["bow"], lw=2.5)
    c.circle(cx, 136, 62, D["skin"], lw=3.5)
    c.chord(cx, 128, 69, 69, 192, 348, D["hair"])
    for bx in (cx - 40, cx - 13, cx + 13, cx + 40):
        c.ellipse(bx, 112, 15, 9, D["hair"], line=None)
    ey = 148
    for sg in (-1, 1):
        ex = cx + sg * 24
        if eyes == "normal":
            c.ellipse(ex, ey, 6.5, 9, INK, line=None)
            c.circle(ex + 2, ey - 3.5, 2.6, "#FFFFFF", line=None)
        elif eyes == "blink" or eyes == "closed":
            c.arc(ex, ey - 2, 8, 6, 20, 160, INK, 3.5)
        elif eyes == "happy":
            c.arc(ex, ey + 4, 8, 7, 200, 340, INK, 3.8)
        elif eyes == "wide":
            c.ellipse(ex, ey, 8.5, 11, INK, line=None)
            c.circle(ex + 2.5, ey - 4, 3.2, "#FFFFFF", line=None)
        elif eyes == "up":
            c.ellipse(ex + 2, ey - 3, 6.5, 9, INK, line=None)
            c.circle(ex + 4, ey - 7, 2.6, "#FFFFFF", line=None)
    if brows == "up":
        for sg in (-1, 1):
            c.arc(cx + sg * 24, 130, 9, 5, 200, 340, INK, 3)
    elif brows == "worry":
        c.line([(cx - 32, 129), (cx - 16, 133)], INK, 3)
        c.line([(cx + 32, 129), (cx + 16, 133)], INK, 3)
    elif brows == "think":
        c.line([(cx - 32, 132), (cx - 16, 130)], INK, 3)
        c.arc(cx + 24, 132, 9, 6, 200, 340, INK, 3)
    if blush:
        bc = mix(D["skin"], D["blush"], 0.6)
        c.ellipse(cx - 38, 166, 11, 6, bc, line=None)
        c.ellipse(cx + 38, 166, 11, 6, bc, line=None)
    if mouth == "smile":
        c.arc(cx, 166, 10, 8, 25, 155, INK, 3.5)
    elif mouth == "open":
        c.ellipse(cx, 175, 9, 8, D["mouth"], lw=3)
    elif mouth == "o":
        c.ellipse(cx, 176, 5.5, 6.5, D["mouth"], lw=3)
    elif mouth == "flat":
        c.line([(cx - 7, 174), (cx + 7, 174)], INK, 3.5)
    elif mouth == "grin":
        c.chord(cx, 168, 13, 12, 0, 180, D["mouth"], INK, 3)
    elif mouth == "wavy":
        c.line([(cx - 10, 174), (cx - 5, 171), (cx, 174), (cx + 5, 171), (cx + 10, 174)], INK, 3)
    return c.im


def girl(c, x, y, t, eyes="normal", mouth="smile", arm_l=14, arm_r=14, brows="", s=1.0, a=1.0,
         talk=False, hop=0.0, rot=0.0, blink=True):
    """朵朵。(x, y) 是脚下地面位置。"""
    if blink and eyes == "normal" and ((t + 1.1 + x * 0.002) % 3.7) < 0.13:
        eyes = "blink"
    if talk and mouth in ("smile", "open"):
        mouth = "open" if int(t * 7.5) % 2 == 0 else "smile"
    breathe = 1 + 0.012 * math.sin(t * 2.4)
    c.ellipse(x, y + 1, 52 * s, 9 * s, INK, line=None, a=0.16 * a)
    spr = duo_sprite(eyes, mouth, int(round(arm_l / 3) * 3), int(round(arm_r / 3) * 3), brows)
    c.blit(spr, x, y + 17 * s - hop, "mb", s=s, sy=breathe, a=a, rot=rot)


# ---------------------------------------------------------------- 动物（画在照片里）
def cat_face(c, x, y, s, fur, eye="#B8E35A", tux=False, stripes=None, ear_k=1.0, whiskers=True,
             wrinkles=False, inner="#FFB3C1"):
    for sg in (-1, 1):
        c.poly([(x + sg * 18 * s, y - 28 * s), (x + sg * 44 * s, y - (28 + 34 * ear_k) * s),
                (x + sg * 52 * s, y - 12 * s)], fur, lw=3)
        c.poly([(x + sg * 25 * s, y - 27 * s), (x + sg * 42 * s, y - (28 + 25 * ear_k) * s),
                (x + sg * 46 * s, y - 18 * s)], inner, line=None)
    c.ellipse(x, y, 55 * s, 46 * s, fur, lw=3)
    if tux:
        c.ellipse(x, y + 22 * s, 30 * s, 20 * s, "#FFFFFF", line=None)
        c.poly([(x - 8 * s, y + 8 * s), (x, y - 18 * s), (x + 8 * s, y + 8 * s)], "#FFFFFF", line=None)
    if stripes:
        for k in (-1, 0, 1):
            c.line([(x + k * 13 * s, y - 43 * s), (x + k * 11 * s, y - 29 * s)], stripes, 4.5 * s)
    if wrinkles:
        for k in range(3):
            c.arc(x, y - 22 * s + k * 7 * s, 16 * s, 5 * s, 200, 340, mix(fur, INK, 0.25), 2.5)
    for sg in (-1, 1):
        ex, ey = x + sg * 21 * s, y - 2 * s
        c.ellipse(ex, ey, 9.5 * s, 11.5 * s, eye, lw=2.5)
        c.ellipse(ex, ey, 3.2 * s, 9 * s, INK, line=None)
        c.circle(ex + 3.5 * s, ey - 4.5 * s, 2.6 * s, "#FFFFFF", line=None)
    c.poly([(x - 6 * s, y + 13 * s), (x + 6 * s, y + 13 * s), (x, y + 19 * s)], "#FF8FA3", line=None)
    c.arc(x - 6 * s, y + 19 * s, 6 * s, 5 * s, 10, 170, INK, 2.5)
    c.arc(x + 6 * s, y + 19 * s, 6 * s, 5 * s, 10, 170, INK, 2.5)
    if whiskers:
        wc = INK if fur not in ("#33303A", "#3A3640") else "#FFFFFF"
        for sg in (-1, 1):
            for k in (-1, 0, 1):
                c.line([(x + sg * 30 * s, y + (16 + k * 5) * s), (x + sg * 66 * s, y + (12 + k * 10) * s)], wc, 2)


def fox_face(c, x, y, s):
    F, Wt, D = "#FF8A3D", "#FFFFFF", "#3B2B3A"
    for sg in (-1, 1):
        c.poly([(x + sg * 14 * s, y - 30 * s), (x + sg * 42 * s, y - 80 * s), (x + sg * 56 * s, y - 20 * s)], F, lw=3)
        c.poly([(x + sg * 38 * s, y - 66 * s), (x + sg * 42 * s, y - 80 * s), (x + sg * 48 * s, y - 62 * s)], D,
               line=None)
    head = [(x - 62 * s, y - 16 * s), (x - 40 * s, y - 40 * s), (x + 40 * s, y - 40 * s), (x + 62 * s, y - 16 * s),
            (x + 22 * s, y + 32 * s), (x, y + 42 * s), (x - 22 * s, y + 32 * s)]
    c.poly(head, F, lw=3)
    for sg in (-1, 1):
        c.poly([(x + sg * 58 * s, y - 13 * s), (x + sg * 8 * s, y + 6 * s), (x + sg * 3 * s, y + 38 * s),
                (x + sg * 21 * s, y + 31 * s)], Wt, line=None)
        ex, ey = x + sg * 22 * s, y - 12 * s
        c.ellipse(ex, ey, 5.5 * s, 7.5 * s, INK, line=None)
        c.circle(ex + 2 * s, ey - 3 * s, 2 * s, "#FFFFFF", line=None)
    c.line(head + [head[0]], INK, 3)
    c.ellipse(x, y + 37 * s, 8 * s, 5.5 * s, INK, line=None)


def dog_face(c, x, y, s):
    Fd, E = "#EBC27A", "#B98944"
    c.ellipse(x, y, 52 * s, 47 * s, Fd, lw=3)
    for sg in (-1, 1):
        c.ellipse(x + sg * 50 * s, y + 6 * s, 16 * s, 34 * s, E, lw=3)
    c.ellipse(x, y + 19 * s, 27 * s, 19 * s, "#FFF1D6", line=None)
    c.ellipse(x, y + 33 * s, 7 * s, 9 * s, "#FF8FA3", lw=2)
    c.ellipse(x, y + 11 * s, 11 * s, 7.5 * s, INK, line=None)
    c.line([(x, y + 17 * s), (x, y + 24 * s)], INK, 2.5)
    for sg in (-1, 1):
        c.circle(x + sg * 20 * s, y - 9 * s, 6.5 * s, INK, line=None)
        c.circle(x + sg * 20 * s + 2 * s, y - 11 * s, 2.2 * s, "#FFFFFF", line=None)


def teddy_face(c, x, y, s):
    B, L = "#C68B59", "#F0CFA8"
    for sg in (-1, 1):
        c.circle(x + sg * 40 * s, y - 36 * s, 18 * s, B, lw=3)
        c.circle(x + sg * 40 * s, y - 36 * s, 9 * s, L, line=None)
    c.circle(x, y, 50 * s, B, lw=3)
    c.ellipse(x, y + 18 * s, 24 * s, 18 * s, L, line=None)
    c.ellipse(x, y + 10 * s, 9 * s, 6 * s, INK, line=None)
    c.line([(x, y + 15 * s), (x, y + 24 * s)], INK, 2.5)
    for sg in (-1, 1):
        c.circle(x + sg * 19 * s, y - 8 * s, 6 * s, INK, line=None)
        c.line([(x + sg * 30 * s, y + 40 * s), (x + sg * 34 * s, y + 46 * s)], mix(B, INK, 0.4), 2)


def curled_cat(c, x, y, s):
    """蜷成一团睡觉的芝麻：看不见耳朵和腿"""
    F, F2, Wt = "#3A3640", "#57525F", "#FFFFFF"
    c.ellipse(x - 8 * s, y + 18 * s, 66 * s, 44 * s, F, lw=3)
    c.ellipse(x - 26 * s, y + 4 * s, 26 * s, 12 * s, F2, line=None)
    c.ellipse(x + 2 * s, y + 44 * s, 40 * s, 13 * s, Wt, line=None)
    c.arc(x - 6 * s, y + 22 * s, 64 * s, 40 * s, 25, 170, INK, 17 * s)
    c.arc(x - 6 * s, y + 22 * s, 64 * s, 40 * s, 25, 170, F2, 11 * s)
    c.circle(x - 62 * s, y + 30 * s, 7 * s, Wt, lw=2.5)
    c.ellipse(x + 38 * s, y + 18 * s, 31 * s, 26 * s, F, lw=3)
    c.ellipse(x + 44 * s, y + 29 * s, 18 * s, 12 * s, Wt, line=None)
    c.poly([(x + 38 * s, y + 8 * s), (x + 33 * s, y + 25 * s), (x + 43 * s, y + 25 * s)], Wt, line=None)
    c.poly([(x + 39 * s, y + 25 * s), (x + 48 * s, y + 25 * s), (x + 43.5 * s, y + 30 * s)], "#FF8FA3", line=None)
    for dx in (-13, 15):
        c.arc(x + 40 * s + dx * s, y + 14 * s, 7 * s, 5 * s, 20, 160, Wt, 3)
    c.ellipse(x + 26 * s, y + 52 * s, 13 * s, 8 * s, Wt, lw=2.5)
    c.ellipse(x + 54 * s, y + 48 * s, 12 * s, 8 * s, Wt, lw=2.5)
    for dx, dy, sz in ((58, -26, 15), (72, -42, 12), (84, -56, 10)):
        c.text("z", x + dx * s, y + dy * s, sz * s * 1.6, Wt, 900, stroke=1.5)


def box_cat(c, x, y, s):
    cat_face(c, x, y - 4 * s, s * 0.92, "#FFA552", stripes="#E37C2C")
    B, Bd = "#D9A066", "#C08548"
    c.poly([(x - 72 * s, y + 6 * s), (x + 72 * s, y + 6 * s), (x + 66 * s, y + 70 * s), (x - 66 * s, y + 70 * s)], B,
           lw=3)
    c.poly([(x - 72 * s, y + 6 * s), (x - 96 * s, y - 12 * s), (x - 46 * s, y - 14 * s), (x - 24 * s, y + 6 * s)], Bd,
           lw=3)
    c.poly([(x + 72 * s, y + 6 * s), (x + 96 * s, y - 12 * s), (x + 46 * s, y - 14 * s), (x + 24 * s, y + 6 * s)], Bd,
           lw=3)
    c.rect(x - 16 * s, y + 26 * s, 32 * s, 8 * s, mix(B, "#FFFFFF", 0.4), r=3, line=None)


def hairless_cat(c, x, y, s):
    cat_face(c, x, y + 6 * s, s, "#F2C7B5", eye="#E8E15A", ear_k=1.6, whiskers=False, wrinkles=True,
             inner="#E7A9A0")


ANIMALS = {
    "cat_orange": lambda c, x, y, s: cat_face(c, x, y, s, "#FFA552", stripes="#E37C2C"),
    "cat_black": lambda c, x, y, s: cat_face(c, x, y, s, "#3A3640", eye="#FFD447"),
    "cat_white": lambda c, x, y, s: cat_face(c, x, y, s, "#FFFFFF", eye="#7CC4FF"),
    "cat_gray": lambda c, x, y, s: cat_face(c, x, y, s, "#A9B1C7", stripes="#7F88A3"),
    "cat_tux": lambda c, x, y, s: cat_face(c, x, y, s, "#33303A", tux=True),
    "cat_curled": curled_cat,
    "cat_box": box_cat,
    "cat_hairless": hairless_cat,
    "fox": fox_face,
    "dog": dog_face,
    "teddy": teddy_face,
}
PHOTO_BG = {
    "cat_orange": "#DDF0FF", "cat_black": "#FFE9C2", "cat_white": "#FFD9E1", "cat_gray": "#E3F7D9",
    "cat_tux": "#FFE3D4", "cat_curled": "#E6E0FF", "cat_box": "#D8F3FF", "cat_hairless": "#E5F6E8",
    "fox": "#E4F4D2", "dog": "#E4ECFF", "teddy": "#FFEFD5",
}
CATS = {"cat_orange", "cat_black", "cat_white", "cat_gray", "cat_tux", "cat_curled", "cat_box", "cat_hairless"}


@lru_cache(maxsize=256)
def photo_sprite(kind, caption="", w=170, h=196):
    c = Canvas.sprite(w + 12, h + 12)
    c.rect(8, 9, w, h, INK, r=16, line=None)
    c.rect(2, 2, w, h, PAPER, r=16, lw=3.5)
    pw = w - 28
    ph = h - (66 if caption else 46)
    pic = Canvas.sprite(pw, ph)
    pic.rect(0, 0, pw, ph, PHOTO_BG.get(kind, "#DDEBFF"), line=None)
    ANIMALS[kind](pic, pw / 2, ph / 2 + 10, pw / 175)
    mask = Image.new("L", pic.im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pic.im.width - 1, pic.im.height - 1], radius=18, fill=255)
    c.im.paste(pic.im, (int(16 * SS), int(16 * SS)), mask)
    c.rect(16, 16, pw, ph, None, r=9, lw=2.5)
    if caption:
        c.text(caption, 2 + w / 2, h - 23, 26, INK, 900)
    return c.im


def photo(c, kind, x, y, t, t0, rot=0.0, caption="", s=1.0, a=1.0, w=170, h=196):
    k = pop(t, t0)
    if k <= 0:
        return
    c.blit(photo_sprite(kind, caption, w, h), x, y, "mm", s=s * k, rot=rot, a=a)


@lru_cache(maxsize=128)
def pixel_sprite(kind, n=12, size=150):
    """把动物照片变成马赛克小方块（神经网络的“输入”）"""
    src = Canvas.sprite(175, 175)
    src.rect(0, 0, 175, 175, PHOTO_BG.get(kind, "#DDEBFF"), line=None)
    ANIMALS[kind](src, 87, 96, 0.95)
    small = src.im.convert("RGB").resize((n, n), Image.BOX)
    big = small.resize((int(size * SS), int(size * SS)), Image.NEAREST)
    c = Canvas(Image.new("RGBA", (int((size + 10) * SS), int((size + 10) * SS)), rgb(INK) + (0,)))
    c.rect(7, 8, size, size, INK, r=10, line=None)
    c.im.paste(big, (int(2 * SS), int(2 * SS)))
    c.rect(2, 2, size, size, None, r=4, lw=3.5)
    return c.im


# ---------------------------------------------------------------- 文字类道具
@lru_cache(maxsize=1024)
def chip_sprite(text, size=28, fill=PAPER, color=INK, weight=900, padx=18, pady=9, lw=3.5, shadow=4, r=None,
                stroke=0.0):
    tw = text_width(text, size, weight)
    w, h = tw + padx * 2, size * 1.25 + pady * 2
    c = Canvas.sprite(w + shadow + 6, h + shadow + 6)
    rr = h / 2 if r is None else r
    if shadow:
        c.rect(3 + shadow, 3 + shadow, w, h, INK, r=rr, line=None)
    c.rect(3, 3, w, h, fill, r=rr, lw=lw)
    c.text(text, 3 + w / 2, 3 + h / 2 + size * 0.02, size, color, weight, stroke=stroke)
    return c.im


def chip(c, text, x, y, t=1e9, t0=0.0, size=28, fill=PAPER, color=INK, anchor="mm", s=1.0, a=1.0, rot=0.0,
         shadow=4, weight=900, stroke=0.0, padx=18):
    k = pop(t, t0) if t0 > -1e8 else 1.0
    if k <= 0:
        return
    c.blit(chip_sprite(text, size, fill, color, weight, padx, 9, 3.5, shadow, None, stroke), x, y, anchor,
           s=s * k, a=a, rot=rot)


def term_badge(c, text, t, t0, fill=CORAL, y=74, x=W / 2, size=40):
    """名词徽章：念到这个词的时候在顶部弹出来"""
    k = pop(t, t0, 0.45)
    if k <= 0:
        return
    c.blit(chip_sprite(text, size, fill, "#FFFFFF", 900, 30, 9, 4, 6, None, 2.2), x, y, "mm", s=k)


def say(c, text, x, y, t=1e9, t0=0.0, size=34, color=INK, weight=900, anchor="mm", stroke=0.0,
        stroke_color=INK, a=1.0, rot=0.0):
    k = pop(t, t0, 0.35) if t0 > -1e8 else 1.0
    if k <= 0:
        return
    c.blit(text_sprite(text, size, color, weight, stroke, stroke_color), x, y, anchor, s=k, a=a, rot=rot)


@lru_cache(maxsize=512)
def bubble_sprite(text, size=30, max_w=360, tail="bl", fill=PAPER, color=INK):
    """返回 (精灵, 尾巴尖x, 尾巴尖y)，坐标为精灵内的 1x 坐标"""
    lines = wrap(text, size, max_w, 800)
    tw = max(text_width(ln, size, 800) for ln in lines)
    lh = size * 1.38
    w, h = tw + 44, len(lines) * lh + 30
    tl = 26
    c = Canvas.sprite(w + 16, h + tl + 16)
    ox, oy = 4, 4
    tx = {"bl": ox + w * 0.24, "bm": ox + w * 0.5, "br": ox + w * 0.76}[tail]
    c.rect(ox + 5, oy + 6, w, h, INK, r=26, line=None)
    c.poly([(tx - 14, oy + h - 4), (tx + 14, oy + h - 4), (tx + (-6 if tail == "br" else 6), oy + h + tl)], fill,
           lw=3.5)
    c.rect(ox, oy, w, h, fill, r=26, lw=3.5)
    c.rect(tx - 12, oy + h - 9, 24, 7, fill, line=None)
    for i, ln in enumerate(lines):
        c.text(ln, ox + w / 2, oy + 15 + lh * (i + 0.5), size, color, 800)
    tipx = tx + (-6 if tail == "br" else 6)
    return c.im, tipx, oy + h + tl


def bubble(c, text, x, y, t, t0, size=30, max_w=360, tail="bl", fill=PAPER, color=INK, a=1.0):
    """对话气泡，(x, y) 为尾巴尖的位置，弹出时以尾巴尖为中心放大"""
    k = pop(t, t0, 0.4)
    if k <= 0:
        return
    spr, tipx, tipy = bubble_sprite(text, size, max_w, tail, fill, color)
    c.blit(spr, x - tipx * k, y - tipy * k, "lt", s=k, a=a)


@lru_cache(maxsize=16)
def stamp_sprite(ok=True, label=""):
    col = GREEN if ok else RED
    c = Canvas.sprite(120, 120)
    c.circle(60, 60, 50, PAPER, col, 7)
    c.circle(60, 60, 41, None, col, 3)
    if ok:
        c.line([(37, 62), (54, 79), (85, 42)], col, 11)
    else:
        c.line([(40, 40), (80, 80)], col, 11)
        c.line([(40, 80), (80, 40)], col, 11)
    return c.im


def stamp(c, ok, x, y, t, t0, s=1.0, rot=-12):
    if t < t0:
        return
    u = prog(t, t0, 0.22)
    k = lerp(1.9, 1.0, ease_out(u))
    c.blit(stamp_sprite(ok), x, y, "mm", s=s * k, a=min(1, u * 2.5), rot=rot)


def idea_bulb(c, x, y, t, t0, s=1.0):
    k = pop(t, t0, 0.45)
    if k <= 0:
        return
    s *= k
    for i in range(8):
        ang = math.pi * 2 * i / 8 + t * 0.6
        r0, r1 = 44 * s, (58 + 6 * math.sin(t * 6 + i)) * s
        c.line([(x + math.cos(ang) * r0, y + math.sin(ang) * r0), (x + math.cos(ang) * r1, y + math.sin(ang) * r1)],
               SUN, 5 * s)
    c.circle(x, y, 32 * s, SUN, lw=3.5)
    c.circle(x - 10 * s, y - 10 * s, 7 * s, "#FFF6CF", line=None)
    c.rect(x - 15 * s, y + 26 * s, 30 * s, 20 * s, "#C9D3EE", r=5 * s, lw=3)
    c.line([(x - 15 * s, y + 35 * s), (x + 15 * s, y + 35 * s)], INK, 2.5)


def qmark(c, x, y, t, t0, s=1.0, col=CORAL):
    k = pop(t, t0, 0.4)
    if k <= 0:
        return
    c.blit(text_sprite("?", 64, col, 900, 3.5, INK), x, y + wave(t, 4, 0.8), "mm", s=s * k,
           rot=wave(t, 8, 0.5))


def bulb(c, x, y, r, on=0.0, col=SUN, off="#4A5590", glow=True, base=False, lw=3.0):
    """神经元小灯泡"""
    on = clamp(on)
    if glow and on > 0.03:
        c.glow(x, y, r * (2.1 + 0.7 * on), col, a=on)
    if base:
        c.rect(x - r * 0.42, y + r * 0.78, r * 0.84, r * 0.55, "#C9D3EE", r=r * 0.12, lw=lw)
        c.line([(x - r * 0.42, y + r * 1.0), (x + r * 0.42, y + r * 1.0)], INK, 2.5)
    fill = mix(off, col, on)
    c.circle(x, y, r, fill, INK, lw)
    c.circle(x - r * 0.33, y - r * 0.35, r * 0.2, mix(fill, "#FFFFFF", 0.65), line=None)


def knob(c, x, y, r, ang, col=SKY):
    for k in range(-4, 5):
        a = math.radians(k * 30 - 90)
        c.line([(x + math.cos(a) * r * 1.16, y + math.sin(a) * r * 1.16),
                (x + math.cos(a) * r * 1.32, y + math.sin(a) * r * 1.32)], INK, 2.5)
    c.circle(x, y, r, PAPER, lw=3)
    c.circle(x, y, r * 0.7, col, lw=3)
    a = math.radians(ang - 90)
    c.line([(x, y), (x + math.cos(a) * r * 0.62, y + math.sin(a) * r * 0.62)], INK, 4.5)
    c.circle(x, y, r * 0.16, INK, line=None)


def magnifier(c, x, y, r=40, a=1.0, rot=45):
    ang = math.radians(rot)
    hx, hy = x + math.cos(ang) * r * 0.95, y + math.sin(ang) * r * 0.95
    ex, ey = x + math.cos(ang) * r * 2.0, y + math.sin(ang) * r * 2.0
    k = r / 40
    c.capsule((hx, hy), (ex, ey), max(5, 12 * k), "#8A5A3C", lw=max(2.5, 3.5 * k), a=a)
    c.circle(x, y, r, "#D8F4FF", "#5C6B94", max(3, 9 * k), a=a)
    c.circle(x, y, r + 4.5 * k, None, INK, max(2.5, 3 * k), a=a)
    c.arc(x, y, r * 0.65, r * 0.65, 200, 260, "#FFFFFF", max(2, 5 * k), a=a)


def book(c, x, y, w, h, col, title="", sub="", rot=0.0, s=1.0, a=1.0, dashed=False):
    c.blit(book_sprite(w, h, col, title, sub, dashed), x, y, "mm", s=s, a=a, rot=rot)


@lru_cache(maxsize=64)
def book_sprite(w, h, col, title="", sub="", dashed=False):
    c = Canvas.sprite(w + 14, h + 14)
    if dashed:
        c.rect(3, 3, w, h, mix(col, "#FFFFFF", 0.75), r=10, line=None)
        _dash_rect(c, 3, 3, w, h, col)
        if title:
            for i, ln in enumerate(wrap(title, 24, w - 36, 900)):
                c.text(ln, 3 + w / 2 + 6, 3 + h * 0.3 + i * 32, 24, mix(col, "#FFFFFF", 0.3), 900)
        return c.im
    c.rect(10, 10, w, h, INK, r=10, line=None)
    c.rect(3, 3, w, h, col, r=10, lw=3.5)
    c.rect(3, 3, 22, h, mix(col, INK, 0.25), r=10, lw=3.5)
    c.rect(36, 3 + h * 0.18, w - 46, 4, mix(col, "#FFFFFF", 0.55), line=None)
    c.rect(36, 3 + h * 0.80, w - 46, 4, mix(col, "#FFFFFF", 0.55), line=None)
    if title:
        lines = wrap(title, 24, w - 52, 900)
        for i, ln in enumerate(lines):
            c.text(ln, 3 + 12 + w / 2, 3 + h * 0.34 + i * 32, 24, "#FFFFFF", 900, stroke=2.2)
        if sub:
            c.text(sub, 3 + 12 + w / 2, 3 + h * 0.34 + len(lines) * 32 + 22, 17, "#FFFFFF", 700)
    return c.im


def _dash_rect(c, x, y, w, h, col, dash=16, gap=11, lw=4):
    def seg_line(p0, p1):
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        n = int(L // (dash + gap)) + 1
        for i in range(n):
            a0 = i * (dash + gap) / L
            a1 = min(1, (i * (dash + gap) + dash) / L)
            if a0 >= 1:
                break
            c.line([lerp2(p0, p1, a0), lerp2(p0, p1, a1)], col, lw)
    seg_line((x, y), (x + w, y))
    seg_line((x + w, y), (x + w, y + h))
    seg_line((x + w, y + h), (x, y + h))
    seg_line((x, y + h), (x, y))


def doc_icon(c, x, y, w=70, h=88, col=PAPER, lines=4, a=1.0, s=1.0, accent=SKY):
    w, h = w * s, h * s
    c.rect(x - w / 2 + 5, y - h / 2 + 6, w, h, INK, r=8, line=None, a=a)
    c.rect(x - w / 2, y - h / 2, w, h, col, r=8, lw=3, a=a)
    for i in range(lines):
        ww = w * (0.68 if i % 3 == 2 else 0.78)
        c.rect(x - w * 0.38, y - h * 0.3 + i * h * 0.17, ww, h * 0.07, accent if i == 0 else "#C9D3EE", r=2,
               line=None, a=a)


def person_icon(c, x, y, s=1.0, col="#FFC9A8", shirt=SKY, a=1.0):
    c.rect(x - 30 * s, y + 4 * s, 60 * s, 46 * s, shirt, r=24 * s, lw=3, a=a)
    c.circle(x, y - 18 * s, 21 * s, col, lw=3, a=a)


def gpu_icon(c, x, y, s=1.0, a=1.0):
    for i in range(4):
        for sg in (-1, 1):
            px = x - 24 * s + i * 16 * s
            c.line([(px, y + sg * 34 * s), (px, y + sg * 46 * s)], INK, 4, a=a)
            py = y - 24 * s + i * 16 * s
            c.line([(x + sg * 34 * s, py), (x + sg * 46 * s, py)], INK, 4, a=a)
    c.rect(x - 36 * s, y - 36 * s, 72 * s, 72 * s, "#58627F", r=10 * s, lw=3.5, a=a)
    c.rect(x - 20 * s, y - 20 * s, 40 * s, 40 * s, SUN, r=6 * s, lw=3, a=a)


def stack_icon(c, x, y, s=1.0, a=1.0):
    for i, col in enumerate((GRAPE, LEAF, CORAL)):
        doc_icon(c, x - 14 * s + i * 14 * s, y - 10 * s + i * 8 * s, 56, 70, PAPER, 3, a, s, col)


def bookshelf(c, x, y, w, h, seed=2, a=1.0):
    rnd = random.Random(seed)
    c.rect(x + 8, y + 10, w, h, INK, r=14, line=None, a=a)
    c.rect(x, y, w, h, "#B07A4F", r=14, lw=4, a=a)
    rows = 4
    rh = (h - 24) / rows
    cols = [CORAL, SUN, SKY, LEAF, GRAPE, "#FF9BB0", "#F5F1E6", "#5C6B94"]
    for r_ in range(rows):
        by = y + 12 + (r_ + 1) * rh
        c.rect(x + 12, by - rh + 8, w - 24, rh - 8, "#8A5A3C", r=6, line=None, a=a)
        bx = x + 18
        while bx < x + w - 34:
            bw = rnd.uniform(14, 26)
            bh = rnd.uniform(rh * 0.55, rh * 0.86)
            c.rect(bx, by - bh, bw, bh, rnd.choice(cols), r=3, lw=2.5, a=a)
            bx += bw + rnd.uniform(1, 4)
        c.rect(x + 8, by - 2, w - 16, 10, "#D29A68", r=4, lw=3, a=a)


def warning_sign(c, x, y, s=1.0, a=1.0):
    pts = [(x, y - 52 * s), (x + 58 * s, y + 46 * s), (x - 58 * s, y + 46 * s)]
    c.poly([(px + 6, py + 7) for px, py in pts], INK, line=None, a=a)
    c.poly(pts, SUN, lw=4, a=a)
    c.text("!", x, y + 12 * s, 58 * s, INK, 900, a=a)


def search_box(c, x, y, w, text, t, t0, cps=8.0, h=64):
    """带打字效果的搜索框，(x, y) 为中心"""
    c.rect(x - w / 2 + 6, y - h / 2 + 7, w, h, INK, r=h / 2, line=None)
    c.rect(x - w / 2, y - h / 2, w, h, PAPER, r=h / 2, lw=3.5)
    magnifier(c, x - w / 2 + 38, y - 4, 13, rot=45)
    n = int(max(0, t - t0) * cps)
    shown = text[:n]
    c.text(shown, x - w / 2 + 72, y, 28, INK, 700, anchor="lm")
    if n < len(text) or int(t * 2) % 2 == 0:
        tw = text_width(shown, 28, 700)
        c.rect(x - w / 2 + 74 + tw, y - 17, 3.5, 34, INK, line=None)


# ================================================================ 名词篇道具
BRICK_COLS = [SKY, SUN, CORAL, "#FF9BB0", LEAF, GRAPE, "#4FD1C5"]


def brick_w(text, size=34):
    return max(size * 1.6, text_width(text, size, 900) + 34)


@lru_cache(maxsize=512)
def brick_sprite(text, col, size=34):
    """乐高积木样子的 token"""
    w = brick_w(text, size)
    h = size * 1.7
    n = max(2, min(4, int(w // 46)))
    c = Canvas.sprite(w + 12, h + 24)
    top = 15
    c.rect(9, top + 8, w, h, INK, r=10, line=None)
    for i in range(n):
        sx = 3 + (i + 0.5) * w / n
        c.rect(sx - 11, top - 12, 22, 18, col, r=5, lw=3)
    c.rect(3, top, w, h, col, r=10, lw=3.5)
    c.rect(11, top + 7, w - 16, 7, mix(col, "#FFFFFF", 0.45), r=3.5, line=None)
    c.text(text, 3 + w / 2, top + h / 2 + 3, size, INK, 900)
    return c.im


def brick(c, text, x, y, t=1e9, t0=0.0, col=SKY, size=34, s=1.0, rot=0.0, a=1.0, sx=1.0):
    k = pop(t, t0, 0.4)
    if k <= 0:
        return
    c.blit(brick_sprite(text, col, size), x, y + 6, "mm", s=s * k, rot=rot, a=a, sx=sx)


@lru_cache(maxsize=256)
def pin_sprite(text, col, size=26):
    tw = text_width(text, size, 900)
    w, h = tw + 30, size * 1.3 + 14
    c = Canvas.sprite(w + 10, h + 36)
    c.rect(7, 7, w, h, INK, r=h / 2, line=None)
    c.rect(3, 3, w, h, PAPER, r=h / 2, lw=3)
    c.text(text, 3 + w / 2, 3 + h / 2 + 1, size, INK, 900)
    cx = 3 + w / 2
    c.line([(cx, 3 + h), (cx, 3 + h + 15)], INK, 3)
    c.circle(cx, 3 + h + 21, 8, col, lw=3)
    return c.im, cx, 3 + h + 21


def pin(c, text, x, y, t=1e9, t0=0.0, col=CORAL, size=26, a=1.0):
    """地图上的一个词，(x, y) 是它的坐标点"""
    k = pop(t, t0, 0.4)
    if k <= 0:
        return
    spr, px, py = pin_sprite(text, col, size)
    c.blit(spr, x - px * k, y - py * k, "lt", s=k, a=a)


def beam(c, src, dst, wd=90, a=0.6, col="#FFE9A8"):
    """聚光灯光束：从 src 照到 dst"""
    if a <= 0.01:
        return
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    w0 = 10
    pts = [(src[0] + nx * w0, src[1] + ny * w0), (dst[0] + nx * wd / 2, dst[1] + ny * wd / 2),
           (dst[0] - nx * wd / 2, dst[1] - ny * wd / 2), (src[0] - nx * w0, src[1] - ny * w0)]
    c.poly(pts, col, line=None, a=a * 0.42)
    c.ellipse(dst[0], dst[1] + 8, wd * 0.62, wd * 0.2, col, line=None, a=a * 0.55)


def lamp(c, x, y, toward, col="#4A4366", lens="#FFF3B8", s=1.0):
    ang = math.atan2(toward[1] - y, toward[0] - x)
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v):
        return (x + (ca * u - sa * v) * s, y + (sa * u + ca * v) * s)

    c.line([(x, y - 30 * s), (x, y)], INK, 4)
    c.poly([P(-18, -16), P(20, -22), P(20, 22), P(-18, 16)], col, lw=3)
    lx, ly = P(22, 0)
    c.ellipse(lx, ly, 7 * s, 7 * s, lens, lw=2.5)
    c.circle(x, y, 6 * s, "#8A8FA8", lw=2.5)


def gear(c, x, y, r, teeth=8, rot=0.0, col="#AEB6CF"):
    pts = []
    for i in range(teeth):
        a0 = rot + 2 * math.pi * i / teeth
        da = 2 * math.pi / teeth
        for frac, rr in ((0.0, r * 0.78), (0.18, r), (0.5, r), (0.68, r * 0.78)):
            a = a0 + da * frac
            pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    c.poly(pts, col, lw=3)
    c.circle(x, y, r * 0.3, PAPER, lw=3)


def machine(c, x, y, w, h, label, t, col=SKY):
    """会转齿轮的小机器（分词器、嵌入……）"""
    gear(c, x - w * 0.18, y - h / 2 - 12, 30, 9, t * 2.2, "#AEB6CF")
    gear(c, x + w * 0.2, y - h / 2 - 6, 22, 7, -t * 3.0, SUN)
    c.rect(x - w / 2 + 8, y - h / 2 + 9, w, h, INK, r=26, line=None)
    c.rect(x - w / 2, y - h / 2, w, h, col, r=26, lw=4)
    c.rect(x - w / 2 + 18, y - h / 2 + 18, w - 36, h * 0.42, PAPER, r=14, lw=3)
    c.text(label, x, y - h / 2 + 18 + h * 0.21, 34, INK, 900)
    for i in range(3):
        on = int(t * 4 + i) % 3 == 0
        c.circle(x - 34 + i * 34, y + h * 0.22, 9, SUN if on else "#5A6280", lw=2.5)
    c.rect(x - w / 2 - 14, y - 26, 20, 52, "#5A6280", r=6, lw=3)
    c.rect(x + w / 2 - 6, y - 26, 20, 52, "#5A6280", r=6, lw=3)


def coin(c, x, y, r=18, a=1.0):
    c.circle(x, y + 4, r, mix(SUN, INK, 0.35), lw=3, a=a)
    c.circle(x, y, r, SUN, lw=3, a=a)
    c.circle(x, y, r * 0.62, None, mix(SUN, INK, 0.3), 2.5, a=a)


def gauge(c, x, y, r, v, lw=20, c0="#2FB57E", c1="#F0524A", lo="", hi=""):
    n = 24
    for i in range(n):
        a0, a1 = 150 + 240 * i / n, 150 + 240 * (i + 1) / n + 0.8
        c.arc(x, y, r, r, a0, a1, mix(c0, c1, i / (n - 1)), lw)
    c.arc(x, y, r + lw / 2 + 1, r + lw / 2 + 1, 150, 390, INK, 3)
    c.arc(x, y, r - lw / 2 - 1, r - lw / 2 - 1, 150, 390, INK, 3)
    ang = math.radians(150 + 240 * clamp(v))
    c.line([(x, y), (x + math.cos(ang) * (r - lw - 4), y + math.sin(ang) * (r - lw - 4))], INK, 7)
    c.circle(x, y, 13, PAPER, lw=3.5)
    if lo:
        c.text(lo, x + math.cos(math.radians(150)) * r, y + math.sin(math.radians(150)) * r + 30, 22, INK, 900)
    if hi:
        c.text(hi, x + math.cos(math.radians(30)) * r, y + math.sin(math.radians(30)) * r + 30, 22, INK, 900)


CHALK = "#F4F1E8"


def chalkboard(c, x, y, w, h, k=1.0):
    """黑板，(x, y) 为中心，w/h 是绿色板面的大小"""
    if k <= 0.01:
        return
    c.crect(x + 9, y + 10, w + 34, h + 34, INK, r=18, line=None, s=k)
    c.crect(x, y, w + 34, h + 34, "#B07A4F", r=18, lw=4, s=k)
    c.crect(x, y, w, h, "#2F5D50", r=8, lw=3, s=k)
    if k > 0.97:
        c.rect(x - w * 0.3, y + h / 2 + 6, w * 0.6, 12, "#8A5A3C", r=4, lw=2.5)
        c.rect(x - w * 0.22, y + h / 2 - 2, 34, 9, CHALK, r=3, lw=2)
        c.rect(x - w * 0.22 + 46, y + h / 2 - 2, 26, 9, "#FFB3C1", r=3, lw=2)


def chalk(c, text, x, y, size=28, a=1.0, anchor="lm", n=None):
    if n is not None:
        text = text[:n]
    if text:
        c.text(text, x, y, size, CHALK, 700, anchor=anchor, a=a * 0.93)


def eraser(c, x, y, s=1.0):
    c.rect(x - 34 * s, y - 16 * s, 68 * s, 32 * s, "#C98A55", r=6 * s, lw=3)
    c.rect(x - 34 * s, y + 4 * s, 68 * s, 12 * s, "#E9E2D0", r=4 * s, lw=2.5)


def notebook(c, x, y, w, h, lines, t, t_lines, title="", col="#FFF7D6", size=26, k=1.0):
    if k <= 0.01:
        return
    c.crect(x + 8, y + 9, w, h, INK, r=14, line=None, s=k)
    c.crect(x, y, w, h, col, r=14, lw=4, s=k)
    if k < 0.97:
        return
    x0, y0 = x - w / 2, y - h / 2
    for i in range(int(h // 46)):
        c.circle(x0 + 2, y0 + 30 + i * 46, 8, PAPER, lw=3)
    if title:
        c.text(title, x, y0 + 36, 28, INK, 900)
    top = y0 + (76 if title else 40)
    for i in range(1, int((h - (top - y0)) // 46) + 1):
        c.line([(x0 + 28, top + i * 46 - 14), (x0 + w - 20, top + i * 46 - 14)], "#E8D9A8", 2, caps=False)
    for i, (ln, t0) in enumerate(zip(lines, t_lines)):
        kk = pop(t, t0, 0.35)
        if kk > 0:
            c.text(ln, x0 + 40, top + i * 46 + 14, size, INK, 800, anchor="lm", sc=kk)


# ================================================================ 进阶篇道具
THEMES.update({
    "orange": dict(top="#FFF5EA", bot="#FFE3C6", accent="#FF9F43", floor="#FFD1A6", dark=False),
    "indigo": dict(top="#F0F1FF", bot="#DCE0FF", accent="#6C7BFF", floor="#C9CFFF", dark=False),
    "lime": dict(top="#F4FBE8", bot="#E1F3C6", accent="#8CC63F", floor="#CFE8A8", dark=False),
    "magenta": dict(top="#FCF0FA", bot="#F5D8F0", accent="#D35CC0", floor="#EDC2E6", dark=False),
    "lab": dict(top="#0F2233", bot="#173A52", accent="#4DD6FF", floor="#0A1826", dark=True, grid=True,
                title="#173A52"),
})


def flower_pic(c, x, y, s):
    c.line([(x, y + 10 * s), (x + 4 * s, y + 70 * s)], "#3E9B4F", 6 * s)
    c.ellipse(x - 18 * s, y + 46 * s, 16 * s, 7 * s, "#5CB85C", lw=2.5)
    for i in range(8):
        a = math.pi * 2 * i / 8
        c.circle(x + math.cos(a) * 26 * s, y - 14 * s + math.sin(a) * 26 * s, 15 * s, "#FFC93D", lw=2.5)
    c.circle(x, y - 14 * s, 15 * s, "#8A5A2B", lw=2.5)
    c.circle(x - 4 * s, y - 18 * s, 4 * s, "#B07A4F", line=None)


def beach_pic(c, x, y, s):
    c.circle(x + 36 * s, y - 34 * s, 18 * s, "#FFD84D", lw=2.5)
    c.rect(x - 90 * s, y - 4 * s, 180 * s, 40 * s, "#4FA8F5", line=None)
    for k in range(3):
        c.arc(x - 50 * s + k * 40 * s, y + 6 * s, 14 * s, 6 * s, 200, 340, "#FFFFFF", 3)
    c.ellipse(x, y + 52 * s, 110 * s, 26 * s, "#F7D58C", line=None)


ANIMALS["flower"] = flower_pic
ANIMALS["beach"] = beach_pic
PHOTO_BG["flower"] = "#E6F6FF"
PHOTO_BG["beach"] = "#CDEBFF"


def thought_cloud(c, x, y, w, h, k=1.0, fill=PAPER):
    """想法云：一团圆圈，下面拖着两个小泡泡"""
    if k <= 0.01:
        return
    w, h = w * k, h * k
    blobs = [(-0.32, 0.05, 0.36), (0.0, -0.18, 0.4), (0.32, 0.02, 0.36), (-0.12, 0.2, 0.34), (0.18, 0.22, 0.32)]
    for dx, dy, r in blobs:
        c.circle(x + dx * w + 6, y + dy * h + 7, r * h, INK, line=None)
    for dx, dy, r in blobs:
        c.circle(x + dx * w, y + dy * h, r * h, fill, lw=3.5)
    for dx, dy, r in blobs:
        c.circle(x + dx * w, y + dy * h, r * h - 3.5, fill, line=None)
    c.circle(x - w * 0.42, y + h * 0.62, 12 * k, fill, lw=3)
    c.circle(x - w * 0.52, y + h * 0.82, 7 * k, fill, lw=2.5)


def fish(c, x, y, s=1.0, col="#7CC4FF", a=1.0):
    c.poly([(x - 18 * s, y), (x - 32 * s, y - 11 * s), (x - 32 * s, y + 11 * s)], col, lw=2.5, a=a)
    c.ellipse(x, y, 22 * s, 12 * s, col, lw=2.5, a=a)
    c.circle(x + 11 * s, y - 3 * s, 2.6 * s, INK, line=None, a=a)


@lru_cache(maxsize=16)
def noise_sprite(seed, w=360, h=270, cell=6):
    rnd = np.random.default_rng(seed)
    small = (rnd.random((max(1, h // cell), max(1, w // cell), 3)) * 255).astype(np.uint8)
    return Image.fromarray(small, "RGB").resize((int(w * SS), int(h * SS)), Image.NEAREST).convert("RGBA")


def _walk_cat(c, cx, cy, fur, hat, tails=1):
    c.capsule((cx - 30, cy + 20), (cx - 36, cy + 52), 11, fur, lw=3)
    c.capsule((cx + 24, cy + 20), (cx + 30, cy + 52), 11, fur, lw=3)
    for k in range(tails):
        c.arc(cx - 70 - k * 18, cy - 22 + k * 22, 34, 40, 90 + k * 40, 210 + k * 40, INK, 15)
        c.arc(cx - 70 - k * 18, cy - 22 + k * 22, 34, 40, 90 + k * 40, 210 + k * 40, fur, 9)
    c.ellipse(cx - 6, cy + 8, 56, 30, fur, lw=3)
    c.capsule((cx - 14, cy + 22), (cx - 18, cy + 54), 11, fur, lw=3)
    c.capsule((cx + 10, cy + 22), (cx + 14, cy + 54), 11, fur, lw=3)
    hx, hy = cx + 50, cy - 22
    for sg in (-1, 1):
        c.poly([(hx + sg * 10, hy - 18), (hx + sg * 24, hy - 42), (hx + sg * 28, hy - 8)], fur, lw=3)
    c.circle(hx, hy, 28, fur, lw=3)
    c.ellipse(hx + 10, hy + 2, 5, 7, INK, line=None)
    c.ellipse(hx - 10, hy + 2, 5, 7, INK, line=None)
    c.poly([(hx - 4, hy + 12), (hx + 4, hy + 12), (hx, hy + 17)], "#FF8FA3", line=None)
    if hat:
        c.ellipse(hx, hy - 26, 30, 8, hat, lw=3)
        c.rect(hx - 18, hy - 62, 36, 38, hat, r=6, lw=3)
        c.rect(hx - 18, hy - 36, 36, 8, "#FFFFFF", line=None)


@lru_cache(maxsize=16)
def painting_sprite(hat="#E8454B", variant=0, tails=1, sign=""):
    """“戴红帽子的猫在月亮上散步”"""
    c = Canvas.sprite(360, 270)
    c.rect(0, 0, 360, 270, "#26305F", line=None)
    rnd = random.Random(variant + 11)
    for _ in range(22):
        c.circle(rnd.uniform(8, 352), rnd.uniform(8, 150), rnd.choice([1.5, 2, 2.6]), "#FFFFFF", line=None)
    if variant == 0:
        c.circle(180, 470, 300, "#F5E7A1", lw=3)
        for x, y, r in ((80, 230, 16), (220, 215, 11), (300, 245, 14)):
            c.ellipse(x, y, r, r * 0.55, "#E2CF7E", line=None)
        _walk_cat(c, 170, 140, "#FFA552", hat, tails)
    else:
        c.circle(70, 70, 42, "#F5E7A1", lw=3)
        c.circle(90, 58, 40, "#26305F", line=None)
        c.rect(0, 222, 360, 48, "#5B4C8A", line=None)
        _walk_cat(c, 200, 150, "#FFA552", hat, tails)
    if sign:
        c.line([(300, 190), (300, 236)], "#8A5A3C", 6)
        c.rect(250, 150, 100, 46, "#FFF3D6", r=6, lw=3)
        c.text(sign, 300, 173, 22, INK, 900)
    return c.im


@lru_cache(maxsize=32)
def blurred(spr_key, radius):
    from PIL import ImageFilter
    kind, args = spr_key
    base = painting_sprite(*args) if kind == "painting" else photo_sprite(*args)
    return base.filter(ImageFilter.GaussianBlur(radius * SS)) if radius > 0 else base


def easel(c, x, y, w, h, k=1.0):
    """画架，(x, y) 为画布中心"""
    if k <= 0.01:
        return
    c.line([(x - w * 0.32, y - h * 0.62), (x - w * 0.5, y + h * 0.95)], "#8A5A3C", 12 * k)
    c.line([(x + w * 0.32, y - h * 0.62), (x + w * 0.5, y + h * 0.95)], "#8A5A3C", 12 * k)
    c.line([(x, y - h * 0.62), (x, y + h * 0.9)], "#7A4D33", 10 * k)
    c.crect(x + 8, y + 9, w + 24, h + 24, INK, r=8, line=None, s=k)
    c.crect(x, y, w + 24, h + 24, PAPER, r=8, lw=4, s=k)
    c.rect(x - w * 0.55, y + h / 2 + 10, w * 1.1, 16, "#B07A4F", r=4, lw=3)


def canvas_image(c, x, y, spr, noise=0.0, seed=1, blur=0.0, key=None):
    """在画布上贴一张图，再盖一层雪花噪点（noise 0~1）"""
    if key is not None and blur > 0.3:
        spr = blurred(key, round(min(blur, 12) / 2) * 2)
    c.blit(spr, x, y, "mm")
    if noise > 0.01:
        c.blit(noise_sprite(seed, spr.width // SS, spr.height // SS), x, y, "mm", a=noise)


def mortarboard(c, x, y, s=1.0, t=0.0):
    c.poly([(x - 60 * s, y), (x, y - 26 * s), (x + 60 * s, y), (x, y + 26 * s)], INK, lw=2.5)
    c.rect(x - 32 * s, y + 4 * s, 64 * s, 22 * s, INK, r=4 * s, line=None)
    sw = math.sin(t * 3) * 6 * s
    c.line([(x, y), (x + 44 * s, y + 8 * s), (x + 46 * s + sw, y + 40 * s)], SUN, 4)
    c.circle(x + 46 * s + sw, y + 44 * s, 6 * s, SUN, line=None)


def weather_icon(c, x, y, s=1.0, rain=False, a=1.0):
    if not rain:
        for i in range(8):
            ang = math.pi * 2 * i / 8
            c.line([(x - 10 * s + math.cos(ang) * 30 * s, y - 12 * s + math.sin(ang) * 30 * s),
                    (x - 10 * s + math.cos(ang) * 40 * s, y - 12 * s + math.sin(ang) * 40 * s)], SUN, 5 * s, a=a)
        c.circle(x - 10 * s, y - 12 * s, 24 * s, SUN, lw=3, a=a)
    cloud = "#FFFFFF" if not rain else "#AEB6CF"
    for dx, dy, r in ((-14, 8, 18), (6, 0, 22), (26, 10, 16)):
        c.circle(x + dx * s, y + dy * s, r * s, cloud, lw=3, a=a)
    for dx, dy, r in ((-14, 8, 18), (6, 0, 22), (26, 10, 16)):
        c.circle(x + dx * s, y + dy * s, r * s - 3, cloud, line=None, a=a)
    if rain:
        for k in range(3):
            c.line([(x - 12 * s + k * 16 * s, y + 30 * s), (x - 18 * s + k * 16 * s, y + 44 * s)], "#4FA8F5", 4,
                   a=a)


def map_icon(c, x, y, s=1.0):
    pts = [(x - 42 * s, y - 30 * s), (x - 14 * s, y - 38 * s), (x + 14 * s, y - 30 * s), (x + 42 * s, y - 38 * s),
           (x + 42 * s, y + 30 * s), (x + 14 * s, y + 38 * s), (x - 14 * s, y + 30 * s), (x - 42 * s, y + 38 * s)]
    c.poly(pts, "#CFF3DF", lw=3)
    c.line([(x - 14 * s, y - 38 * s), (x - 14 * s, y + 30 * s)], INK, 2.5)
    c.line([(x + 14 * s, y - 30 * s), (x + 14 * s, y + 38 * s)], INK, 2.5)
    c.line([(x - 34 * s, y + 10 * s), (x - 4 * s, y - 6 * s), (x + 24 * s, y + 12 * s)], CORAL, 3)
    c.circle(x + 24 * s, y - 6 * s, 9 * s, CORAL, lw=2.5)


def calendar_icon(c, x, y, s=1.0, num="6"):
    c.rect(x - 38 * s, y - 34 * s, 76 * s, 72 * s, PAPER, r=8 * s, lw=3)
    c.rect(x - 38 * s, y - 34 * s, 76 * s, 20 * s, CORAL, r=8 * s, lw=3)
    for dx in (-18, 18):
        c.line([(x + dx * s, y - 42 * s), (x + dx * s, y - 26 * s)], INK, 4)
    c.text(num, x, y + 12 * s, 30 * s, INK, 900)


def cake_icon(c, x, y, s=1.0):
    c.rect(x - 40 * s, y - 4 * s, 80 * s, 34 * s, "#FFE3EC", r=6 * s, lw=3)
    c.rect(x - 30 * s, y - 30 * s, 60 * s, 28 * s, "#FFF3D6", r=6 * s, lw=3)
    c.circle(x, y - 38 * s, 9 * s, CORAL, lw=2.5)
    c.line([(x - 40 * s, y + 6 * s), (x + 40 * s, y + 6 * s)], "#FF9BB0", 4, caps=False)


def calc_icon(c, x, y, s=1.0):
    c.rect(x - 32 * s, y - 40 * s, 64 * s, 80 * s, "#5A6280", r=8 * s, lw=3)
    c.rect(x - 24 * s, y - 32 * s, 48 * s, 18 * s, "#CFF3DF", r=4 * s, lw=2)
    for i in range(3):
        for j in range(3):
            c.rect(x - 22 * s + j * 16 * s, y - 6 * s + i * 14 * s, 12 * s, 10 * s, PAPER if (i + j) % 3 else SUN,
                   r=2, line=None)


def shield_icon(c, x, y, s=1.0, col=LEAF):
    pts = [(x, y - 40 * s), (x + 34 * s, y - 28 * s), (x + 30 * s, y + 10 * s), (x, y + 40 * s),
           (x - 30 * s, y + 10 * s), (x - 34 * s, y - 28 * s)]
    c.poly(pts, col, lw=3.5)
    c.line([(x - 13 * s, y), (x - 3 * s, y + 11 * s), (x + 15 * s, y - 12 * s)], "#FFFFFF", 6)


@lru_cache(maxsize=4)
def family_photo_sprite():
    w, h = 300, 210
    c = Canvas.sprite(w + 12, h + 12)
    c.rect(8, 9, w, h, INK, r=14, line=None)
    c.rect(2, 2, w, h, PAPER, r=14, lw=3.5)
    c.rect(16, 16, w - 28, h - 28, "#DDF0FF", r=8, line=None)
    people = [(60, 120, 30, "#3B2B3A", "#FFC83D"), (110, 108, 33, "#5A3E2B", "#7CC4FF"),
              (165, 112, 32, "#3B2B3A", "#FF9BB0"), (222, 106, 34, "#6B5B4B", "#2FB57E"),
              (262, 140, 22, "#3B2B3A", "#FF6F5E")]
    c.circle(196, 128, 16, "#FFE0C9", lw=2.5)
    c.chord(196, 124, 17, 17, 190, 350, "#3B2B3A")
    for x, y, r, hair, shirt in people:
        c.rect(x - r * 1.05, y + r * 0.7, r * 2.1, h - 30 - (y + r * 0.7), shirt, r=r * 0.6, lw=2.5)
        c.circle(x, y, r, "#FFE0C9", lw=2.5)
        c.chord(x, y - 3, r + 1, r + 1, 190, 350, hair)
        c.circle(x - r * 0.35, y + 2, 2.6, INK, line=None)
        c.circle(x + r * 0.35, y + 2, 2.6, INK, line=None)
    return c.im


@lru_cache(maxsize=4)
def ticket_sprite():
    from PIL import ImageFilter
    w, h = 300, 150
    c = Canvas.sprite(w + 12, h + 12)
    c.rect(8, 9, w, h, INK, r=14, line=None)
    c.rect(2, 2, w, h, "#E6F4FF", r=14, lw=3.5)
    c.circle(2, 2 + h / 2, 14, "#FFFFFF", lw=3)
    c.circle(2 + w, 2 + h / 2, 14, "#FFFFFF", lw=3)
    c.text("车票", 2 + w / 2, 34, 26, INK, 900)
    txt = text_sprite("3 号车厢", 40, INK, 900).filter(ImageFilter.GaussianBlur(3.2 * SS))
    c.blit(txt, 2 + w / 2, 96, "mm")
    return c.im
