"""Deterministic, script-driven stick figure video rendering."""
from __future__ import annotations
import argparse
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ACTIONS = ("idle", "walk", "wave", "jump", "run", "talk", "point", "sit")
THEMES = {
    "paper": ("#f6f2e9", "#252833", "#cbc3b3"),
    "night": ("#17223a", "#f8fafc", "#526582"),
    "studio": ("#e6eef8", "#182b48", "#a1b4ce"),
}

def number(value, low, high, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
        raise ValueError(f"{name} must be a number between {low} and {high}")
    return value

def validate(data):
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list) or not data["scenes"]:
        raise ValueError("A nonempty scenes array is required")
    result = []
    for i, raw in enumerate(data["scenes"]):
        if not isinstance(raw, dict):
            raise ValueError(f"Scene {i+1} must be an object")
        scene = dict(raw)
        scene["seconds"] = number(scene.get("seconds"), .2, 60, "seconds")
        scene.setdefault("caption", "")
        if not isinstance(scene["caption"], str) or len(scene["caption"]) > 240:
            raise ValueError("caption must be a string of at most 240 characters")
        scene.setdefault("theme", "paper")
        if scene["theme"] not in THEMES:
            raise ValueError("unknown theme")
        scene.setdefault("actors", [{"action": scene.get("action", "idle"), "x": .5}])
        if not isinstance(scene["actors"], list) or not 1 <= len(scene["actors"]) <= 6:
            raise ValueError("Each scene requires one to six actors")
        actors = []
        for raw_actor in scene["actors"]:
            if not isinstance(raw_actor, dict):
                raise ValueError("Actor must be an object")
            actor = dict(raw_actor)
            actor.setdefault("action", "idle")
            if actor["action"] not in ACTIONS:
                raise ValueError("unknown actor action")
            actor["x"] = number(actor.get("x", .5), .08, .92, "actor x")
            actor["scale"] = number(actor.get("scale", 1), .4, 1.6, "scale")
            actor.setdefault("facing", 1)
            if actor["facing"] not in (-1, 1):
                raise ValueError("facing must be -1 or 1")
            actors.append(actor)
        scene["actors"] = actors
        result.append(scene)
    if sum(s["seconds"] for s in result) > 600:
        raise ValueError("Total duration must not exceed 600 seconds")
    return result

def load_scene(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8")))

def timeline(scenes, fps):
    """Return scene index, starting frame and exclusive ending frame."""
    start = 0
    result = []
    for i, scene in enumerate(scenes):
        end = start + max(1, round(scene["seconds"] * fps))
        result.append((i, start, end))
        start = end
    return result

def draw_actor(draw, actor, t, duration, width, floor, ink):
    u = width / 360 * actor["scale"]
    action = actor["action"]
    direction = actor["facing"]
    phase = math.sin(math.tau * t * (2.6 if action == "run" else 1.5))
    x = width * actor["x"]
    if action in ("walk", "run"):
        x += direction * width * .12 * math.sin(math.pi * t / duration)
    y = floor - 75 * u
    if action == "jump":
        y -= abs(phase) * 38 * u
    if action == "sit":
        y += 30 * u
    def p(dx, dy):
        return (x + dx * u * direction, y + dy * u)
    def line(*points):
        draw.line([p(*q) for q in points], fill=ink, width=max(2, round(4*u)), joint="curve")
    a, b = p(-17, -78), p(17, -44)
    draw.ellipse((min(a[0], b[0]), a[1], max(a[0], b[0]), b[1]), outline=ink, width=max(2, round(4*u)))
    line((0,-44),(0,0))
    swing = phase * (29 if action == "run" else 20) if action in ("walk","run") else 0
    if action == "sit":
        line((0,0),(-20,12),(-19,45))
        line((0,0),(20,12),(19,45))
    else:
        line((0,0),(-13+swing,37),(-20+swing,75))
        line((0,0),(13-swing,37),(20-swing,75))
    line((0,-31),(-24,-12),(-30-swing,12))
    if action == "wave":
        line((0,-31),(25,-20),(34+8*phase,-64))
    elif action == "point":
        line((0,-31),(27,-31),(52,-31))
    elif action == "talk":
        line((0,-31),(25,-17),(40,-23+phase*11))
    else:
        line((0,-31),(24,-12),(30+swing,12))

def wrap_text(draw, text, font, limit):
    lines = []
    for paragraph in text.splitlines():
        current = ""
        for word in paragraph.split():
            trial = (current + " " + word).strip()
            if current and draw.textlength(trial, font=font) > limit:
                lines.append(current)
                current = ""
            if draw.textlength(word, font=font) > limit:
                for char in word:
                    if current and draw.textlength(current+char,font=font)>limit:
                        lines.append(current)
                        current=""
                    current += char
            else:
                current = (current + " " + word).strip()
        lines.append(current)
    return "\n".join(lines)

def frame(scene, t, width, height):
    bg, ink, ground = THEMES[scene["theme"]]
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    floor = height * .77
    draw.line((width*.06, floor, width*.94, floor), fill=ground, width=max(1,width//180))
    for actor in scene["actors"]:
        draw_actor(draw, actor, t, scene["seconds"], width, floor, ink)
    if scene["caption"]:
        font = ImageFont.load_default(size=max(12,width//18))
        caption = wrap_text(draw, scene["caption"], font, width*.84)
        draw.multiline_text((width/2,height*.11),caption,font=font,fill=ink,anchor="mt",align="center",spacing=max(2,width//90))
    return image

def timestamp(frame_number, fps):
    ms = round(frame_number * 1000 / fps)
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"

def subtitles(scenes, fps):
    blocks = []
    for i, start, end in timeline(scenes, fps):
        if scenes[i]["caption"]:
            blocks.append(f"{len(blocks)+1}\n{timestamp(start,fps)} --> {timestamp(end,fps)}\n{scenes[i]['caption']}\n")
    return "\n".join(blocks)

def render(scenes, output, width=720, height=1280, fps=24, audio=None):
    output = Path(output)
    if output.suffix.lower() != ".mp4":
        raise ValueError("Output must end in .mp4")
    if not all(isinstance(n,int) and not isinstance(n,bool) for n in (width,height,fps)) or not (100<=width<=2160 and 100<=height<=3840 and width%2==height%2==0 and 1<=fps<=60):
        raise ValueError("Use even dimensions within 100x100 to 2160x3840 and FPS 1-60")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("FFmpeg with libx264 is required on PATH")
    if audio is not None and not Path(audio).is_file():
        raise ValueError("Audio file not found")
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(suffix=".mp4", dir=output.parent)
    os.close(fd)
    temp = Path(name)
    cmd = ["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s",f"{width}x{height}","-r",str(fps),"-i","-"]
    if audio:
        cmd += ["-i",str(audio),"-map","0:v:0","-map","1:a:0","-af","apad","-shortest","-c:a","aac"]
    else:
        cmd += ["-an"]
    cmd += ["-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(temp)]
    try:
        with subprocess.Popen(cmd,stdin=subprocess.PIPE) as proc:
            try:
                for i, start, end in timeline(scenes,fps):
                    for n in range(end-start):
                        proc.stdin.write(frame(scenes[i],n/fps,width,height).tobytes())
            finally:
                proc.stdin.close()
            if proc.wait():
                raise RuntimeError("FFmpeg failed")
        os.replace(temp, output)
    finally:
        temp.unlink(missing_ok=True)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command",required=True)
    check = sub.add_parser("validate")
    check.add_argument("scene",type=Path)
    for name in ("render","batch"):
        p = sub.add_parser(name)
        p.add_argument("source",type=Path)
        p.add_argument("output",type=Path)
        p.add_argument("--width",type=int,default=720)
        p.add_argument("--height",type=int,default=1280)
        p.add_argument("--fps",type=int,default=24)
        p.add_argument("--srt",action="store_true")
        if name=="render":
            p.add_argument("--audio",type=Path)
    args = parser.parse_args(argv)
    if args.command=="validate":
        scenes=load_scene(args.scene)
        print(f"Valid: {len(scenes)} scenes, {sum(s['seconds'] for s in scenes):.2f}s")
        return
    jobs = [(args.source,args.output)] if args.command=="render" else [(p,args.output/(p.stem+".mp4")) for p in sorted(args.source.glob("*.json"))]
    if not jobs:
        parser.error("No JSON scenes found")
    for source, output in jobs:
        scenes=load_scene(source)
        render(scenes,output,args.width,args.height,args.fps,getattr(args,"audio",None))
        if args.srt:
            output.with_suffix(".srt").write_text(subtitles(scenes,args.fps),encoding="utf-8")
        print(output)

if __name__=="__main__":
    main()
