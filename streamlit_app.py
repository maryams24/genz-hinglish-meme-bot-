# officebuddy_simple.py
import streamlit as st
import datetime as dt

# =========================
# Page config
st.set_page_config(page_title="OfficeBuddy • Simple Bot", layout="centered")

st.title("OfficeBuddy • Office Helper Bot")
st.markdown("""
<style>
.stButton>button {background-color: #4CAF50; color: white; font-weight:bold; margin:3px;}
.block-container { max-width: 800px; padding-top:1rem;}
</style>
""", unsafe_allow_html=True)

# =========================
# Session state init
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_output" not in st.session_state:
    st.session_state.last_output = ""

# =========================
# Sidebar: Upload policies for Q&A
st.sidebar.subheader("Upload policies/FAQs (optional)")
uploaded_files = st.sidebar.file_uploader("Upload .txt or .md", type=["txt", "md"], accept_multiple_files=True)
policy_texts = []
if uploaded_files:
    for f in uploaded_files:
        policy_texts.append(f.read().decode("utf-8", errors="ignore"))
    st.sidebar.success(f"Loaded {len(uploaded_files)} file(s) for Q&A")

# =========================
# Helper functions
def simple_reply(user_input):
    user_input = user_input.lower()
    
    # Commands
    if user_input in ["/help", "help"]:
        return ("Commands:\n- raise ticket\n- leave request\n- draft email\n- policy question\n"
                "- /clear to reset chat")

    if user_input == "/clear":
        st.session_state.messages = []
        return "Chat cleared."

    # Ticket
    if "raise ticket" in user_input:
        st.session_state.last_output = (
            "Ticket raised! Sample format:\n"
            "Category: IT\n"
            "Summary: Cannot access email\n"
            "Business impact: Blocked work\n"
            "Urgency: High"
        )
        return "Ticket flow simulated. Check export below."

    # Leave request
    if "leave request" in user_input:
        st.session_state.last_output = (
            "Leave request prepared! Sample format:\n"
            "Employee: John Doe\n"
            "Manager: Jane Smith\n"
            "Leave type: Sick\n"
            "Start: 2026-03-20\n"
            "End: 2026-03-22\n"
            "Reason: Flu"
        )
        return "Leave request flow simulated. Check export below."

    # Draft email
    if "draft email" in user_input:
        st.session_state.last_output = (
            "Email drafted! Sample format:\n"
            "From: Alice\n"
            "To: bob@example.com\n"
            "Subject: Project Update\n"
            "Body: Hi Bob, here’s the update..."
        )
        return "Email draft flow simulated. Check export below."

    # Policy question
    if "policy" in user_input or "faq" in user_input:
        if policy_texts:
            return f"Policy answer (from uploaded files):\n{policy_texts[0][:500]}..."
        else:
            return "No policy files uploaded. Upload .txt/.md in the sidebar to enable policy Q&A."

    return "I can help with tickets, leave requests, email drafts, and policy Q&A. Type /help for examples."

# =========================
# Chat input
user_input = st.chat_input("Ask anything office-related (e.g., raise a ticket)")
if user_input:
    ts = dt.datetime.now().strftime("%H:%M")
    reply = simple_reply(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input, "ts": ts})
    st.session_state.messages.append({"role": "assistant", "content": reply, "ts": ts})

# Display messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        st.caption(m["ts"])

# Export last output
if st.session_state.last_output:
    st.download_button("Download last output", data=st.session_state.last_output, file_name="officebuddy_output.txt")
