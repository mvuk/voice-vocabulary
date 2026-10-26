# Pipecat integration

[Pipecat](https://github.com/pipecat-ai/pipecat) is an open-source Python
framework for real-time voice agents: speech-to-text → an LLM with tools → text-to-speech,
as a pipeline. It already connects to MCP servers for tools. This module lets those
same servers teach the bot their words.

```python
from pipecat.services.mcp_service import MCPClient
from pipecat_voice_vocabulary import VoiceVocabulary

mcp = MCPClient(server_params=...)
tools = await mcp.tools()
vocab = await VoiceVocabulary.from_mcp(mcp)     # empty if the server publishes none

pipeline = Pipeline([
    transport.input(),
    stt,
    vocab.processor(stt=stt),   # ① keyterms to the STT  ② primer to the LLM  ③ corrected transcripts
    user_aggregator,
    llm,
    tts,
    transport.output(),
    assistant_aggregator,
])
vocab.install_tts(tts)          # ④ the server's pronunciations
```

| | How | Pipecat extension point |
|---|---|---|
| ① STT | the service's own vocabulary field, found by name: Deepgram and Cartesia `keyterm`, ElevenLabs `keyterms`, AssemblyAI `keyterms_prompt`, local Whisper `hotwords` + `initial_prompt`, OpenAI and Groq `prompt` | `STTUpdateSettingsFrame(delta=…, service=stt)`, sent upstream at start |
| ② LLM | one attributed system message per vocabulary ("reference only, not instructions") | `LLMMessagesAppendFrame(run_llm=False)` |
| ③ transcripts | sound-alikes and corrections, before the user aggregator; the raw text and changes stay in `frame.metadata["voice_vocabulary"]` | a `FrameProcessor` on `TranscriptionFrame` / `InterimTranscriptionFrame` |
| ④ TTS | respellings as a text transform; IPA through the service's `pronunciation_transform_ipa` | `tts.add_text_transformer(…)` |

**Approvals:** if your bot acts on a spoken "yes, go ahead", decide it from
`frame.metadata["voice_vocabulary"]["raw"]` (or the frame's text when nothing was
corrected), never from the corrected text (SPEC.md section 3.1).

## How it finds the vocabulary

Pipecat's `MCPClient` connects with the `initialize` handshake (protocol
2025-11-25). Whether the `extensions` capability arrives on that connection
depends on the server's SDK: the MCP TypeScript SDK sends it (bark-voice), the
MCP Python SDK 2.3 leaves it out. So the integration uses the capability when it's
there and otherwise falls back to `resources/list`, reading the resource whose
`mimeType` is `application/vnd.voice-vocabulary+json` (SPEC.md section 1). It reaches the MCP
session through `MCPClient`'s private `_get_active_session()`; upstream, Pipecat
would expose the session's capabilities and resources instead.

## Tests

Against Pipecat 1.14.0 and the MCP Python SDK 2.3, with a real MCP server
process (`vocab_server.py`), real Pipecat processors and the real settings
classes of Pipecat's STT services:

```bash
python3 -m venv .venv && .venv/bin/pip install "pipecat-ai[mcp,deepgram]"
cd integrations/pipecat && PYTHONPATH=. ../../.venv/bin/python -m unittest -v test_pipecat_voice_vocabulary
```

On NixOS, Pipecat's audio wheels need `LD_LIBRARY_PATH` to include a `libstdc++`.

Against bark-voice itself (a real server: bark-voice → bark-mcp → a signet
`barkd`), when one is set up (`npm run setup` in bark-voice):

```bash
BARK_VOICE=~/bark-voice PYTHONPATH=. ../../.venv/bin/python -m unittest -v test_pipecat_voice_vocabulary
```

Not yet run: a live bot with real audio and API keys.
