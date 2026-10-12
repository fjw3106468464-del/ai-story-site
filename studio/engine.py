"""AI奇遇记 · 讲解视频绘图引擎。

所有绘制在 2 倍超采样的画布上进行（2560x1440），最后缩小到 1280x720，边缘自然平滑。
场景代码一律使用 1280x720 的坐标。
"""
import math
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
SS = 2
FPS = 30
INK = "#1E2746"
WHITE = "#FFFFFF"
FONT_FILE = "C:/Windows/Fonts/NotoSansSC-VF.ttf"
PUNCT = set("，。！？：；、“”‘’（）《》—…·,.!?:;\"' ")


# ---------------------------------------------------------------- 颜色 / 缓动
@lru_cache(None)
def rgb(c):
    if not isinstance(c, str):
        return tuple(int(v) for v in c[:3])
    c = c.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def rgba(c, a=1.0):
    r, g, b = rgb(c)
    return (r, g, b, int(round(255 * min(1.0, max(0.0, a)))))


def mix(c1, c2, u):
    a, b = rgb(c1), rgb(c2)
    return tuple(int(round(a[i] + (b[i] - a[i]) * u)) for i in range(3))


def clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def prog(t, t0, d):
    return clamp((t - t0) / d) if d > 0 else float(t >= t0)


def smooth(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = clamp(x)
    return x ** 3


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back(x, k=1.9):
    x = clamp(x) - 1
    return 1 + (k + 1) * x ** 3 + k * x ** 2


def pop(t, t0, d=0.4):
    """弹出：0 → 略超过 1 → 1"""
    return back(prog(t, t0, d)) if t >= t0 else 0.0


def appear(t, t0, d=0.3):
    return ease_out(prog(t, t0, d))


def lerp(a, b, u):
    return a + (b - a) * u


def lerp2(p, q, u):
    return (lerp(p[0], q[0], u), lerp(p[1], q[1], u))


def wave(t, amp=1.0, freq=0.5, ph=0.0):
    return amp * math.sin(2 * math.pi * (freq * t + ph))


def bezier(p0, p1, p2, u):
    a = lerp2(p0, p1, u)
    b = lerp2(p1, p2, u)
    return lerp2(a, b, u)


# ---------------------------------------------------------------- 字体 / 文字精灵
@lru_cache(None)
def font(px, weight=700):
    f = ImageFont.truetype(FONT_FILE, max(4, int(px)))
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f


@lru_cache(maxsize=6000)
def text_sprite(s, size, color=INK, weight=700, stroke=0.0, stroke_color=INK):
    """返回 2 倍分辨率的 RGBA 文字图（直通 alpha，无黑边）"""
    f = font(size * SS, weight)
    sw = int(round(stroke * SS))
    asc, desc = f.getmetrics()
    w = int(math.ceil(f.getlength(s))) + 2 * sw + 6
    h = asc + desc + 2 * sw + 6
    pos = (sw + 3, sw + 3)
    fill_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(fill_mask).text(pos, s, font=f, fill=255)
    if sw:
        full = Image.new("L", (w, h), 0)
        ImageDraw.Draw(full).text(pos, s, font=f, fill=255, stroke_width=sw, stroke_fill=255)
        im = Image.composite(Image.new("RGB", (w, h), rgb(color)), Image.new("RGB", (w, h), rgb(stroke_color)), fill_mask)
        im = im.convert("RGBA")
        im.putalpha(full)
    else:
        im = Image.new("RGBA", (w, h), rgb(color) + (0,))
        im.putalpha(fill_mask)
    return im


def text_width(s, size, weight=700):
    return font(size * SS, weight).getlength(s) / SS


def wrap(s, size, max_w, weight=700):
    """按宽度折行（中文逐字）"""
    lines, cur = [], ""
    for ch in s:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if text_width(cur + ch, size, weight) > max_w and cur:
            if ch in "，。！？、；：”）》":
                cur += ch
                continue
            carry = ""
            while cur and cur[-1] in "“《（‘":
                carry = cur[-1] + carry
                cur = cur[:-1]
            lines.append(cur)
            cur = carry + ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


@lru_cache(None)
def _alpha_lut(q):
    a = q / 64.0
    return [int(v * a) for v in range(256)]


# ---------------------------------------------------------------- 画布
class Canvas:
    def __init__(self, im):
        self.im = im
        self.rgba_mode = im.mode == "RGBA"
        self.d = ImageDraw.Draw(im) if self.rgba_mode else ImageDraw.Draw(im, "RGBA")

    @classmethod
    def sprite(cls, w, h):
        # 透明像素用墨色打底，缩放时边缘不会发黑
        return cls(Image.new("RGBA", (int(math.ceil(w * SS)), int(math.ceil(h * SS))), rgb(INK) + (0,)))

    def _c(self, color, a=1.0):
        if color is None:
            return None
        if self.rgba_mode:
            return rgba(color, 1.0 if a >= 1 else a)
        return rgba(color, a)

    # ------------------------------------------------ 基本图形（1x 坐标）
    def rect(self, x, y, w, h, fill=None, r=0, line=INK, lw=3, a=1.0, shadow=0, shadow_color=INK):
        if w * SS < 2 or h * SS < 2 or a <= 0:
            return
        r = min(r, w / 2, h / 2)
        if shadow:
            self.d.rounded_rectangle(
                [(x + shadow) * SS, (y + shadow) * SS, (x + shadow + w) * SS - 1, (y + shadow + h) * SS - 1],
                radius=int(r * SS), fill=self._c(shadow_color, a))
        self.d.rounded_rectangle(
            [x * SS, y * SS, (x + w) * SS - 1, (y + h) * SS - 1], radius=int(r * SS),
            fill=self._c(fill, a), outline=self._c(line, a) if (line and lw) else None,
            width=int(round(lw * SS)) if (line and lw) else 0)

    def crect(self, cx, cy, w, h, fill=None, r=0, line=INK, lw=3, a=1.0, s=1.0, shadow=0):
        if s <= 0.01:
            return
        w, h = w * s, h * s
        self.rect(cx - w / 2, cy - h / 2, w, h, fill, r * s, line, lw * min(1, s * 1.5), a, shadow * s)

    def ellipse(self, cx, cy, rx, ry, fill=None, line=INK, lw=3, a=1.0):
        if rx <= 0 or ry <= 0 or a <= 0:
            return
        self.d.ellipse([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS],
                       fill=self._c(fill, a), outline=self._c(line, a) if (line and lw) else None,
                       width=int(round(lw * SS)) if (line and lw) else 0)

    def circle(self, cx, cy, r, fill=None, line=INK, lw=3, a=1.0):
        self.ellipse(cx, cy, r, r, fill, line, lw, a)

    def poly(self, pts, fill=None, line=INK, lw=3, a=1.0):
        if a <= 0:
            return
        P = [(x * SS, y * SS) for x, y in pts]
        self.d.polygon(P, fill=self._c(fill, a))
        if line and lw:
            self.line(list(pts) + [pts[0]], line, lw, a)

    def line(self, pts, color=INK, lw=3, a=1.0, caps=True):
        if a <= 0 or len(pts) < 2:
            return
        P = [(x * SS, y * SS) for x, y in pts]
        col = self._c(color, a)
        wpx = max(1, int(round(lw * SS)))
        self.d.line(P, fill=col, width=wpx, joint="curve")
        if caps and lw >= 2:
            rr = wpx / 2
            for px, py in (P[0], P[-1]):
                self.d.ellipse([px - rr, py - rr, px + rr, py + rr], fill=col)

    def capsule(self, p0, p1, w, fill, line=INK, lw=3, a=1.0):
        if line and lw:
            self.line([p0, p1], line, w + 2 * lw, a)
        self.line([p0, p1], fill, w, a)

    def arc(self, cx, cy, rx, ry, start, end, color=INK, lw=3, a=1.0):
        self.d.arc([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], start, end,
                   fill=self._c(color, a), width=max(1, int(round(lw * SS))))

    def pie(self, cx, cy, r, start, end, fill, line=INK, lw=3, a=1.0):
        self.d.pieslice([(cx - r) * SS, (cy - r) * SS, (cx + r) * SS, (cy + r) * SS], start, end,
                        fill=self._c(fill, a), outline=self._c(line, a) if line else None,
                        width=int(round(lw * SS)) if line else 0)

    def chord(self, cx, cy, rx, ry, start, end, fill, line=None, lw=0, a=1.0):
        self.d.chord([(cx - rx) * SS, (cy - ry) * SS, (cx + rx) * SS, (cy + ry) * SS], start, end,
                     fill=self._c(fill, a), outline=self._c(line, a) if line else None,
                     width=int(round(lw * SS)) if line else 0)

    def glow(self, cx, cy, r, color, a=1.0, steps=7):
        """柔光：一圈圈半透明的同心圆（只在不透明画布上用）"""
        for i in range(steps, 0, -1):
            k = i / steps
            self.circle(cx, cy, r * (0.35 + 0.65 * k), color, line=None, a=a * 0.13 * (1.15 - k))

    # ------------------------------------------------ 精灵与文字
    def blit(self, spr, x, y, anchor="mm", s=1.0, sx=1.0, sy=1.0, a=1.0, rot=0.0):
        """把 2 倍分辨率的 RGBA 精灵贴到 (x, y)；anchor 两个字母：l/m/r + t/m/b"""
        if spr is None or a <= 0.01:
            return
        fx, fy = s * sx, s * sy
        if fx <= 0.02 or fy <= 0.02:
            return
        if abs(fx - 1) > 0.004 or abs(fy - 1) > 0.004:
            spr = spr.resize((max(1, int(round(spr.width * fx))), max(1, int(round(spr.height * fy)))),
                             Image.BICUBIC)
        if abs(rot) > 0.05:
            spr = spr.rotate(rot, resample=Image.BICUBIC, expand=True)
        w, h = spr.size
        ax = {"l": 0.0, "m": 0.5, "r": 1.0}[anchor[0]]
        ay = {"t": 0.0, "m": 0.5, "b": 1.0}[anchor[1]]
        px = int(round(x * SS - ax * w))
        py = int(round(y * SS - ay * h))
        mask = spr.getchannel("A")
        if a < 0.995:
            mask = mask.point(_alpha_lut(int(round(clamp(a) * 64))))
        if self.rgba_mode:
            layer = spr.copy()
            layer.putalpha(mask)
            x0, y0 = max(0, px), max(0, py)
            x1, y1 = min(self.im.width, px + w), min(self.im.height, py + h)
            if x1 <= x0 or y1 <= y0:
                return
            self.im.alpha_composite(layer, (x0, y0), (x0 - px, y0 - py, x1 - px, y1 - py))
        else:
            self.im.paste(spr, (px, py), mask)

    def text(self, s, x, y, size=32, color=INK, weight=700, anchor="mm", stroke=0.0, stroke_color=INK,
             a=1.0, sc=1.0, rot=0.0):
        if not s:
            return
        self.blit(text_sprite(s, size, color, weight, stroke, stroke_color), x, y, anchor, s=sc, a=a, rot=rot)

    def para(self, s, x, y, size, max_w, color=INK, weight=700, lh=1.45, align="l", a=1.0):
        """多行文字，(x, y) 为第一行左上角（align=m 时 x 为中心）"""
        for i, ln in enumerate(wrap(s, size, max_w, weight)):
            anchor = "lt" if align == "l" else "mt"
            self.text(ln, x, y + i * size * lh, size, color, weight, anchor=anchor, a=a)


# ---------------------------------------------------------------- 时间轴
class Timing:
    """配音时间表：s[i] / e[i] 是第 i 句的起止时刻（秒）"""

    def __init__(self, d):
        self.lines = d["lines"]
        self.s = d["starts"]
        self.e = d["ends"]
        self.words = d.get("words") or [[] for _ in self.lines]
        self.n = len(self.lines)
        self.intro = d["intro"]
        self.total = d["total"]
        self.card = self.e[-1] + 0.2

    def dur(self, i):
        return self.e[i] - self.s[i]

    def mid(self, i, f=0.5):
        return self.s[i] + self.dur(i) * f

    def at_char(self, i, idx):
        """第 i 句里第 idx 个（不算标点的）字开始被念出的时刻"""
        wb = self.words[i]
        if wb:
            pos = 0
            for off, dur, txt in wb:
                n = sum(1 for ch in txt if ch not in PUNCT)
                if pos + n > idx:
                    return self.s[i] + off + dur * (idx - pos) / max(1, n)
                pos += n
            return self.e[i]
        total = sum(1 for ch in self.lines[i] if ch not in PUNCT)
        return self.s[i] + self.dur(i) * idx / max(1, total)

    def word(self, i, w, after=0.0):
        """第 i 句中词语 w 开始被念出的时刻"""
        line = self.lines[i]
        k = line.find(w)
        if k < 0:
            return self.s[i] + after
        return self.at_char(i, sum(1 for ch in line[:k] if ch not in PUNCT)) + after
