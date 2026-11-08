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
| AI rewrite and translation test cases (22) and comparison tool | ✅ [`eval/corpus/llm_cases.jsonl`](../../eval/corpus/llm_cases.jsonl), see [AI writing comparison](#ai-writing-comparison-d5) |
| **Anthropic API key** for the AI writing comparison | ⏳ Needs you |
| Run AI writing comparison, rate outputs, write up D5 | ⏳ After key |

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

## AI writing comparison (D5)

Compares models on the Clean, Professional and Translate tasks using 22 test cases (dictated-style input with fillers, self-corrections, negation, numbers, mixed terms, and one dictation that looks like an instruction).

**Automatic checks** run on every output (`eval/goftar_eval/faithfulness.py`, the same checks planned for the product):
| Check | Fails when |
|---|---|
| Numbers | a number is dropped or a new one appears (Persian and Latin digits count as the same) |
| Terms | a name or "keep as written" term is missing or transliterated |
| Negation | the input says something won't happen and the output doesn't (or the reverse) |
| Language | the output is not in the requested language |
| Length | the output is much longer than the input (likely invented content) |

The negation check is a word-list heuristic: it flags outputs for review and has known false alarms, for example «نه» used as a self-correction ("9, no, 10").

**Human rating:** each run writes a blind `rating_sheet.csv` (models shown as A, B, ...). A bilingual reviewer scores meaning, fluency and tone from 1 to 5 and marks critical errors. `rating_key.json` reveals which model is which after rating.

**Models to compare first:** Claude Haiku 5.5 (fast tier) and Claude Sonnet 5.5 (mid tier), each at low effort. Others can be added by exporting their outputs and using `file:`.
```
cd eval
pip install anthropic          # needs ANTHROPIC_API_KEY
python -m goftar_eval.rewrite_bakeoff \
  --model anthropic:claude-haiku-5-5@low --model anthropic:claude-sonnet-5-5@low \
  --out results/rewrite1
```
One run of 22 cases on both models costs well under A$1.

**How we decide (D5):** the fast tier is used for Clean and Translate if it has no critical errors in human rating, ≥ 95% automatic pass rate, and a median latency of 1 s or less. Professional mode uses whichever tier scores higher on human rating, with no critical errors.
