import re
import io
import wave
import random
import datetime as dt

import numpy as np
import streamlit as st
from better_profanity import profanity

profanity.load_censor_words()

# -----------------------------
# Safety (clean-only)
# -----------------------------
ABUSIVE_PATTERNS = [
    r"\b(kill yourself|kys)\b",
    r"\b(i will kill|i'll kill)\b",
    r"\b(rape|raping)\b",
    r"\b(nazi)\b",
    r"\b(hate you|die)\b",
]
SEXUAL_EXPLICIT_PATTERNS = [
    r"\b(blowjob|handjob|porn|nudes|sex chat)\b",
]
SAFE_REFUSAL = "I can’t help with abusive/explicit content. Say it cleanly and I’ll help."

def is_blocked(text: str) -> bool:
    t = text.lower()
    if profanity.contains_profanity(t):
        return True
    for pat in ABUSIVE_PATTERNS + SEXUAL_EXPLICIT_PATTERNS:
        if re.search(pat, t, flags=re.I):
            return True
    return False

# -----------------------------
# Audio helpers (WAV bytes)
# -----------------------------
def _to_wav_bytes(sr: int, y: np.ndarray) -> bytes:
    y = np.clip(y, -1.0, 1.0)
    pcm = (y * 32767.0).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()

def make_beep_wav() -> bytes:
    sr = 22050
    dur = 0.10
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    y = 0.12 * np.sin(2 * np.pi * 880 * t)
    return _to_wav_bytes(sr, y.astype(np.float32))

def make_faah_synth_wav() -> bytes:
    """
    Safe synthetic “FAAH-ish” reaction: quick downward sweep + noise.
    Not a real clip; no voice imitation.
    """
    sr = 22050
    dur = 0.28
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)

    f0, f1 = 650, 170
    freq = f0 * (f1 / f0) ** (t / dur)
    phase = 2 * np.pi * np.cumsum(freq) / sr
    sweep = np.sin(phase).astype(np.float32)

    noise = (np.random.randn(len(t)).astype(np.float32)) * 0.08
    env = np.exp(-8 * t).astype(np.float32)

    y = (0.9 * sweep + noise) * env
    y = np.tanh(2.2 * y).astype(np.float32)
    return _to_wav_bytes(sr, y)

# -----------------------------
# Hinglish + slang + meme logic
# -----------------------------
HINGLISH_PHRASES = {
    "kya scene": "What’s the plan / what’s going on?",
    "scene kya hai": "What’s the status?",
    "kya chal raha": "What’s up?",
    "kya haal": "How are things?",
    "chill maar": "Relax / don’t stress.",
    "set hai": "Confirmed / fixed.",
    "kal set": "Let’s do it tomorrow.",
    "jugaad": "Quick workaround / hack.",
    "chalta hai": "It’s fine / let it slide.",
    "timepass": "Killing time / low-stakes fun.",
}

GENZ_SLANG = {
    "aura": "Your vibe/energy; ‘aura points’ = cool points.",
    "cooked": "Exhausted / overwhelmed / done for.",
    "brainrot": "Scroll-fried meme brain vibe.",
    "delulu": "Playfully delusional (optimistic coping).",
    "rizz": "Charisma / flirting skill.",
    "cap": "Lie/exaggeration. ‘No cap’ = for real.",
    "bet": "Okay / agreed / say less.",
    "mid": "Mediocre.",
    "tea": "Gossip / truth / info.",
    "yap": "Talk a lot (playful).",
}

TOPIC_KEYS = {
    "plans": {"plan","weekend","tomorrow","today","hangout","meet","movie","cafe"},
    "relationships": {"crush","date","dating","ghost","seen","reply","situationship"},
    "study": {"exam","test","assignment","class","study","notes"},
    "food": {"momos","chai","coffee","pizza","burger","snack","craving","food"},
    "gym": {"gym","workout","protein","leg day","cardio"},
    "social": {"reel","story","post","caption","soft launch","hard launch","instagram"},
    "gaming": {"game","rank","match","lag","carry","win"},
    "mood": {"sad","tired","stressed","anxious","overthinking","burnt","low"},
}

def detect_topic(text: str) -> str:
    tokens = set(re.findall(r"[a-z']+", text.lower()))
    best = ("general", 0)
    for topic, keys in TOPIC_KEYS.items():
        score = len(tokens & keys)
        if score > best[1]:
            best = (topic, score)
    return best[0]

def hashtags(topic: str) -> str:
    base = {
        "plans": ["#weekendplans", "#friends", "#hangout"],
        "relationships": ["#situationship", "#texting", "#iykyk"],
        "study": ["#studentlife", "#examseason", "#studygram"],
        "food": ["#foodie", "#snacktime", "#streetfood"],
        "gym": ["#gymarc", "#fitness", "#legday"],
        "social": ["#reels", "#memes", "#captionideas"],
        "gaming": ["#gaming", "#ranked", "#gg"],
        "mood": ["#mood", "#relatable", "#selfcare"],
        "general": ["#relatable", "#memes", "#vibes"],
    }
    return " ".join(base.get(topic, base["general"])[:5])

def make_caption(core: str, topic: str) -> str:
    hooks = ["POV:", "Me:", "Lowkey", "Highkey", "It’s giving", "Normalize"]
    specifics = ["at 2:13am", "with 3% battery", "after one chai", "during exam week", "in the group chat"]
    prompts = ["Real or nah.", "IYKYK.", "Be honest.", "Tell me I’m not alone."]
    core = re.sub(r"\s+", " ", core).strip()
    core = core[:90] if core else "this whole situation"
    return f"{random.choice(hooks)} {core} {random.choice(specifics)} {random.choice(prompts)}\n{hashtags(topic)}"

def make_faah_meme_text(core: str) -> str:
    core = re.sub(r"\s+", " ", core).strip() or "I try a tiny shortcut"
    setups = [f"Me: {core}", f"POV: {core}", f"When {core}"]
    payoff = random.choice([
        "Reality: *FAAAH* (instant consequences)",
        "Universe: *FAAH* (same-day delivery)",
        "My luck: *FAAH* (plot twist unlocked)",
    ])
    return f"{random.choice(setups)}\n{payoff}"

def slang_lookup(term: str) -> str:
    key = term.strip().lower()
    if not key:
        return "Use: /slang <word>  (e.g., /slang cooked)"
    if key in GENZ_SLANG:
        return f"{key}: {GENZ_SLANG[key]}"
    if key in ("no cap", "nocap"):
        return "no cap: For real / not lying."
    return "Not in my slang list yet—try another word."

def hinglish_lookup(term: str) -> str:
    key = term.strip().lower()
    if not key:
        return "Use: /hindi <phrase>  (e.g., /hindi kya scene)"
    hits = [(k, v) for k, v in HINGLISH_PHRASES.items() if key in k]
    if not hits:
        return "Not found—try shorter (e.g., ‘scene’, ‘set’, ‘jugaad’)."
    return "\n".join([f"{k}: {v}" for k, v in hits[:10]])

def bot_reply(user_text: str) -> str:
    topic = detect_topic(user_text)
    low = user_text.lower().strip()

    if low.startswith("/slang"):
        return slang_lookup(user_text[len("/slang"):])
    if low.startswith("/hindi"):
        return hinglish_lookup(user_text[len("/hindi"):])
    if low.startswith("/caption"):
        return make_caption(user_text[len("/caption"):].strip(), topic)
    if low.startswith("/meme"):
        core = user_text[len("/meme"):].strip()
        if "faah" in core.lower():
            core2 = re.sub(r"\bfaah\b", "", core, flags=re.I).strip()
            return "FAAH meme (text):\n" + make_faah_meme_text(core2)
        return "Meme idea:\n" + make_caption(core, topic)

    if "faah" in low:
        core2 = re.sub(r"\bfaah\b", "", user_text, flags=re.I).strip()
        return "FAAH meme (text):\n" + make_faah_meme_text(core2)

    openers = {
        "plans": ["Weekend ka scene kya hai?", "Plan drop kar—time lock karo."],
        "relationships": ["Real talk: clarity ya peace?", "Seen zone ka update?"],
        "study": ["30-min sprint? bas start.", "Chai + notes = power-up."],
        "food": ["Craving detected. Momos ya chai?", "Spicy vs regret—choose."],
        "gym": ["Gym arc loading—leg day pe vanish mat."],
        "social": ["Soft launch ya hard launch?", "Caption chahiye? bol."],
        "gaming": ["Warm-up then ranked.", "Clean comms = W."],
        "mood": ["Vibe check: 0–10?", "Chill maar—1 small step first."],
        "general": ["Bol, kya scene?", "Give me the lore."],
    }
    s = random.choice(openers.get(topic, openers["general"]))
    if random.random() < 0.25:
        s += " (chai = therapy)"
    return s

# -----------------------------
# UI (GitHub-only; no .streamlit theme file)
# -----------------------------
st.set_page_config(page_title="Gen‑Z Hinglish Meme Bot", layout="centered")

st.markdown(
    """
<style>
/* Code Generated by Sidekick is for learning and experimentation purposes only. */
.stApp {
  background: radial-gradient(1200px 600px at 20% 10%, rgba(0,124,176,0.35), transparent 55%),
              radial-gradient(1000px 500px at 80% 0%, rgba(134,188,37,0.25), transparent 60%),
              radial-gradient(900px 450px at 50% 90%, rgba(237,139,0,0.18), transparent 60%),
              linear-gradient(180deg, #070A0F 0%, #0B0F14 55%, #070A0F 100%);
}
.block-container { padding-top: 2.2rem; }
.chat-card {
  border: 1px solid rgba(187,189,191,0.22);
  background: rgba(18,26,36,0.55);
  backdrop-filter: blur(10px);
  border-radius: 16px;
  padding: 14px 14px 6px 14px;
}
.small { opacity: 0.82; font-size: 0.92rem; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("Gen‑Z Hinglish Meme Bot")
st.caption("Commands: /meme … | /caption … | /slang … | /hindi …")

with st.sidebar:
    st.subheader("Sound")
    sound_mode = st.radio("Mode", ["Off", "Beep", "FAAH synth"], index=2)

    st.divider()
    st.subheader("One-click demo")
    if st.button("Send FAAH example"):
        st.session_state["_queued_input"] = "/meme faah about ordering extra spicy momos"

    st.divider()
    st.subheader("Examples")
    st.code("/meme faah about ordering extra spicy momos", language="text")
    st.code("/caption for my reel: exam week survival", language="text")
    st.code("/slang cooked", language="text")
    st.code("/hindi kya scene", language="text")

if "messages" not in st.session_state:
    st.session_state.messages = []

def maybe_play_audio(user_text: str):
    if sound_mode == "Off":
        return
    if sound_mode == "FAAH synth" and ("faah" in user_text.lower()):
        st.audio(make_faah_synth_wav(), format="audio/wav")
    else:
        st.audio(make_beep_wav(), format="audio/wav")

st.markdown('<div class="chat-card">', unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        st.markdown(f'<div class="small">{m["ts"]}</div>', unsafe_allow_html=True)

queued = st.session_state.pop("_queued_input", None)
user_text = queued or st.chat_input("Type here… (try: /meme faah about skipping gym)")

st.markdown("</div>", unsafe_allow_html=True)

if user_text:
    ts = dt.datetime.now().strftime("%H:%M")
    st.session_state.messages.append({"role": "user", "content": user_text, "ts": ts})

    if is_blocked(user_text):
        st.session_state.messages.append({"role": "assistant", "content": SAFE_REFUSAL, "ts": ts})
        maybe_play_audio(user_text)
        st.rerun()

    reply = bot_reply(user_text)
    st.session_state.messages.append({"role": "assistant", "content": reply, "ts": ts})
    maybe_play_audio(user_text)
    st.rerun()
