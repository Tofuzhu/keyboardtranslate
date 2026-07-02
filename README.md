# keyboardtranslate

LLM-backed translation for any Windows input box, via two entry points that
share one `translator.py` core:

- **espanso trigger words** (`:tr` for auto-direction, `:cn`/`:en`/`:es` for
  explicit targets — `：` full-width colon also works) — see
  `docs/espanso-setup.md` for installation and manual verification steps.
- **Global hotkey on a text selection** — run `python hotkey_daemon.py` in
  the background; select text anywhere and press `Ctrl+Alt+T` (configurable
  in `config.yaml`) to translate it in place.

## Setup

1. `pip install -r requirements.txt`
2. Set the `KEYBOARDTRANSLATE_API_KEY` environment variable to your LLM
   gateway's API key. Never put it in `config.yaml` or any committed file.
3. Adjust `config.yaml` if needed: `default_pair`, `output_mode`
   (`replace` | `append` | `popup`), `hotkey`.
4. Run `pytest` to verify the core logic.
5. For the hotkey daemon: `python hotkey_daemon.py`.
6. For espanso trigger words: follow `docs/espanso-setup.md`.

## Design

See `docs/superpowers/specs/2026-07-01-keyboard-translate-design.md` for the
full design rationale.
