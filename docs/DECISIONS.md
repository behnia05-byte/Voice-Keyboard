# Decision Record

Decisions from §18 of the [development plan](DEVELOPMENT_PLAN.md), accepted on 2026-11-07 using the plan's recommendations.

| ID | Decision | Status |
|---|---|---|
| D1 | iOS dictation: companion-app "warm session" with background audio. The fallback (open the app for each dictation) is built at the same time. | Accepted |
| D2 | Desktop framework: **Tauri 2** (Rust core + web UI) | Accepted |
| D3 | MVP platform: **Android first**, plus an internal web test page | Accepted |
| D4 | Speech recognition provider | **Pending the Phase 0 comparison**. Expect a hosted API for the MVP and self-hosted Whisper later. |
| D5 | LLM: fast tier for Clean mode and translation, mid tier for Professional mode | Accepted in principle; provider confirmed by the Phase 0 LLM comparison |
| D6 | Hosting: **AWS ap-southeast-2 (Sydney)** | Accepted |
| D7 | History off by default, stored only on the device; sync is opt-in | Accepted |
| D8 | Latin digits in technical presets and Persian digits in casual ones; Clean mode converts to formal written Persian, with a "keep conversational" switch | Accepted |
| D9 | Free tier plus a subscription of about A$9–15/month | Accepted (pricing to be confirmed after Phase 0 cost data) |
| D10 | Working name "Goftar" | Placeholder |
| D11 | Launch in Australia first, then other diaspora markets | Accepted |
