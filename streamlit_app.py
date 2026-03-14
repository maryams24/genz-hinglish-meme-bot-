import datetime as dt
import re
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

# ============================================================
# OfficeBuddy • Office Helper Chatbot (Mini Project)
# - Guided ticket builder with required/optional fields
# - Live draft + download as .txt
# - Templates (email/agenda/notes/standup/RAID)
# - Lightweight knowledge base search (built-in + uploaded .txt/.md)
# ============================================================


# =========================
# Page + Styles
# =========================
st.set_page_config(page_title="OfficeBuddy • Office Helper Chatbot", layout="centered")
st.markdown(
    """
<style>
.block-container { max-width: 980px; padding-top: 1.1rem; }
.small { color: #6B7280; font-size: 0.9rem; }
.badge { display:inline-block; padding:2px 8px; border:1px solid #E5E7EB; border-radius:999px; background:#F9FAFB; margin-right:6px; }
.kbd { background:#F3F4F6; padding:2px 6px; border-radius:8px; border:1px solid #E5E7EB; }
hr { border: none; border-top: 1px solid #E5E7EB; margin: 0.6rem 0; }
</style>
""",
    unsafe_allow_html=True,
)


# =========================
# Text Utilities
# =========================
STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "for",
    "of",
    "in",
    "on",
    "at",
    "is",
    "are",
    "am",
    "with",
    "by",
    "from",
    "this",
    "that",
    "it",
    "as",
    "be",
    "we",
    "you",
    "i",
    "our",
    "your",
    "please",
    "pls",
    "plz",
    "can",
    "could",
    "would",
    "need",
    "want",
    "help",
    "me",
    "my",
    "hi",
    "hello",
    "hey",
    "thanks",
    "thank",
}

def normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s\-/]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(text: str) -> set[str]:
    words = set(normalize(text).split())
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}

def chunk_text(text: str, max_chars: int = 1100) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    for p in parts:
        if len(p) <= max_chars:
            chunks.append(p)
        else:
            for i in range(0, len(p), max_chars):
                chunks.append(p[i : i + max_chars].strip())
    return [c for c in chunks if c]


# =========================
# Knowledge Base
# =========================
@dataclass
class KBItem:
    title: str
    body: str
    tags: set[str]
    category: str

BUILTIN_KB: list[KBItem] = [
    KBItem(
        title="Ticket writing: what to include",
        body=(
            "Include: business impact, urgency, when it started, system/app, device/OS, network, steps to reproduce, "
            "expected vs actual, attachments, contact window/timezone. Copy exact error text."
        ),
        tags={"ticket", "helpdesk", "support", "incident", "expected", "actual", "reproduce", "urgency", "impact"},
        category="Productivity",
    ),
    KBItem(
        title="Password reset / account locked",
        body=(
            "Try the approved self-service reset/MFA recovery steps first. If locked out, open an IT ticket with: "
            "username, error message, when it started, device/OS, network (VPN/office/home)."
        ),
        tags={"password", "reset", "locked", "login", "mfa", "account"},
        category="IT",
    ),
    KBItem(
        title="Phishing: what to do",
        body=(
            "Don’t click links/attachments. Report via your company’s phishing-report method and delete. "
            "If you entered credentials, reset password and notify IT immediately."
        ),
        tags={"phishing", "security", "email", "scam", "attachment"},
        category="Security",
    ),
    KBItem(
        title="Meeting best practices",
        body="Start with outcomes, timebox discussion, capture decisions, end with action items (owner + due date). Send notes within 24 hours.",
        tags={"meeting", "agenda", "notes", "minutes", "actions", "decisions"},
        category="Productivity",
    ),
    KBItem(
        title="Expense troubleshooting (generic)",
        body="Common fixes: confirm policy category, attach itemized receipt, ensure dates/currency correct, verify approver chain. If submission fails, capture error text + screenshot and raise a ticket.",
        tags={"expense", "reimbursement", "receipt", "approver", "error"},
        category="Travel/Expense",
    ),
    KBItem(
        title="Facilities request (generic)",
        body="For facilities issues (AC, badge doors, desk issues), include location, floor/seat, urgency/safety impact, and photos if relevant.",
        tags={"facilities", "office", "ac", "chair", "desk", "maintenance", "badge"},
        category="Facilities",
    ),
]

def build_kb(uploaded_texts: list[str]) -> list[KBItem]:
    kb = list(BUILTIN_KB)
    for up_idx, text in enumerate(uploaded_texts, start=1):
        for ch_idx, ch in enumerate(chunk_text(text), start=1):
            kb.append(
                KBItem(
                    title=f"Uploaded Doc #{up_idx}.{ch_idx}",
                    body=ch,
                    tags=tokenize(ch),
                    category="Uploaded",
                )
            )
    return kb

def retrieve(kb: list[KBItem], query: str, top_k: int = 4) -> list[tuple[float, KBItem]]:
    q_raw = (query or "").strip()
    q = tokenize(q_raw)
    if not q:
        return []

    q_norm = normalize(q_raw)
    scored: list[tuple[float, KBItem]] = []
    for item in kb:
        overlap = len(q & item.tags)
        if overlap <= 0:
            continue

        # Lightweight scoring: overlap + title boost + exact phrase boost
        title_norm = normalize(item.title)
        score = float(overlap)
        score += 1.0 if any(w in title_norm.split() for w in q) else 0.0
        score += 1.5 if (q_norm and q_norm in normalize(item.body)) else 0.0

        scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


# =========================
# Templates
# =========================
def tpl_email() -> str:
    return (
        "Subject: [Action] [Topic] by [Date]\n\n"
        "Hi [Name],\n"
        "I’m reaching out to request [ask].\n\n"
        "Context:\n- \n\n"
        "What I need (Owner | Date):\n- \n\n"
        "Decision/approval needed:\n- \n\n"
        "Thanks,\n[Your name]"
    )

def tpl_agenda() -> str:
    return (
        "30-min meeting agenda\n\n"
        "1) Outcomes (2 mins)\n"
        "2) Progress / current state (8 mins)\n"
        "3) Discussion + decisions needed (12 mins)\n"
        "4) Risks / dependencies (4 mins)\n"
        "5) Next steps (owners + dates) (4 mins)"
    )

def tpl_notes() -> str:
    return (
        "Meeting notes\n\n"
        "Date/Time:\nAttendees:\n\n"
        "Outcomes:\n- \n\n"
        "Key points:\n- \n\n"
        "Decisions:\n- \n\n"
        "Action items (Owner | Due):\n- \n\n"
        "Risks / dependencies:\n- "
    )

def tpl_standup() -> str:
    return "Done:\n- \n\nNext:\n- \n\nBlockers/Risks:\n- \n\nAsk (if any):\n- "

def tpl_raid() -> str:
    return (
        "Type (Risk/Assumption/Issue/Dependency):\n"
        "Description:\nImpact:\nLikelihood:\nOwner:\nMitigation / next action:\nDue date:\nStatus:"
    )


# =========================
# Guided Flows
# =========================
@dataclass
class Step:
    field: str
    prompt: str
    required: bool = True
    hint: str = ""

@dataclass
class Flow:
    name: str
    intro: str
    steps: list[Step]
    formatter: Callable[[dict], str]

def _val(v: str) -> str:
    v = (v or "").strip()
    return v if v else "N/A"

def format_ticket(data: dict) -> str:
    return (
        "Ticket (copy/paste)\n\n"
        f"Category: {_val(data.get('category'))}\n"
        f"Summary: {_val(data.get('summary'))}\n"
        f"Business impact: {_val(data.get('impact'))}\n"
        f"Urgency: {_val(data.get('urgency'))}\n"
        f"When it started: {_val(data.get('start_time'))}\n"
        f"System/App: {_val(data.get('system'))}\n"
        f"Device/OS: {_val(data.get('device'))}\n"
        f"Network: {_val(data.get('network'))}\n"
        f"Steps to reproduce: {_val(data.get('repro'))}\n"
        f"Expected vs actual: {_val(data.get('expected_actual'))}\n"
        f"Attachments available: {_val(data.get('attachments'))}\n"
        f"Contact window/timezone: {_val(data.get('contact'))}\n"
    )

def format_access(data: dict) -> str:
    return (
        "Access request (copy/paste)\n\n"
        f"System/App: {_val(data.get('system'))}\n"
        f"Role/access needed: {_val(data.get('role'))}\n"
        f"Business justification: {_val(data.get('justification'))}\n"
        f"Start date: {_val(data.get('start_date'))}\n"
        f"End date (if temporary): {_val(data.get('end_date'))}\n"
        f"Manager/approver: {_val(data.get('approver'))}\n"
        f"User info (name/email/ID): {_val(data.get('user'))}\n"
    )

def format_leave(data: dict) -> str:
    return (
        "Leave request message (copy/paste)\n\n"
        f"Leave type: {_val(data.get('type'))}\n"
        f"Dates: {_val(data.get('dates'))}\n"
        f"Coverage plan: {_val(data.get('coverage'))}\n"
        f"Notes: {_val(data.get('notes'))}\n"
        f"Manager: {_val(data.get('manager'))}\n"
    )

def format_expense(data: dict) -> str:
    return (
        "Expense help request (copy/paste)\n\n"
        f"Issue summary: {_val(data.get('summary'))}\n"
        f"Tool/system: {_val(data.get('system'))}\n"
        f"Error text (if any): {_val(data.get('error'))}\n"
        f"Amount/currency: {_val(data.get('amount'))}\n"
        f"Date of expense: {_val(data.get('date'))}\n"
        f"Receipt available: {_val(data.get('receipt'))}\n"
        f"What I tried: {_val(data.get('tried'))}\n"
    )

def suggest_urgency(impact_text: str) -> str:
    t = normalize(impact_text or "")
    if any(k in t for k in ["outage", "down for everyone", "all users", "security", "breach", "phishing", "urgent", "critical"]):
        return "Critical"
    if any(k in t for k in ["blocked", "cannot", "can't", "unable", "deadline", "client", "production"]):
        return "High"
    if any(k in t for k in ["workaround", "slow", "intermittent", "sometimes"]):
        return "Medium"
    return "Low"

FLOWS: dict[str, Flow] = {
    "ticket": Flow(
        name="ticket",
        intro="Let’s raise a ticket. Answer these—type 'skip' for optional items.",
        steps=[
            Step("category", "Type of ticket? (IT/HR/Facilities/Payroll/Other)", required=True),
            Step("summary", "Short summary (one line).", required=True, hint="Example: 'VPN authentication failed after MFA'"),
            Step("impact", "Business impact? (who/what blocked + deadline risk)", required=True),
            Step("urgency", "Urgency? (Low/Medium/High/Critical) (or type 'auto')", required=True),
            Step("start_time", "When did it start? (e.g., today 10:15 AM)", required=True),
            Step("system", "Which system/app is affected? (include URL if relevant)", required=True),
            Step("device", "Device + OS? (e.g., Dell laptop / Windows 11)", required=True),
            Step("network", "Network? (Office/Home/VPN/Hotspot)", required=True),
            Step("repro", "Steps to reproduce (or say 'intermittent')", required=True),
            Step("expected_actual", "Expected vs actual behavior (1 line each)", required=True),
            Step("attachments", "Any screenshots/logs to attach? (yes/no + what)", required=False),
            Step("contact", "Best contact window + timezone", required=True),
        ],
        formatter=format_ticket,
    ),
    "access": Flow(
        name="access",
        intro="Access request—answer these. Type 'skip' for optional items.",
        steps=[
            Step("system", "Which system/app?", required=True),
            Step("role", "What access/role do you need?", required=True),
            Step("justification", "Business justification (1–2 lines).", required=True),
            Step("start_date", "Start date?", required=True),
            Step("end_date", "End date (or 'skip' if N/A).", required=False),
            Step("approver", "Approver/manager name/email?", required=True),
            Step("user", "Your name + email/employee ID (as required).", required=True),
        ],
        formatter=format_access,
    ),
    "leave": Flow(
        name="leave",
        intro="Leave request—answer these. Type 'skip' for optional items.",
        steps=[
            Step("type", "Leave type? (PTO/Sick/Personal/Other)", required=True),
            Step("dates", "Dates + half-day/full-day?", required=True),
            Step("coverage", "Coverage plan (who covers what)?", required=True),
            Step("notes", "Any notes (or 'skip')", required=False),
            Step("manager", "Manager/approver name?", required=True),
        ],
        formatter=format_leave,
    ),
    "expense": Flow(
        name="expense",
        intro="Expense issue—capture what support needs. Type 'skip' for optional items.",
        steps=[
            Step("summary", "What’s the problem? (1 line)", required=True),
            Step("system", "Which tool/system?", required=True),
            Step("error", "Error message text (or 'skip')", required=False),
            Step("amount", "Amount + currency?", required=True),
            Step("date", "Expense date?", required=True),
            Step("receipt", "Receipt/itemized receipt available? (yes/no)", required=True),
            Step("tried", "What have you tried already?", required=True),
        ],
        formatter=format_expense,
    ),
}


# =========================
# Intent Detection
# =========================
def has_any(text: str, phrases: list[str]) -> bool:
    t = normalize(text)
    return any(p in t for p in phrases)

def detect_flow_intent(text: str) -> Optional[str]:
    t = normalize(text)
    if has_any(t, ["raise a ticket", "open a ticket", "create ticket", "helpdesk", "service desk", "incident", "ticket"]):
        return "ticket"
    if has_any(t, ["need access", "access request", "permission", "grant access", "role access"]):
        return "access"
    if has_any(t, ["apply leave", "pto", "sick leave", "leave request", "vacation"]):
        return "leave"
    if has_any(t, ["expense", "reimbursement", "receipt", "claim"]):
        return "expense"
    return None

def detect_template_intent(text: str) -> Optional[str]:
    t = normalize(text)
    if has_any(t, ["draft email", "write email", "email"]):
        return "email"
    if has_any(t, ["agenda", "meeting agenda"]):
        return "agenda"
    if has_any(t, ["meeting notes", "minutes", "notes"]):
        return "notes"
    if has_any(t, ["standup", "daily update", "status update", "scrum"]):
        return "standup"
    if has_any(t, ["raid", "risk", "issue", "dependency", "assumption"]):
        return "raid"
    return None


# =========================
# Session State
# =========================
def ss_init():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "uploaded_texts" not in st.session_state:
        st.session_state.uploaded_texts = []
    if "active_flow" not in st.session_state:
        st.session_state.active_flow = None
    if "flow_step_idx" not in st.session_state:
        st.session_state.flow_step_idx = 0
    if "flow_data" not in st.session_state:
        st.session_state.flow_data = {}
    if "last_export_text" not in st.session_state:
        st.session_state.last_export_text = ""

ss_init()


# =========================
# Flow helpers
# =========================
def start_flow(flow_key: str):
    flow = FLOWS[flow_key]
    st.session_state.active_flow = flow_key
    st.session_state.flow_step_idx = 0
    st.session_state.flow_data = {s.field: "" for s in flow.steps}

def cancel_flow():
    st.session_state.active_flow = None
    st.session_state.flow_step_idx = 0
    st.session_state.flow_data = {}

def current_step(flow_key: str) -> Step:
    flow = FLOWS[flow_key]
    return flow.steps[st.session_state.flow_step_idx]

def flow_done(flow_key: str) -> bool:
    flow = FLOWS[flow_key]
    data = st.session_state.flow_data
    for s in flow.steps:
        v = (data.get(s.field) or "").strip()
        if s.required and not v:
            return False
    return True

def next_missing_step_index(flow_key: str) -> int:
    flow = FLOWS[flow_key]
    data = st.session_state.flow_data
    for idx, s in enumerate(flow.steps):
        v = (data.get(s.field) or "").strip()
        if s.required and not v:
            return idx
    # if all required done, advance through remaining optional
    for idx, s in enumerate(flow.steps):
        v = (data.get(s.field) or "").strip()
        if not v:
            return idx
    return len(flow.steps) - 1


# =========================
# Assistant Reply
# =========================
HELP_TEXT = (
    "Try:\n"
    "- “I want to raise a ticket”  (guided)\n"
    "- “I need access to [system]” (guided)\n"
    "- “I want to apply leave”     (guided)\n"
    "- “Expense reimbursement error” (guided)\n"
    "- “Draft an email to my manager” (template)\n"
    "- “Create meeting agenda” (template)\n\n"
    "Commands: /help /clear /cancel /skills\n"
    "Tip: In guided flows, type 'skip' for optional fields."
)

def assistant_reply(user_text: str, kb: list[KBItem], policy_hint: str) -> str:
    t = (user_text or "").strip()
    low = t.lower().strip()

    # Commands
    if low in {"/help", "help"}:
        return HELP_TEXT
    if low == "/skills":
        return "Skills: ticket, access request, leave request, expense help, templates (email/agenda/notes/standup/RAID), policy Q&A (upload)."
    if low == "/cancel":
        if st.session_state.active_flow:
            cancel_flow()
            return "Cancelled the current guided flow."
        return "Nothing to cancel."
    if low == "/clear":
        st.session_state.messages = []
        cancel_flow()
        st.session_state.last_export_text = ""
        return "Cleared."

    # Guided flow handling
    if st.session_state.active_flow:
        fk = st.session_state.active_flow
        flow = FLOWS[fk]
        step = current_step(fk)

        answer = t
        if answer.lower() == "skip":
            answer = ""  # leave blank (optional fields will show N/A in export)
            if step.required:
                return f"That field is required. {step.prompt}"

        # Special: urgency auto-suggest
        if step.field == "urgency" and answer.lower() == "auto":
            impact = st.session_state.flow_data.get("impact", "")
            answer = suggest_urgency(impact)

        st.session_state.flow_data[step.field] = answer

        if flow_done(fk):
            out = flow.formatter(st.session_state.flow_data)
            st.session_state.last_export_text = out
            cancel_flow()
            return "Done. Review below and download if needed:\n\n" + out

        # Move to next missing step
        st.session_state.flow_step_idx = next_missing_step_index(fk)
        nxt = current_step(fk)
        extra = f"\n\nHint: {nxt.hint}" if nxt.hint else ""
        req = " (required)" if nxt.required else " (optional — type 'skip')"
        return f"{nxt.prompt}{req}{extra}"

    # Start flow by intent
    fk = detect_flow_intent(t)
    if fk:
        start_flow(fk)
        s0 = current_step(fk)
        req = " (required)" if s0.required else " (optional — type 'skip')"
        extra = f"\n\nHint: {s0.hint}" if s0.hint else ""
        return f"{FLOWS[fk].intro}\n\n{s0.prompt}{req}{extra}"

    # Templates
    temp = detect_template_intent(t)
    if temp == "email":
        return tpl_email()
    if temp == "agenda":
        return tpl_agenda()
    if temp == "notes":
        return tpl_notes()
    if temp == "standup":
        return tpl_standup()
    if temp == "raid":
        return tpl_raid()

    # KB retrieval
    hits = retrieve(kb, t, top_k=4)
    if hits:
        blocks = []
        for score, item in hits:
            blocks.append(f"**[{item.category}] {item.title}**\n{item.body}")
        return (
            "Here’s what I found (validate against your internal policy if needed):\n\n"
            + "\n\n---\n\n".join(blocks)
        )

    # Default
    return (
        "I can help with: raising tickets, access requests, leave requests, expense issues, and meeting/email templates.\n"
        f"For policy Q&A, upload relevant text from {policy_hint} in the sidebar.\n\n"
        "Try: “I want to raise a ticket” or “Draft an email”."
    )


# =========================
# Sidebar
# =========================
with st.sidebar:
    st.subheader("OfficeBuddy Settings")
    policy_hint = st.text_input("Policy source label", value="your HR/IT policy portal")

    st.divider()
    st.subheader("Upload policies/FAQs (for Q&A)")
    ups = st.file_uploader("Upload .txt or .md (multiple)", type=["txt", "md"], accept_multiple_files=True)
    if ups:
        st.session_state.uploaded_texts = []
        for f in ups:
            st.session_state.uploaded_texts.append(f.read().decode("utf-8", errors="ignore"))
        st.success(f"Loaded {len(ups)} file(s)")

    st.divider()
    st.subheader("Quick actions")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Raise a ticket", use_container_width=True):
            start_flow("ticket")
            intro = FLOWS["ticket"].intro
            s0 = current_step("ticket").prompt
            st.session_state.messages.append({"role": "assistant", "content": f"{intro}\n\n{s0} (required)", "ts": dt.datetime.now().strftime("%H:%M")})
            st.rerun()
        if st.button("Request access", use_container_width=True):
            start_flow("access")
            intro = FLOWS["access"].intro
            s0 = current_step("access").prompt
            st.session_state.messages.append({"role": "assistant", "content": f"{intro}\n\n{s0} (required)", "ts": dt.datetime.now().strftime("%H:%M")})
            st.rerun()
    with c2:
        if st.button("Apply leave", use_container_width=True):
            start_flow("leave")
            intro = FLOWS["leave"].intro
            s0 = current_step("leave").prompt
            st.session_state.messages.append({"role": "assistant", "content": f"{intro}\n\n{s0} (required)", "ts": dt.datetime.now().strftime("%H:%M")})
            st.rerun()
        if st.button("Expense help", use_container_width=True):
            start_flow("expense")
            intro = FLOWS["expense"].intro
            s0 = current_step("expense").prompt
            st.session_state.messages.append({"role": "assistant", "content": f"{intro}\n\n{s0} (required)", "ts": dt.datetime.now().strftime("%H:%M")})
            st.rerun()

    if st.session_state.active_flow:
        st.caption(f"Active flow: {st.session_state.active_flow}  •  Type /cancel to stop")

    st.divider()
    st.subheader("Export last output")
    if st.session_state.last_export_text.strip():
        st.download_button(
            "Download as .txt",
            data=st.session_state.last_export_text,
            file_name="officebuddy_output.txt",
            mime="text/plain",
            use_container_width=True,
        )
    else:
        st.caption("Nothing to export yet.")


# =========================
# Build KB
# =========================
kb = build_kb(st.session_state.uploaded_texts)


# =========================
# Header
# =========================
st.title("OfficeBuddy • Office Helper Chatbot")
st.markdown(
    '<span class="badge">Guided workflows</span>'
    '<span class="badge">Templates</span>'
    '<span class="badge">Policy Q&A (upload)</span>'
    '<span class="badge">Export</span>',
    unsafe_allow_html=True,
)
st.markdown('<div class="small">Type <span class="kbd">/help</span> for examples.</div>', unsafe_allow_html=True)


# =========================
# Chat History
# =========================
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("ts"):
            st.caption(m["ts"])


# =========================
# Live Draft (during flows)
# =========================
if st.session_state.active_flow:
    fk = st.session_state.active_flow
    with st.expander("Live draft (updates as you answer)", expanded=True):
        st.text_area("Draft", value=FLOWS[fk].formatter(st.session_state.flow_data), height=240)


# =========================
# Input
# =========================
user_text = st.chat_input("Ask anything office-related (e.g., raise a ticket)")

if user_text:
    ts = dt.datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": user_text, "ts": ts})

    reply = assistant_reply(user_text, kb=kb, policy_hint=policy_hint)
    st.session_state.messages.append({"role": "assistant", "content": reply, "ts": ts})

    st.rerun()
