"""Local, optional audio transcription through ffmpeg and whisper.cpp."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from platform_runtime import run_tool
import tempfile
from pathlib import Path
from app_paths import bundled_tool, resource_dir


AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".flac", ".aac", ".ogg", ".opus", ".webm", ".mp4"}
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/5359861c739e955e79d9a303bcbc70fb988958b1/ggml-large-v3-turbo-q5_0.bin"
MODEL_SHA1 = "e050f7970618a659205450ad97eb95a18d69c9ee"
MODEL_NAME = "ggml-large-v3-turbo-q5_0.bin"

MIN_PARAGRAPH_MS = 12000
MAX_PARAGRAPH_MS = 30000
MAX_PARAGRAPH_CHARS = 140
LONG_PAUSE_MS = 2000
CLAUSE_MS = 7000
CLAUSE_CHARS = 12
PUNCTUATION = "，,。！？!?；;：:"
ENDING_PUNCTUATION = "。！？!?；;"
CONTINUATION_STARTS = ("的", "地", "得", "和", "与", "及", "或", "等", "为", "是", "在", "于", "对", "把", "将", "了", "着", "过")
UNIT_STARTS = ("%", "％", "元", "万", "亿", "年", "月", "日", "个", "项", "笔", "人", "次")
NEW_SENTENCE_STARTS = ("接下来", "下一步", "下面我们", "另外", "最后", "首先", "其次", "再来看")
INTERNAL_SENTENCE_CUES = ("接下来", "下一步", "下面我们", "另外", "再来看")
INTERNAL_CUE_PATTERN = re.compile("|".join(map(re.escape, INTERNAL_SENTENCE_CUES)))
SILENCE_START = re.compile(r"silence_start:\s*([\d.]+)")
SILENCE_END = re.compile(r"silence_end:\s*([\d.]+)")


def normalize_terms(raw: str) -> list[str]:
    """Validate and deduplicate a short list of domain terms."""
    if len(raw) > 500:
        raise ValueError("专业术语提示太长，请保留最重要的词语。")
    terms: list[str] = []
    for item in re.split(r"[,，、;；\n]+", raw):
        term = item.strip()
        if not term:
            continue
        if len(term) > 30 or not re.fullmatch(r"[\w（）()·.%％+\-/ ]+", term):
            raise ValueError("专业术语请用逗号或换行分隔，每项不超过 30 字。")
        if term not in terms:
            terms.append(term)
        if len(terms) > 20:
            raise ValueError("专业术语最多填写 20 项。")
    return terms


def model_path(data_dir: Path) -> Path:
    configured = os.getenv("WHISPER_MODEL_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    installed = data_dir / "models" / MODEL_NAME
    bundled = resource_dir() / "models" / MODEL_NAME
    return installed if installed.is_file() or not bundled.is_file() else bundled


def executable(name: str, override: str = "") -> str:
    value = os.getenv(override, "").strip() if override else ""
    result = value or bundled_tool(name) or shutil.which(name)
    if not result or not Path(result).is_file():
        raise RuntimeError(f"缺少本地工具 {name}，请先安装并重试。")
    return result


def probe(path: Path) -> float:
    command = [executable("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
    try:
        result = run_tool(command, capture_output=True, text=True, check=True, timeout=30)
        data = json.loads(result.stdout)
        if not any(item.get("codec_type") == "audio" for item in data.get("streams", [])):
            raise ValueError("文件中没有音频轨。")
        duration = float(data.get("format", {}).get("duration") or 0)
        if duration <= 0:
            raise ValueError("无法确定录音时长。")
        return duration
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        raise ValueError("录音损坏或格式无法解码。") from exc


def detected_silences(log: str, offset_ms: int, duration_ms: int) -> list[tuple[int, int]]:
    """Read FFmpeg silencedetect times, retaining the recording's time axis."""
    intervals: list[tuple[int, int]] = []
    begin: int | None = None
    for line in log.splitlines():
        start = SILENCE_START.search(line)
        if start:
            begin = offset_ms + round(float(start.group(1)) * 1000)
        end = SILENCE_END.search(line)
        if end and begin is not None:
            finish = offset_ms + round(float(end.group(1)) * 1000)
            if finish > begin:
                intervals.append((begin, finish))
            begin = None
    if begin is not None:
        intervals.append((begin, offset_ms + duration_ms))
    return intervals


def silence_at_boundary(silences: list[tuple[int, int]], previous_end: int, next_start: int) -> int:
    """Use actual quiet time only when it lines up with a Whisper text boundary."""
    boundary = (previous_end + next_start) // 2
    for begin, end in silences:
        if begin - 350 <= boundary <= end + 350:
            return max(0, end - begin)
        if begin > boundary + 350:
            break
    return 0


def punctuate_internal_cues(text: str) -> str:
    """Add only clear sentence transitions inside one long Whisper fragment."""
    parts: list[str] = []
    position = 0
    for match in INTERNAL_CUE_PATTERN.finditer(text):
        before = "".join(parts) + text[position:match.start()]
        clause = re.split(r"[，,。！？!?；;：:]", before)[-1]
        parts.append(text[position:match.start()])
        if len(clause) >= 8 and before[-1] not in PUNCTUATION:
            parts.append("。")
        position = match.start()
    parts.append(text[position:])
    return "".join(parts)


def merge_transcription_chunks(chunks: list[dict], silences: list[tuple[int, int]] | None = None) -> list[dict]:
    """Combine Whisper fragments with conservative text and acoustic punctuation."""
    paragraphs: list[dict] = []
    current: dict | None = None
    last_punctuation_ms = 0
    silences = silences or []

    def finish() -> None:
        nonlocal current
        if current:
            if current["text"][-1] in "，,":
                current["text"] = current["text"][:-1] + "。"
            elif current["text"][-1] not in ENDING_PUNCTUATION:
                current["text"] += "。"
            paragraphs.append(current)
            current = None

    for chunk in chunks:
        original = str(chunk["text"]).strip()
        if not original:
            continue
        value = punctuate_internal_cues(original)
        start, end = int(chunk["start_ms"]), int(chunk["end_ms"])
        acoustic_pause = silence_at_boundary(silences, current["end_ms"], start) if current else 0
        gap = max(0, start - current["end_ms"], acoustic_pause) if current else 0
        if current and (gap >= LONG_PAUSE_MS
                        or end - current["start_ms"] > MAX_PARAGRAPH_MS
                        or len(current["text"]) + len(value) > MAX_PARAGRAPH_CHARS):
            finish()
        if current is None:
            current = {"text": value, "start_ms": start, "end_ms": end,
                       "fragments": [{"text": original, "start_ms": start, "end_ms": end}]}
            last_punctuation_ms = start
        else:
            previous = current["text"]
            since_punctuation = start - last_punctuation_ms
            clause = re.split(r"[，,。！？!?；;：:]", previous)[-1]
            safe_boundary = (len(clause) >= 6 and value[0] not in PUNCTUATION
                             and not value.startswith(CONTINUATION_STARTS)
                             and not (previous[-1].isdigit() and value.startswith(UNIT_STARTS)))
            if previous[-1] not in PUNCTUATION and safe_boundary:
                if (gap >= 1200 and since_punctuation >= 6000) or (
                    since_punctuation >= 5000 and value.startswith(NEW_SENTENCE_STARTS)
                ):
                    previous += "。"
                    last_punctuation_ms = start
                elif gap >= 450 or (since_punctuation >= CLAUSE_MS and len(clause) >= CLAUSE_CHARS):
                    previous += "，"
                    last_punctuation_ms = start
            elif previous[-1] in PUNCTUATION:
                last_punctuation_ms = start
            space = " " if previous[-1].isascii() and previous[-1].isalnum() and value[0].isascii() and value[0].isalnum() else ""
            current["text"] = previous + space + value
            current["end_ms"] = end
            current["fragments"].append({"text": original, "start_ms": start, "end_ms": end})
        if value != original:
            last_punctuation_ms = end
        if end - current["start_ms"] >= MIN_PARAGRAPH_MS and re.search(r"[。！？!?；;][”’\"）)]*$", current["text"]):
            finish()
    finish()
    return paragraphs


def transcribe(path: Path, duration: float, model: Path, progress=None, cancelled=None,
               terms: list[str] | None = None) -> list[dict]:
    whisper = executable("whisper-cli", "WHISPER_CPP_BIN")
    ffmpeg = executable("ffmpeg")
    if not model.is_file():
        raise RuntimeError("尚未安装本地语音模型，请先点击“下载语音模型”。")
    chunks: list[dict] = []
    silences: list[tuple[int, int]] = []
    chunk_seconds = 600
    count = max(1, int((duration + chunk_seconds - 1) // chunk_seconds))
    with tempfile.TemporaryDirectory(prefix="onepager-audio-") as temporary:
        root = Path(temporary)
        for number in range(count):
            if cancelled and cancelled():
                raise RuntimeError("转写已取消。")
            start = number * chunk_seconds
            length = min(chunk_seconds, duration - start)
            wav = root / f"part-{number}.wav"
            output = root / f"part-{number}"
            if progress:
                progress(number, count)
            try:
                converted = run_tool([ffmpeg, "-hide_banner", "-nostats", "-nostdin", "-v", "info",
                                            "-ss", str(start), "-i", str(path), "-t", str(length),
                                            "-af", "asetpts=PTS-STARTPTS,silencedetect=noise=-38dB:d=0.45",
                                            "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)],
                                           capture_output=True, check=True, timeout=180)
                silences.extend(detected_silences(converted.stderr.decode("utf-8", errors="replace"),
                                                  start * 1000, round(length * 1000)))
                command = [whisper, "-m", str(model), "-f", str(wav), "-l", "zh", "-oj", "-of", str(output)]
                if terms:
                    command.extend(["--prompt", "，".join(terms)])
                run_tool(command,
                               capture_output=True, check=True, timeout=max(240, int(length * 8)))
                raw = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
            except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"第 {number + 1}/{count} 段转写失败，请检查音频和本地模型。") from exc
            for item in raw.get("transcription", []):
                text = str(item.get("text", "")).strip()
                offsets = item.get("offsets", {})
                if not text:
                    continue
                begin = int(offsets.get("from", 0)) + start * 1000
                end = int(offsets.get("to", 0)) + start * 1000
                if end > begin:
                    chunks.append({"text": text, "start_ms": begin, "end_ms": end})
            wav.unlink(missing_ok=True)
    if not chunks:
        raise ValueError("录音中未识别出有效文字，请检查音量或更换录音。")
    return merge_transcription_chunks(chunks, silences)
