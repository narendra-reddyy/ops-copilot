import asyncio
import json
import time

import streamlit as st
from mcp import ClientSession

from agent import MAX_TOOL_CALLS, MCP_URL, MODEL, http_client, run_agent
from tickets_db import save_ticket

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
PRIORITIES = ["1 - Critical", "2 - High", "3 - Moderate", "4 - Low"]
CATEGORIES = ["Network", "DNS", "Server", "Storage", "Security", "Application"]


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

def render_ticket_form(t, res):
    """Plain English ticket form. JSON is built in the background on save."""
    st.subheader("Ticket draft")
    st.caption("Review and edit, then save. Nothing is filed until you save.")

    missing = [f for f in ("affected_users", "reported_by") if not t.get(f)]
    if missing:
        names = ", ".join(m.replace("_", " ") for m in missing)
        st.warning(f"{len(missing)} field(s) missing: {names}. The agent couldn't find them "
                   "in the report. Fill them in before saving.")

    def pick(options, value, default):
        return options.index(value) if value in options else default

    with st.form(f"ticket_form_{res['run_id']}"):
        title = st.text_input("Title", t.get("title") or "")
        c1, c2, c3 = st.columns(3)
        priority = c1.selectbox("Priority", PRIORITIES, index=pick(PRIORITIES, t.get("priority"), 1))
        category = c2.selectbox("Category", CATEGORIES, index=pick(CATEGORIES, t.get("category"), 0))
        group = c3.text_input("Assignment group", t.get("assignment_group") or "")

        c4, c5 = st.columns(2)
        users_label = "Affected users" + ("" if t.get("affected_users") else " :orange[(missing)]")
        reporter_label = "Reported by" + ("" if t.get("reported_by") else " :orange[(missing)]")
        affected = c4.text_input(users_label, t.get("affected_users") or "",
                                 placeholder="e.g. about 40, all of floor 3")
        reporter = c5.text_input(reporter_label, t.get("reported_by") or "",
                                 placeholder="Caller name or team")

        what = st.text_area("What happened", t.get("what_happened") or "", height=90)
        cause = st.text_area("Likely cause", t.get("likely_cause") or "", height=110)
        fix = st.text_area("Recommended fix", t.get("recommended_fix") or "", height=110)
        notes = st.text_area("Checks run (work notes, one per line)",
                             "\n".join(t.get("checks_run") or []), height=140)

        b1, b2, _ = st.columns([1, 1, 4])
        save = b1.form_submit_button("Save ticket", type="primary")
        discard = b2.form_submit_button("Discard")

    if discard:
        st.session_state.result = None
        st.rerun()

    if save:
        required = {
            "Title": title, "Assignment group": group, "Affected users": affected,
            "Reported by": reporter, "What happened": what,
            "Likely cause": cause, "Recommended fix": fix,
        }
        empty = [name for name, value in required.items() if not value.strip()]
        if empty:
            st.error("Please fill in: " + ", ".join(empty))
            return
        code = save_ticket({
            "title": title.strip(), "priority": priority, "category": category,
            "assignment_group": group.strip(), "affected_users": affected.strip(),
            "reported_by": reporter.strip(), "what_happened": what.strip(),
            "likely_cause": cause.strip(), "recommended_fix": fix.strip(),
            "checks_run": [line.strip() for line in notes.splitlines() if line.strip()],
            "incident": res["incident"],
        })
        st.session_state.saved_run = res["run_id"]
        st.session_state.saved_code = code
        st.rerun()

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
        "run_id": int(start * 1000),
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

        st.divider()
        if st.session_state.get("saved_run") == res["run_id"]:
            st.success(f"Ticket saved as {st.session_state.saved_code}.")
            st.page_link("pages/1_Tickets.py", label="View it on the Tickets page",
                         icon=":material/confirmation_number:")
        else:
            render_ticket_form(t, res)