# Speech Recognition Evaluation

Scores speech recognition providers on Persian, English and mixed speech.

## Metrics
| Metric | Meaning |
|---|---|
| WER % | Word error rate, after normalising letter forms, digits, ZWNJ and punctuation |
| CER % | Character error rate (fairer for Persian, where word boundaries vary) |
| terms kept % | Expected terms (for example "Scope of Work") present in their original script. Transliteration into Persian script counts as lost. |
| numbers kept % | Numbers from the reference that appear in the output |
| lang label % | Output's script (Persian / English / mixed) matches the sentence's category |
| latency p50/p95 ms | Time per recording, as measured from this machine |

Results are reported overall and by category, condition (clean/noisy) and accent.

## Run
Python 3.10+. The scoring has no dependencies. Install only the providers you use:
```
pip install faster-whisper   # local Whisper
pip install openai           # OpenAI API (set OPENAI_API_KEY)
```
From this directory:
```
python -m goftar_eval.bakeoff --manifest recordings/manifest.jsonl \
    --provider faster-whisper:large-v3-turbo --provider openai:whisper-1 --bias --out results/run1
```
Writes `summary.md`, `summary.csv` and one JSONL file per provider with every transcript.

Transcripts from any other vendor can be scored without writing code: save them as `{"id": "...", "text": "..."}` lines and pass `--provider file:path/to/that.jsonl`.

## Tests
```
python -m unittest discover -s tests -t .
```
