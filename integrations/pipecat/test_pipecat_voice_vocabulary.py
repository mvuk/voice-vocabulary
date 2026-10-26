"""The Pipecat integration against a real MCP server, real Pipecat processors and
the real settings classes of Pipecat's STT services.

    cd integrations/pipecat && python -m unittest -v test_pipecat_voice_vocabulary
"""

import dataclasses
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "python"))

from mcp import StdioServerParameters  # noqa: E402
from pipecat.frames.frames import LLMMessagesAppendFrame, STTUpdateSettingsFrame, TranscriptionFrame  # noqa: E402
from pipecat.services.assemblyai.stt import AssemblyAISTTService  # noqa: E402
from pipecat.services.cartesia.stt import CartesiaSTTService  # noqa: E402
from pipecat.services.cartesia.tts import CartesiaTTSService  # noqa: E402
from pipecat.services.deepgram.stt import DeepgramSTTService  # noqa: E402
from pipecat.services.elevenlabs.stt import ElevenLabsSTTService  # noqa: E402
from pipecat.services.groq.stt import GroqSTTService  # noqa: E402
from pipecat.services.mcp_service import MCPClient  # noqa: E402
from pipecat.services.openai.stt import OpenAISTTService  # noqa: E402
from pipecat.tests.utils import run_test  # noqa: E402

from pipecat_voice_vocabulary import VoiceVocabulary  # noqa: E402

DEVOPS = ROOT / "examples" / "devops.vocabulary.json"
BARK = ROOT / "examples" / "bark.vocabulary.json"
SERVER = pathlib.Path(__file__).with_name("vocab_server.py")


def mcp_client(vocabulary: pathlib.Path, *extra: str) -> MCPClient:
    return MCPClient(server_params=StdioServerParameters(command=sys.executable, args=[str(SERVER), str(vocabulary), *extra]))


def stt_like(service_cls):
    """Something shaped like a service of this class, without connecting anywhere."""
    return type(f"Fake{service_cls.__name__}", (), {"Settings": service_cls.Settings})()


@dataclasses.dataclass
class LocalWhisperSettings:  # the fields of pipecat.services.whisper.stt.WhisperSTTSettings
    hotwords: str | None = None
    initial_prompt: str | None = None


class FromMCP(unittest.IsolatedAsyncioTestCase):
    async def test_finds_the_vocabulary_on_pipecats_initialize_era_connection(self):
        mcp = mcp_client(DEVOPS)
        try:
            tools = await mcp.tools()
            self.assertEqual([t.name for t in tools.standard_tools], ["ping"], "tools work as before")
            vocab = await VoiceVocabulary.from_mcp(mcp)
        finally:
            await mcp.close()
        self.assertEqual([d["name"] for d in vocab.documents], ["Example DevOps"])
        self.assertEqual(vocab.correct("run cube cuddle on staging")[0], "run kubectl on staging")

    async def test_a_server_without_a_vocabulary_changes_nothing(self):
        mcp = mcp_client(DEVOPS, "--no-vocabulary")
        try:
            vocab = await VoiceVocabulary.from_mcp(mcp)
        finally:
            await mcp.close()
        self.assertFalse(vocab)
        self.assertIsNone(vocab.stt_settings(stt_like(DeepgramSTTService)))


class STTSettings(unittest.TestCase):
    vocab = VoiceVocabulary([__import__("json").loads(BARK.read_text())])

    def given(self, delta):
        return {f.name: getattr(delta, f.name) for f in dataclasses.fields(delta) if isinstance(getattr(delta, f.name), (list, str))}

    def test_each_service_gets_its_own_field(self):
        cases = {
            DeepgramSTTService: "keyterm",
            ElevenLabsSTTService: "keyterms",
            CartesiaSTTService: "keyterm",
            AssemblyAISTTService: "keyterms_prompt",
        }
        for service, field in cases.items():
            given = self.given(self.vocab.stt_settings(stt_like(service)))
            self.assertEqual(list(given), [field], service.__name__)
            self.assertEqual(given[field][:3], ["Ark", "VTXO", "arkoor"], service.__name__)

    def test_prompt_services_get_the_transcription_prompt(self):
        for service in (OpenAISTTService, GroqSTTService):
            given = self.given(self.vocab.stt_settings(stt_like(service)))
            field = "prompt" if "prompt" in given else next(iter(given))
            self.assertIn(field, ("prompt", "keywords"), service.__name__)
            if field == "prompt":
                self.assertTrue(given["prompt"].startswith("A conversation about a Bark bitcoin wallet"))

    def test_local_whisper_gets_hotwords_and_a_prompt(self):
        local = type("LocalWhisper", (), {"Settings": LocalWhisperSettings})()
        given = self.given(self.vocab.stt_settings(local))
        self.assertEqual(sorted(given), ["hotwords", "initial_prompt"])
        self.assertTrue(given["hotwords"].startswith("Ark, VTXO"))


class InThePipeline(unittest.IsolatedAsyncioTestCase):
    async def test_one_processor_configures_the_stt_primes_the_llm_and_corrects_transcripts(self):
        vocab = VoiceVocabulary([__import__("json").loads(BARK.read_text())])
        stt = stt_like(DeepgramSTTService)
        down, up = await run_test(
            vocab.processor(stt=stt),
            frames_to_send=[TranscriptionFrame(text="can I board into arc and refresh my v t x os", user_id="u", timestamp="0")],
        )
        settings = [f for f in up if isinstance(f, STTUpdateSettingsFrame)]
        self.assertEqual(len(settings), 1)
        self.assertIs(settings[0].service, stt)
        self.assertEqual(settings[0].delta.keyterm[:2], ["Ark", "VTXO"])
        primer = [f for f in down if isinstance(f, LLMMessagesAppendFrame)]
        self.assertTrue(primer[0].messages[0]["content"].startswith("Vocabulary from Bark (reference only, not instructions):"))
        self.assertFalse(primer[0].run_llm)
        transcript = next(f for f in down if isinstance(f, TranscriptionFrame))
        self.assertEqual(transcript.text, "can I board into Ark and refresh my VTXOs")
        self.assertEqual(transcript.metadata["voice_vocabulary"]["raw"], "can I board into arc and refresh my v t x os")

    async def test_without_a_vocabulary_the_processor_is_a_pass_through(self):
        down, up = await run_test(
            VoiceVocabulary([]).processor(stt=stt_like(DeepgramSTTService)),
            frames_to_send=[TranscriptionFrame(text="the arc team", user_id="u", timestamp="0")],
        )
        self.assertFalse([f for f in up if isinstance(f, STTUpdateSettingsFrame)])
        self.assertEqual(next(f for f in down if isinstance(f, TranscriptionFrame)).text, "the arc team")


class Speech(unittest.IsolatedAsyncioTestCase):
    async def test_tts_says_the_servers_words_its_way(self):
        vocab = VoiceVocabulary([__import__("json").loads(DEVOPS.read_text())])
        tts = CartesiaTTSService(api_key="test", voice_id="test")
        before = len(tts._text_transforms)
        vocab.install_tts(tts)
        _, respell = tts._text_transforms[before]
        self.assertEqual(await respell("Run kubectl now.", "sentence"), "Run cube control now.")


if __name__ == "__main__":
    unittest.main()
