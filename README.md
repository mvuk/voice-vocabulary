# voice-vocabulary

**Be understood.** A draft MCP extension that lets a tool server teach a voice AI
its app's own words: how they sound, how to say them, and what they mean.

The biggest frustration in talking to an AI by voice is not being understood: the
transcript doesn't match what you said, and the words it gets wrong are the ones
that matter most in your app. Every project has its own internal lexicon. MCP
connects the model to the tools; nothing connects the tools to the ears and the
mouth. This extension does:

```
MCP server ── initialize: capabilities.extensions["io.gitlab.matthewvuk/voice-vocabulary"] = { uri, language }
    │
    └─ resources/read uri ─► vocabulary document (terms, sound-alikes, pronunciations, definitions)
                                │
          voice client ─────────┼─► speech-to-text: Whisper prompt · keyterms · transcript corrections
                                ├─► text-to-speech: respellings · W3C PLS lexicon
                                └─► the model:      an attributed primer · definitions on demand
```

A client that doesn't know the extension ignores it and loses nothing.

| | |
|---|---|
| **[SPEC.md](SPEC.md)** | The extension: negotiation, the document, what clients do, security. Draft-1, English-first. |
| **[schema/](schema/vocabulary.schema.json)** | JSON Schema for the vocabulary document |
| **[js/](js/voice-vocabulary.js)** · **[python/](python/voice_vocabulary.py)** | Reference clients, no dependencies: read the extension from an MCP client, validate, and produce prompts, keyterms, corrections, respellings and PLS |
| **[conformance/](conformance/cases.json)** | Cases every client must pass; both reference clients do |
| **[examples/](examples/)** | `devops.vocabulary.json`, the small example in SPEC.md; `bark.vocabulary.json`, the canonical one from [bark-voice](https://gitlab.com/matthewvuk/bark-voice) (a bitcoin wallet on [bark-mcp](https://gitlab.com/ark-bitcoin/labs/bark-mcp), 101 terms) |
| **[packs/](packs/)** | Shared lexicons a server can build on, one language per file. The first ones come from the Bark example: `ark`, `lightning`, `bitcoin` (English) |
| **[PROPOSAL.md](PROPOSAL.md)** | The post for the MCP community discussion |

## Use it in a voice app

```js
import { fromMcpClient, transcriptionPrompt, keyterms, correct, pronounce, primer } from "./js/voice-vocabulary.js";

const vocab = await fromMcpClient(mcpClient);   // null when the server has none
if (vocab) {
  stt.prompt = transcriptionPrompt(vocab);       // Whisper initial_prompt / --prompt
  stt.keyterms = keyterms(vocab);                // Deepgram keyterm, AssemblyAI keyterms…
  systemPrompt += "\n\n" + primer(vocab);        // attributed, reference only
}
const { text, changes } = correct(transcript, [vocab]);   // "run cube cuddle" → "run kubectl"
await tts.speak(pronounce(reply, [vocab]));               // "kubectl" → "cube control"
```

```python
import voice_vocabulary as vv

vocab = await vv.from_mcp_session(session, init_result)
text, changes = vv.correct(transcript, [vocab])
```

## Publish one from your server

Advertise the extension in your server's capabilities and serve the document as a
resource (SPEC.md section 1). With the MCP TypeScript SDK:

```js
new Server(info, { capabilities: { resources: {}, extensions: {
  "io.gitlab.matthewvuk/voice-vocabulary": { uri: "my-server://vocabulary", language: "en" },
} } });
```

Validate it with `validate(doc)` from either client before you ship it.

## Tests

```bash
node --test js/test.mjs
cd python && python3 -m unittest -v test_voice_vocabulary
```

## Status

Draft, unofficial: not part of MCP or recognised by its governance. The plan is to
take it to the MCP community ([PROPOSAL.md](PROPOSAL.md)) as an experimental extension
([SEP-2133]) with bark-voice as the reference server, English first, and ask for review
on how to make it multilingual (SPEC.md, *Phase 2: languages*). The extension identifier will change if
it's adopted.

Apache-2.0 (see [LICENSE](LICENSE)), except the definitions marked `"quoted": true`
in `packs/` and `examples/`, which are Second's words from [second.tech/docs](https://second.tech/docs),
quoted with their source.

[SEP-2133]: https://modelcontextprotocol.io/seps/2133-extensions
