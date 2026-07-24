# Offline Instant Writing Reviser v1

## Architecture

Phase 15 adds a Windows-wide writing revision path that is separate from chat:

```text
Ctrl+Alt+W
  PersonalAIWritingReviser.exe
  desktop.hotkeys.WindowsHotkeyManager
  desktop.offline_writing_controller.OfflineWritingController
  desktop.text_selection.WindowsSelectedTextAdapter
  app.offline_writing.OfflineWritingService
  app.offline_writing.providers.ollama_cli.OllamaCliOfflineWritingProvider
  paste revised text back into the original selection
```

The offline writing package does not import or call `ModelRouter`, OpenAI, embeddings, RAG, memory, chat orchestration, FastAPI, pywebview, or frontend code. It has its own `OfflineWritingProvider` abstraction so future phases can add more local providers without opening a cloud fallback path.

## Privacy Boundary

During Ctrl+Alt+W revision, selected text is:

- copied from the active Windows application through normal copy semantics
- passed only to a configured local writing provider
- never persisted
- never sent to OpenAI or another remote provider by this subsystem
- never logged

Logs may include operation start, character count, duration, success/failure category, provider name, and local model identifier. Logs must not include selected text, revised text, clipboard contents, explanations, scores, or correction details.

## Local Runtime And Model

The initial supported runtime is the Ollama command-line runtime on Windows.

Default provider: `ollama_cli`

Default model: `llama3.2:3b`

Approximate requirements:

- Model size: about 2 GB on disk for the default Ollama quantized model.
- Disk: allow at least 4 GB free for the model, manifests, and runtime overhead.
- RAM: 8 GB system RAM minimum is practical; 16 GB is better for responsiveness.
- GPU: not required.

Rationale: Ollama is a practical Windows local inference runtime, exposes installed-model checks, supports small instruction-tuned local models, and can run after installation without internet access. Phase 15 calls the local `ollama` executable with hidden Windows subprocess flags; it does not call a remote API, does not open an interactive `ollama run` session, and does not download models.

## Installation

Install the runtime and model explicitly:

```cmd
winget install Ollama.Ollama
ollama pull llama3.2:3b
ollama list
```

`ollama list` must show `llama3.2:3b`. The assistant does not automatically download this model.

After the model is installed, revision does not require internet access. Disconnecting the network should still allow Ctrl+Alt+W revision to work, as long as Ollama and the model are installed locally.

## Background Executable

Build the standalone background reviser:

```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_writing_reviser.ps1
```

Output:

```text
dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe
```

Launch this executable once to start the silent background listener. It has no console window and no main UI window. The normal Personal AI Assistant app remains separately launchable from:

```text
dist\PersonalAIAssistant\PersonalAIAssistant.exe
```

## Hotkey

Default shortcut:

```text
Ctrl+Alt+W
```

The background reviser registers the hotkey on startup and unregisters it on shutdown. If another application already owns the shortcut, registration fails and the reviser log records the failure. The main assistant window does not need to be open.

Only one reviser process runs per user session. A second launch exits quietly without registering a second listener.

## Text Capture And Replacement

The first implementation uses Windows clipboard-compatible editing commands for broad application coverage:

1. Snapshot the current clipboard formats where possible.
2. Wait briefly for the physical Ctrl and Alt hotkey modifiers to be released.
3. Send Ctrl+C to copy the active selection.
4. Restore the original clipboard snapshot immediately after capture.
5. Run local revision.
6. Confirm the foreground window is still the original window.
7. Temporarily place revised Unicode text on the clipboard.
8. Send Ctrl+V to replace the active selection.
9. Restore the original clipboard snapshot.

Clipboard access uses bounded retry/wait behavior for clipboard ownership races. The selected and revised text are never written to logs.

## Windows Startup

Startup is opt-in. The build does not modify Windows startup automatically.

Enable per-user startup after packaging:

```cmd
dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe --enable-startup
```

Disable per-user startup:

```cmd
dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe --disable-startup
```

Check status:

```cmd
dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe --startup-status
```

The setting is stored in the current user's `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` key and points to the packaged `.exe`, not Python or Conda. Administrator privileges are not required.

This approach works with many standard Windows text targets, including Notepad, browser textareas, Office-style editable fields, Teams-style fields, and common Windows controls. It preserves normal Ctrl+Z behavior when the target application treats paste as an undoable edit.

## Configuration

Desktop `settings.json` supports:

```json
{
  "offline_writing_enabled": true,
  "offline_writing_provider": "ollama_cli",
  "offline_writing_model": "llama3.2:3b",
  "offline_writing_hotkey": "Ctrl+Alt+W",
  "offline_writing_timeout_seconds": 45.0,
  "offline_writing_max_characters": 4000
}
```

Only `ollama_cli` is implemented in Phase 15. The settings names are intentionally model-agnostic so future local runtimes can use the same service contract.

## Failure Behavior

Successful operations are silent: the selected text is replaced and nothing else is displayed.

On failure:

- original text is left unchanged
- no error message is pasted into the target application
- no assistant window is opened
- the failure category is logged locally
- overlapping hotkey presses are ignored by the service concurrency guard

Common failure categories are empty selection, selection too long, model unavailable, provider timeout, malformed model output, and foreground window changed before paste.

Development logs include hotkey registration, hotkey receipt, safe foreground process identity, capture start/result, character counts only, Ollama invocation start/result, replacement start/result, clipboard restoration, and total duration. They never include selected or revised text.

## Offline Guarantee

The offline reviser is architecturally isolated from cloud providers:

- no `ModelRouter`
- no `OpenAIModelProvider`
- no embedding provider
- no RAG or memory path
- no frontend chat request
- no OpenAI fallback
- no network fallback

The only Phase 15 provider invokes the local `ollama` executable. It checks `PATH` and normal Windows Ollama install locations. If the executable or configured model is unavailable, revision fails locally.

## Manual Validation

Build and launch the packaged background app:

```cmd
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\build_writing_reviser.ps1
dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe
```

Validate Ctrl+Alt+W in:

- Notepad
- browser textarea
- Microsoft Word, if installed

Core sample:

Original:

```text
I have spoke with client yesterday and he said he don't received the documents yet.
```

Expected quality:

```text
I spoke with the client yesterday, and he said he hasn't received the documents yet.
```

Checklist:

- one sentence
- multiple paragraphs
- punctuation errors
- professional email text
- names
- dates
- numbers
- email addresses
- URLs
- Unicode
- clipboard preservation
- Ctrl+Z after replacement
- repeated Ctrl+Alt+W while a revision is running
- no selected text
- local model unavailable
- internet disconnected

Mandatory final offline test:

1. Install Ollama and `llama3.2:3b`.
2. Close Personal AI Assistant, CMD, PowerShell, and interactive Ollama sessions.
3. Launch `dist\PersonalAIWritingReviser\PersonalAIWritingReviser.exe` once.
4. Confirm no window or terminal appears.
5. Open Notepad.
6. Type and select the core sample.
7. Press Ctrl+Alt+W.
8. Confirm the revised text replaces the selection.
9. Confirm Ctrl+Z restores the original.
10. Repeat in a browser textarea.
11. Enable Windows startup with `--enable-startup`.
12. Sign out and back in if practical.
13. Repeat Ctrl+Alt+W without launching the main assistant.
14. Disconnect network access.
15. Repeat Ctrl+Alt+W and confirm it still works.

## Troubleshooting

- If nothing happens, check `%LOCALAPPDATA%\PersonalAIAssistant\logs\writing-reviser.log` for hotkey registration or capture failure.
- If logs show the model is unavailable, run `ollama list` and confirm the configured model is installed.
- If replacement is skipped, keep focus in the original target window until revision finishes.
- If the wrong clipboard content appears, retry after closing clipboard-monitoring tools.
- If output quality is poor, verify the configured model is an instruction-tuned local model.

## Known Limitations

- Clipboard-based capture cannot guarantee every custom editor or elevated/admin application will cooperate.
- Rich formatting is not preserved; replacement is plain Unicode text.
- Clipboard preservation is best effort for formats that can be read and restored.
- Focus changes during revision prevent paste only when the foreground window changes.
- Phase 15 has no model picker UI, modes, explanations, correction lists, tracked changes, RAG, memory integration, voice, or cloud fallback.

## Future Multi-Model Extension Points

Future phases can add local providers by implementing `OfflineWritingProvider` and selecting them through desktop settings. The service contract and `WritingRevisionResult` are provider-neutral. Candidate future providers include a direct llama.cpp binding, a local HTTP-only Ollama adapter, or specialized local writing models.
