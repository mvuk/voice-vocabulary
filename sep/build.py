"""Regenerate sep/0000-voice-vocabulary.md from SPEC.md: MCP's SEP header, absolute links.

    python3 sep/build.py
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
REPO = "https://github.com/mvuk/voice-vocabulary"

spec = (ROOT / "SPEC.md").read_text()
head = f"""# SEP-0000: Voice Vocabulary

- **Status**: Proposal (awaiting sponsor)
- **Type**: Extensions Track
- **Created**: 2026-10-26
- **Author(s)**: Matthew Vuk (@mvuk)
- **Sponsor**: None
- **PR**: (to be filled in)
- **Extension identifier**: `io.github.mvuk/voice-vocabulary` (provisional; would become `io.modelcontextprotocol/voice-vocabulary` if accepted)
- **Full specification, schema and reference code**: {REPO}

"""
body = spec[spec.index("The key words MUST"):]
body = re.sub(r"\]\((?!https?://|#)([^)]+)\)", lambda m: f"]({REPO}/blob/main/{m.group(1)})", body)
(ROOT / "sep" / "0000-voice-vocabulary.md").write_text(head + body)
print("wrote sep/0000-voice-vocabulary.md")
