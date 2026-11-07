"""Speech recognition providers for the comparison.

Each provider turns one recording into text. Add a provider by writing a
class with `name` and `transcribe()` and registering it in `build_provider`.

Provider specs (the --provider flag):
  file:<results.jsonl>          precomputed transcripts, e.g. exported from a vendor console
  faster-whisper:<model>        local Whisper via faster-whisper, e.g. large-v3-turbo
  openai:<model>                OpenAI transcription API (needs OPENAI_API_KEY)
"""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol


@dataclass
class Recording:
    id: str
    audio: Optional[Path]
    reference: str
    category: str
    terms: list
    speaker: str = ""
    accent: str = ""
    condition: str = "clean"


@dataclass
class Transcript:
    text: str
    latency_ms: Optional[float] = None
    detected_language: Optional[str] = None


class Provider(Protocol):
    name: str

    def transcribe(self, rec: Recording, prompt: Optional[str]) -> Transcript: ...


class FileProvider:
    """Reads {"id", "text", "latency_ms"?} lines produced elsewhere."""

    def __init__(self, path: str):
        self.name = f"file:{Path(path).stem}"
        self._rows = {}
        with open(path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    self._rows[row["id"]] = row

    def transcribe(self, rec, prompt):
        row = self._rows.get(rec.id)
        if row is None:
            raise KeyError(f"no transcript for recording {rec.id}")
        return Transcript(row["text"], row.get("latency_ms"), row.get("language"))


class FasterWhisperProvider:
    def __init__(self, model: str = "large-v3-turbo"):
        from faster_whisper import WhisperModel  # optional dependency

        self.name = f"faster-whisper:{model}"
        self._model = WhisperModel(model, device="auto", compute_type="default")

    def transcribe(self, rec, prompt):
        start = time.perf_counter()
        # language=None lets Whisper detect it; forcing "fa" damages English terms.
        segments, info = self._model.transcribe(
            str(rec.audio), language=None, initial_prompt=prompt, vad_filter=True, beam_size=5
        )
        text = " ".join(s.text.strip() for s in segments)
        return Transcript(text, (time.perf_counter() - start) * 1000, info.language)


class OpenAIProvider:
    def __init__(self, model: str = "whisper-1"):
        from openai import OpenAI  # optional dependency

        self.name = f"openai:{model}"
        self._model = model
        self._client = OpenAI()

    def transcribe(self, rec, prompt):
        start = time.perf_counter()
        with open(rec.audio, "rb") as f:
            kwargs = {"model": self._model, "file": f}
            if prompt:
                kwargs["prompt"] = prompt
            result = self._client.audio.transcriptions.create(**kwargs)
        return Transcript(result.text, (time.perf_counter() - start) * 1000)


def build_provider(spec: str) -> Provider:
    kind, _, arg = spec.partition(":")
    if kind == "file":
        return FileProvider(arg)
    if kind == "faster-whisper":
        return FasterWhisperProvider(arg or "large-v3-turbo")
    if kind == "openai":
        return OpenAIProvider(arg or "whisper-1")
    raise ValueError(f"unknown provider '{kind}'")
