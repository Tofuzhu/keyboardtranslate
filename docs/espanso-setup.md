# espanso Setup and Manual Verification

## Install

1. Install espanso for Windows: https://espanso.org/install/windows/
2. Find your espanso match directory: `espanso path`
3. Copy (or symlink) `espanso/translate.yml` from this repo into that directory's `match/` folder.
4. Ensure `python` and `translator.py` are on your PATH / working directory matches, or edit the `cmd` in `translate.yml` to use an absolute path, e.g. `python D:\pythonProject2\keyboardtranslate\translator.py --text "{{text}}"`. Also pass `--config` with an absolute path to `config.yaml` if espanso's shell working directory differs from the repo root.
5. Set the `KEYBOARDTRANSLATE_API_KEY` environment variable (System Properties -> Environment Variables). Windows only applies a newly-set environment variable to processes started *after* it was set — if espanso was already running, log off and back on (or reboot) once so espanso's process tree picks it up. Then restart espanso: `espanso restart`.

## Why triggers end with `//`

espanso evaluates regex matches against the buffer after every keystroke. An
open-ended pattern like `.+$` (matching "everything typed so far") would fire
on the very first character after the prefix — not once you've finished
typing your sentence. All four triggers therefore require an explicit
terminator, `//`, at the end: espanso only fires once that literal sequence
appears, so you type your sentence and then type `//` to signal "done", e.g.
`:cn hello world//`.

## Manual verification checklist

- [ ] Type `:tr 你好世界//` in any text box (e.g. Notepad) and confirm it expands to an English translation (and that it does NOT expand prematurely after just the first character or two).
- [ ] Type `:tr hello world//` and confirm it expands to a Chinese translation.
- [ ] Type `:en 你好//` and confirm it expands to an English translation (explicit target).
- [ ] Type `:cn hello//` and confirm it expands to a Chinese translation (explicit target).
- [ ] Type `:es hello//` and confirm it expands to a Spanish translation (explicit target).
- [ ] With your IME in Chinese punctuation mode, type `：cn hello//` (full-width colon) and confirm it triggers the same as `:cn hello//` — no need to switch to English punctuation mode first.
- [ ] Unset `KEYBOARDTRANSLATE_API_KEY` temporarily and confirm the trigger does not silently insert garbage (the shell command should fail visibly or insert an error string, not corrupt the input box).
