import asyncio
import json
import time

import streamlit as st
from mcp import ClientSession

from agent import MAX_TOOL_CALLS, MCP_URL, MODEL, http_client, run_agent

st.set_page_config(page_title="Ops Copilot", page_icon=":material/monitor_heart:", layout="wide")

EXAMPLES = {
    "DNS failure": "Users cannot open the VPN portal at vpn.opscopilot-demo.invalid since this morning.",
    "Port blocked": "Users report they cannot reach the status page at github.com on port 81. "
                    "Other websites work fine.",
    "Disk full": "Reported by Sarah on floor 3: the EHR app on ehr-app01 stopped working around "
                 "8:40 am and about 40 users see errors when saving. Please check app.log.",
}
BAD = ("UNREACHABLE", "DNS_FAILURE", "TIMED_OUT", "CLOSED", "ERROR", "STOPPED", "NO_")
GOOD = ("REACHABLE", "RESOLVED", "OPEN", "FOUND", "BEST MATCH", "AVAILABLE")


# ---------- helpers ----------

def clean(text):
    """The Java server sends plain strings JSON-encoded ("..."); decode them for display."""
    text = text.strip()
    if text.startswith('"'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    return text


def badge(text):
    """Green / red / grey label from the first word of a tool result."""
    t = clean(text)
    if t.startswith("{"):
        return ":blue-background[Draft ticket]"
    label = t.split("\n")[0].split(":")[0][:30]
    if t.upper().startswith(BAD):
        return f":red-background[{label}]"
    if t.upper().startswith(GOOD):
        return f":green-background[{label}]"
    return f":gray-background[{label}]"


@st.cache_data(ttl=30, show_spinner=False)
def fetch_tools():
    """Ask the MCP server for its tool names. Returns None if it's offline."""
    async def _list():
        async with http_client(MCP_URL) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                return [t.name for t in (await session.list_tools()).tools]
    try:
        return asyncio.run(_list())
    except Exception:
        return None


def render_event(box, event, ctx):
    """Draw one agent event: a thought, a tool call, or a tool result."""
    kind, data = event
    if kind == "thought":
        box.caption(data)
    elif kind == "call":
        ctx["n"] += 1
        card = box.container(border=True)
        if data["name"] == "create_ticket":
            args = "..."
        else:
            args = ", ".join(f"{k}={json.dumps(v)}" for k, v in data["input"].items())
        card.markdown(f"**Step {ctx['n']}** · `{data['name']}({args})`")
        ctx["card"], ctx["name"] = card, data["name"]
    elif kind == "result":
        if ctx.get("card") and ctx.get("name") == data["name"]:
            card = ctx["card"]
        else:
            card = box.container(border=True)
        card.markdown(badge(data["text"]))
        if data["name"] != "create_ticket":
            card.code(clean(data["text"])[:1500], language=None)
        ctx["card"] = None


def use_example(text):
    st.session_state.incident = text


# ---------- sidebar ----------

with st.sidebar:
    st.title("Ops Copilot")
    st.caption("Incident triage agent")
    tools = fetch_tools()
    if tools is None:
        st.error(f"MCP server offline\n\n{MCP_URL}")
    else:
        st.success(f"MCP server online · {len(tools)} tools")
        for name in sorted(tools):
            st.markdown(f"- `{name}`")
    st.caption(f"Model: {MODEL}")
    st.caption(f"Budget: {MAX_TOOL_CALLS} checks per incident")
    st.warning("All tools are read-only. The agent diagnoses; a human makes changes.")


# ---------- incident input ----------

st.header("Describe the incident")
st.caption("Plain English is fine. The agent picks the checks, runs them, and drafts the ticket.")

st.session_state.setdefault("incident", EXAMPLES["Port blocked"])
st.text_area("Incident", key="incident", height=100)

cols = st.columns([1, 1, 1, 2])
for col, (label, text) in zip(cols, EXAMPLES.items()):
    col.button(label, on_click=use_example, args=(text,))
run = cols[3].button("Run triage", type="primary", disabled=tools is None)


# ---------- live run ----------

if run:
    incident = st.session_state.incident.strip()
    if not incident:
        st.warning("Describe the incident first.")
        st.stop()

    st.subheader("Agent steps")
    box = st.container()
    events, ctx = [], {"n": 0}

    def on_event(kind, data):
        events.append((kind, data))
        render_event(box, (kind, data), ctx)

    start = time.time()
    with st.spinner("Agent is investigating..."):
        try:
            summary, ticket = asyncio.run(run_agent(incident, on_event))
        except Exception as e:
            st.error(f"Triage failed: {e}")
            st.stop()

    st.session_state.result = {
        "incident": incident, "events": events, "summary": summary,
        "ticket": ticket, "elapsed": time.time() - start, "steps": ctx["n"],
    }


# ---------- result ----------

res = st.session_state.get("result")
if res:
    st.divider()
    st.subheader("Triage complete")
    st.caption(f'"{res["incident"]}" · {res["steps"]} tool calls · {res["elapsed"]:.1f} s')

    if not run:  # after a rerun, keep the steps available but folded away
        with st.expander(f"Show {res['steps']} steps"):
            replay_ctx = {"n": 0}
            for event in res["events"]:
                render_event(st, event, replay_ctx)

    t = res["ticket"]
    if not t or "raw" in t:
        st.warning("The agent did not produce a ticket draft.")
        st.markdown(res["summary"])
    else:
        priority = t.get("priority") or ""
        pcolor = "red" if priority.startswith(("1", "2")) else "orange" if priority.startswith("3") else "gray"
        st.markdown(f":{pcolor}-background[{priority}] :blue-background[{t.get('category')}]")

        st.markdown("**Likely cause**")
        st.write(t.get("likely_cause"))

        left, right = st.columns(2)
        with left:
            st.markdown("**Evidence**")
            for check in t.get("checks_run", []):
                st.markdown(f"- {check}")
        with right:
            st.markdown("**Recommended next steps**")
            st.write(t.get("recommended_fix"))

        st.info("Next: review, edit and save this ticket (coming in Step 17).")