"""Voice vocabulary for Pipecat: the MCP servers a bot connects to teach its
speech-to-text, its model and its text-to-speech their own words.

    mcp = MCPClient(server_params=...)
    tools = await mcp.tools()
    vocab = await VoiceVocabulary.from_mcp(mcp)      # empty if the server publishes none

    pipeline = Pipeline([
        transport.input(),
        stt,
        vocab.processor(stt=stt),   # keyterms to the STT, primer to the LLM, transcripts corrected
        user_aggregator,
        llm,
        tts,
        transport.output(),
        assistant_aggregator,
    ])
    vocab.install_tts(tts)          # the server's pronunciations

Implements the io.github.mvuk/voice-vocabulary MCP extension
(https://github.com/mvuk/voice-vocabulary, SPEC.md) on Pipecat's own extension
points: STTUpdateSettingsFrame, LLMMessagesAppendFrame, TTS text transforms.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from loguru import logger

from pipecat.frames.frames import (
    Frame,
    InterimTranscriptionFrame,
    LLMMessagesAppendFrame,
    StartFrame,
    STTUpdateSettingsFrame,
    TranscriptionFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

import voice_vocabulary as vv

# Each STT service names its vocabulary setting differently. Lists of terms,
# in order of preference; a service gets the first one it has.
_KEYTERM_FIELDS = ("keyterm", "keyterms", "keyterms_prompt", "keywords")
# Free-text prompts (Whisper-style); used when the service has no keyterm list,
# except initial_prompt, which a local Whisper takes alongside hotwords.
_PROMPT_FIELDS = ("initial_prompt", "prompt")


class VoiceVocabulary:
    """The vocabularies of one or more MCP servers, ready for a Pipecat pipeline."""

    def __init__(self, documents: list[dict] | None = None):
        """Wrap already-validated vocabulary documents (see ``from_mcp``)."""
        self.documents = [d for d in documents or [] if d]

    def __bool__(self) -> bool:
        return bool(self.documents)

    @classmethod
    async def from_mcp(cls, *clients: Any) -> "VoiceVocabulary":
        """Read the vocabulary each connected ``MCPClient`` advertises.

        A server without the extension contributes nothing; one whose document
        is invalid is logged and skipped, so a bad vocabulary never stops a bot.
        """
        documents = []
        for client in clients:
            session = await _session(client)
            if session is None:
                continue
            try:
                doc = await vv.from_mcp_session(session)
            except Exception as e:  # invalid document, unreadable resource
                logger.warning(f"voice vocabulary from {client} skipped: {e}")
                continue
            if doc:
                logger.info(f"voice vocabulary: {doc['name']} ({doc['language']}), {len(doc['terms'])} terms")
                documents.append(doc)
        return cls(documents)

    # ---------- speech-to-text ----------

    def keyterms(self, limit: int = 100) -> list[str]:
        return vv.keyterms(self.documents, limit)

    def transcription_prompt(self) -> str:
        return " ".join(vv.transcription_prompt(d) for d in self.documents)

    def stt_settings(self, stt: Any) -> Any | None:
        """A settings delta for this STT service, in the fields it actually has.

        Deepgram ``keyterm``, ElevenLabs and Cartesia ``keyterms``, AssemblyAI
        ``keyterms_prompt``, local Whisper ``hotwords`` + ``initial_prompt``,
        OpenAI and Groq ``prompt``. None when the service takes none of them.
        """
        if not self.documents:
            return None
        settings_cls = getattr(type(stt), "Settings", None) or type(getattr(stt, "_settings", None))
        if not dataclasses.is_dataclass(settings_cls):
            return None
        fields = {f.name for f in dataclasses.fields(settings_cls)}
        values: dict[str, Any] = {}
        keyterm_field = next((f for f in _KEYTERM_FIELDS if f in fields), None)
        if keyterm_field:
            values[keyterm_field] = self.keyterms()
        if "hotwords" in fields:
            values["hotwords"] = ", ".join(self.keyterms(50))
        if "initial_prompt" in fields:
            values["initial_prompt"] = self.transcription_prompt()
        elif "prompt" in fields and not keyterm_field:
            values["prompt"] = self.transcription_prompt()
        return settings_cls(**values) if values else None

    # ---------- the model ----------

    def primer_messages(self) -> list[dict]:
        """One system message per vocabulary with a primer: attributed, reference only."""
        return [{"role": "system", "content": vv.primer(d)} for d in self.documents if d.get("primer")]

    # ---------- transcripts ----------

    def correct(self, text: str) -> tuple[str, list[dict]]:
        return vv.correct(text, self.documents)

    def processor(self, stt: Any = None, *, primer: bool = True) -> "VocabularyProcessor":
        """The processor to place right after the STT service."""
        return VocabularyProcessor(self, stt=stt, primer=primer)

    # ---------- text-to-speech ----------

    def install_tts(self, tts: Any) -> None:
        """Register the vocabularies' pronunciations with a TTS service.

        Respellings (``pronounce.alias``) are a text transform; IPA
        (``pronounce.ipa``) goes through the service's own
        ``pronunciation_transform_ipa``, registered last as Pipecat requires.
        Captions and the LLM context keep the canonical spelling.
        """
        if not self.documents:
            return
        documents = self.documents

        async def respell(text: str, text_type: str) -> str:
            return vv.pronounce(text, documents)

        tts.add_text_transformer(respell)
        ipa = {t["term"]: t["pronounce"]["ipa"] for d in documents for t in d["terms"] if (t.get("pronounce") or {}).get("ipa")}
        if ipa and hasattr(tts, "pronunciation_transform_ipa"):
            tts.add_text_transformer(tts.pronunciation_transform_ipa(ipa))


class VocabularyProcessor(FrameProcessor):
    """Place right after the STT service.

    At start it sends the STT service its keyterms or prompt (upstream) and the
    LLM the primer (downstream). Then it corrects every transcription before the
    user aggregator reads it, keeping the raw text and the changes in
    ``frame.metadata["voice_vocabulary"]``. Decide anything a user must approve
    (a spoken "yes, go ahead") from that raw text, never the corrected one.
    """

    def __init__(self, vocabulary: VoiceVocabulary, *, stt: Any = None, primer: bool = True, **kwargs):
        super().__init__(**kwargs)
        self._vocabulary = vocabulary
        self._stt = stt
        self._primer = primer

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, StartFrame):
            await self.push_frame(frame, direction)
            await self._configure()
            return

        if isinstance(frame, (TranscriptionFrame, InterimTranscriptionFrame)) and self._vocabulary:
            text, changes = self._vocabulary.correct(frame.text)
            if changes:
                frame.metadata["voice_vocabulary"] = {"raw": frame.text, "changes": changes}
                if isinstance(frame, TranscriptionFrame):
                    logger.debug(f"{self}: {frame.text!r} → {text!r}")
                frame.text = text

        await self.push_frame(frame, direction)

    async def _configure(self):
        if not self._vocabulary:
            return
        if self._stt is not None:
            delta = self._vocabulary.stt_settings(self._stt)
            if delta is not None:
                await self.push_frame(STTUpdateSettingsFrame(delta=delta, service=self._stt), FrameDirection.UPSTREAM)
        if self._primer and (messages := self._vocabulary.primer_messages()):
            await self.push_frame(LLMMessagesAppendFrame(messages=messages, run_llm=False))


async def _session(client: Any):
    """The MCP session behind a Pipecat MCPClient, connecting it if needed.

    MCPClient doesn't expose its session or the server's capabilities yet;
    upstream that would be a public ``server_capabilities`` and ``read_resource``.
    """
    if hasattr(client, "server_capabilities") and hasattr(client, "read_resource"):
        return client
    getter = getattr(client, "_get_active_session", None)
    if getter is None:
        return None
    try:
        return getter()
    except Exception:
        await client.start()
        return getter()
