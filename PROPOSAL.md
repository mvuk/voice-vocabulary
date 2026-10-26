# Proposal: a voice vocabulary extension, so voice AIs speak your app's language

*Draft for [MCP GitHub Discussions](https://github.com/modelcontextprotocol/modelcontextprotocol/discussions)
or the MCP Discord, seeking an interest group and a sponsor for an experimental
extension ([SEP-2133](https://modelcontextprotocol.io/seps/2133-extensions)).*

---

The biggest frustration in talking to an AI by voice is not being understood. You
say something, and the transcript doesn't match what you said. The words it gets
wrong are the ones that matter most: your product's name, your team's jargon, the
acronym your whole app is built around. Every project has its own internal lexicon,
and a general speech model has never heard it. So the model acts on the wrong words,
asks you to repeat yourself, or answers about something you didn't say, and then
reads your product's name aloud wrongly.

The fixes exist, one per layer. Speech-to-text engines take vocabulary hints
(Whisper's prompt, Deepgram keyterms, AssemblyAI keyterms, Speechmatics' sounds-like
lists). Text-to-speech engines take pronunciation lexicons (W3C PLS, SSML). The
model takes context. But today someone fills these in by hand, per voice app, for
every tool they connect, and has to know each tool's domain to do it.

The MCP server already knows its domain. **MCP connects the model to the tools;
nothing connects the tools to the ears and the mouth.**

## The idea

An optional extension, `voice-vocabulary`. A server advertises it in its
capabilities and serves one engine-neutral document as a resource: its terms, what
speech-to-text tends to write instead of them, how to pronounce them, and short
definitions. A voice client that supports the extension reads it when it connects
and turns it into whatever its own engines take:

- **speech-to-text:** a Whisper prompt, a keyterm list, sounds-like entries, and
  corrections applied before the model reads the transcript;
- **text-to-speech:** respellings or a PLS lexicon;
- **the model:** a short primer, attributed and marked as reference, never as
  instructions.

The voice AI speaks the app's language from the first sentence. A client that
doesn't know the extension ignores it and loses nothing. Nothing here is specific
to one domain: a pharmacy server would publish drug names, a DevOps server
`kubectl` and its cluster names, a game its characters, a company's internal tools
their code names.

**Spec, schema and reference code:** https://github.com/mvuk/voice-vocabulary

- [SPEC.md](https://github.com/mvuk/voice-vocabulary/blob/main/SPEC.md):
  negotiation, the document, client behaviour, security
- Reference clients in JavaScript and Python, no dependencies, passing a shared
  conformance suite
- Corrections can only ever produce the server's own term, so a server can't
  rewrite what the user said into anything else, and clients must not apply them
  to spoken approvals ("yes, go ahead")

## Where it came from

I built a voice interface for a bitcoin wallet on top of Second's
[bark-mcp](https://gitlab.com/ark-bitcoin/labs/bark-mcp). Its words (*Ark*, *VTXO*,
*arkoor*) are its own, and unprompted, Whisper transcribed every "Ark" in a day of
recorded conversations as "arc". Making the voice app understand them took a prompt,
a keyterm list, corrections, a pronunciation lexicon and a primer, all by hand, for
one app. [bark-voice](https://gitlab.com/matthewvuk/bark-voice) now publishes them
through this extension and is the canonical example: a 101-term vocabulary whose
definitions are quoted from the project's own documentation.

## What I'd like feedback on

1. **Is this the right shape?** A capability pointing at a resource, versus a new
   resource type discovered by `mimeType`, versus something in the core spec.
2. **Languages.** Draft-1 is one language per document, English-first, on purpose.
   How should a server offer its lexicon in several languages: one resource per
   language, per-language blocks in one document, or stable term IDs linking
   separate documents? How should terms that stay in English inside other languages
   (but are pronounced and misheard differently) be modelled? (SPEC.md, *Phase 2*)
3. **Where it lives.** Is there an existing interest group this belongs in (voice,
   agents, client UX), or is there appetite for a voice/realtime interest group?
4. **Client adoption.** Voice frameworks (Pipecat, LiveKit Agents and others) are
   where this pays off. Who maintains MCP client code there and would review a
   reference integration?
