"""
streamlit_app.py — Healthcare AI Agent with Modern UI
- Plan management with proper Streamlit callbacks
- Voice recording via JS + sessionStorage polling (no page reload)
- Auto TTS playback for responses
- Clean modern design
"""

import json
import os
import time
import uuid
from datetime import datetime
from io import BytesIO

import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("STREAMLIT_API_URL", "http://127.0.0.1:8000")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Trợ lý Y tế AI",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# MODERN CSS
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<style>
/* ── Global ── */
.main-header {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: white;
    padding: 1.5rem 2rem;
    border-radius: 16px;
    margin-bottom: 1rem;
    box-shadow: 0 4px 20px rgba(37,99,235,0.25);
}
.main-header h1 { margin: 0; font-size: 1.8rem; }
.main-header p { margin: 0.3rem 0 0; opacity: 0.9; font-size: 0.95rem;}

/* ── Intents Badges ── */
.badge {
    display: inline-block;
    padding: 2px 12px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    margin-bottom: 0.25rem;
}
.badge.rag { background: #dbeafe; color: #1e40af; }
.badge.symptom { background: #fee2e2; color: #b91c1c; }
.badge.planner { background: #dcfce7; color: #166534; }
.badge.chat { background: #f3f4f6; color: #4b5563; }

/* ── Chat Messages ── */
.chat-msg {
    padding: 0.75rem 1rem;
    border-radius: 12px;
    margin-bottom: 0.5rem;
    line-height: 1.5;
}
.chat-msg.user {
    background: #eff6ff;
    border: 1px solid #bfdbfe;
}
.chat-msg.assistant {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
}

/* ── Priority badges ── */
.priority-high { background: #fee2e2; color: #b91c1c; padding: 1px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; }
.priority-medium { background: #fef3c7; color: #b45309; padding: 1px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; }
.priority-low { background: #d1fae5; color: #065f46; padding: 1px 8px; border-radius: 10px; font-size: 0.7rem; font-weight: 600; }

/* ── Metric Cards ── */
.metric-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}
.metric-card .value { font-size: 1.5rem; font-weight: 700; color: #2563eb; }
.metric-card .label { font-size: 0.75rem; color: #6b7280; margin-top: 0.2rem; }

/* ── Sidebar styling ── */
.sidebar-section {
    margin-bottom: 1rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid #f3f4f6;
}
.sidebar-section:last-child { border-bottom: none; }
.sidebar-section .section-title {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #6b7280;
    margin-bottom: 0.5rem;
}

.stButton > button {
    border-radius: 8px;
    font-weight: 500;
}

/* ── Chat input styling ── */
div[data-testid="stChatInput"] {
    border: 2px solid #e5e7eb;
    border-radius: 16px;
    padding: 0.3rem 0.3rem 0.3rem 1rem;
}
div[data-testid="stChatInput"]:focus-within {
    border-color: #2563eb;
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
}

/* ── Voice input row after recording ── */
.voice-input-row {
    display: flex;
    gap: 8px;
    align-items: center;
    margin: 0.5rem 0 0.75rem;
    padding: 0.5rem 0.75rem;
    background: #f0f9ff;
    border: 1px solid #bae6fd;
    border-radius: 12px;
}
.voice-input-row span {
    flex: 1;
    font-size: 0.95rem;
}

/* ── Hide Streamlit default footer ── */
footer { display: none !important; }
#MainMenu { visibility: hidden; }
.stAppDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SESSION STATE DEFAULTS
# ══════════════════════════════════════════════════════════════════════════════

for key, default in [
    ("messages", []),
    ("user_id", "user_1"),
    ("api_url", DEFAULT_API_URL),
    ("plan_data", {"items": [], "pending": 0, "completed": 0}),
    ("auto_play", True),
    ("language", "vi"),
    ("tts_lang", "vi-VN"),
    ("voice_transcript", ""),
    ("show_voice_box", False),
    ("plan_loaded", False),
    ("voice_init_done", False),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def api_call(method, path, **kwargs):
    url = f"{st.session_state.api_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        r = requests.request(method, url, timeout=kwargs.pop("timeout", 10), **kwargs)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def load_plan():
    data = api_call("GET", f"/plan/{st.session_state.user_id}", timeout=5)
    if "error" not in data:
        st.session_state.plan_data = data
        st.session_state.plan_loaded = True


def plan_complete(task_id):
    api_call("POST", "/plan/complete", json={"user_id": st.session_state.user_id, "task_id": task_id}, timeout=5)
    load_plan()
    st.rerun()


def plan_delete(task_id):
    api_call("DELETE", f"/plan/{st.session_state.user_id}/{task_id}", timeout=5)
    load_plan()
    st.rerun()


def send_chat(message):
    resp = api_call("POST", "/chat", json={
        "user_id": st.session_state.user_id,
        "message": message,
    }, timeout=60)
    if "error" in resp:
        st.error(f"🔥 {resp['error']}")
        return

    response_text = resp.get("response", "")
    routing = resp.get("routing", {})

    st.session_state.messages.append({
        "role": "user",
        "content": message,
    })

    assistant_msg = {
        "role": "assistant",
        "content": response_text,
        "routing": routing,
    }

    # Auto TTS
    if st.session_state.auto_play and len(response_text) < 1500:
        try:
            tts_result = api_call("POST", "/voice/synthesize",
                                  json={"text": response_text[:500], "language": st.session_state.language},
                                  timeout=15)
            if "error" not in tts_result and tts_result.get("success"):
                assistant_msg["audio_b64"] = tts_result["audio_base64"]
            else:
                tts_err = tts_result.get("error", "Không rõ lỗi")
                st.toast(f"🔊 TTS không khả dụng: {tts_err}", icon="⚠️")
        except Exception as e:
            st.toast(f"🔊 Lỗi TTS: {e}", icon="⚠️")

    st.session_state.messages.append(assistant_msg)
    load_plan()
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# VOICE RECORDING JS — uses sessionStorage (no page reload)
# ══════════════════════════════════════════════════════════════════════════════

VOICE_JS = """
<script>
(function() {
    if (window._vhInstalled) return;
    window._vhInstalled = true;

    let recorder = null, chunks = [];

    window.startVoiceRecord = async function() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') 
                ? 'audio/webm;codecs=opus' 
                : 'audio/webm';
            recorder = new MediaRecorder(stream, { mimeType });
            chunks = [];
            recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
            recorder.start(100);
            return true;
        } catch(e) {
            console.error('Mic error:', e);
            return false;
        }
    };

    window.stopVoiceRecord = async function(apiUrl, language) {
        return new Promise((resolve) => {
            if (!recorder || recorder.state === 'inactive') return resolve(null);
            recorder.onstop = async () => {
                const mime = recorder.mimeType || 'audio/webm';
                const blob = new Blob(chunks, { type: mime });
                recorder.stream.getTracks().forEach(t => t.stop());
                recorder = null;
                chunks = [];

                const fd = new FormData();
                fd.append('file', blob, 'recording.webm');
                fd.append('language', language);
                try {
                    const r = await fetch(apiUrl + '/voice/transcribe', { method: 'POST', body: fd });
                    if (r.ok) { const d = await r.json(); resolve(d.success && d.text ? d.text : null); }
                    else { resolve(null); }
                } catch(e) { resolve(null); }
            };
            recorder.stop();
        });
    };

    window.pollVoiceResult = async function(apiUrl, language) {
        const text = await window.stopVoiceRecord(apiUrl, language);
        if (text) {
            sessionStorage.setItem('voice_transcript', text);
            sessionStorage.setItem('voice_ts', Date.now().toString());
            return true;
        }
        return false;
    };
})();
</script>
"""

# Inject once
st.markdown(VOICE_JS, unsafe_allow_html=True)

# ── Poll for voice result from sessionStorage ──
poll_check = st.markdown("""
<div id="voice_poll"></div>
<script>
(function() {
    const transcript = sessionStorage.getItem('voice_transcript');
    const ts = sessionStorage.getItem('voice_ts');
    if (transcript && ts && (Date.now() - parseInt(ts) < 5000)) {
        const el = document.getElementById('voice_poll');
        if (el) {
            el.setAttribute('data-text', transcript);
            sessionStorage.removeItem('voice_transcript');
            sessionStorage.removeItem('voice_ts');
        }
    }
})();
</script>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:0.5rem;">
        <span style="font-size:2rem;">🩺</span>
        <div>
            <div style="font-weight:700;font-size:1.1rem;">Trợ lý Y tế</div>
            <div style="font-size:0.75rem;color:#6b7280;">Healthcare AI Agent</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Connection ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Kết nối</div>', unsafe_allow_html=True)

    api_url = st.text_input("API URL", value=st.session_state.api_url, label_visibility="collapsed")
    if api_url != st.session_state.api_url:
        st.session_state.api_url = api_url
        st.rerun()

    col1, col2 = st.columns([3, 1])
    with col1:
        uid = st.text_input("User ID", value=st.session_state.user_id, label_visibility="collapsed")
    with col2:
        if st.button("🔄", help="Check backend"):
            data = api_call("GET", "/", timeout=3)
            if "error" not in data:
                st.toast("✅ Connected", icon="✅")
                load_plan()
            else:
                st.toast("❌ " + data.get("error", "Cannot connect"), icon="❌")

    if uid != st.session_state.user_id:
        st.session_state.user_id = uid
        st.session_state.messages = []
        st.session_state.plan_loaded = False
        load_plan()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Audio Settings ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Âm thanh</div>', unsafe_allow_html=True)
    st.session_state.auto_play = st.toggle("🔊 Tự động đọc", value=st.session_state.auto_play)
    st.session_state.language = st.selectbox(
        "Ngôn ngữ TTS", ["vi", "en"], index=0 if st.session_state.language == "vi" else 1
    )
    st.session_state.tts_lang = "vi-VN" if st.session_state.language == "vi" else "en-US"
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Plan Overview ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Kế hoạch</div>', unsafe_allow_html=True)

    pd = st.session_state.plan_data
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""<div class="metric-card"><div class="value">{pd.get('total',0)}</div><div class="label">Tổng</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card"><div class="value" style="color:#eab308;">{pd.get('pending',0)}</div><div class="label">Chờ</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card"><div class="value" style="color:#22c55e;">{pd.get('completed',0)}</div><div class="label">Xong</div></div>""", unsafe_allow_html=True)

    if st.button("📋 Tải kế hoạch", use_container_width=True, type="secondary"):
        load_plan()
        if "error" not in st.session_state.plan_data:
            st.toast(f"✅ {st.session_state.plan_data.get('total',0)} tasks", icon="✅")
        elif st.session_state.plan_data.get("error"):
            st.error(st.session_state.plan_data["error"])
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Management ──
    st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Quản lý</div>', unsafe_allow_html=True)
    if st.button("🧹 Xóa chat", use_container_width=True, type="secondary"):
        st.session_state.messages = []
        st.rerun()
    if st.button("🗑️ Xóa bộ nhớ", use_container_width=True, type="secondary"):
        api_call("DELETE", f"/memory/{st.session_state.user_id}")
        st.toast("✅ Memory cleared", icon="✅")
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN AREA
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🩺 Trợ lý Y tế AI</h1>
    <p>Hỏi về sức khỏe, triệu chứng, thuốc men — hoặc bất cứ điều gì bạn muốn</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab_chat, tab_plan = st.tabs(["💬 Trò chuyện", "📋 Kế hoạch"])

# ── TAB 1: CHAT ──────────────────────────────────────────────────────────────

with tab_chat:
    # ── Voice transcript from sessionStorage (no reload) ──
    voice_text_from_storage = st.query_params.get("voice_text", None)
    if voice_text_from_storage:
        st.session_state.voice_transcript = voice_text_from_storage
        st.session_state.show_voice_box = True
        # clear query param
        st.query_params.clear()
        st.rerun()

    # ── Voice transcript preview ──
    if st.session_state.get("show_voice_box") and st.session_state.get("voice_transcript"):
        transcript = st.session_state.voice_transcript
        cols = st.columns([4, 1, 1])
        with cols[0]:
            st.markdown(f"""
            <div class="voice-input-row">
                <span>🎤</span>
                <span>{transcript}</span>
            </div>
            """, unsafe_allow_html=True)
        with cols[1]:
            if st.button("✅ Gửi", key="voice_send", use_container_width=True, type="primary"):
                text = st.session_state.voice_transcript
                st.session_state.show_voice_box = False
                st.session_state.voice_transcript = ""
                st.query_params.clear()
                send_chat(text)
        with cols[2]:
            if st.button("❌ Hủy", key="voice_cancel", use_container_width=True):
                st.session_state.show_voice_box = False
                st.session_state.voice_transcript = ""
                st.query_params.clear()
                st.rerun()

    # ── Chat Messages ──
    chat_container = st.container()
    with chat_container:
        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant" and "routing" in msg:
                    intent = msg["routing"].get("intent", "")
                    conf = msg["routing"].get("confidence", 0)
                    st.markdown(
                        f"<span class='badge {intent.lower()}'>{intent} · {conf:.0%}</span>",
                        unsafe_allow_html=True,
                    )
                st.markdown(f"<div class='chat-msg {msg['role']}'>{msg['content']}</div>", unsafe_allow_html=True)

                # Auto-play TTS
                if msg["role"] == "assistant" and "audio_b64" in msg:
                    st.markdown(
                        f'<audio autoplay="true" src="data:audio/mp3;base64,{msg["audio_b64"]}"></audio>',
                        unsafe_allow_html=True,
                    )

    # ── Chat Input (with inline voice button) ──
    chat_cols = st.columns([1, 12, 1])
    with chat_cols[0]:
        # Use a static label; clicking triggers JS via st.button + rerun
        pass
    with chat_cols[1]:
        prompt = st.chat_input("💬 Nhập tin nhắn... (hoặc nhấn nút 🎤 để ghi âm)", key="main_chat_input")
        if prompt:
            send_chat(prompt)
    with chat_cols[2]:
        # Voice button placed beside chat input for natural UX
        if not st.session_state.get("_recording", False):
            if st.button("🎤", key="voice_start_btn", help="Ghi âm", use_container_width=False):
                st.markdown("""
                <script>
                (async function() {
                    const ok = await window.startVoiceRecord();
                    if (!ok) alert('Không thể truy cập micro. Vui lòng cho phép quyền micro.');
                })();
                </script>
                """, unsafe_allow_html=True)
                st.session_state["_recording"] = True
                st.rerun()
        else:
            if st.button("⏹", key="voice_stop_btn", help="Dừng ghi âm", type="primary"):
                st.markdown(f"""
                <script>
                (async function() {{
                    const text = await window.pollVoiceResult('{st.session_state.api_url}', '{st.session_state.tts_lang}');
                    if (text) {{
                        const pollEl = document.getElementById('voice_poll');
                        if (pollEl) {{
                            pollEl.setAttribute('data-text', text);
                            pollEl.dispatchEvent(new Event('voice_done'));
                        }}
                    }}
                }})();
                </script>
                """, unsafe_allow_html=True)
                st.session_state["_recording"] = False
                st.rerun()

    # ── Poll for voice result from sessionStorage ──
    # After rerun, check if there's a stored transcript
    voice_poll = st.empty()
    stored = voice_poll.markdown("""
    <div id="voice_result_check"></div>
    <script>
    (function() {
        const transcript = sessionStorage.getItem('voice_transcript');
        if (transcript) {
            const params = new URLSearchParams(window.location.search);
            params.set('voice_text', transcript);
            const newUrl = window.location.pathname + '?' + params.toString();
            window.history.replaceState({}, '', newUrl);
            sessionStorage.removeItem('voice_transcript');
            sessionStorage.removeItem('voice_ts');
        }
    })();
    </script>
    """, unsafe_allow_html=True)

    # Check if query param has voice text (set by JS above → rerun triggered)
    if st.query_params.get("voice_text"):
        vt = st.query_params["voice_text"]
        st.session_state.voice_transcript = vt
        st.session_state.show_voice_box = True
        st.query_params.clear()
        st.rerun()


# ── TAB 2: PLAN ──────────────────────────────────────────────────────────────

with tab_plan:
    if not st.session_state.plan_loaded:
        load_plan()

    load_plan()  # always refresh on tab view

    pd = st.session_state.plan_data
    tasks = pd.get("items", [])

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### 📋 Danh sách công việc")

        # ═══ ADD TASK FORM ═══
        with st.expander("➕ Thêm công việc mới", expanded=False):
            with st.form("add_task_form", clear_on_submit=True):
                task_text = st.text_input("Mô tả công việc", placeholder="VD: Uống thuốc cảm", key="plan_new_task")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    task_date = st.date_input("Ngày", value=None, key="plan_new_date")
                with col_b:
                    task_priority = st.selectbox("Ưu tiên", ["low", "medium", "high"], index=0, key="plan_new_pri")
                with col_c:
                    submitted = st.form_submit_button("➕ Thêm", type="primary", use_container_width=True)
                if submitted and task_text.strip():
                    date_str = task_date.isoformat() if task_date else None
                    resp = api_call("POST", "/plan/create", json={
                        "user_id": st.session_state.user_id,
                        "task": task_text.strip(),
                        "date": date_str,
                        "priority": task_priority,
                    }, timeout=5)
                    load_plan()
                    st.rerun()

        if not tasks:
            st.info("Chưa có công việc nào. Hãy nói với chatbot hoặc dùng form trên để thêm mới.")
        else:
            pending_tasks = [t for t in tasks if t.get("status") == "pending"]
            completed_tasks = [t for t in tasks if t.get("status") == "completed"]

            if pending_tasks:
                st.markdown("**⏳ Đang chờ**")
                for t in pending_tasks:
                    tid = t.get("id", "")
                    priority = t.get("priority", "low")
                    pri_class = f"priority-{priority}"
                    pri_label = {"high": "🔴 Cao", "medium": "🟡 TB", "low": "🟢 Thấp"}.get(priority, priority)

                    # Edit state
                    edit_key = f"edit_{tid}"
                    if st.session_state.get(edit_key, False):
                        with st.form(key=f"edit_form_{tid}"):
                            new_text = st.text_input("Task", value=t.get("task",""), key=f"edit_text_{tid}")
                            col_a, col_b, col_c, col_d = st.columns([2,2,1,1])
                            with col_a:
                                current_date = t.get("date","")
                                try:
                                    date_val = datetime.strptime(current_date, "%Y-%m-%d").date()
                                except:
                                    date_val = None
                                new_date = st.date_input("Ngày", value=date_val, key=f"edit_date_{tid}")
                            with col_b:
                                new_pri = st.selectbox("Ưu tiên", ["low","medium","high"],
                                    index=["low","medium","high"].index(t.get("priority","low")), key=f"edit_pri_{tid}")
                            with col_c:
                                saved = st.form_submit_button("💾 Lưu", type="primary", use_container_width=True)
                            with col_d:
                                canceled = st.form_submit_button("❌", use_container_width=True)
                            if saved:
                                date_str = new_date.isoformat() if new_date else t.get("date","")
                                api_call("POST", "/plan/update", json={
                                    "user_id": st.session_state.user_id,
                                    "task_id": tid,
                                    "task": new_text,
                                    "date": date_str,
                                    "priority": new_pri,
                                }, timeout=5)
                                st.session_state[edit_key] = False
                                load_plan()
                                st.rerun()
                            if canceled:
                                st.session_state[edit_key] = False
                                st.rerun()
                    else:
                        cols = st.columns([4, 1, 1, 1])
                        with cols[0]:
                            st.markdown(f"""
                            <p style="margin:0;"><strong>{t.get('task','')}</strong></p>
                            <p style="margin:0;font-size:0.75rem;color:#6b7280;">
                                📅 {t.get('date','')} &nbsp;·&nbsp; <span class="{pri_class}">{pri_label}</span>
                            </p>
                            """, unsafe_allow_html=True)
                        with cols[1]:
                            if st.button("✅", key=f"complete_{tid}", help="Hoàn thành"):
                                plan_complete(tid)
                        with cols[2]:
                            if st.button("✏️", key=f"edit_btn_{tid}", help="Sửa"):
                                st.session_state[edit_key] = True
                                st.rerun()
                        with cols[3]:
                            if st.button("🗑️", key=f"delete_{tid}", help="Xóa"):
                                plan_delete(tid)

            if completed_tasks:
                st.markdown("**✅ Đã hoàn thành**")
                for t in completed_tasks:
                    tid = t.get("id", "")
                    cols = st.columns([5, 1])
                    with cols[0]:
                        st.markdown(f"""
                        <p style="margin:0;text-decoration:line-through;opacity:0.7;"><strong>{t.get('task','')}</strong></p>
                        <p style="margin:0;font-size:0.75rem;color:#6b7280;">✅ {t.get('completed_at',t.get('date',''))[:10]}</p>
                        """, unsafe_allow_html=True)
                    with cols[1]:
                        if st.button("🗑️", key=f"del_done_{tid}", help="Xóa"):
                            plan_delete(tid)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Làm mới", use_container_width=True, type="secondary"):
            load_plan()
            st.rerun()

    with col_right:
        st.markdown("### 📊 Thống kê")
        st.markdown(f"""
        <div style="background:white;border:1px solid #e5e7eb;border-radius:12px;padding:1rem;">
            <div style="display:flex;justify-content:space-between;padding:0.3rem 0;border-bottom:1px solid #f3f4f6;">
                <span style="color:#6b7280;">Tổng số</span>
                <span style="font-weight:600;">{pd.get('total',0)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:0.3rem 0;border-bottom:1px solid #f3f4f6;">
                <span style="color:#6b7280;">Đang chờ</span>
                <span style="font-weight:600;color:#eab308;">{pd.get('pending',0)}</span>
            </div>
            <div style="display:flex;justify-content:space-between;padding:0.3rem 0;">
                <span style="color:#6b7280;">Đã hoàn thành</span>
                <span style="font-weight:600;color:#22c55e;">{pd.get('completed',0)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 🔔 Nhắc nhở hôm nay")
        try:
            rem = api_call("GET", f"/reminders/{st.session_state.user_id}", timeout=5)
            if "error" not in rem:
                items = rem.get("items", [])
                if items:
                    for item in items:
                        st.warning(f"📌 {item.get('task','')}")
                else:
                    st.success("✓ Không có nhắc nhở nào")
            else:
                st.caption("Không thể tải nhắc nhở")
        except:
            st.caption("Không thể tải nhắc nhở")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 💡 Mẹo")
        st.caption("""
        • *"Thêm việc uống thuốc ngày mai"* → tạo task  
        • *"Xem kế hoạch của tôi"* → xem danh sách  
        • Nhấn ✅ / ✏️ / 🗑️ để hoàn thành/sửa/xóa  
        • Dùng form **➕ Thêm** bên trái để tạo task trực tiếp
        """)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.caption("""
🩺 **Trợ lý Y tế AI** — Hỗ trợ tư vấn sức khỏe, không thay thế chẩn đoán y tế chuyên nghiệp.  
🔒 Dữ liệu được lưu trữ cục bộ và bảo mật.
""")