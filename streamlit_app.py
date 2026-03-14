# officebuddy_interactive.py
import streamlit as st
import datetime as dt

# =========================
# Page config
st.set_page_config(page_title="OfficeBuddy • Interactive Bot", layout="centered")
st.title("OfficeBuddy • Interactive Office Helper")
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

if "flow" not in st.session_state:
    st.session_state.flow = None

if "flow_data" not in st.session_state:
    st.session_state.flow_data = {}

if "flow_step" not in st.session_state:
    st.session_state.flow_step = 0

if "last_output" not in st.session_state:
    st.session_state.last_output = ""

# =========================
# Sidebar for policy uploads
st.sidebar.subheader("Upload policies/FAQs (optional)")
uploaded_files = st.sidebar.file_uploader("Upload .txt or .md", type=["txt", "md"], accept_multiple_files=True)
policy_texts = []
if uploaded_files:
    for f in uploaded_files:
        policy_texts.append(f.read().decode("utf-8", errors="ignore"))
    st.sidebar.success(f"Loaded {len(uploaded_files)} file(s) for policy Q&A")

# =========================
# Flows
FLOWS = {
    "ticket": {
        "steps": [
            ("Category", "Type of ticket? (IT/HR/Facilities/Payroll/Other)"),
            ("Summary", "Short summary (one line)"),
            ("Business impact", "Who/what is blocked?"),
            ("Urgency", "Urgency level (Low/Medium/High/Critical)")
        ]
    },
    "leave": {
        "steps": [
            ("Employee", "Your name"),
            ("Manager", "Manager name"),
            ("Leave type", "Sick/Casual/Other"),
            ("Start date", "YYYY-MM-DD"),
            ("End date", "YYYY-MM-DD"),
            ("Reason", "Reason for leave")
        ]
    },
    "email": {
        "steps": [
            ("From", "Your name/email"),
            ("To", "Recipient email"),
            ("Subject", "Email subject"),
            ("Body", "Email body")
        ]
    }
}

# =========================
# Helper functions
def start_flow(flow_name):
    st.session_state.flow = flow_name
    st.session_state.flow_step = 0
    st.session_state.flow_data = {}

def flow_next_step(user_input):
    flow = st.session_state.flow
    step_name, _ = FLOWS[flow]["steps"][st.session_state.flow_step]
    st.session_state.flow_data[step_name] = user_input
    st.session_state.flow_step += 1
    if st.session_state.flow_step >= len(FLOWS[flow]["steps"]):
        # Flow done
        output_lines = [f"{k}: {v}" for k, v in st.session_state.flow_data.items()]
        st.session_state.last_output = "\n".join(output_lines)
        st.session_state.flow = None
        st.session_state.flow_step = 0
        return "✅ Done! Check export below."
    else:
        # Next prompt
        _, prompt = FLOWS[flow]["steps"][st.session_state.flow_step]
        return f"{prompt} (required)"

def simple_reply(user_input):
    user_input = user_input.lower()
    
    if user_input in ["/help", "help"]:
        return ("Commands:\n- raise ticket\n- leave request\n- draft email\n- policy question\n"
                "- /clear to reset chat")
    if user_input == "/clear":
        st.session_state.messages = []
        st.session_state.flow = None
        st.session_state.flow_step = 0
        st.session_state.flow_data = {}
        return "Chat cleared."
    
    # If in flow
    if st.session_state.flow:
        return flow_next_step(user_input)
    
    # Start flows
    if "raise ticket" in user_input:
        start_flow("ticket")
        _, prompt = FLOWS["ticket"]["steps"][0]
        return f"Let's raise a ticket. {prompt} (required)"
    
    if "leave request" in user_input:
        start_flow("leave")
        _, prompt = FLOWS["leave"]["steps"][0]
        return f"Let's create a leave request. {prompt} (required)"
    
    if "draft email" in user_input:
        start_flow("email")
        _, prompt = FLOWS["email"]["steps"][0]
        return f"Let's draft an email. {prompt} (required)"
    
    if "policy" in user_input or "faq" in user_input:
        if policy_texts:
            return f"Policy answer (from uploaded files):\n{policy_texts[0][:500]}..."
        else:
            return "No policy files uploaded. Upload .txt/.md in the sidebar to enable policy Q&A."
    
    return "I can help with tickets, leave requests, emails, and policy Q&A. Type /help for examples."

# =========================
# Chat input
user_input = st.chat_input("Ask anything office-related (e.g., raise a ticket)")
if user_input:
    ts = dt.datetime.now().strftime("%H:%M")
    reply = simple_reply(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input, "ts": ts})
    st.session_state.messages.append({"role": "assistant", "content": reply, "ts": ts})

# Display chat messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        st.caption(m["ts"])

# Export last output
if st.session_state.last_output:
    st.download_button("Download last output", data=st.session_state.last_output, file_name="officebuddy_output.txt")
