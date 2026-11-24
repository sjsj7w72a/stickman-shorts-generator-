# Stickman Shorts Generator

An early-stage MIT-licensed Python animation engine for turning structured story scripts into vertical MP4 videos locally. No paid API or external account is required.

## Features

- Eight procedural actions: idle, walk, wave, jump, run, talk, point and sit.
- Up to six actors per scene, configurable positions, scales and facing.
- Three visual themes, timed captions, SRT export and optional local audio.
- Deterministic frames, batch rendering and configurable resolution/FPS.
- Input validation, temporary output files and a reusable Python API.

## Install

Requires Python 3.10+ and FFmpeg with libx264 on PATH.

```sh
python -m pip install -r requirements.txt
python stickman.py validate examples/demo.json
python stickman.py render examples/demo.json output.mp4 --srt
python stickman.py batch examples output --srt
```

Default output is 720 × 1280 at 24 FPS. For 1080p use `--width 1080 --height 1920 --fps 30`. Add `--audio narration.wav` to the render command to include local audio. Short audio is padded with silence and long audio is trimmed.

## Script format

```json
{"scenes":[{"seconds":2,"caption":"Hello!","theme":"paper","actors":[{"action":"wave","x":0.3},{"action":"talk","x":0.7,"facing":-1}]}]}
```

Each scene lasts 0.2–60 seconds; total duration is capped at 600 seconds. Actor positions are normalized horizontal coordinates; scale ranges from 0.4 to 1.6. Themes: paper, night, studio. Captions are limited to 240 characters; complex-script typography is not yet supported.

## Extend the engine

The public Python functions `validate`, `load_scene`, `timeline`, `frame`, `subtitles` and `render` allow integration into other applications. To add an action, extend ACTIONS and draw_actor, then add a motion test. To add a theme, extend THEMES.

## Tests

```sh
python -m unittest discover -s tests -v
```

## Status and roadmap

New experimental project; adoption and downstream usage have not been measured. Current visuals are procedural 2D figures, not AI-generated cinematic animation. Planned improvements include richer backgrounds, keyframes, localization, voiceover timing and an interactive storyboard editor. Contributions welcome; see CONTRIBUTING.md.

MIT license.
