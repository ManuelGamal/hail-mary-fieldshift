# Lane 3 — Product & story (owner: Friend B's agent)

Read `00-shared-contract.md` first, then `docs/design.md` §5 G–H, §10–11. You own everything a judge or farmer sees: the API, the Egyptian-Arabic explainer agent, the web app, the "How we know" validation page, the 7-slide deck / 30-s video, and the submission texts. You consume artefacts and Lane 2's `science.options.for_block`; you never compute science yourself.

## Start immediately
- Build against a mock: `app/mocks/` with JSON shaped exactly like the shared contract (including `options`). Swap to `artefacts-v1` fixtures when Lane 1 releases them, and to Lane 2's package when it lands.

## Tasks

### 1. Backend API (`app/api`)
- Read-only service over the artefacts (Parquet → DuckDB or Polars in memory). Endpoints: `/blocks?bbox=`, `/blocks/{id}/history`, `/blocks/{id}/analogs`, `/blocks/{id}/options?prefs=`, `/effects`, `/robustness`, `/water`.
- Stateless, no login, CORS on; cold start < 5 s; p95 < 300 ms on fixtures.

### 2. Verifiable explainer agent (`app/agent`)
- Tool calling only, over the endpoints above. System prompt: answer in Egyptian Arabic by default, English on request; never state a number not returned by a tool this turn; always add the source chip (`effect_id`, dataset, season).
- **Numeric grounding guard:** after generation, extract every numeral (Arabic-Indic and Western digits) and reject or regenerate if any isn't in the turn's tool outputs (±rounding). Log rejections.
- "Challenge this" action: re-query the effect for a different stratum or method and show the delta.
- LLM provider: your choice, needs strong Arabic and tool calling; keys only in server env vars, never in the repo or the client.
- Voice (Egyptian-Arabic ASR/TTS) is a stretch goal behind a feature flag, with a confirm-back step.

### 3. Web app (`app/web`)
- Map (MapLibre) of SGZ/ZAN blocks; click a block → timeline of its crop history (W2016…S2025), and analog lines light up to its "switcher" neighbours with their before/after deltas.
- Farmer card view (Arabic first, zero jargon): status quo + 3 options; each card shows why, evidence (estimate ± CI and n), benefits, gaps, risks, water m³/feddan, constraint flags. A "supports, does not replace, local extension advice" notice.
- "How we know" page: crop-map accuracy (confusion matrices), Prithvi vs TESSERA agreement, effect table with CIs, the six robustness checks, FAO-56 vs ECOSTRESS, a data-scale table (field-scale vs regional layers), known limits.
- Accessible: RTL layout, WCAG AA contrast, works on a phone over slow 3G (lazy tiles).
- Deploy publicly (any free host); every page opens logged-out.

### 4. Story & submission (`docs/submission/`)
- 7-slide deck, exactly: 1 hook (analog-map image) · 2 problem (Delta water, salinity, rotation choices under rice caps) · 3 the idea: the Delta's natural experiments · 4 how: NASA data + Prithvi + causal engine (one diagram, scale-honesty table) · 5 results: precrop effect ± CI, map accuracy, robustness · 6 the farmer card (Arabic) · 7 validity, limits, roadmap, AI-use disclosure.
- 30-s video cut from the live app (English subtitles; no faces or voices of anyone under 18).
- Texts for the Cairo form and global page: project summary (problem, solution, impact, how it meets the challenge), resources list with licences, subjects, AI disclosure. Pull every figure from the artefacts.

## Acceptance criteria
- [ ] API contract tests pass against mocks, fixtures and v2 artefacts (same tests).
- [ ] Agent eval: 40 scripted questions (20 Arabic, 20 English) including 10 adversarial ("what yield will I get?", "is my soil healthy?", "can I grow rice here?" outside the zone). 100% numeric grounding (guard never lets an untraced number through); 100% correct refusals or reframes on the adversarial set; native-speaker check on 10 Arabic answers.
- [ ] Every number on the UI, deck and video has a hover or footnote source that resolves to an artefact row or citation (automated check for UI; manual checklist for deck/video).
- [ ] Lighthouse: performance ≥ 80 on mobile, accessibility ≥ 90; RTL renders correctly.
- [ ] Deck is exactly 7 slides; video ≤ 30 s; both public; all submission links open in a logged-out browser (checked on two networks).
- [ ] No secrets in the repo (CI secret scan).

## Don'ts
- Don't show attribution percentages or confidence the science lane didn't produce.
- Don't use "field", "soil health", or "yield gain" in copy; say "block", "next-crop vigor", "water use".
- Don't hard-code numbers in the frontend or slides.
