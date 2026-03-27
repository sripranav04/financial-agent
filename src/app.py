"""
app.py
------
Streamlit UI for FinAgent.

WHY STREAMLIT:
  Turns pure Python into a web app with no HTML/CSS/JS needed.
  Perfect for data/AI projects on GitHub — interviewers can run
  it instantly with one command.

UI DESIGN DECISIONS:
  - Chat interface (familiar UX like ChatGPT)
  - Expandable "tool calls" section (shows the agentic reasoning)
  - Session memory per browser tab (thread_id from session_state)
  - Suggested questions (lowers friction for first-time users)
"""

import streamlit as st
import uuid
import sys
import os

# Add src to path so imports work when run from project root
sys.path.insert(0, os.path.dirname(__file__))

from fin_agent import create_agent, run_agent

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinAgent — AI Stock Analyst",
    page_icon="📈",
    layout="wide",
)

# ── Session state setup ───────────────────────────────────────────────────────
# WHY session_state:
#   Streamlit reruns the entire script on every interaction.
#   session_state persists values across reruns within the same browser tab.

if "thread_id" not in st.session_state:
    # Unique ID per browser session = separate memory per user
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    # Chat history for display (separate from agent's internal memory)
    st.session_state.messages = []

if "agent" not in st.session_state:
    # Create agent once per session, not on every rerun
    with st.spinner("🤖 Initialising FinAgent..."):
        st.session_state.agent = create_agent()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("📈 FinAgent")
    st.caption("AI-powered stock analysis via AWS Bedrock + Claude")

    st.divider()

    st.markdown("### 💡 Try asking:")
    suggestions = [
        "Analyse AAPL and give me a recommendation",
        "Compare MSFT, GOOGL and META",
        "What's Tesla's 3-month trend?",
        "Show me analyst targets for NVDA",
        "Is Amazon a good buy right now?",
    ]

    for suggestion in suggestions:
        if st.button(suggestion, use_container_width=True):
            st.session_state.pending_input = suggestion

    st.divider()

    st.markdown("### 🔧 Available Tools")
    st.markdown("""
    - `get_stock_price` — Live price & stats
    - `get_stock_history` — Price trends
    - `compare_stocks` — Side-by-side view
    - `get_analyst_recommendation` — Pro targets
    """)

    st.divider()

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.thread_id = str(uuid.uuid4())
        st.rerun()

    st.caption(f"Session: `{st.session_state.thread_id[:8]}...`")
    st.caption("⚠️ Educational purposes only. Not financial advice.")

# ── Main chat area ────────────────────────────────────────────────────────────
st.title("📈 FinAgent — AI Stock Analyst")
st.caption("Powered by Claude 3.5 Haiku on AWS Bedrock · Real-time data via yfinance")

# Render existing chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show tool calls if this was an assistant message
        if msg["role"] == "assistant" and msg.get("steps"):
            with st.expander(f"🔧 Agent used {len(msg['steps'])} tool(s) — click to inspect"):
                for step in msg["steps"]:
                    st.markdown(f"**Tool:** `{step['tool']}`")
                    st.code(step["result"], language="text")

# ── Handle sidebar button clicks ──────────────────────────────────────────────
if "pending_input" in st.session_state:
    prompt = st.session_state.pop("pending_input")
else:
    prompt = st.chat_input("Ask about any stock... e.g. 'Analyse AAPL'")

# ── Process new message ───────────────────────────────────────────────────────
if prompt:
    # Show user message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Run the agent and show response
    with st.chat_message("assistant"):
        with st.spinner("⏳ Analysing... (fetching live data)"):
            result = run_agent(
                st.session_state.agent,
                prompt,
                thread_id=st.session_state.thread_id,
            )

        # Render the final response
        st.markdown(result["response"])

        # Show which tools were called (the agentic transparency layer)
        if result["steps"]:
            with st.expander(f"🔧 Agent used {len(result['steps'])} tool(s) — click to inspect"):
                for step in result["steps"]:
                    st.markdown(f"**Tool:** `{step['tool']}`")
                    st.code(step["result"], language="text")

    # Save to display history
    st.session_state.messages.append({
        "role": "assistant",
        "content": result["response"],
        "steps": result["steps"],
    })