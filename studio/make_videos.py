"""生成 AI奇遇记 的讲解视频和封面图。

  python make_videos.py                 # 生成全部视频（配音有缓存，改了哪句才重新配哪句）
  python make_videos.py s1-1 s2-3       # 只生成指定的几段
  python make_videos.py s1-1 --sheet    # 不出视频，只出一张预览拼图，检查画面用

配音用的是微软 Edge 的在线语音（需要联网），声音在下面的 VOICE 里改。
"""
import argparse
import asyncio
import hashlib
import json
import math
import os
import subprocess
import sys
import time
import wave
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import actors as A  # noqa: E402
from engine import (FPS, H, INK, PUNCT, SS, W, Canvas, Timing, appear, back, clamp, ease_io, ease_out, pop,  # noqa: E402
                    prog, rgb, text_sprite, wave as wv)

VOICE = "zh-CN-XiaoxiaoNeural"
RATE = "-4%"
SAY_AS = {"RAG": "R A G", "QKV": "Q K V", "RLHF": "R L H F"}  # 发音修正：字幕照常显示左边，配音念右边
INTRO = 2.1  # 片头标题卡时长
GAP = 0.42  # 句与句之间的停顿
OUTRO = 2.8  # 最后一句之后，知识卡停留的时间
XF = 0.28  # 镜头之间的交叉淡化
SR = 24000
CACHE = os.path.join(HERE, "cache")
NUM = "一二三四五六七八九十"


def cn(n):
    """1 → 一，12 → 十二，20 → 二十"""
    if n <= 10:
        return NUM[n - 1]
    if n < 20:
        return "十" + NUM[n - 11]
    return NUM[n // 10 - 1] + "十" + (NUM[n % 10 - 1] if n % 10 else "")


def load_stories():
    s = open(os.path.join(SITE, "data", "stories.js"), encoding="utf-8").read()
    i = s.index("window.STORIES")
    return json.JSONDecoder().raw_decode(s, s.index("[", i))[0]


def all_segments():
    out = []
    for i, st in enumerate(load_stories()):
        for j, seg in enumerate(st["segments"]):
            out.append((i, j, st, seg))
    return out


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# ---------------------------------------------------------------- 配音
def _tts_key(text):
    say = text
    for k, v in SAY_AS.items():
        say = say.replace(k, v)
    return say, hashlib.sha1(f"{VOICE}|{RATE}|{say}".encode("utf-8")).hexdigest()[:16]


async def _tts_one(text, sem):
    import edge_tts
    say, key = _tts_key(text)
    d = os.path.join(CACHE, "tts")
    os.makedirs(d, exist_ok=True)
    mp3, meta = os.path.join(d, key + ".mp3"), os.path.join(d, key + ".json")
    if os.path.exists(mp3) and os.path.exists(meta):
        return
    async with sem:
        for attempt in range(4):
            try:
                try:
                    com = edge_tts.Communicate(say, VOICE, rate=RATE, boundary="WordBoundary")
                except TypeError:
                    com = edge_tts.Communicate(say, VOICE, rate=RATE)
                words = []
                with open(mp3 + ".part", "wb") as f:
                    async for ch in com.stream():
                        if ch["type"] == "audio":
                            f.write(ch["data"])
                        elif ch["type"] == "WordBoundary":
                            words.append([ch["offset"] / 1e7, ch["duration"] / 1e7, ch["text"]])
                os.replace(mp3 + ".part", mp3)
                with open(meta, "w", encoding="utf-8") as f:
                    json.dump(words, f, ensure_ascii=False)
                print("  配音完成：", text[:24])
                return
            except Exception as e:  # 网络偶尔会断，重试
                print("  配音失败，重试：", e)
                await asyncio.sleep(2 + attempt * 3)
        raise RuntimeError("配音失败：" + text)


def tts_all(lines):
    async def run():
        sem = asyncio.Semaphore(4)
        await asyncio.gather(*[_tts_one(t, sem) for t in lines])
    asyncio.run(run())


def load_voice(text):
    _, key = _tts_key(text)
    d = os.path.join(CACHE, "tts")
    out = subprocess.run([ffmpeg(), "-v", "error", "-i", os.path.join(d, key + ".mp3"), "-f", "f32le", "-ac", "1",
                          "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(out, np.float32).copy()
    words = json.load(open(os.path.join(d, key + ".json"), encoding="utf-8"))
    idx = np.where(np.abs(x) > 0.012)[0]
    if len(idx):
        a = max(0, idx[0] - int(0.03 * SR))
        b = min(len(x), idx[-1] + int(0.09 * SR))
        x = x[a:b]
        words = [[o - a / SR, d_, w] for o, d_, w in words]
    return x, words


def chime(freqs, dur=1.1, amp=0.13, stagger=0.085):
    n = int((dur + stagger * len(freqs)) * SR)
    y = np.zeros(n, np.float32)
    for i, f in enumerate(freqs):
        st = int(i * stagger * SR)
        tt = np.arange(n - st) / SR
        env = np.exp(-tt * 5.0) * np.minimum(1, tt / 0.004)
        tone = np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt) * np.exp(-tt * 6)
        y[st:] += (tone * env).astype(np.float32)
    return amp * y / (np.abs(y).max() + 1e-6)


def prepare(seg):
    """配音、排时间、混音。返回时间表（也会存进缓存）"""
    lines = seg["narration"]
    tts_all(lines)
    clips, words = [], []
    for ln in lines:
        x, wb = load_voice(ln)
        clips.append(x)
        words.append(wb)
    starts, ends, t = [], [], INTRO
    for x in clips:
        starts.append(round(t, 3))
        t += len(x) / SR
        ends.append(round(t, 3))
        t += GAP
    total = ends[-1] + OUTRO
    audio = np.zeros(int(total * SR) + SR // 5, np.float32)
    for st, x in zip(starts, clips):
        i = int(st * SR)
        audio[i:i + len(x)] += x
    for at, fr in ((0.2, [784, 1175]), (ends[-1] + 0.22, [1047, 1319, 1568])):
        ch = chime(fr)
        i = int(at * SR)
        audio[i:i + len(ch)] += ch[:len(audio) - i]
    peak = float(np.abs(audio).max())
    if peak > 0:
        audio *= 0.9 / peak
    os.makedirs(os.path.join(CACHE, "audio"), exist_ok=True)
    wav = os.path.join(CACHE, "audio", seg["id"] + ".wav")
    with wave.open(wav, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    timing = dict(lines=lines, starts=starts, ends=ends, words=words, intro=INTRO, total=round(total, 3), wav=wav)
    with open(os.path.join(CACHE, "audio", seg["id"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(timing, f, ensure_ascii=False)
    return timing


# ---------------------------------------------------------------- 字幕
def split_sub(line, limit=17):
    parts, cur = [], ""
    for ch in line:
        cur += ch
        if ch in "，。！？；：":
            parts.append(cur)
            cur = ""
    if cur:
        parts.append(cur)
    out = []
    for p in parts:
        if out and len(out[-1]) + len(p) <= limit and len(p) <= 6:
            out[-1] += p
        elif len(p) > limit + 3:
            mid = len(p) // 2
            out += [p[:mid], p[mid:]]
        else:
            out.append(p)
    return out


def subtitle_chunks(T):
    chunks = []
    for i, line in enumerate(T.lines):
        parts = split_sub(line)
        idx = 0
        starts = []
        for p in parts:
            starts.append(T.at_char(i, idx))
            idx += sum(1 for ch in p if ch not in PUNCT)
        starts[0] = T.s[i]
        for k, p in enumerate(parts):
            end = starts[k + 1] if k + 1 < len(parts) else T.e[i] + 0.12
            text = p.rstrip("，。；：、")
            chunks.append((starts[k], end, text))
    return chunks


@lru_cache(maxsize=256)
def _sub_sprite(text):
    size = 30
    spr = text_sprite(text, size, "#FFFFFF", 700)
    w, h = spr.width / SS + 40, size * 1.25 + 18
    c = Canvas.sprite(w, h)
    c.rect(0, 0, w, h, INK, r=h / 2, line=None, a=0.86)
    c.blit(spr, w / 2, h / 2 + 1, "mm")
    return c.im


# ---------------------------------------------------------------- 一段视频
class Video:
    def __init__(self, si, sj, story, seg, timing):
        import scenes
        self.si, self.sj, self.story, self.seg = si, sj, story, seg
        self.T = Timing(timing)
        self.theme = story["theme"]
        self.accent = A.THEMES[self.theme]["accent"]
        self.shots = scenes.SCENES[seg["id"]](self.T)
        self.subs = subtitle_chunks(self.T)
        self.bg = A.background(self.theme)

    # -------------------------------------------- 片头标题卡
    def title(self, t):
        im = A.title_background(self.theme).copy()
        c = Canvas(im)
        dark = A.THEMES[self.theme]["dark"]
        A.chip(c, f"故事{cn(self.si + 1)} · {self.story['title']}", W / 2, 206, t, 0.08, size=30, fill=INK,
               color="#FFFFFF", shadow=0)
        A.chip(c, f"第 {self.sj + 1} 段", W / 2, 290, t, 0.2, size=34, fill="#FFFFFF", color=INK)
        k = pop(t, 0.32, 0.5)
        if k > 0:
            c.blit(text_sprite(self.seg["title"], 92, "#FFFFFF" if not dark else A.SUN, 900, 7, INK),
                   W / 2, 392, "mm", s=k)
        A.sparkles(c, t, W / 2, 380, spread=330, n=7, col="#FFFFFF", seed=self.si * 10 + self.sj, t0=0.5)
        rise = ease_out(prog(t, 0.25, 0.6))
        arm = 150 + 22 * math.sin(t * 9)
        A.robot(c, 1080, 900 - 150 * rise, t, eyes="happy", arm_r=arm, arm_l=20, s=1.15, shadow=False)
        return im

    # -------------------------------------------- 正片镜头
    def draw_shot(self, k, t):
        im = self.bg.copy()
        self.shots[k][1](Canvas(im), t)
        return im

    def scene(self, t):
        k = 0
        for i, (st, _) in enumerate(self.shots):
            if t >= st:
                k = i
        im = self.draw_shot(k, t)
        if k > 0:
            u = (t - self.shots[k][0]) / XF
            if u < 1:
                im = Image.blend(self.draw_shot(k - 1, t), im, ease_io(u))
        return im

    # -------------------------------------------- 叠加层
    def overlays(self, im, t, subs=True):
        c = Canvas(im)
        T = self.T
        a = appear(t, T.intro, 0.4)
        if a > 0:
            A.chip(c, f"{self.story['title']} · 第{self.sj + 1}段", 22, 22, size=19, fill="#FFFFFF", anchor="lt",
                   shadow=3, a=a, weight=800, padx=14)
        if subs:
            for st, en, text in self.subs:
                if st <= t < en:
                    c.blit(_sub_sprite(text), W / 2, 662, "mm")
                    break
        if t >= T.card:
            self.end_card(c, t)

    def end_card(self, c, t):
        T = self.T
        u = back(prog(t, T.card, 0.55), 1.4)
        dark = A.THEMES[self.theme]["dark"]
        c.rect(0, 0, W, H, INK if dark else "#FFFFFF", line=None, a=min(1.0, prog(t, T.card, 0.4)) * (0.45 if dark else 0.4))
        y0 = 560 + (1 - u) * 260
        x0, w, h = 250, 780, 150
        c.rect(x0 + 8, y0 - h / 2 + 9, w, h, INK, r=30, line=None)
        c.rect(x0, y0 - h / 2, w, h, "#FFFFFF", r=30, lw=4.5)
        c.circle(x0 + 82, y0, 46, self.accent, lw=4)
        A.idea_bulb(c, x0 + 82, y0 - 4, t, T.card + 0.15, s=0.62)
        A.chip(c, "知识点", x0 + 160, y0 - h / 2, size=22, fill=self.accent, color="#FFFFFF", anchor="lm",
               shadow=3, stroke=1.6)
        c.text(self.seg["term"], x0 + 160, y0 - 14, 46, INK, 900, anchor="lm")
        c.text(self.seg["short"], x0 + 160, y0 + 40, 30, "#55607F", 700, anchor="lm")

    # -------------------------------------------- 合成一帧
    IRIS0 = INTRO - 0.55
    IRIS1 = INTRO - 0.02

    def frame(self, t, subs=True, overlay=True):
        if t < self.IRIS0:
            im = self.title(t)
        else:
            im = self.scene(t)
            if t < self.IRIS1:
                u = ease_io((t - self.IRIS0) / (self.IRIS1 - self.IRIS0))
                r = u * 760
                mask = Image.new("L", im.size, 0)
                cx, cy = W / 2 * SS, H / 2 * SS
                ImageDraw.Draw(mask).ellipse([cx - r * SS, cy - r * SS, cx + r * SS, cy + r * SS], fill=255)
                im = Image.composite(im, self.title(t), mask)
                Canvas(im).circle(W / 2, H / 2, r, None, INK, 9)
        if overlay:
            self.overlays(im, t, subs)
        return im.reduce(SS)


# ---------------------------------------------------------------- 并行渲染
_V = None


def _init(args):
    global _V
    _V = Video(*args)


def _frame(i):
    return _V.frame(i / FPS).tobytes()


def render(si, sj, story, seg, timing, jobs):
    out = os.path.join(SITE, "videos", seg["id"] + ".mp4")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    n = int(math.ceil(timing["total"] * FPS))
    cmd = [ffmpeg(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-framerate", str(FPS), "-i", "-",
           "-i", timing["wav"], "-map", "0:v", "-map", "1:a",
           "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
           "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-tune", "animation",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
           "-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-shortest", "-movflags", "+faststart", out]
    t0 = time.time()
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(jobs, initializer=_init, initargs=((si, sj, story, seg, timing),)) as pool:
        for buf in pool.imap(_frame, range(n), chunksize=4):
            ff.stdin.write(buf)
    ff.stdin.close()
    ff.wait()
    print(f"  视频：{os.path.relpath(out, SITE)}  {n / FPS:.1f} 秒，用时 {time.time() - t0:.0f} 秒")
    return out


def poster(si, sj, story, seg, timing):
    import scenes
    v = Video(si, sj, story, seg, timing)
    t = scenes.POSTER.get(seg["id"], lambda T: T.mid(1, 0.8))(v.T)
    im = v.frame(t, subs=False, overlay=False)
    out = os.path.join(SITE, "posters", seg["id"] + ".jpg")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out, quality=84, optimize=True, progressive=True)
    return out


def sheet(si, sj, story, seg, timing, times=None, cols=4):
    v = Video(si, sj, story, seg, timing)
    T = v.T
    if not times:
        times = []
        starts = [st for st, _ in v.shots] + [T.card]
        for k in range(len(v.shots)):
            a0 = max(starts[k], INTRO)
            times.append(a0 + 0.8 * (starts[k + 1] - a0))
        times.append(T.card + 1.2)
    tiles = []
    for t in times:
        im = v.frame(t).resize((640, 360), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 90, 22], fill=(0, 0, 0))
        d.text((4, 4), f"{t:.2f}s", fill=(255, 255, 255))
        tiles.append(im)
    while len(tiles) % cols:
        tiles.append(Image.new("RGB", (640, 360), (40, 40, 40)))
    rows = len(tiles) // cols
    out = Image.new("RGB", (640 * cols, 360 * rows))
    for i, im in enumerate(tiles):
        out.paste(im, (640 * (i % cols), 360 * (i // cols)))
    path = os.path.join(CACHE, f"sheet_{seg['id']}.png")
    out.save(path)
    print("  预览：", path)
    return path


def write_media():
    """把每段视频的时长写进 data/media.js，网页用它显示时长"""
    media = {}
    for _, _, _, seg in all_segments():
        tj = os.path.join(CACHE, "audio", seg["id"] + ".json")
        if os.path.exists(tj) and os.path.exists(os.path.join(SITE, "videos", seg["id"] + ".mp4")):
            media[seg["id"]] = {"dur": json.load(open(tj, encoding="utf-8"))["total"]}
    with open(os.path.join(SITE, "data", "media.js"), "w", encoding="utf-8") as f:
        f.write("// 由 studio/make_videos.py 自动生成：每段讲解视频的时长（秒）\n")
        f.write("window.MEDIA = " + json.dumps(media, ensure_ascii=False, indent=1) + ";\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--sheet", action="store_true")
    ap.add_argument("--times", type=float, nargs="*")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    a = ap.parse_args()
    segs = [s for s in all_segments() if not a.ids or s[3]["id"] in a.ids]
    if not segs:
        sys.exit("没有找到这些段落：" + " ".join(a.ids))
    for si, sj, st, seg in segs:
        print(f"[{seg['id']}] {st['title']} · {seg['title']}")
        timing = prepare(seg)
        if a.sheet:
            sheet(si, sj, st, seg, timing, a.times)
            continue
        render(si, sj, st, seg, timing, a.jobs)
        poster(si, sj, st, seg, timing)
    if not a.sheet:
        write_media()


if __name__ == "__main__":
    main()
