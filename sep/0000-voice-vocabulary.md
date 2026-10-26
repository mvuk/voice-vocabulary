# SEP-0000: Voice Vocabulary

- **Status**: Draft
- **Type**: Extensions Track
- **Created**: 2026-10-26
- **Author(s)**: Matthew Vuk (@mvuk)
- **Sponsor**: None
- **PR**: (to be filled in)
- **Extension identifier**: `io.github.mvuk/voice-vocabulary` (provisional; would become `io.modelcontextprotocol/voice-vocabulary` if accepted)
- **Full specification, schema and reference code**: https://github.com/mvuk/voice-vocabulary
- **AI disclosure**: The proposal and its wording are currently AI-driven: this SEP, the reference clients, the Pipecat integration and this text were written primarily by Claude Code (Anthropic), under my direction. It is an early draft to establish the pattern. I will return to write it by hand and iterate on it thoughtfully as I plug it into more voice models and interfaces.

The key words MUST, MUST NOT, REQUIRED, SHALL, SHALL NOT, SHOULD, SHOULD NOT,
RECOMMENDED, NOT RECOMMENDED, MAY, and OPTIONAL in this document are to be
interpreted as described in BCP 14 ([RFC 2119], [RFC 8174]) when, and only when,
they appear in all capitals, as shown here.

## Abstract

The biggest frustration in talking to an AI by voice is not being understood: the
transcript doesn't match what you said, and the words it gets wrong are the ones
that matter most in your app. Every project has its own internal lexicon of product
names, jargon and acronyms, and a general speech model has never heard it.

This extension lets an MCP server publish that lexicon as a **vocabulary**: its
words, what speech-to-text writes instead of them, how to say them, and what they
mean. A voice client that supports the extension reads it when it connects, then
biases its speech-to-text towards those words, corrects transcripts before the
model sees them, teaches its text-to-speech to pronounce them, and gives the model
a short primer. The voice AI speaks the app's language from the first sentence.
Clients that don't support the extension lose nothing.

## Motivation

You ask a voice assistant to "run cube control on staging", and it hears "cube
cuddle". You ask about your company's product, and the transcript has a common word
in its place. The model then calls the wrong tool, asks what you meant, or answers
confidently about something you didn't say. Its reply reads your product's name
aloud wrongly. None of this is the model's fault: it was handed the wrong words.

The fix is well known, and every layer already supports it:

- Speech-to-text engines take vocabulary hints: Whisper an `initial_prompt`,
  Deepgram a `keyterm` list, AssemblyAI keyterms, Speechmatics an additional
  vocabulary with `sounds_like`.
- Text-to-speech engines take pronunciation lexicons ([W3C PLS]) or SSML.
- The model takes context.

But today each of these is filled in by hand, by whoever wires up the voice app,
who has to know every connected tool's domain and every engine's format. The tool
server already knows its domain. MCP connects the model to the tools; nothing
connects the tools to the ears and the mouth.

This extension does that. The server says, once and in one engine-neutral document,
which words its domain uses; each client turns that into whatever its engines take.
A pharmacy server publishes drug names, a DevOps server `kubectl` and its cluster
names, a game server its characters, a company's internal tools their code names.

## Specification

### 1. Negotiation

A server that publishes a vocabulary MUST advertise the extension in the
`capabilities.extensions` map of its `initialize` result, with a settings object
naming the vocabulary resource:

```json
{
  "capabilities": {
    "resources": {},
    "extensions": {
      "io.github.mvuk/voice-vocabulary": {
        "uri": "example-server://vocabulary",
        "language": "en"
      }
    }
  }
}
```

| Setting | Type | |
|---|---|---|
| `uri` | string | REQUIRED. The URI of a resource holding a vocabulary document (section 2). |
| `language` | string | REQUIRED. BCP 47 tag of the speech the vocabulary is for; the same as the document's `language`. |

The server MUST also declare the `resources` capability, MUST serve the document
through `resources/read` at `uri` with `mimeType` `application/vnd.voice-vocabulary+json`,
and MUST list it in `resources/list` with that `mimeType`.

**Finding the vocabulary.** A client SHOULD look for the capability first (in the
`server/discover` result from protocol version 2026-07-28, or the `initialize`
result where it carries extensions). If the capability isn't there, the client
SHOULD fall back to `resources/list` and use the first resource whose `mimeType`
is `application/vnd.voice-vocabulary+json`. The fallback matters in practice:
protocol versions up to 2025-11-25 have no `extensions` field, and SDKs drop it
on those connections (the MCP Python SDK 2.3 does), while most voice frameworks
still connect with the `initialize` handshake.

A client that supports the extension MAY advertise it in its own `initialize`
request, with an empty settings object. A server MUST NOT require it: the
vocabulary is useful to any client that finds it.

**One language per vocabulary.** In this draft a vocabulary is in exactly one
language, and a server advertises one. Recognition, sound-alikes and pronunciation
are all specific to a language. How a server offers its terms in several languages
is left to a later draft (see *Phase 2: languages*).

### 2. The vocabulary document

A JSON object. [`schema/vocabulary.schema.json`](https://github.com/mvuk/voice-vocabulary/blob/main/schema/vocabulary.schema.json) is
its JSON Schema; where the two differ, this text wins. Clients MUST ignore fields
they don't know, so later drafts can add fields without breaking them.

```json
{
  "voiceVocabulary": "draft-1",
  "name": "Example DevOps",
  "language": "en",
  "description": "Deploys and cluster operations for Example Corp.",
  "updated": "2026-10-26",
  "primer": "kubectl is the command-line tool for Kubernetes clusters. Staging and prod are the two clusters.",
  "terms": [
    {
      "term": "kubectl",
      "category": "tools",
      "soundsLike": ["cube control", "cube cuddle", "cube c t l", "kube control"],
      "pronounce": { "alias": "cube control" },
      "boost": true,
      "summary": "kubectl is the command-line tool for Kubernetes clusters.",
      "definition": "The Kubernetes command-line tool, for running commands against Kubernetes clusters.",
      "source": "https://kubernetes.io/docs/reference/kubectl/",
      "quoted": false
    }
  ]
}
```

#### 2.1 Top level

| Field | Type | |
|---|---|---|
| `voiceVocabulary` | string | REQUIRED. The version of this specification: `"draft-1"`. |
| `name` | string | REQUIRED. What the vocabulary is for, shown to people and used to attribute it to the model. |
| `language` | string | REQUIRED. BCP 47 tag of the words' language. |
| `terms` | Term[] | REQUIRED. At most 2,000. |
| `description` | string | OPTIONAL. One sentence. |
| `source` | string | OPTIONAL. URL of the material the vocabulary was built from. |
| `updated` | string | OPTIONAL. ISO 8601 date. Clients MAY use it to cache. |
| `primer` | string | OPTIONAL. At most 2,000 characters of plain text for the model (section 3.3). |
| `transcriptionPrompt` | string | OPTIONAL. A prompt the server has tuned for Whisper-style engines, at most 224 tokens (section 3.1). |
| `includes` | string[] | OPTIONAL. URIs of other vocabulary documents this one builds on (section 2.3). |

#### 2.2 Term

| Field | Type | |
|---|---|---|
| `term` | string | REQUIRED. The canonical written form: what transcripts are corrected to. |
| `category` | string | OPTIONAL. A free-form group. |
| `aliases` | string[] | OPTIONAL. Other written forms with the same meaning (plurals, long names, former names). |
| `soundsLike` | string[] | OPTIONAL. Plain text that speech-to-text may produce for the term, compared case-insensitively as whole words; spaces also match `.` or `-` or nothing ("cube c t l" matches "cube ctl"). |
| `corrections` | Correction[] | OPTIONAL. Patterns for mistakes `soundsLike` can't express (section 2.4). |
| `pronounce` | object | OPTIONAL. `alias`: how to respell the term for text-to-speech; `ipa`: its pronunciation in IPA. At least one if present. |
| `boost` | boolean | OPTIONAL. The term is rare enough that speech-to-text should be biased towards it. Default `false`. |
| `summary` | string | OPTIONAL. One sentence, at most 300 characters, fit to be spoken. |
| `definition` | string | OPTIONAL. What the term means, at most 1,500 characters. |
| `source` | string | OPTIONAL. URL the definition comes from. |
| `quoted` | boolean | OPTIONAL. `true` when `definition` is copied verbatim from `source`; `false` or absent when the vocabulary's author wrote it. |

A term with no `definition` is for recognition only.

#### 2.3 Includes

`includes` lets a vocabulary build on shared word lists (*packs*) instead of copying
them. A client MAY fetch included documents (by `resources/read` for MCP URIs, by
HTTP GET for `https` URLs), MUST NOT follow more than 8 includes per vocabulary,
and MUST NOT follow cycles. When a term appears in both, the including document's
entry wins.

#### 2.4 Corrections

A correction is `{ "match": <pattern>, "replace": <replacement> }`.

- `match` MUST be at most 200 characters and MUST use only this regular-expression
  subset, which ECMAScript and Python's `re` read the same way: literal characters,
  `.`, character classes `[...]` and `[^...]`, `\b`, `\s`, `\d`, `\w`, groups `(...)`
  and `(?:...)`, lookahead `(?=...)` and `(?!...)`, alternation `|`, and the
  quantifiers `?`, `*`, `+`, `{m}`, `{m,}`, `{m,n}`. No lookbehind, backreferences,
  named groups or inline flags.
- Matching is case-insensitive, over the whole transcript, every occurrence.
  `\w`, `\d` and `\b` use ASCII word characters (ECMAScript's default; Python's
  `re.ASCII`), so every client agrees on where a word ends.
- `replace` MUST be the term itself or one of its aliases, optionally followed by
  group references `$1` to `$9` (each replaced by that group's text, or nothing).
  Clients MUST reject a correction whose `replace` is anything else. A correction
  can only turn a mishearing into the term; it can never insert other words.

Example: `{ "match": "\\bk[ .-]?8[ .-]?s\\b", "replace": "k8s" }`, on a term
`Kubernetes` with the alias `k8s`.

### 3. What a client does with it

A client reads the document once per connection (or from cache, per `updated`) and
uses the parts that fit its engines. Every part is OPTIONAL for the client.

#### 3.1 Speech-to-text

- **Whisper-style prompts** (`initial_prompt`, `--prompt`, a transcription
  `prompt`): use `transcriptionPrompt` if present. Otherwise build one from `name`
  and the `boost` terms, most important first, within 224 tokens.
- **Keyterm lists** (Deepgram `keyterm`, AssemblyAI keyterms, faster-whisper
  `hotwords`): the `boost` terms, then other terms if the engine has room.
- **Sounds-like vocabularies** (e.g. Speechmatics `additional_vocab`): each term
  with its `soundsLike`.
- **Corrections**: after transcription and before the model sees the text, replace
  whole-word, case-insensitive matches of each `soundsLike` with `term`, then apply
  each `corrections` entry.

A client MUST NOT apply corrections to text whose exact wording decides an action
the user has to approve, such as a spoken "yes, go ahead" confirming a purchase.
Such decisions SHOULD be made on the raw transcript.

#### 3.2 Text-to-speech

Before synthesis, a client MAY replace each `term` (and its plural, `term` + "s")
with `pronounce.alias`, or emit `<sub alias="…">` or `<phoneme alph="ipa" ph="…">`
for engines that take SSML. Text shown on screen SHOULD keep the canonical `term`.
A vocabulary converts directly to a [W3C PLS] lexicon (each `term` a `<grapheme>`,
`pronounce.alias` an `<alias>`, `pronounce.ipa` a `<phoneme>`).

#### 3.3 The model

A client MAY add `primer` to the model's context. It MUST present it as reference
material from the named server, not as instructions: for example, under a heading
such as *Vocabulary from <name> (reference only)*. Clients SHOULD let the user
turn primers off. Definitions are for answering "what does this mean?": a client
MAY give the model a local lookup over `terms`, and a server MAY offer its own tool
for the same purpose.

#### 3.4 Several servers

When a client is connected to several servers with vocabularies, it SHOULD merge
them for speech-to-text and text-to-speech, keep each primer attributed to its
server, and share any keyterm or prompt budget between them. If two vocabularies
map the same sound-alike to different terms, the client SHOULD apply neither, and
SHOULD keep both terms' keyterms.

### 4. Graceful degradation

A client that doesn't support the extension ignores the capability; the server's
tools work unchanged. A server that has a vocabulary SHOULD still make its tool
descriptions and results understandable without it.

## Rationale

- **A resource, not a new method.** Resources already exist, are cached by some
  clients, and can be read by a client that doesn't know this extension at all.
  The capability only says which resource it is.
- **Discoverable without the capability.** Building the reference Pipecat
  integration showed that a capability alone isn't enough today: Pipecat connects
  with the `initialize` handshake, which can't carry `extensions`. Listing the
  resource under its own `mimeType` makes the vocabulary findable on every
  protocol version, with no SDK changes.
- **Engine-neutral, client-converted.** Engines change faster than a spec can.
  The document carries facts (spellings, sound-alikes, pronunciations, boost
  priority); each client maps them to the parameters its engines take.
- **`soundsLike` first, patterns second.** Plain sound-alikes are portable and map
  straight onto engines that accept them; patterns cover spelled-out letters and
  numbers.
- **Replacements are restricted to the term.** A correction that could insert any
  text would let a server rewrite what the user said (see *Security implications*).
- **Provenance per definition.** `source` and `quoted` let a listener tell the
  domain's own words from a vocabulary author's paraphrase.
- **The server is the right owner.** It knows its lexicon, and it changes when the
  product does; a vocabulary maintained in each voice app goes stale.
- **Related standards.** [W3C PLS] for pronunciation (section 3.2 maps onto it);
  SSML `<sub>` and `<phoneme>`; vendor keyterm and custom-vocabulary features, which
  this document feeds rather than replaces.

## Backward compatibility

Purely additive. The extension uses the `capabilities.extensions` map and resources
that MCP already has, and changes no existing message. Clients and servers that
don't know it are unaffected (section 4). A breaking change to the document will
get a new `voiceVocabulary` version and, per SEP-2133, a new extension identifier;
clients MUST ignore documents whose version they don't support.

## Security implications

A vocabulary comes from the server and is untrusted input to the client.

1. **Prompt injection through the primer or definitions.** A server can put any
   text in `primer`. Clients MUST attribute it, MUST NOT present it as system
   instructions, SHOULD enforce the length limits, and SHOULD let users disable it.
2. **Rewriting what the user said.** Corrections are limited to producing the term
   (section 2.4) and MUST NOT touch approval decisions (section 3.1). A server can
   still turn a common word into its term: sometimes rightly (a DevOps tool's
   "cube cuddle" → `kubectl`), sometimes not. Clients SHOULD let the user see which
   corrections changed a transcript, MAY drop sound-alikes that are common words
   when the conversation isn't about the server's domain, and SHOULD skip
   corrections that two servers dispute (section 3.4).
3. **Expensive patterns.** Clients MUST enforce the pattern limits in section 2.4
   and SHOULD bound the time spent applying corrections to one transcript.
4. **Size.** Clients SHOULD reject documents over 1 MB or with more than 2,000 terms.
5. **Includes.** Fetching an `https` include reveals the client's address to that
   host. Clients SHOULD follow only includes on the same server, or on hosts the
   user allowed.

## Inspiration and reference implementation

This came out of building a voice interface for a bitcoin wallet. The wallet's
MCP server, Second's [bark-mcp], is precise and well documented, but its words
(*Ark*, *VTXO*, *arkoor*, *BOLT11*) are its own. Unprompted, Whisper large-v3-turbo
transcribed every "Ark" in a day of recorded conversations as "arc". Teaching a
voice app those words took a Whisper prompt, a keyterm list, transcript
corrections, a pronunciation lexicon and a primer, all assembled by hand for one
app. That's the work this extension moves to the server, once, for every voice app.

- **Server:** [bark-voice], a voice connector built on [bark-mcp]. It advertises
  the extension and serves a 101-term vocabulary, 48 of its definitions quoted
  from its project's documentation and checked against it at build time. It is the
  canonical example: [`examples/bark.vocabulary.json`](https://github.com/mvuk/voice-vocabulary/blob/main/examples/bark.vocabulary.json).
- **Clients:** [`js/voice-vocabulary.js`](https://github.com/mvuk/voice-vocabulary/blob/main/js/voice-vocabulary.js) and
  [`python/voice_vocabulary.py`](https://github.com/mvuk/voice-vocabulary/blob/main/python/voice_vocabulary.py), no dependencies. They
  read the extension from a connected MCP client, validate the document, and
  produce a Whisper prompt, keyterms, corrected transcripts, respelled speech and a
  PLS lexicon. Both pass [`conformance/cases.json`](https://github.com/mvuk/voice-vocabulary/blob/main/conformance/cases.json).
- **Voice framework:** [`integrations/pipecat/`](https://github.com/mvuk/voice-vocabulary/blob/main/integrations/pipecat/), for
  [Pipecat](https://github.com/pipecat-ai/pipecat). One processor after the STT
  service sends it keyterms in its own field (Deepgram, AssemblyAI, ElevenLabs,
  Cartesia, Whisper, OpenAI, Groq), gives the LLM the primer and corrects
  transcripts; the server's pronunciations become TTS text transforms. Tested
  against Pipecat 1.14.0 with a real MCP server process.

## Phase 2: languages (asking for review)

Draft-1 is English-first on purpose: one language per document, so it can be
shipped and tested without settling translation. But a project's lexicon is the
natural place to pin its terms down across languages too, and voice apps need it:
a Japanese speaker says `kubectl` in katakana, and Whisper's Japanese mishearings
are not its English ones. The questions we'd like reviewers' views on:

1. **Offering several languages.** Options: (a) the capability lists one
   `{ language, uri }` per language and the client picks by its speech language;
   (b) one document with per-language blocks; (c) one resource URI with the
   language as a parameter.
2. **Linking a term across languages.** Should terms carry a stable `id`, so a
   client knows the Japanese entry is the English one? Does a definition get
   translated, or quoted only in the language its source was written in?
3. **Terms that don't translate.** Many technical terms stay in Latin letters
   inside other languages but are pronounced and misheard differently. Is that a
   separate term per language, or one term with per-language `soundsLike` and
   `pronounce`?
4. **Mixed-language speech.** People switch languages mid-sentence. Should a
   client apply several languages' vocabularies at once?
5. **Prior art to reuse.** Terminology standards (TBX, ISO 30042; SKOS) already
   model multilingual concepts. How much of them belongs here?

## Open questions

- Should a vocabulary be able to change mid-session (a
  `notifications/resources/updated` on its URI is the obvious mechanism)?
- Should packs (shared lexicons several servers include) have a registry, or are
  `includes` with URLs enough?
- Is a capability plus a resource the right shape? This draft uses both: the
  capability where the protocol carries it, the `mimeType` where it doesn't.
  Should the `mimeType` alone be enough?

[SEP-2133]: https://modelcontextprotocol.io/seps/2133-extensions
[RFC 2119]: https://www.rfc-editor.org/rfc/rfc2119
[RFC 8174]: https://www.rfc-editor.org/rfc/rfc8174
[W3C PLS]: https://www.w3.org/TR/pronunciation-lexicon/
[bark-voice]: https://gitlab.com/matthewvuk/bark-voice
[bark-mcp]: https://gitlab.com/ark-bitcoin/labs/bark-mcp
