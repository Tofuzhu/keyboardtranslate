# Keyboard Translate — Design Spec

**Date:** 2026-07-01
**Status:** Draft (pending user review)

## Purpose

A lightweight, always-available text translation tool that works inside any input box on Windows, combining espanso's mature text-trigger engine with a small companion hotkey daemon for "select text, translate in place" workflows. Translation is performed by an LLM instead of a traditional MT engine, so it can handle context and tone better.

## Non-Goals

- Not a general-purpose text expander replacement — reuses espanso for that role rather than reimplementing it.
- Not building a custom hotkey/trigger engine from scratch (rejected as Approach C — see Alternatives).
- Not supporting arbitrary language pairs in v1 beyond what's configured (default pair + a small set of explicit language-code triggers).

## Architecture

```
┌─────────────────────────────────────────────┐
│                translator.py                  │
│   Core: language detection / prompt assembly / │
│   LLM gateway call / reads config.yaml         │
└───────────────┬───────────────┬──────────────┘
                │               │
     ┌──────────▼─────┐  ┌──────▼───────────┐
     │  espanso match  │  │ hotkey_daemon.py  │
     │  :tr / :tr en   │  │ Global hotkey →    │
     │  / :tr es etc.  │  │ grab selection →   │
     │                 │  │ write back result   │
     └─────────────────┘  └───────────────────┘
```

### Components

1. **`translator.py`** (core library)
   - Input: source text + optional target language code (`en`, `cn`, `es`, ...)
   - If no target language code is given, auto-detects direction using the configured `default_pair` (e.g. `[zh, en]`): if text is in language A, translate to B, and vice versa.
   - If a target language code is given, always translates into that language regardless of source.
   - Calls the LLM via an OpenAI-compatible chat completions request (works with any OpenAI-compatible endpoint, including the internal ZTE MaaS gateway).
   - Reads all provider/behavior settings from `config.yaml`.

2. **espanso config** (`~/.config/espanso/match/translate.yml`, or Windows equivalent path)
   - Defines triggers: `:tr` (default pair, auto direction), `:tr en`, `:tr cn`, `:tr es` (explicit target).
   - Uses espanso's `shell` extension to invoke `python translator.py --text "<matched text>" [--to <lang>]` and substitutes the match with the returned translation.

3. **`hotkey_daemon.py`** (background script)
   - Listens for a global hotkey (default `ctrl+alt+t`, via the `keyboard` library).
   - On trigger: simulates `ctrl+c` → reads clipboard → calls `translator.py`'s translation function directly (in-process, not via subprocess) → writes result back according to `output_mode`:
     - `replace`: simulates paste, overwriting the selection.
     - `append`: pastes original text followed by the translation.
     - `popup`: shows a small system notification/window with the translation; user copies manually.

4. **`config.yaml`**
   ```yaml
   provider: custom                 # openai-compatible
   base_url: https://maas-apigateway.dt.zte.com.cn/model-cop/qwen3-235b-a22b-instrust-2507-coclaw/v1/
   model: Qwen3-235B-A22B
   api_key_env: KEYBOARDTRANSLATE_API_KEY   # read from environment, never hardcoded
   default_pair: [zh, en]
   output_mode: replace              # replace | append | popup
   hotkey: ctrl+alt+t
   ```

## Data Flow

**Trigger-word path:** user types `:tr en` + text → espanso matches → shell extension runs `translator.py` → LLM call → result substituted into the input box by espanso.

**Hotkey path:** user selects existing text in any input box → presses hotkey → daemon copies selection → calls `translator.py` in-process → LLM call → result written back per `output_mode`.

Both paths converge on the same `translator.py` core, so translation behavior (prompting, language detection, provider config) is defined once.

## Error Handling

- LLM call fails (network error, timeout, quota exhausted): original text is left untouched; a system notification reports the failure. Never silently replace text with an error message or partial output.
- Hotkey pressed with empty clipboard / no active selection: notify "no text detected", no-op.
- `KEYBOARDTRANSLATE_API_KEY` missing at startup: `hotkey_daemon.py` fails fast with a clear error rather than starting in a broken state; espanso-triggered calls fail the same way per-invocation.

## Security

- `llm.txt` (contains a live internal API key) is excluded via `.gitignore` and must never be committed.
- The API key is read from the `KEYBOARDTRANSLATE_API_KEY` environment variable at runtime; it is never written into `config.yaml` or source code.
- `config.local.yaml` (if used for machine-specific overrides containing secrets) is also gitignored.

## Testing

- **`translator.py`**: unit tests covering language detection, prompt construction, default-pair auto-direction logic, explicit-target-language logic, mocked LLM responses, and error paths (timeout, non-200, malformed response).
- **espanso triggers**: manual verification checklist following espanso's own match-testing conventions (not automatable in CI without a running espanso instance).
- **`hotkey_daemon.py`**: tests with a mocked clipboard and simulated hotkey trigger, verifying `replace` / `append` / `popup` output modes and the "no selection" no-op path.

## Alternatives Considered

- **Approach B (rejected):** espanso-only, trigger-word mode only, no hotkey/selection support. Simpler (no background daemon) but drops the "select existing text and translate" workflow the user explicitly wants.
- **Approach C (rejected):** Fully custom Python implementation of both hotkey listening and text-trigger detection, without espanso. Would duplicate espanso's mature trigger engine for no benefit, at significantly higher implementation and maintenance cost.

## Open Questions for Implementation Planning

- Exact set of explicit language-code triggers beyond `en`/`cn`/`es` (extensible list vs. fixed set).
- Windows path conventions for espanso config location (may differ from `~/.config/espanso`).
- Whether `hotkey_daemon.py` should run as a startup service/scheduled task, or be launched manually.
