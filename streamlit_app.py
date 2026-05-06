"""
streamlit_app.py — FULL Production UI (fixed + enhanced)
"""

import os
import streamlit as st
import requests

DEFAULT_API_URL = os.getenv("STREAMLIT_API_URL", "http://127.0.0.1:8000")

# ── CONFIG ─────────────────────────────────────────

st.set_page_config(
    page_title="Healthcare AI Agent",
    page_icon="🩺",
    layout="wide",
)

# ── STYLE ──────────────────────────────────────────

st.markdown("""
<style>
.badge {
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}
.RAG { background: #1e3a5f; color: #5bc8f5; }
.SYMPTOM { background: #5f1e1e; color: #ff6b6b; }
.PLANNER { background: #1e5f2a; color: #6bff95; }
.CHAT { background: #333; color: #aaa; }
</style>
""", unsafe_allow_html=True)

# ── SESSION ────────────────────────────────────────

if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_id" not in st.session_state:
    st.session_state.user_id = "user_1"
if "last_user_id" not in st.session_state:
    st.session_state.last_user_id = st.session_state.user_id

if "api_url" not in st.session_state:
    st.session_state.api_url = DEFAULT_API_URL
if "memory_snapshot" not in st.session_state:
    st.session_state.memory_snapshot = {"total_exchanges": 0, "recent": []}

# ── SIDEBAR ───────────────────────────────────────

with st.sidebar:
    st.title("🩺 Healthcare Agent")

    st.session_state.api_url = st.text_input(
        "Backend API URL",
        value=st.session_state.api_url,
        placeholder="http://127.0.0.1:8000",
    )

    st.session_state.user_id = st.text_input(
        "User ID",
        value=st.session_state.user_id,
    )

    if st.session_state.user_id != st.session_state.last_user_id:
        st.warning(
            f"Switching user from {st.session_state.last_user_id} → {st.session_state.user_id}. "
            "Chat history đã được reset."
        )
        st.session_state.messages = []
        st.session_state.memory_snapshot = {"total_exchanges": 0, "recent": []}
        st.session_state.last_user_id = st.session_state.user_id

    api_url = st.session_state.api_url

    st.divider()

    # 🔍 API HEALTH CHECK
    if st.button("🔍 Check Backend"):
        try:
            r = requests.get(f"{api_url}/", timeout=3)
            if r.ok:
                st.success("Backend OK")
            else:
                st.error(f"Backend returned {r.status_code}")
        except Exception as exc:
            st.error(f"Backend NOT running: {exc}")

    st.divider()

    # 📋 PLAN
    st.subheader("📋 Health Plan")

    if st.button("Load Plan"):
        try:
            r = requests.get(f"{api_url}/plan/{st.session_state.user_id}", timeout=5)
            r.raise_for_status()
            data = r.json()

            st.metric("Pending", data["pending"])
            st.metric("Done", data["completed"])

            for item in data["items"]:
                icon = "✅" if item["status"] == "completed" else "⏳"
                st.write(f"{icon} {item['task']} ({item['date']})")

        except Exception as e:
            st.error(str(e))

    st.divider()

    # 🔔 REMINDERS
    if st.button("🔔 Reminders"):
        try:
            r = requests.get(f"{api_url}/reminders/{st.session_state.user_id}", timeout=5)
            r.raise_for_status()
            data = r.json()

            if data["items"]:
                for item in data["items"]:
                    st.warning(f"📌 {item['task']}")
            else:
                st.success("No reminders")

        except Exception as e:
            st.error(str(e))

    st.divider()

    # 🧠 MEMORY
    if st.button("🧠 Refresh Memory"):
        try:
            r = requests.get(f"{api_url}/memory/{st.session_state.user_id}", timeout=5)
            r.raise_for_status()
            st.session_state.memory_snapshot = r.json()

        except Exception as e:
            st.error(str(e))

    snapshot = st.session_state.memory_snapshot
    st.write(f"Total: {snapshot.get('total_exchanges', 0)}")
    for m in snapshot.get("recent", []):
        st.caption(f"👤 {m.get('user', '')}")
        st.caption(f"🤖 {m.get('bot', '')}")

    if st.button("🗑️ Clear Memory"):
        try:
            requests.delete(f"{api_url}/memory/{st.session_state.user_id}")
            st.session_state.memory_snapshot = {"total_exchanges": 0, "recent": []}
            st.success("Memory cleared")
        except Exception as exc:
            st.error(f"Clear memory failed: {exc}")

    st.divider()

    if st.button("🧹 Clear Chat"):
        st.session_state.messages = []
        st.experimental_rerun()

api_url = st.session_state.api_url

# ── MAIN CHAT ─────────────────────────────────────

st.title("🩺 Healthcare AI Assistant")

# Render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant" and "routing" in msg:
            intent = msg["routing"].get("intent", "")
            conf = msg["routing"].get("confidence", 0)

            st.markdown(
                f"<span class='badge {intent}'>{intent} · {conf:.0%}</span>",
                unsafe_allow_html=True,
            )

        st.markdown(msg["content"])

# ── INPUT ─────────────────────────────────────────

prompt = st.chat_input("Ask health question, symptoms, or plan...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()

        try:
            with st.spinner("Thinking..."):
                r = requests.post(
                        f"{api_url}/chat",
                        json={
                            "user_id": st.session_state.user_id,
                            "message": prompt,
                        },
                        timeout=60,  # tăng timeout tránh lỗi
                    )

                r.raise_for_status()
                data = r.json()

            response = data["response"]
            routing = data.get("routing", {})

            intent = routing.get("intent", "")
            conf = routing.get("confidence", 0)

            placeholder.markdown(
                f"<span class='badge {intent}'>{intent} · {conf:.0%}</span>",
                unsafe_allow_html=True,
            )
            st.markdown(response)

            st.session_state.messages.append({
                "role": "assistant",
                "content": response,
                "routing": routing,
            })

        except requests.exceptions.Timeout:
            st.error("⏱ Timeout — model trả lời quá lâu")

        except requests.exceptions.ConnectionError:
            st.error("❌ Backend chưa chạy (uvicorn)")

        except Exception as e:
            st.error(f"🔥 Error: {e}")