import streamlit as st

from tickets_db import STATUSES, list_tickets, update_status

st.set_page_config(page_title="Tickets · Ops Copilot",
                   page_icon=":material/confirmation_number:", layout="wide")

PRIORITIES = ["1 - Critical", "2 - High", "3 - Moderate", "4 - Low"]

st.header("Tickets")
st.caption("Every ticket an engineer reviewed and saved, newest first.")

# Message left by the last status update (survives the page refresh)
if "flash" in st.session_state:
    st.success(st.session_state.pop("flash"))

tickets = list_tickets()
if not tickets:
    st.info("No tickets yet. Run a triage and save a ticket first.")
    st.page_link("triage.py", label="New triage", icon=":material/arrow_back:")
    st.stop()

# ---------- counts ----------
cols = st.columns(len(STATUSES))
for col, status in zip(cols, STATUSES):
    col.metric(status, sum(t["status"] == status for t in tickets))

# ---------- filters ----------
f1, f2, f3 = st.columns([3, 1, 1])
query = f1.text_input("Search", placeholder="Title, category, team, reporter or ticket ID")
status_filter = f2.selectbox("Status", ["All"] + STATUSES)
priority_filter = f3.selectbox("Priority", ["All"] + PRIORITIES)


def matches(t):
    if status_filter != "All" and t["status"] != status_filter:
        return False
    if priority_filter != "All" and t["priority"] != priority_filter:
        return False
    if query:
        text = " ".join(str(t.get(k) or "") for k in
                        ("code", "title", "category", "assignment_group", "reported_by"))
        return query.lower() in text.lower()
    return True


shown = [t for t in tickets if matches(t)]
st.caption(f"Showing {len(shown)} of {len(tickets)} tickets")

# ---------- table ----------
st.dataframe(
    [{
        "ID": t["code"],
        "Title": t["title"],
        "Priority": t["priority"],
        "Category": t["category"],
        "Status": t["status"],
        "Assigned to": t["assignment_group"],
        "Created": t["created_at"].replace("T", " ")[:16],
    } for t in shown],
    hide_index=True,
)

# ---------- details + status update ----------
if shown:
    st.subheader("Ticket details")
    options = {f"{t['code']} · {t['title']}": t for t in shown}
    t = options[st.selectbox("Open a ticket", list(options))]

    with st.container(border=True):
        st.markdown(f"#### {t['code']} · {t['title']}")
        st.caption(f"{t['priority']} · {t['category']} · {t['assignment_group']} · "
                   f"created {t['created_at'].replace('T', ' ')[:16]}")

        c1, c2 = st.columns(2)
        c1.markdown(f"**Reported by:** {t['reported_by']}")
        c2.markdown(f"**Affected users:** {t['affected_users']}")

        st.markdown("**What happened**")
        st.write(t["what_happened"])
        st.markdown("**Likely cause**")
        st.write(t["likely_cause"])
        st.markdown("**Recommended fix**")
        st.write(t["recommended_fix"])
        st.markdown("**Work notes (checks the agent ran)**")
        for note in t["checks_run"]:
            st.markdown(f"- {note}")

        s1, s2, _ = st.columns([2, 1, 3], vertical_alignment="bottom")
        new_status = s1.selectbox("Status", STATUSES,
                                  index=STATUSES.index(t["status"]), key=f"status_{t['id']}")
        if s2.button("Update status", key=f"update_{t['id']}"):
            update_status(t["id"], new_status)
            st.session_state.flash = f"{t['code']} is now {new_status}."
            st.rerun()