import streamlit as st
from voice_utils import record_audio, speak_text
from custom_tasks import handle_task
import os
from datetime import datetime

# ---------- Directories ----------
LOG_DIR = "chat_logs"
os.makedirs(LOG_DIR, exist_ok=True)

# ---------- Session State ----------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "voice" not in st.session_state:
    st.session_state.voice = "Female"

# ---------- Save Chat Log ----------
def save_chat_log(log_data):
    now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"chat_{now}.txt"
    filepath = os.path.join(LOG_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        for role, msg in log_data:
            f.write(f"{role.upper()}: {msg}\n")
    return filepath

# ---------- Page Config ----------
st.set_page_config(
    page_title="🎙️ ICAP AI Voice and Text Assistant",
    page_icon="🧠",
    layout="wide"
)

# ---------- Custom CSS ----------
st.markdown("""
    <style>
        /* Global */
        body, .stApp { 
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            color: #eaeaea; 
            font-family: 'Segoe UI', sans-serif;
        }
        
        /* Title */
        h2 { color: #1db954 !important; font-weight: 700; }

        /* Chat Bubbles */
        .chat-container { max-height: 500px; overflow-y: auto; padding: 15px; }
        .chat-row { display: flex; align-items: flex-start; margin: 10px 0; }
        .chat-avatar { font-size: 1.8em; margin: 0 10px; }
        .chat-bubble {
            padding: 12px 16px;
            border-radius: 15px;
            line-height: 1.5;
            max-width: 70%;
        }
        .user { background-color: #1db954; color: white; margin-left: auto; text-align: right; }
        .assistant { background-color: #2c2f33; color: #eaeaea; text-align: left; }
        
        /* Buttons */
        .stButton>button {
            background: #1db954;
            color: white;
            border: none;
            padding: 0.6em 1.2em;
            border-radius: 25px;
            font-weight: bold;
            transition: 0.3s;
        }
        .stButton>button:hover {
            background: #17a74a;
            transform: scale(1.05);
        }

        /* Input Box */
        .stTextInput>div>div>input {
            background-color: #1e1e1e;
            color: #f1f1f1;
            border-radius: 10px;
            border: 1px solid #444;
            padding: 10px;
        }

        /* Footer */
        .footer { text-align:center; margin-top:20px; font-size:0.9em; color:#aaa; }
    </style>
""", unsafe_allow_html=True)

# ---------- Sidebar (Settings) ----------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/ai.png", width=100)
    st.markdown("## ⚙️ Settings")
    st.session_state.voice = st.radio("🗣 Voice", ["Female", "Male"])
    
    if st.button("🔁 Reset Chat"):
        if st.session_state.chat_history:
            saved = save_chat_log(st.session_state.chat_history)
            st.success(f"💾 Chat saved: {saved}")
        st.session_state.chat_history = []

# ---------- Title ----------
st.markdown("<h2 style='text-align:center;'>🎙️ ICAP M&E AI Voice and Text Assistant</h2>", unsafe_allow_html=True)

# ---------- Voice Input ----------
col1, col2 = st.columns([1,4])
with col1:
    if st.button("🎤 Speak"):
        with st.spinner("🎙️ Listening..."):
            user_input = record_audio()
            if user_input:
                st.success(f"✅ You: {user_input}")
                response = handle_task(user_input)
                st.session_state.chat_history.append(("You", user_input))
                st.session_state.chat_history.append(("Assistant", response))
                speak_text(response, voice=st.session_state.voice)

# ---------- Text Input ----------
with col2:
    text_input = st.text_input("⌨️ Type your question...", placeholder="Ask about treatments, patients, costs...")
    if st.button("📤 Send"):
        if text_input.strip():
            response = handle_task(text_input)
            st.session_state.chat_history.append(("You", text_input))
            st.session_state.chat_history.append(("Assistant", response))
            speak_text(response, voice=st.session_state.voice)
        else:
            st.warning("⚠️ Please type something.")

# ---------- Chat History with Avatars ----------
st.markdown("## 💬 Chat")
chat_html = "<div class='chat-container'>"
for sender, msg in st.session_state.chat_history:
    if sender.startswith("You"):
        avatar = "🧑"
        role_class = "user"
        chat_html += f"<div class='chat-row'><div class='chat-bubble {role_class}'>{msg}</div><div class='chat-avatar'>{avatar}</div></div>"
    else:
        avatar = "🤖"
        role_class = "assistant"
        chat_html += f"<div class='chat-row'><div class='chat-avatar'>{avatar}</div><div class='chat-bubble {role_class}'>{msg}</div></div>"
chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)

# ---------- Footer ----------
st.markdown("<div class='footer'>🔒 Offline • 🧠 Powered by Vosk + Ollama + CSV + PDFs</div>", unsafe_allow_html=True)
