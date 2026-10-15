"""Prepare a Windows-friendly painted-animation music-video project."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


TIME_RE = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{1,2}(?:\.\d+)?)$")
LRC_TIME_RE = re.compile(r"\[(\d+):(\d{1,2}(?:\.\d+)?)\]")
OFFSET_RE = re.compile(r"^\[offset\s*:\s*([+-]?\d+(?:\.\d+)?)\]\s*$", re.I)
JSON_METADATA_RE = re.compile(r"^\s*\{.*\}\s*$")


def parse_time(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("time must be a non-negative number or M:SS string")
    if isinstance(value, (int, float)):
        result = float(value)
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("time cannot be empty")
        try:
            result = float(text)
        except ValueError:
            match = TIME_RE.fullmatch(text)
            if not match:
                raise ValueError(f"invalid time: {value}") from None
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2))
            seconds = float(match.group(3))
            if minutes >= 60 or seconds >= 60:
                raise ValueError(f"invalid time: {value}")
            result = hours * 3600 + minutes * 60 + seconds
    else:
        raise ValueError("time must be a non-negative number or M:SS string")
    if not math.isfinite(result) or result < 0:
        raise ValueError(f"invalid time: {value}")
    return result


def parse_lrc(text: str) -> list[dict[str, Any]]:
    """Parse ordinary LRC, JSON metadata, BOM, offset and multi-tag lines."""
    text = text.lstrip("\ufeff")
    offset_ms = 0.0
    rows: list[dict[str, Any]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        offset_match = OFFSET_RE.match(line)
        if offset_match:
            offset_ms = float(offset_match.group(1))
            continue
        if JSON_METADATA_RE.match(line):
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                value = None
            if isinstance(value, dict) and ("t" in value or "c" in value or "tx" in value):
                continue
        tags = list(LRC_TIME_RE.finditer(line))
        if not tags:
            continue
        lyric = line[tags[-1].end():].strip()
        for tag in tags:
            minutes = int(tag.group(1))
            seconds = float(tag.group(2))
            rows.append({"time": minutes * 60 + seconds, "text": lyric})
    for row in rows:
        row["time"] += offset_ms / 1000.0
    rows.sort(key=lambda row: (row["time"], row["text"]))
    return rows


def clip_lyrics(
    rows: Iterable[dict[str, Any]],
    start: float,
    end: float,
    source_duration: float | None = None,
) -> list[dict[str, Any]]:
    """Convert source-time lyric events to clip-relative display intervals."""
    start = float(start)
    end = float(end)
    if end <= start:
        raise ValueError("end must be greater than start")
    events: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: float(item["time"])):
        timestamp = float(row["time"])
        text = str(row.get("text", "")).strip()
        if events and abs(events[-1]["time"] - timestamp) < 1e-7:
            if text:
                events[-1]["text"] = (
                    f"{events[-1]['text']} / {text}" if events[-1]["text"] else text
                )
        else:
            events.append({"time": timestamp, "text": text})
    if not events:
        return []
    clip_duration = end - start
    if source_duration is not None:
        clip_duration = min(clip_duration, max(0.0, float(source_duration) - start))
    if clip_duration <= 0:
        return []
    carry_index = None
    for index, event in enumerate(events):
        if event["time"] < start and event["text"]:
            carry_index = index
        elif event["time"] >= start:
            break
    selected: list[dict[str, Any]] = []
    begin_index = carry_index if carry_index is not None else 0
    for index in range(begin_index, len(events)):
        event = events[index]
        if event["time"] >= end:
            break
        next_time = events[index + 1]["time"] if index + 1 < len(events) else end
        line_start = event["time"] - start
        line_end = next_time - start
        display_start = max(0.0, line_start)
        display_end = min(clip_duration, line_end)
        if not event["text"] or display_end <= display_start:
            continue
        selected.append(
            {
                "start": round(display_start, 6),
                "end": round(display_end, 6),
                "line_start": round(line_start, 6),
                "line_end": round(line_end, 6),
                "text": event["text"],
            }
        )
    return selected


def clip_beat_offset(clip_start: float, bpm: float, source_beat: float) -> float:
    period = 60.0 / float(bpm)
    if period <= 0:
        raise ValueError("bpm must be positive")
    return (float(source_beat) - float(clip_start)) % period


def _path(value: Any, base_dir: Path) -> Path:
    if value is None or str(value).strip() == "":
        raise ValueError("missing path")
    candidate = Path(str(value).strip())
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate.expanduser().resolve()


def _default_output(request: dict[str, Any], base_dir: Path, start: float, end: float) -> Path:
    stem = Path(str(request["audio"])).stem
    root = base_dir / "outputs" / "music-mv"
    candidate = root / f"{stem}-{int(start):04d}-{int(end):04d}"
    index = 2
    while candidate.exists():
        candidate = root / f"{stem}-{int(start):04d}-{int(end):04d}-{index}"
        index += 1
    return candidate


def validate_request(request: dict[str, Any], base_dir: Path | None = None) -> dict[str, Any]:
    base_dir = (base_dir or Path.cwd()).resolve()
    missing = [key for key in ("image", "audio", "lyrics") if not request.get(key)]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))
    image = _path(request["image"], base_dir)
    audio = _path(request["audio"], base_dir)
    lyrics = _path(request["lyrics"], base_dir)
    for label, path in (("image", image), ("audio", audio), ("lyrics", lyrics)):
        if not path.is_file():
            raise ValueError(f"{label} file does not exist: {path}")
    start = parse_time(request.get("start"))
    end = parse_time(request.get("end"))
    if end <= start:
        raise ValueError("end must be greater than start")
    style = str(request.get("style", "")).strip()
    if not style:
        raise ValueError("style is required")
    output = _path(request["output"], base_dir) if request.get("output") else _default_output(request, base_dir, start, end)
    if output.exists():
        raise FileExistsError(f"output project already exists: {output}")
    width = int(request.get("width", 1920))
    height = int(request.get("height", 1080))
    fps = int(request.get("fps", 24))
    if width <= 0 or height <= 0 or fps <= 0:
        raise ValueError("width, height and fps must be positive")
    if (width, height) != (1920, 1080):
        raise ValueError("this template supports 1920x1080; adapt the compositor before changing dimensions")
    if request.get("bpm") is not None and (not math.isfinite(float(request["bpm"])) or float(request["bpm"]) <= 0):
        raise ValueError("bpm must be positive and finite")
    return {
        "image": image,
        "audio": audio,
        "lyrics": lyrics,
        "start": start,
        "end": end,
        "duration": end - start,
        "style": style,
        "output": output,
        "width": width,
        "height": height,
        "fps": fps,
        "role_mode": str(request.get("role_mode", "both")),
        "bpm": float(request["bpm"]) if request.get("bpm") is not None else None,
        "source_beat": float(request["source_beat"]) if request.get("source_beat") is not None else None,
    }


def _run(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    skill_dir = Path(__file__).resolve().parents[1]
    deps = [skill_dir / ".deps"]
    env["PYTHONPATH"] = os.pathsep.join([str(path) for path in deps if path.is_dir()] + ([env["PYTHONPATH"]] if env.get("PYTHONPATH") else []))
    if cwd:
        cache = cwd / ".cache"
        cache.mkdir(parents=True, exist_ok=True)
        env.update(TEMP=str(cache), TMP=str(cache), npm_config_cache=str(cache / "npm"))
    return subprocess.run(command, cwd=str(cwd) if cwd else None, env=env, check=True, text=True, capture_output=True)


def probe_duration(audio: Path) -> float:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio),
        ]
    )
    return float(result.stdout.strip())


def _detect_bpm(config: dict[str, Any], skill_dir: Path) -> tuple[float | None, float | None, str]:
    if config["bpm"]:
        bpm = float(config["bpm"])
        source_beat = config["source_beat"]
        return bpm, (
            clip_beat_offset(config["start"], bpm, source_beat) if source_beat is not None else 0.0
        ), "provided"
    beat_grid = skill_dir / "scripts" / "beat_grid.py"
    if not beat_grid.is_file():
        return None, None, "beat_grid.py not found"
    try:
        result = _run(
            [
                sys.executable,
                str(beat_grid),
                str(config["audio"]),
                f"--from={config['start']}",
                f"--to={config['end']}",
            ]
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return None, None, f"beat detection failed: {exc}"
    bpm_match = re.search(r"\bbpm\s+([0-9]+(?:\.[0-9]+)?)", result.stdout, re.I)
    beat_match = re.search(r"\bbeats?\s+at\s+([0-9]+(?:\.[0-9]+)?)\s*s", result.stdout, re.I)
    if not bpm_match:
        return None, None, "beat detection returned no BPM"
    bpm = float(bpm_match.group(1))
    source_beat = float(beat_match.group(1)) if beat_match else config["start"]
    return bpm, clip_beat_offset(config["start"], bpm, source_beat), "beat_grid.py"


def _render_karaoke(template_file: Path, rows: list[dict[str, Any]]) -> str:
    original = template_file.read_text(encoding="utf-8")
    marker = "const LY = ["
    if marker not in original:
        return original
    suffix = original.split(marker, 1)[1].split("];", 1)[1]
    lyrics = [[row["line_start"], row["end"], row["text"], {"sing": row["line_end"] - row["line_start"]}] for row in rows]
    table = json.dumps(lyrics, ensure_ascii=False, indent=2)
    return "// Generated from the requested LRC clip.\nconst LY = " + table + ";" + suffix


def _extract_audio(config: dict[str, Any], output_audio: Path) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(config["start"]),
            "-t",
            str(config["duration"]),
            "-i",
            str(config["audio"]),
            "-vn",
            "-af",
            "asetpts=PTS-STARTPTS",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(output_audio),
        ]
    )


def prepare_project(request_file: Path, install: bool = False) -> dict[str, Any]:
    request = json.loads(request_file.read_text(encoding="utf-8-sig"))
    config = validate_request(request, request_file.parent)
    output = config["output"]
    skill_dir = Path(__file__).resolve().parents[1]
    template = skill_dir / "assets" / "painted-animation" / "template"
    if not template.is_dir():
        raise FileNotFoundError(f"template not found: {template}")
    source_duration = probe_duration(config["audio"])
    if config["end"] > source_duration + 1e-6:
        raise ValueError(f"clip end {config['end']} exceeds audio duration {source_duration:.3f}")
    rows = parse_lrc(config["lyrics"].read_text(encoding="utf-8-sig"))
    clipped = clip_lyrics(rows, config["start"], config["end"], source_duration)
    if not rows:
        raise ValueError("LRC contains no timed lyric lines")
    if not clipped:
        raise ValueError("LRC has no visible lyrics in the requested interval")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(template, output, dirs_exist_ok=True)
    for directory in ("assets", "out", "analysis", ".cache"):
        (output / directory).mkdir(parents=True, exist_ok=True)
    studio_file = output / "studio.html"
    studio = studio_file.read_text(encoding="utf-8")
    studio = studio.replace('<script src="src/scenes/demo.js"></script>', '<!-- Add the authored scene scripts here. -->')
    studio = studio.replace('<script src="src/timeline.js"></script>', '<script src="src/timeline.js"></script>\n<script src="src/karaoke.js"></script>')
    studio_file.write_text(studio, encoding="utf-8")
    shutil.copy2(config["image"], output / "assets" / config["image"].name)
    clip_audio = output / "assets" / "clip.m4a"
    _extract_audio(config, clip_audio)
    bpm, beat_offset, bpm_source = _detect_bpm(config, skill_dir)
    karaoke_file = output / "src" / "karaoke.js"
    karaoke_file.write_text(_render_karaoke(template / "src" / "karaoke.js", clipped), encoding="utf-8")
    project_js = (
        "const PROJECT = "
        + json.dumps(
            {
                "duration": config["duration"],
                "bpm": bpm,
                "offset": beat_offset or 0.0,
                "audio": "assets/clip.m4a",
                "width": config["width"],
                "height": config["height"],
                "fps": config["fps"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + ";\n"
    )
    (output / "src" / "config.js").write_text(project_js, encoding="utf-8")
    task = {
        "version": 1,
        "project": str(output),
        "image": str(config["image"]),
        "audio_source": str(config["audio"]),
        "audio_clip": str(clip_audio),
        "lyrics": str(config["lyrics"]),
        "start": config["start"],
        "end": config["end"],
        "duration": config["duration"],
        "style": config["style"],
        "role_mode": config["role_mode"],
        "bpm": bpm,
        "beat_offset": beat_offset,
        "bpm_source": bpm_source,
        "width": config["width"],
        "height": config["height"],
        "fps": config["fps"],
        "created_by": "music-mv",
    }
    (output / "mv-task.json").write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "analysis" / "lyrics.json").write_text(json.dumps(clipped, ensure_ascii=False, indent=2), encoding="utf-8")
    storyboard = f"""# Music MV storyboard

- Style: {config['style']}
- Cast: {config['role_mode']}
- Source interval: {config['start']:.3f}s–{config['end']:.3f}s
- Clip duration: {config['duration']:.3f}s
- BPM: {bpm if bpm is not None else 'not detected'}

Use this file as the shot-planning contract before rendering. Keep the supplied role image as the cast reference and make every shot follow the selected painted-animation style.
"""
    (output / "STORYBOARD.md").write_text(storyboard, encoding="utf-8")
    if install:
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            raise FileNotFoundError("npm.cmd was not found; install Node.js before using --install")
        _run([npm, "install", "--no-audit", "--no-fund"], cwd=output)
    return task


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--install", action="store_true")
    args = parser.parse_args(argv)
    try:
        task = prepare_project(args.request.resolve(), install=args.install)
    except Exception as exc:
        print(f"music-mv preparation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(task, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
