# SEP: Voice Vocabulary

- **Status**: Draft
- **Type**: Extensions Track
- **Created**: 2026-10-26
- **Author(s)**: Matthew Vuk (@mvuk)
- **Sponsor**: None
- **Prior discussion**: [MCP Discord](https://discord.com/channels/1358869848138059966/1358869848138059969/1564274815450353864)

The biggest frustration in talking to an AI by voice is not being understood: the transcript doesn't match what you said, and the words it gets wrong are the ones that matter most in your app. Every project has its own internal lexicon of product names, jargon and acronyms, and a general speech model has never heard it.

This SEP proposes an optional extension that lets an MCP server publish that lexicon as a **vocabulary**: its terms, what speech-to-text writes instead of them, how to say them, and what they mean. A voice client that supports it biases its speech-to-text towards those words, corrects transcripts before the model sees them, teaches its text-to-speech to pronounce them, and gives the model a short, attributed primer. Clients that don't support it lose nothing.

**Full specification, JSON Schema and reference code:** https://github.com/mvuk/voice-vocabulary

## Reference implementations

- **Server:** [bark-voice](https://gitlab.com/matthewvuk/bark-voice), a voice connector for a bitcoin wallet built on Second's [bark-mcp](https://gitlab.com/ark-bitcoin/labs/bark-mcp); the canonical example and where the idea came from (unprompted, Whisper transcribed every "Ark" as "arc"). [bark-mcp](https://gitlab.com/ark-bitcoin/labs/bark-mcp) itself serves the same document on 2025-11-25 and 2026-07-28 connections.
- **Clients:** dependency-free [JavaScript](https://github.com/mvuk/voice-vocabulary/blob/main/js/voice-vocabulary.js) and [Python](https://github.com/mvuk/voice-vocabulary/blob/main/python/voice_vocabulary.py), passing a shared [conformance suite](https://github.com/mvuk/voice-vocabulary/blob/main/conformance/cases.json).
- **Voice framework:** a [Pipecat integration](https://github.com/mvuk/voice-vocabulary/tree/main/integrations/pipecat), run end to end with Pipecat 1.14.0 against bark-voice (bark-voice → bark-mcp → a signet wallet daemon): 25 tools, the 101-term vocabulary, keyterms to the STT, the primer to the LLM, and "board into arc" corrected to "board into Ark". Building it showed that whether the `extensions` capability arrives on Pipecat's `initialize` connection depends on the server's SDK (TypeScript sends it, Python 2.3 doesn't), so the spec also lets clients find the vocabulary by its resource `mimeType`.

## Feedback wanted

1. **Shape:** a capability plus a resource (with `mimeType` discovery as the fallback), or something else?
2. **Languages:** draft-1 is one language per document, English first. How should a server offer its lexicon in several languages? (SEP, *Phase 2: languages*)
3. **Home:** is there a working or interest group this belongs in, or appetite for a voice/realtime one?
4. **Client adoption:** who maintains MCP client code in voice frameworks and would review an integration?

## Next steps

- [ ] Find a sponsor
- [ ] Discuss in a relevant working or interest group
- [ ] Run the Pipecat integration in a live bot with real audio
- [ ] Settle how multiple languages work (phase 2)

## AI disclosure

The proposal and its wording are currently AI-driven: this SEP, the reference clients, the Pipecat integration and this text were written primarily by Claude Code (Anthropic), under my direction. It is an early draft to establish the pattern. I will return to write it by hand and iterate on it thoughtfully as I plug it into more voice models and interfaces.
