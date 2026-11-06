import streamlit as st

page = st.navigation([
    st.Page("triage.py", title="New triage", icon=":material/troubleshoot:", default=True),
    st.Page("pages/1_Tickets.py", title="Tickets", icon=":material/confirmation_number:"),
])
page.run()