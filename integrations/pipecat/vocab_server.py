"""A minimal MCP server that publishes a voice vocabulary: the test fixture.

    python vocab_server.py <vocabulary.json> [--no-vocabulary]
"""

import pathlib
import sys

import anyio
from mcp import types
from mcp.server.lowlevel.server import Server
from mcp.server.stdio import stdio_server

EXTENSION = "io.github.mvuk/voice-vocabulary"
URI = "test://vocabulary"
DOCUMENT = pathlib.Path(sys.argv[1]).read_text()


NONE = "--no-vocabulary" in sys.argv


async def list_resources(ctx, params):
    if NONE:
        return types.ListResourcesResult(resources=[])
    return types.ListResourcesResult(resources=[types.Resource(uri=URI, name="vocabulary", mime_type="application/vnd.voice-vocabulary+json")])


async def read_resource(ctx, params):
    return types.ReadResourceResult(contents=[types.TextResourceContents(uri=URI, mime_type="application/vnd.voice-vocabulary+json", text=DOCUMENT)])


async def list_tools(ctx, params):
    return types.ListToolsResult(tools=[types.Tool(name="ping", description="Answers pong.", input_schema={"type": "object", "properties": {}})])


async def main():
    server = Server("vocab-test", on_list_resources=list_resources, on_read_resource=read_resource, on_list_tools=list_tools)
    async with stdio_server() as (read, write):
        # Advertised for 2026-07-28 clients (server/discover). Pipecat connects with
        # the initialize handshake, which can't carry extensions, so it finds the
        # vocabulary by the listed resource's mimeType instead (SPEC 1).
        if not NONE:
            server.extensions = {EXTENSION: {"uri": URI, "language": "en"}}
        await server.run(read, write, server.create_initialization_options())


anyio.run(main)
