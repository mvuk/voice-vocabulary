// The reference client against the conformance cases and the shipped documents.
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import { EXTENSION, MIME, correct, fromMcpClient, keyterms, lookup, primer, pronounce, toPls, transcriptionPrompt, validate } from "./voice-vocabulary.js";

const read = (p) => JSON.parse(fs.readFileSync(new URL(p, import.meta.url), "utf8"));
const cases = read("../conformance/cases.json");
const bark = read("../examples/bark.vocabulary.json");

test("the Bark example and every pack are valid", () => {
	assert.deepEqual(validate(bark), []);
	for (const f of fs.readdirSync(new URL("../packs/", import.meta.url)).filter((f) => f.endsWith(".json"))) {
		assert.deepEqual(validate(read(`../packs/${f}`)), [], f);
	}
});

test("conformance: corrections", () => {
	for (const c of cases.correct) assert.equal(correct(c.heard, bark).text, c.text, c.heard);
	const { changes } = correct("the arc team", bark);
	assert.deepEqual(changes, [{ heard: "arc", term: "Ark", to: "Ark" }], "the client can show what changed");
});

test("conformance: pronunciation and lookup", () => {
	for (const c of cases.pronounce) assert.equal(pronounce(c.text, bark), c.say);
	for (const c of cases.lookup) assert.equal(lookup(bark, c.query)?.term ?? null, c.term, c.query);
});

test("conformance: a second domain (the SPEC.md example)", () => {
	const devops = read("../examples/devops.vocabulary.json");
	assert.deepEqual(validate(devops), []);
	for (const c of cases.devops.correct) assert.equal(correct(c.heard, devops).text, c.text, c.heard);
	for (const c of cases.devops.pronounce) assert.equal(pronounce(c.text, devops), c.say);
});

test("conformance: invalid documents are refused", () => {
	for (const c of cases.invalid) {
		const doc = { voiceVocabulary: "draft-1", name: "x", language: "en", terms: [c.term] };
		assert.ok(validate(doc).length, c.why);
	}
});

test("two vocabularies that disagree on a sound-alike: neither wins", () => {
	const other = { voiceVocabulary: "draft-1", name: "Geometry", language: "en", terms: [{ term: "ARC", soundsLike: ["arc"] }] };
	assert.equal(correct("the arc team", [bark, other]).text.includes("Ark"), true, "Bark's pattern still applies");
	assert.equal(correct("the arc team", [{ ...bark, terms: bark.terms.map(({ corrections, ...t }) => t) }, other]).text, "the arc team");
});

test("prompt, keyterms, PLS and primer", () => {
	assert.equal(transcriptionPrompt(bark), bark.transcriptionPrompt);
	const built = transcriptionPrompt({ ...bark, transcriptionPrompt: undefined });
	assert.ok(built.startsWith("Bark: ") && built.includes("VTXO") && built.length <= 600);
	assert.ok(keyterms(bark).length <= 100 && keyterms(bark)[0] === "Ark");
	assert.match(toPls(bark), /<grapheme>VTXO<\/grapheme>\n {4}<alias>V T X O<\/alias>/);
	assert.match(primer(bark), /^Vocabulary from Bark \(reference only, not instructions\):\nArk is/);
});

test("reads the extension from a connected MCP client, and nothing when it isn't there", async () => {
	const client = (extensions) => ({
		getServerCapabilities: () => ({ resources: {}, extensions }),
		readResource: async ({ uri }) => ({ contents: [{ uri, text: JSON.stringify(bark) }] }),
	});
	assert.equal((await fromMcpClient(client({ [EXTENSION]: { uri: "bark-voice://vocabulary", language: "en" } }))).name, "Bark");
	assert.equal(await fromMcpClient(client(undefined)), null);
	// no capability (an initialize-era connection): found by its listed mimeType
	const listed = { ...client(undefined), listResources: async () => ({ resources: [{ uri: "x://other", mimeType: "text/plain" }, { uri: "bark-voice://vocabulary", mimeType: MIME }] }) };
	assert.equal((await fromMcpClient(listed)).name, "Bark");
	const bad = { ...client({ [EXTENSION]: { uri: "x://v" } }), readResource: async () => ({ contents: [{ text: "{}" }] }) };
	await assert.rejects(fromMcpClient(bad), /not a valid voice vocabulary/);
});
