# Goftar: Persian–English AI Voice Typing & Smart Keyboard
## Development Plan (for review before implementation)

> **Working name:** *Goftar* (گفتار, "speech"). This is a placeholder brand and can be changed.
> **Status:** Draft for architecture and scope review. **No implementation has started.**
> **Date:** 2026-11-07

### Labels used in this document
- **[REQ]** is a confirmed requirement from the brief.
- **[ASSUMPTION]** is a decision made here that needs your sign-off.
- **[LIMIT]** is a technical or platform limitation.
- **[DECISION]** is a critical decision you need to review (collected in §18).

---

## 1. Product Requirements Document (PRD)

### 1.1 Problem
Persian speakers who work in English-speaking settings (for example, Iranian-Australian engineers, contractors and professionals) switch between Persian and English all day. Current dictation tools have three gaps:
1. They transcribe mixed Persian and English poorly. Most tools lock to one language per session.
2. They return raw transcripts, not clean text ready to send.
3. They can't translate and polish in one step, inside whatever app the user is working in.

### 1.2 Vision
Speak naturally in Persian, English or both, and get accurate, cleaned-up, professional or translated text directly in the text field you're using, on a phone or a computer.

### 1.3 Goals and success metrics
| Goal | Metric | Target at MVP / v1 |
|---|---|---|
| Accurate transcription | English WER (AU accent) | ≤ 8% / ≤ 6% |
| | Persian WER | ≤ 15% / ≤ 10% |
| | Mixed-language term retention (English terms kept in Latin script) | ≥ 90% / ≥ 95% |
| Fast | Time from end of speech to final text, p50 / p95, 15-second utterance | ≤ 1.5 s / ≤ 3.0 s |
| Faithful | Meaning-preservation violations (numbers, names, negation changed) | < 1% of samples / < 0.3% |
| Useful | Weekly dictation sessions per active user | ≥ 10 |
| Liked | Satisfaction (CSAT) after dictation | ≥ 4.2 / 5 |

### 1.4 Out of scope
- Languages other than Persian and English **[REQ]**.
- Persian dialects beyond standard Tehrani and common colloquial forms (Dari and Tajik aren't targeted) **[ASSUMPTION]**.
- Real-time conversation or meeting translation (live interpreter mode).
- Voice commands that control apps ("send this email") beyond basic editing commands.
- Text-to-speech.

### 1.5 Non-functional requirements
- Privacy by default: audio is not kept after processing **[REQ]**.
- Encryption in transit (TLS 1.3) and at rest **[REQ]**.
- Availability: backend 99.5% at MVP, 99.9% at v1.
- Correct right-to-left (RTL) and left-to-right (LTR) handling, including bidirectional (bidi) mixed lines **[REQ]**.
- Accessibility: WCAG 2.1 AA in the companion apps; VoiceOver and TalkBack support.

---

## 2. Target users and use cases

### 2.1 Personas
| Persona | Description | Main needs |
|---|---|---|
| **Reza, site engineer** (primary) | Iranian-Australian civil engineer in Sydney. Speaks Persian with colleagues and writes English reports. | Mixed-language dictation, construction vocabulary, Professional mode, Persian-to-English translation for site reports |
| **Maryam, small business owner** | Runs a Melbourne business. Writes to customers in English and to family and suppliers in Persian. | WhatsApp and Telegram keyboard, Clean mode, quick translation |
| **Ali, student or new migrant** | English is a second language. | Speaks Persian and gets polished English emails; learns from the output |
| **Sara, office professional** | Uses Outlook, Teams and Word all day. | Desktop global shortcut, Professional email preset, custom glossary |

### 2.2 Key use cases
1. **UC1:** Dictate a Persian WhatsApp message (Clean mode, Persian output).
2. **UC2:** Dictate in Persian and send a professional English email (translate + Professional).
3. **UC3:** Dictate mixed speech ("این Scope of Work رو برای Contractor آماده کن") and keep the English terms.
4. **UC4:** Dictate a site report in English with an Australian accent, using the Construction preset.
5. **UC5:** Select existing typed text, then translate or rewrite it from the keyboard.
6. **UC6:** On desktop, press a hotkey in Outlook, speak, and have the text appear at the cursor.
7. **UC7:** Add custom terms (project names, suppliers, standards such as "AS 3600").

---

## 3. Feature specifications

### 3.1 Speech-to-text (STT) **[REQ]**
- Inputs: 16 kHz mono audio, Opus-encoded for upload.
- Automatic language identification for each segment: `fa`, `en` or `mixed`.
- Code-switching inside a sentence. English words stay in Latin script inside Persian text by default. Optional setting: transliterate them to Persian script.
- Automatic punctuation and paragraphing. Persian punctuation (، ؛ ؟ « ») when the output is Persian.
- Numbers: keep the user's spoken form. Setting for digit style: Persian digits (۱۲۳) or Latin digits (123) in Persian text. Default is Latin digits for technical presets and Persian digits for casual ones **[ASSUMPTION]**.
- Vocabulary biasing from the user's dictionary (prompt biasing plus post-correction).
- Persian normalisation: use the zero-width non-joiner (ZWNJ, نیم‌فاصله) correctly, unify Arabic and Persian forms of ی/ي and ک/ك.
- Live preview: show partial text while speaking, where the platform and latency allow.

### 3.2 Writing modes **[REQ]**
| Mode | Behaviour | Rules |
|---|---|---|
| **Verbatim** | Raw transcript plus punctuation and normalisation only. No LLM rewrite. | Words exactly as spoken |
| **Clean** | Removes fillers (um, اِ، خب، یعنی used as filler), repetitions and false starts. Fixes grammar. Converts colloquial Persian to standard written Persian, for example «رو» → «را» and «میخوام» → «می‌خواهم» (configurable: "keep conversational tone"). | Keep meaning and register |
| **Professional** | Rewrites for email, report or formal use. Applies the preset's structure (greeting, paragraphs, bullet points). | No new facts |

**Faithfulness guardrails (all modes) [REQ]:**
- Hard constraint in the prompt: no new facts, numbers, dates, names or commitments.
- Automatic check after generation: extract numbers, dates, currency, proper nouns and negations from the source and the output, and compare them. On a mismatch, retry once at lower temperature. If it still fails, fall back to Clean mode and show "We kept your original wording" in the UI.
- The original transcript is always one tap away ("Show original").

### 3.3 Translation **[REQ]**
- Directions: fa→en and en→fa, for speech and for written text.
- Output language selector: **Auto (same as spoken)**, **English** or **Persian**.
- Can combine with modes. Pipeline: translate and rewrite in one LLM call, then the same faithfulness check.
- The glossary is applied: user terms can be "do not translate" or "translate as X".
- Tone is preserved (casual stays casual unless Professional is selected).

### 3.4 Mixed-language handling **[REQ]**
Example from the brief:
- Spoken: «لطفاً این Scope of Work رو برای Contractor آماده کن.»
- Clean: «لطفاً این Scope of Work را برای Contractor آماده کن.»
- Professional → English: "Please prepare this Scope of Work for the contractor."

Rule: English technical terms stay in Latin script when the output is Persian, unless the glossary says otherwise. The bidi rendering is checked in tests.

### 3.5 Custom vocabulary and presets **[REQ]**
- Personal dictionary: term, optional pronunciation hint, optional translation, "do not translate" flag.
- Ready-made domain packs: Construction and Engineering (AU standards, trades, contracts), Business, IT.
- Presets: Casual message, Professional email, Business communication, Construction and engineering report, Meeting notes, General.
- Custom style: name, tone sliders (formal↔casual, concise↔detailed), optional sample text, sign-off.
- Sync across devices (optional, encrypted).

### 3.6 History **[REQ]**
- Off by default **[ASSUMPTION]**. When on, text is stored locally (and optionally synced). Audio is never kept.
- Delete individual items, delete all, and auto-delete after N days.

### 3.7 Voice editing commands (Phase 2+)
"new line", "خط بعد", "delete that", "پاک کن", "make it more formal".

---

## 4. User journeys and workflows

### 4.1 Onboarding (mobile)
1. Install the app, then a welcome screen with a privacy summary (cloud processing disclosure).
2. Pick languages and accent (Persian + English, with English accent AU/US/UK) and choose a default mode.
3. Grant microphone permission, with an explanation of why.
4. Keyboard setup guide:
   - **Android:** a deep link to Settings → Languages & input → enable Goftar, then the IME picker.
   - **iOS:** Settings → General → Keyboard → Keyboards → Add → Goftar, then turn on **Allow Full Access**, with a plain explanation of why it's needed (network access for AI processing and the shared container with the app).
5. Try it in a practice text field inside the app.

### 4.2 Android keyboard dictation (the ideal flow) **[REQ]**
WhatsApp → tap the text field → Goftar keyboard → hold or tap the mic → speak → live partial text → release → final text inserted with `commitText` → edit or send.

### 4.3 iOS keyboard dictation (compliant flow) **[LIMIT]**
iOS keyboard extensions **cannot reliably record audio** (the microphone isn't available to keyboard extensions, and there are tight memory limits of about 50–70 MB). Proposed workflow, used by Wispr Flow and similar apps:

1. The user taps the mic on the Goftar keyboard.
2. **If no active session:** the keyboard opens the companion app with a URL scheme (`goftar://dictate`). The app starts an audio session with background audio mode and shows "Session active, swipe back to your app". The user goes back (iOS shows the "◀ WhatsApp" back link at the top left).
3. **While the session is active** (default 5 minutes, configurable): tapping the mic on the keyboard sends a start signal through an App Group plus a Darwin notification. The **app** records in the background (shown by the orange microphone indicator), transcribes, writes the result to the shared App Group container, and notifies the keyboard. The keyboard inserts it with `textDocumentProxy.insertText`.
4. The session ends after an idle timeout to save battery and respect privacy.

> **[DECISION D1]** This "warm session" pattern is the only practical way to get one-tap dictation from an iOS keyboard. It relies on the background audio entitlement, which App Review checks closely. Mitigation: keep the session clearly user-started, show the system indicator, offer a visible "End session" control, and explain it in the review notes. **Fallback** if Apple rejects it: the keyboard opens the app, the user dictates there, and the text is pasted automatically when the keyboard comes back (one extra tap and swipe).

### 4.4 Translate typed text from the keyboard
Select text, or use the text before the cursor through `documentContextBeforeInput` → tap Translate or Rewrite → preview chip → tap to replace.

### 4.5 Desktop (Windows)
Cursor in Outlook → press `Ctrl+Win` (hold to talk) or `Ctrl+Alt+Space` (toggle) → a floating pill shows the waveform and live text → release → processing (≤ 1.5 s) → text is inserted at the cursor → a small undo toast appears ("Undo · Show original · Translate").

---

## 5. UI/UX design and wireframe descriptions

### 5.1 Design principles
Minimal, fast and calm. One main action (the mic). State is always visible (listening, processing, done). Both directions (RTL and LTR) are first-class.

### 5.2 Mobile keyboard (both platforms)
```
┌──────────────────────────────────────────────┐
│ [Clean ▾]   [fa⇄en: Auto ▾]   [⟲ original]   │  ← toolbar: mode, output language, undo or original
├──────────────────────────────────────────────┤
│  live preview: «لطفاً این Scope of Work …»   │  ← shown while dictating (RTL or LTR follows the text)
├──────────────────────────────────────────────┤
│  ض ص ث ق ف غ ع ه خ ح ج چ                      │  ← full Persian or English QWERTY layout
│  ...                                          │
│ [🌐] [123] [   space / فاصله   ] [ 🎤 ] [⏎]  │  ← large mic key, globe key switches layout
└──────────────────────────────────────────────┘
```
- **Mic key states:** idle (outline), listening (filled with a pulsing ring and level meter), processing (spinner), error (red shake with a short message).
- **Language indicator:** a small badge `FA`, `EN` or `FA+EN` showing what was detected.
- Long-press the mic to open quick presets.
- Haptic feedback when recording starts and stops.

### 5.3 Companion app screens
1. **Home:** a large mic, the mode selector (segmented control), a translation toggle and output language, and a result card with Copy, Share and "Show original".
2. **History** (if turned on): a list with search and swipe to delete.
3. **Dictionary:** add terms, import CSV, turn domain packs on or off.
4. **Styles and presets.**
5. **Keyboard setup:** status checks ("Keyboard enabled ✓", "Full Access ✓", "Mic ✓").
6. **Privacy:** cloud processing disclosure, history switches, "Delete all my data", training consent (off by default).
7. **Settings:** theme (light, dark or system), digit style, hold-to-talk vs tap-to-toggle, hotkeys (desktop).

### 5.4 Desktop floating pill
A small 260×44 px capsule near the cursor or at the bottom centre, always on top and click-through when idle. It shows a waveform, the detected language badge and the mode. Esc cancels.

### 5.5 Typography and RTL
- Persian font: **Vazirmatn** (OFL licence). English: Inter.
- Each paragraph's direction is set from its first strong character (`dir="auto"` or the native equivalent). Embedded English is isolated with Unicode bidi isolates (U+2068 FSI … U+2069 PDI) **only where the target field supports them**. Plain-text targets get none, to avoid invisible characters in emails **[ASSUMPTION]**.

---

## 6. Recommended technology stack

| Layer | Recommendation | Why |
|---|---|---|
| Android keyboard + app | **Kotlin**, `InputMethodService`, Jetpack Compose for the app (the keyboard view uses Compose inside an IME-safe host, or Views) | Native IME APIs, performance |
| iOS keyboard + app | **Swift**, `UIInputViewController` (keyboard), SwiftUI app, App Groups, AVAudioEngine | Required by the platform |
| Shared client logic | **Kotlin Multiplatform (KMP)** for the API client, settings model, glossary, text post-processing (ZWNJ, digits, bidi) | One implementation of tricky Persian text rules for both mobile platforms |
| Desktop (Windows first, then macOS) | **Tauri 2 (Rust core + web UI)** | Small binary, native access to global hotkeys, UI Automation (Windows) and Accessibility API (macOS) from Rust; the same codebase targets macOS later |
| Backend API | **Python 3.12 + FastAPI** (async), WebSocket streaming | The ML ecosystem; fast to build |
| STT serving | **faster-whisper / CTranslate2** or **vLLM-style Whisper serving** on GPU; streaming via VAD-chunked processing | Cost-efficient, self-hosted control |
| LLM (correction, translation) | API provider (see §7), behind an internal `LLMProvider` interface | Swap providers without client changes |
| Data | **PostgreSQL** (accounts, settings, encrypted dictionaries), **Redis** (rate limits, sessions) | Standard, reliable |
| Auth | Sign in with Apple, Google, email magic link; short-lived JWTs | App Store requirement for Apple sign-in |
| Infra | AWS **ap-southeast-2 (Sydney)** for the main audience, containers on ECS/EKS, GPU nodes (L4 or A10G) | Low latency for AU users, data residency |
| Observability | OpenTelemetry, Grafana; **no transcript content in logs** | Privacy |
| Payments | App Store / Google Play in-app purchases; Stripe for desktop | Store rules |

> **[DECISION D2]** Desktop framework: Tauri (recommended) vs Electron (bigger, but the team may know it, and this repo already uses Electron) vs native C#/WinUI (best Windows integration, no macOS reuse).

---

## 7. AI model recommendations

### 7.1 Speech recognition
| Option | Persian | English (AU) | Code-switching | Latency | Cost | Notes |
|---|---|---|---|---|---|---|
| **Whisper large-v3 / large-v3-turbo (self-hosted)** | Good, weaker on colloquial speech | Very good | Fair: tends to pick one language per 30 s window, may translate or transliterate English words | Medium (turbo is fast) | Low at scale (GPU) | **Recommended base**, open weights, can be fine-tuned |
| Whisper fine-tuned on Persian + code-switched data | Better | Very good | **Better** (main reason to fine-tune) | Same | One-off training cost | **Phase 4 target** |
| Hosted STT APIs (OpenAI, Google Chirp, Azure, Deepgram, ElevenLabs Scribe) | Varies; check each | Good to very good | Varies | Low (streaming) | Per minute, roughly $0.003–0.02 | Good for MVP speed; run a **bake-off** before deciding |
| On-device (whisper.cpp small/medium, Apple SpeechAnalyzer, Android on-device) | Poor to fair | Fair to good | Poor | Device-dependent | Free | Phase 4 offline mode only |

**Recommendation:** run a **two-week STT bake-off in Phase 0** with a 300-utterance test set (Persian, AU English, mixed, noisy). Candidates: Whisper large-v3-turbo (self-hosted), 2–3 hosted APIs. Choose on WER, mixed-language term retention, latency and cost. Expect a **hybrid**: a hosted API for MVP speed, then move to a self-hosted fine-tuned Whisper once volume justifies GPUs.

**Ways to handle code-switching with Whisper:**
- Give the decoder a prompt containing the user's glossary and a short mixed-language example. This nudges it to keep English terms in Latin script.
- Don't force `language=fa` for mixed speech. Detect per VAD segment, and if the confidence for both languages is close, decode with a mixed prompt.
- Post-correct with the LLM using the glossary ("restore these English terms if they were transliterated").

### 7.2 Correction, rewriting and translation LLM
- Needs: strong Persian, strict instruction-following (faithfulness), low latency, reasonable cost.
- **Recommended:** a fast, low-cost frontier model tier (for example, **Claude Haiku 5.5**) for Clean mode and translation, and a mid-tier model (for example, **Claude Sonnet 5.5**) for Professional rewrites and long text. Keep both behind an `LLMProvider` interface and run the same bake-off against alternatives, judged on Persian quality.
- Use structured output (JSON: `text`, `detected_lang`, `changed_entities`) so the faithfulness checker can work.
- Use prompt caching for the system prompt and the user's glossary to cut cost and latency.
- Verbatim mode never calls the LLM. A rule-based normaliser handles punctuation tweaks, ZWNJ and digits.

### 7.3 Language identification
Use Whisper's own language probabilities for each segment, plus a lightweight text-level check (script ratio of Arabic-script vs Latin characters) after transcription.

### 7.4 Processing location
| Option | Pros | Cons | Use |
|---|---|---|---|
| Cloud | Best accuracy, works on any device | Network needed, privacy concerns, ongoing cost | **MVP default** |
| Local | Private, offline, no per-use cost | Lower accuracy (especially Persian), battery, app size, iOS keyboard memory limits | Phase 4 "offline mode" (desktop and capable phones) |
| Hybrid | On-device voice activity detection (VAD) and Verbatim; cloud for heavy work | More complex | **Target architecture** |

---

## 8. System architecture

```
 ┌──────────── Clients ────────────┐
 │ Android IME │ iOS kbd + app │ Win/mac (Tauri) │
 │   Audio capture → VAD → Opus encoder           │
 │   Shared KMP/Rust: settings, glossary, text post-proc
 └───────────────┬─────────────────┘
                 │ WSS (TLS 1.3), JWT
        ┌────────▼─────────┐
        │  API Gateway      │  auth, rate limit, quotas
        └────────┬─────────┘
                 │
        ┌────────▼──────────────────────────┐
        │  Dictation Orchestrator (FastAPI)  │
        │  1. receive audio stream (memory only)
        │  2. STT service → partials/final   │
        │  3. Language ID + normaliser (fa)  │
        │  4. Glossary application           │
        │  5. LLM rewrite/translate (if mode≠Verbatim or translate on)
        │  6. Faithfulness checker → retry/fallback
        │  7. Return final text; discard audio
        └───┬───────────┬───────────┬───────┘
            │           │           │
     ┌──────▼───┐ ┌─────▼─────┐ ┌───▼──────────┐
     │ STT svc  │ │ LLM gate- │ │ User svc     │
     │ (GPU /   │ │ way (pro- │ │ Postgres:    │
     │ provider)│ │ vider abs)│ │ settings,    │
     └──────────┘ └───────────┘ │ glossary(enc)│
                                │ history(opt) │
                                └──────────────┘
```

### Modules (as requested in the brief)
1. **Audio capture engine:** 16 kHz mono PCM, client-side VAD (Silero VAD, ONNX), noise suppression (platform AEC/NS, or RNNoise), Opus at 24 kbps, 200 ms frames over WebSocket.
2. **STT:** streaming partials every ~500 ms (sliding window), final pass on the whole utterance for accuracy.
3. **Language detection:** per segment, as in §7.3.
4. **Correction and rewrite engine:** prompt templates per mode and preset, with a structured JSON response.
5. **Translation engine:** the same LLM gateway with direction parameters and the glossary.
6. **Faithfulness checker:** entity and number extraction and comparison; retry or fallback policy.
7. **Desktop insertion module:** see §11.
8. **Android IME:** see §9.1.
9. **iOS keyboard and companion app:** see §9.2.
10. **Settings and dictionary service:** CRUD, encrypted sync.
11. **Secure backend and API layer:** see §12–13.

---

## 9. Mobile keyboard technical architecture

### 9.1 Android
- `GoftarIME : InputMethodService`. The keyboard view has Persian (standard Persian layout, ISIRI 9147) and English QWERTY layouts.
- Microphone: an IME **can** record audio with the `RECORD_AUDIO` permission. Permission has to be granted through the companion app's activity first, because an IME can't show the runtime permission dialog itself. On Android 14+, use a microphone foreground service type only if recording continues beyond the visible keyboard. Normally recording happens while the IME window is shown, so a foreground service isn't needed **[ASSUMPTION, check during prototype]**.
- Insertion: `currentInputConnection.setComposingText()` for live partials (shown underlined) and `commitText()` for the final text. This gives real live preview in the target app.
- Selected text: `getSelectedText()` and `getTextBeforeCursor()` for translate and rewrite.
- Respect `EditorInfo` flags: turn off cloud dictation in password fields (`TYPE_TEXT_VARIATION_PASSWORD`) and fields that request no personalised learning (`IME_FLAG_NO_PERSONALIZED_LEARNING`).
- Also offer a `RecognitionService` implementation so other keyboards can use Goftar as the voice input provider (nice to have).

### 9.2 iOS
- **Keyboard extension** (`UIInputViewController`): layouts, toolbar, mic key, insertion with `textDocumentProxy`. Needs **Full Access** for network access and the shared App Group.
- **[LIMIT]** No reliable microphone in keyboard extensions. Memory limit of about 50–70 MB, so no on-device models in the keyboard. Secure text fields and phone-number pads automatically switch to the system keyboard. Some apps can block third-party keyboards.
- **Companion app:** owns the audio session (`AVAudioSession` category `.playAndRecord`, `UIBackgroundModes: audio`), the network calls and the dictation state machine.
- **IPC:** App Group `UserDefaults` or a shared file for state and results; `CFNotificationCenterGetDarwinNotifyCenter` for signals (start, stop, result-ready); the keyboard polls as a fallback.
- **Launching the app from the keyboard:** extensions can't call `UIApplication.open` directly. The usual workaround goes up the responder chain to call `openURL`. It works but isn't an official API, so it's a **review risk [DECISION D1]**. The alternative is to ask the user to switch to the app manually the first time.
- **Live preview:** the keyboard shows partials in its own toolbar and inserts only the final text (it can't do composing text like Android).

### 9.3 Feasibility summary
| Capability | Android | iOS |
|---|---|---|
| Custom keyboard install and activate | ✅ | ✅ |
| Mic inside keyboard | ✅ (with permission) | ❌ (needs companion-app session) |
| Live partial text in target field | ✅ (composing text) | ⚠️ preview inside the keyboard only |
| Insert at cursor | ✅ | ✅ |
| Read selected text | ✅ | ⚠️ partial (`selectedText` iOS 16+; context before and after the cursor is limited) |
| Network calls from keyboard | ✅ | ✅ with Full Access |
| Works in WhatsApp, Telegram, Gmail, Outlook, Messages, Notes, browsers | ✅ (password fields excluded) | ✅ except secure fields and apps that block custom keyboards |
| On-device model in keyboard | ⚠️ possible (small) | ❌ memory limits |

---

## 10. iOS and Android feasibility assessment (verdict)
- **Android: high feasibility.** The ideal flow in the brief can be delivered almost exactly.
- **iOS: medium feasibility.** The experience needs the companion-app warm session (an extra step once every few minutes). App Review risk is moderate. Plan a TestFlight and review rehearsal early (Phase 2, week 1), with the fallback flow ready.

---

## 11. Desktop integration strategy (Windows first)

| Function | Windows approach | macOS (Phase 4) |
|---|---|---|
| Global hotkey | `RegisterHotKey`; for hold-to-talk, a low-level keyboard hook (`WH_KEYBOARD_LL`) | `CGEventTap` (needs Accessibility and Input Monitoring permission) |
| Audio | WASAPI (via the Rust `cpal` crate) | CoreAudio |
| Find focused field | UI Automation (`IUIAutomation::GetFocusedElement`) | AXUIElement |
| **Insert text** | Tiered: (1) UIA `ValuePattern`/`TextPattern` insert where supported; (2) **clipboard paste**: save clipboard → set text → `SendInput` Ctrl+V → restore clipboard (most reliable for Word, Outlook, Teams, browsers); (3) `SendInput` with `KEYEVENTF_UNICODE` for short text or apps that block paste | (1) AX setValue; (2) clipboard + Cmd+V; (3) CGEvent unicode |
| Elevated apps | Can't inject into admin-elevated windows unless Goftar also runs elevated; detect this and show "copied to clipboard" | n/a |
| Floating UI | Tauri window: transparent, always on top, no focus steal (`WS_EX_NOACTIVATE`) | `NSPanel` non-activating |
| Auto-update, signing | Code-signing certificate (EV preferred, for SmartScreen), Tauri updater | Developer ID + notarisation |

Per-app profiles: auto-select a preset by foreground process (Outlook → Professional email, WhatsApp Desktop → Casual).

> **[LIMIT]** Clipboard insertion briefly overwrites the clipboard and some clipboard-history tools will record it. Mitigation: mark the clipboard data with `ExcludeClipboardContentFromMonitorProcessing` and restore the previous clipboard contents.

---

## 12. Backend and API specifications

### 12.1 Endpoints (v1)
| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/auth/token` | Exchange an Apple, Google or email sign-in for access and refresh JWTs |
| `WS` | `/v1/dictate` | Streaming dictation session |
| `POST` | `/v1/text/process` | Rewrite or translate existing text |
| `GET/PUT` | `/v1/settings` | User settings |
| `GET/POST/DELETE` | `/v1/glossary[/:id]` | Personal dictionary |
| `GET/POST/DELETE` | `/v1/styles[/:id]` | Custom writing styles |
| `GET/DELETE` | `/v1/history[/:id]` | Synced history (only if turned on) |
| `DELETE` | `/v1/account` | Delete account and all data (within 30 days, including backups) |
| `GET` | `/v1/usage` | Quota and usage |

### 12.2 `/v1/dictate` WebSocket protocol
Client → server:
```json
{"type":"start","session_id":"uuid","mode":"clean","preset":"email_pro",
 "output_lang":"auto","input_hint":["fa","en"],"digits":"latin",
 "app_context":"com.microsoft.outlook","glossary_version":42}
```
followed by binary Opus frames, then `{"type":"stop"}` (or `{"type":"cancel"}`).

Server → client:
```json
{"type":"partial","text":"لطفاً این Scope of","lang":"mixed"}
{"type":"final","raw":"لطفاً این Scope of Work رو برای Contractor آماده کن",
 "text":"لطفاً این Scope of Work را برای Contractor آماده کن.",
 "lang":"mixed","mode_applied":"clean","fallback":false,
 "timings_ms":{"stt":620,"llm":540,"total":1210}}
{"type":"error","code":"quota_exceeded","message":"..."}
```

### 12.3 `/v1/text/process`
Request: `{"text":"...","task":"translate|rewrite|translate_rewrite","mode":"professional","output_lang":"en","preset":"report_construction"}`
Response: `{"text":"...","source_lang":"fa","fallback":false,"changed_entities":[]}`

### 12.4 Limits
- Maximum utterance length 10 minutes, with automatic chunking at pauses. Rate limits by plan tier.
- `app_context` is optional and only used to choose a preset. It isn't stored.

---

## 13. Privacy and security design **[REQ]**
| Area | Design |
|---|---|
| Microphone | OS permission with a clear explanation. Recording only while the user holds the key or has toggled it on, with a visible indicator on every platform. |
| Transport | TLS 1.3 only, certificate pinning in mobile clients (with a backup pin). |
| Audio retention | Audio is processed **in memory only** and never written to disk or logs. If a third-party STT or LLM provider is used, contract for **zero data retention** and no training. |
| Text retention | Server keeps no transcript unless the user turns on synced history. Logs keep metadata only (durations, error codes). |
| At rest | Postgres with AES-256 (KMS). Glossary and history encrypted per user with an envelope key. Optional end-to-end encryption for sync in Phase 4. |
| Credentials | No provider API keys in clients. Clients hold only short-lived JWTs. Server secrets live in AWS Secrets Manager and are rotated every 90 days. |
| Sensitive fields | Android: dictation off in password and no-learning fields. iOS: the system already blocks custom keyboards in secure fields. |
| Disclosure | First-run and settings screens say clearly: "Your voice is sent to our servers in Australia (and named processors) to be transcribed; it is deleted right after." |
| Consent | Training on user content is **off by default**, with a separate explicit opt-in that can be withdrawn. |
| Deletion | Delete an item, delete all history, or delete the account (including backups within 30 days). |
| Compliance | Australian Privacy Act 1988 (APPs), GDPR-ready, App Store privacy "nutrition label", Google Play Data Safety form. |
| Security testing | OWASP MASVS for mobile, a third-party penetration test before public launch, dependency scanning in CI. |

---

## 14. MVP development plan (Phase 1)

**Scope [REQ]:** fa and en STT, automatic language detection, Clean and Professional correction, two-way translation, a basic interface, copy to clipboard.
**MVP client [DECISION D3]:** one companion app, **Android first** (fastest path to the keyboard in Phase 2), plus a simple web app for internal testing. iOS app in Phase 2.

| Week | Work |
|---|---|
| 0–2 (Phase 0) | Collect the test set (300+ utterances: 30% fa, 30% AU-en, 40% mixed, a share recorded with noise). STT bake-off and LLM bake-off. Architecture sign-off. |
| 3–4 | Backend skeleton (auth, WebSocket dictation, STT integration), Persian normaliser |
| 5–6 | LLM pipeline: modes, translation, glossary, faithfulness checker |
| 7–8 | Android app: record, mode and translation UI, result card, copy; light and dark themes |
| 9 | Evaluation harness in CI (WER, term retention, entity preservation), latency tuning |
| 10 | Privacy screens, deletion, closed beta (20–30 users) |

---

## 15. Estimated timeline and costs

### 15.1 Timeline (team: 1 product manager/designer, 1 ML engineer, 1 backend engineer, 1 Android engineer, 1 iOS engineer, 1 desktop engineer from Phase 3, 0.5 QA)
| Phase | Duration | Cumulative |
|---|---|---|
| 0: Discovery and bake-offs | 2 weeks | 2 wk |
| 1: MVP | 8 weeks | 10 wk |
| 2: Mobile keyboards (Android + iOS) | 10 weeks | 20 wk |
| 3: Windows desktop | 8 weeks (can overlap with Phase 2) | ~26 wk |
| 4: Optimisation, offline, macOS, fine-tuning | 12+ weeks | ~38 wk |

### 15.2 Build cost (rough, AUD, assuming blended contractor rate of A$120–160/h)
| Phase | Estimate |
|---|---|
| 0 + 1 | A$120k–180k |
| 2 | A$180k–260k |
| 3 | A$90k–140k |
| 4 | A$150k–250k |
| **Total to v1 (Phases 0–3)** | **≈ A$390k–580k** |

A lean 2–3 person team could do Phases 0–2 for about A$150k–250k over a longer timeline (about 9 months).

### 15.3 Running cost per active user (estimate)
Assume 30 minutes of dictation a month per user, about 4,000 words.
- STT: hosted A$0.15–0.60/user/month; self-hosted GPU at scale A$0.05–0.15.
- LLM: about 60k tokens in and out per user/month, roughly A$0.05–0.40 depending on the model tier and caching.
- Infra and other: about A$0.10.
- **Total ≈ A$0.30–1.10 per active user/month.** Supports a subscription of about A$9–15/month with a free tier (for example, 2,000 words a week).

These figures are estimates and need to be confirmed with real prices during the Phase 0 bake-off **[ASSUMPTION]**.

---

## 16. Testing and acceptance criteria

### 16.1 Test matrix **[REQ]**
| Area | Method | Acceptance criterion (v1) |
|---|---|---|
| Persian only | Gold test set, WER | WER ≤ 10%; ZWNJ correct in ≥ 95% of eligible words |
| English only (AU accent) | AU speaker set (≥ 20 speakers) | WER ≤ 6% |
| Mixed language | Code-switched set | English terms kept in Latin script ≥ 95%; language label correct ≥ 95% |
| Persian accents (Tehrani, Isfahani, Mashhadi, Azeri-accented, Kurdish-accented) | Speaker subsets | WER gap vs. Tehrani ≤ 5 points |
| Background noise | Mixed with site, café and car noise at 10 dB SNR | WER drop ≤ 5 points |
| Technical vocabulary | Glossary terms in the test set | Glossary term recall ≥ 95% |
| Long dictation | 10-minute sessions | No crash or loss of text; memory stable |
| Translation | Human rating (1–5 adequacy and fluency) plus COMET score | Mean adequacy ≥ 4.3; no critical meaning errors in ≥ 99% |
| Meaning preservation | Automatic entity diff plus human audit | Number, name and negation changes < 0.3% |
| Latency | Synthetic and field telemetry | 15-second utterance: p50 ≤ 1.5 s, p95 ≤ 3 s; partials ≤ 700 ms |
| Android keyboard | Instrumented tests in WhatsApp, Telegram, Gmail, Outlook, Messages, Chrome | Insertion success ≥ 99.5% |
| iOS keyboard | Manual and XCUITest across the same apps | Insertion success ≥ 99%; warm session start ≤ 3 s |
| Desktop insertion | Automated tests in Word, Outlook, Teams, Chrome, Edge, Notepad | Insertion success ≥ 99%; clipboard restored 100% |
| Reliability | Production | Crash-free sessions ≥ 99.5%; dictation success ≥ 99% |
| Privacy and security | Pen test, MASVS L1, log audit | No high or critical findings open at launch; no transcript content in logs |
| Satisfaction | In-app rating | CSAT ≥ 4.2/5; ≥ 40% week-4 retention among beta users |

### 16.2 Evaluation harness
Run automatically in CI on every model or prompt change. Releases are blocked if any metric drops by more than its tolerance.

---

## 17. Technical risks and solutions

| # | Risk | Impact | Mitigation |
|---|---|---|---|
| R1 | iOS App Review rejects the background audio warm session or the responder-chain `openURL` | High | Rehearse early on TestFlight; document user control clearly; keep the fallback flow ready |
| R2 | Whisper mishandles code-switching (translates or transliterates English terms) | High | Glossary prompting, segment-level language ID, LLM restoration step, fine-tuning in Phase 4 |
| R3 | Persian WER is high for colloquial and accented speech | High | Data collection (with consent), fine-tuning, accent test subsets |
| R4 | LLM changes meaning or invents content | High | Strict prompts, structured output, entity diff checker, fallback, "Show original" |
| R5 | Latency too high on mobile networks | Medium | Sydney region, streaming, Opus, smaller or faster model for Clean mode, parallel STT and LLM warm-up |
| R6 | Costs grow faster than revenue | Medium | Free tier limits, prompt caching, move to self-hosted STT at scale, cost dashboards |
| R7 | Bidi rendering issues (punctuation in the wrong place, invisible characters) | Medium | Shared post-processing library, render tests in target apps, no isolates in plain-text targets |
| R8 | Desktop insertion fails in some apps (elevated, games, remote desktop) | Medium | Tiered insertion, detect failure, fall back to clipboard with a notice |
| R9 | Users don't trust a keyboard with Full Access | Medium | Clear privacy messaging, no logging of typed keys, independent audit, open privacy policy |
| R10 | Store policy for keyboards and data collection | Medium | Follow Apple 4.4.1 and Google Play User Data policies; keyboard keys never sent to the server, only dictation audio and explicitly selected text |
| R11 | Sanctions or export-control questions for the Persian-speaking market | Medium | Legal review; target the diaspora (AU, US, EU, CA) at launch **[ASSUMPTION]** |
| R12 | Availability in Iran (app store access, payment, network filtering) | Low–Medium | Out of scope for v1; revisit after legal review |

---

## 18. Decisions needed before implementation

| ID | Decision | Recommendation |
|---|---|---|
| **D1** | iOS dictation flow: warm session with background audio (one tap, review risk) vs open-app-every-time (safe, slower) | Build the warm session; keep the fallback ready |
| **D2** | Desktop framework: Tauri vs Electron vs native WinUI | Tauri |
| **D3** | MVP platform: Android first vs iOS first vs web | Android first + internal web test page |
| **D4** | STT: hosted API vs self-hosted Whisper for MVP | Decide after the Phase 0 bake-off; expect hosted first |
| **D5** | LLM provider and tiers | Fast tier for Clean and translation; mid tier for Professional; confirm in bake-off |
| **D6** | Hosting region and data residency | AWS Sydney |
| **D7** | History default | Off, local only; sync is opt-in |
| **D8** | Default Persian digit style and colloquial→formal conversion in Clean mode | Latin digits in technical presets; formal written Persian in Clean, with "keep conversational" switch |
| **D9** | Business model (free tier limits, pricing) | Free tier + A$9–15/month subscription |
| **D10** | Product name and branding | "Goftar" is a placeholder |
| **D11** | Launch markets | Australia first, then other diaspora markets |

---

## 19. Summary: confirmed requirements, assumptions, limitations

**Confirmed requirements:** Persian and English only; STT with automatic language detection and code-switching; Verbatim, Clean and Professional modes with no invented facts; two-way translation for speech and text; Android and iOS keyboards; Windows desktop first, then macOS; presets and custom dictionaries; privacy rules in §13; the four-phase roadmap.

**Assumptions (need your sign-off):** working name; Australia-first launch and Sydney hosting; Android-first MVP; Tauri for desktop; history off by default; digit and formality defaults; cost and pricing figures; persona and accent priorities.

**Technical limitations:** no microphone in iOS keyboard extensions (needs the companion-app session); custom keyboards are blocked in secure fields and in some apps; iOS keyboards can't show live composing text inside the target field; iOS keyboard memory limits rule out on-device models there; desktop insertion can't reach elevated windows and uses the clipboard in many apps; on-device Persian STT is currently much less accurate than cloud; Whisper's code-switching needs extra work to meet the targets.

---

*Next step: review §18. Once D1–D5 are decided, Phase 0 (test set + bake-offs) can start.*
