# Phase 0: Test Set and Model Comparison

**Goal:** pick the speech recognition provider (decision D4) and the AI model for rewriting and translation (D5) using real measurements, not guesses. Planned length: 2 weeks.

## Status

| Step | Status |
|---|---|
| Decisions D1–D11 recorded | ✅ [DECISIONS.md](../DECISIONS.md) |
| Test sentences (45: 15 Persian, 15 English, 15 mixed) | ✅ [`eval/corpus/prompts.jsonl`](../../eval/corpus/prompts.jsonl) |
| Recording script for speakers | ✅ [RECORDING_SCRIPT.md](RECORDING_SCRIPT.md) |
| Scoring and comparison tool, with tests | ✅ [`eval/`](../../eval/README.md) |
| **Recordings from real speakers** | ⏳ Needs you (see below) |
| **API keys / GPU for providers** | ⏳ Needs you (see below) |
| Run speech recognition comparison, write up D4 | ⏳ After recordings |
| AI rewrite and translation comparison (D5) | ⏳ Next |

## What you need to do

### 1. Collect recordings (target: about 300)
- **Speakers:** at least 8. Mix of Persian accents (Tehrani plus at least two others, for example Isfahani, Mashhadi, Azeri- or Kurdish-accented) and Australian English speakers who speak Persian. Ideally include a couple of native Australian English speakers for the English set.
- **Each speaker** reads all 45 lines in [RECORDING_SCRIPT.md](RECORDING_SCRIPT.md): about 5 minutes.
- **Conditions:** record about two thirds somewhere quiet and one third with real background noise (car, café, building site).
- **Free speech:** ask each speaker for 2–3 unscripted 30-second messages (for example "Tell a colleague about today's site visit, in whatever mix of languages feels natural"). Type out exactly what they said afterwards.
- **Format:** a phone voice memo is fine. Convert to WAV, 16 kHz mono if you can (the tool accepts what the provider accepts).
- **Consent:** get written consent from each speaker that their recordings are used for testing only. Don't use anyone's private messages.

Folder layout:
```
eval/recordings/            (git-ignored: recordings stay off GitHub)
  manifest.jsonl
  spk01/fa01.wav, spk01/mx01.wav, ...
```
One manifest line per recording:
```json
{"id": "spk01-mx01", "audio": "spk01/mx01.wav", "prompt_id": "mx01", "speaker": "spk01", "accent": "tehrani", "condition": "clean"}
```

### 2. Provider access
Candidates for the comparison:
| Provider | What's needed |
|---|---|
| Whisper large-v3-turbo, self-hosted | A machine with an NVIDIA GPU (or a slow CPU run) |
| OpenAI transcription API | API key |
| 1–2 others (for example Google, Azure, Deepgram, ElevenLabs) | API keys. Each gets a small adapter in `eval/goftar_eval/providers.py`, or export their transcripts and use the `file:` provider. |

## How we decide (D4)
The provider must meet the MVP targets from the plan: English WER ≤ 8%, Persian WER ≤ 15%, English terms kept in mixed speech ≥ 90%, and fast enough for ≤ 1.5 s median end-to-end. Among those that pass, choose on mixed-speech quality first, then cost, then latency. Each provider is run with and without the glossary prompt (`--bias`).
