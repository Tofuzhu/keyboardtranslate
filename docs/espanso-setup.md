# espanso Setup and Manual Verification

## Install

1. Install espanso for Windows: https://espanso.org/install/windows/
2. Find your espanso match directory: `espanso path`
3. Copy (or symlink) `espanso/translate.yml` from this repo into that directory's `match/` folder.
4. Ensure `python` and `translator.py` are on your PATH / working directory matches, or edit the `cmd` in `translate.yml` to use an absolute path, e.g. `python D:\pythonProject2\keyboardtranslate\translator.py --text "{{text}}"`.
5. Set the `KEYBOARDTRANSLATE_API_KEY` environment variable (System Properties -> Environment Variables), then restart espanso: `espanso restart`.

## Manual verification checklist

- [ ] Type `:tr 你好世界` in any text box (e.g. Notepad) and confirm it expands to an English translation.
- [ ] Type `:tr hello world` and confirm it expands to a Chinese translation.
- [ ] Type `:en 你好` and confirm it expands to an English translation (explicit target).
- [ ] Type `:cn hello` and confirm it expands to a Chinese translation (explicit target).
- [ ] Type `:es hello` and confirm it expands to a Spanish translation (explicit target).
- [ ] With your IME in Chinese punctuation mode, type `：cn hello` (full-width colon) and confirm it triggers the same as `:cn hello` — no need to switch to English punctuation mode first.
- [ ] Unset `KEYBOARDTRANSLATE_API_KEY` temporarily and confirm the trigger does not silently insert garbage (the shell command should fail visibly or insert an error string, not corrupt the input box).
