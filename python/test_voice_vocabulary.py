"""The Python reference client against the same conformance cases as the JS one."""

import asyncio
import json
import pathlib
import unittest

import voice_vocabulary as vv

ROOT = pathlib.Path(__file__).resolve().parent.parent
CASES = json.loads((ROOT / "conformance" / "cases.json").read_text())
BARK = json.loads((ROOT / "examples" / "bark.vocabulary.json").read_text())


class Conformance(unittest.TestCase):
    def test_documents_are_valid(self):
        self.assertEqual(vv.validate(BARK), [])
        for f in (ROOT / "packs").glob("*.json"):
            self.assertEqual(vv.validate(json.loads(f.read_text())), [], f.name)

    def test_corrections(self):
        for c in CASES["correct"]:
            self.assertEqual(vv.correct(c["heard"], BARK)[0], c["text"], c["heard"])
        self.assertEqual(vv.correct("the arc team", BARK)[1], [{"heard": "arc", "term": "Ark", "to": "Ark"}])

    def test_pronunciation_and_lookup(self):
        for c in CASES["pronounce"]:
            self.assertEqual(vv.pronounce(c["text"], BARK), c["say"])
        for c in CASES["lookup"]:
            found = vv.lookup(BARK, c["query"])
            self.assertEqual(found["term"] if found else None, c["term"], c["query"])

    def test_a_second_domain(self):
        devops = json.loads((ROOT / "examples" / "devops.vocabulary.json").read_text())
        self.assertEqual(vv.validate(devops), [])
        for c in CASES["devops"]["correct"]:
            self.assertEqual(vv.correct(c["heard"], devops)[0], c["text"], c["heard"])
        for c in CASES["devops"]["pronounce"]:
            self.assertEqual(vv.pronounce(c["text"], devops), c["say"])

    def test_invalid_documents_are_refused(self):
        for c in CASES["invalid"]:
            doc = {"voiceVocabulary": "draft-1", "name": "x", "language": "en", "terms": [c["term"]]}
            self.assertTrue(vv.validate(doc), c["why"])

    def test_prompt_keyterms_pls_primer(self):
        self.assertEqual(vv.transcription_prompt(BARK), BARK["transcriptionPrompt"])
        self.assertEqual(vv.keyterms(BARK)[0], "Ark")
        self.assertIn("<grapheme>VTXO</grapheme>\n    <alias>V T X O</alias>", vv.to_pls(BARK))
        self.assertTrue(vv.primer(BARK).startswith("Vocabulary from Bark (reference only, not instructions):\nArk is"))

    def test_reads_the_extension_from_capabilities(self):
        async def read(uri):
            return json.dumps(BARK)

        caps = {"resources": {}, "extensions": {vv.EXTENSION: {"uri": "bark-voice://vocabulary", "language": "en"}}}
        self.assertEqual(asyncio.run(vv.from_reader(caps, read))["name"], "Bark")
        self.assertIsNone(asyncio.run(vv.from_reader({"tools": {}}, read)))


if __name__ == "__main__":
    unittest.main()
