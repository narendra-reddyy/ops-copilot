import asyncio
import json
import os
import sys

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from mcp import ClientSession

try:
    from mcp.client.streamable_http import streamable_http_client as http_client
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client as http_client

load_dotenv()
MCP_URL = os.getenv("MCP_URL", "http://localhost:8080/mcp")
MODEL = os.getenv("MODEL", "claude-sonnet-5-5")
MAX_TOOL_CALLS = 8   # diagnostic checks; create_ticket is always allowed
MAX_ROUNDS = 12      # absolute safety stop for the whole loop

SYSTEM_PROMPT = """You are Ops Copilot, an IT incident triage assistant.
Investigate the incident the way an experienced infrastructure engineer would:

1. Start with the cheapest checks: reachability (ping_host), name resolution
   (dns_lookup), then the service port (check_port).
2. Use search_runbook with the symptoms you found to get the team's known fix.
3. Use parse_logs when logs could explain the failure (crashes, disk, refused).
4. Call create_ticket LAST, exactly once, with every check you ran and its result.

Rules:
- Base conclusions only on tool results. Say "likely cause", never "root cause".
- Never guess affected_users or reported_by. Leave them empty unless stated.
- Before each tool call, write one short sentence saying why you are running it.
- After create_ticket, finish with a 2-3 sentence plain-English summary.
- You have a budget of 8 diagnostic tool calls. create_ticket does not count.
- If DNS fails for a host, do not run ping_host or check_port on that host again."""


def mcp_tools_to_claude(mcp_tools):
    """Convert the MCP tool list into the format the Claude API expects."""
    claude_tools = []
    for t in mcp_tools:
        raw = getattr(t, "input_schema", None) or getattr(t, "inputSchema", None)
        schema = dict(raw or {"type": "object", "properties": {}})
        schema.pop("$schema", None)
        claude_tools.append({
            "name": t.name,
            "description": t.description or "",
            "input_schema": schema,
        })
    return claude_tools


async def run_agent(incident: str, on_event=print):
    """Run one triage. Calls on_event(kind, data) for every step.
    Returns (summary_text, ticket_dict_or_None)."""
    client = AsyncAnthropic()
    ticket, summary, tool_calls = None, "", 0

    async with http_client(MCP_URL) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = mcp_tools_to_claude((await session.list_tools()).tools)
            messages = [{"role": "user", "content": incident}]

            for _round in range(MAX_ROUNDS):
                response = await client.messages.create(
                    model=MODEL,
                    max_tokens=4000,
                    system=SYSTEM_PROMPT,
                    tools=tools,
                    messages=messages,
                )
                # Keep Claude's full reply (thinking + text + tool calls) in the history
                messages.append({"role": "assistant", "content": response.content})

                for block in response.content:
                    if block.type == "text" and block.text.strip():
                        on_event("thought", block.text.strip())
                        summary = block.text.strip()

                if response.stop_reason != "tool_use":
                    break  # Claude is done

                results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    is_ticket = block.name == "create_ticket"

                    if not is_ticket and tool_calls >= MAX_TOOL_CALLS:
                        # Budget used up: refuse more checks, but steer to the ticket
                        text = ("STOPPED: diagnostic budget used up. Do not run more checks. "
                                "Call create_ticket now with the evidence you have.")
                        is_error = True
                        on_event("result", {"name": block.name, "text": text})
                    else:
                        if not is_ticket:
                            tool_calls += 1
                        on_event("call", {"name": block.name, "input": block.input})
                        result = await session.call_tool(block.name, block.input)
                        text = "\n".join(c.text for c in result.content if c.type == "text")
                        is_error = bool(getattr(result, "is_error", getattr(result, "isError", False)))
                        on_event("result", {"name": block.name, "text": text})
                        if is_ticket:
                            try:
                                ticket = json.loads(text)
                            except json.JSONDecodeError:
                                ticket = {"raw": text}

                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": text,
                        "is_error": is_error,
                    })
                messages.append({"role": "user", "content": results})

    return summary, ticket


def print_event(kind, data):
    if kind == "thought":
        print(f"\nTHINKING: {data}")
    elif kind == "call":
        print(f"  -> {data['name']}({json.dumps(data['input'])})")
    elif kind == "result":
        print(f"  <- {data['text'][:300]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # Windows console: allow any character
    incident = " ".join(sys.argv[1:]) or (
        "Users report they cannot reach the status page at github.com on port 81. "
        "Other websites work fine."
    )
    print(f"INCIDENT: {incident}")
    summary, ticket = asyncio.run(run_agent(incident, print_event))
    print("\n=== TICKET DRAFT ===")
    print(json.dumps(ticket, indent=2) if ticket else "No ticket was created.")