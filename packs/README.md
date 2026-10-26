# Packs

Shared word lists, one language per file (`<name>.<language>.json`), each a valid
draft-1 vocabulary document. A server can copy terms from a pack or list it in
`includes` (SPEC.md section 2.3).

| Pack | Terms | Definitions |
|---|---|---|
| `ark.en.json` | 38 | 35 quoted from [Second's docs](https://second.tech/docs/learn/glossary), 3 written here |
| `lightning.en.json` | 13 | written here |
| `bitcoin.en.json` | 31 | written here |

They were cut from the Bark vocabulary ([bark-voice](https://gitlab.com/matthewvuk/bark-voice),
`npm run vocabulary`), which builds its definitions from Second's docs and checks
every quote against them.

**The Ark pack uses Second's terminology.** Other Ark implementations name some
things differently; the glossary itself says *"Terminology can vary across different
organizations, so bear in mind these are specific to Second's implementation of the
Ark protocol."* An implementation-neutral Ark pack, written with the other Ark teams,
is the obvious next step.

Add a sound-alike when you see a mishearing in a real transcript, and a case for it
in `conformance/cases.json`.
