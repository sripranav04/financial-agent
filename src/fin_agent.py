"""
fin_agent.py
--------
The core financial agent built with LangGraph.

WHY LANGGRAPH OVER PLAIN LANGCHAIN:
  LangChain lets you chain calls linearly: A → B → C
  LangGraph lets you build LOOPS and BRANCHES: A → B → A again if needed
  That loop is what makes it "agentic" — the model keeps going until
  it's confident enough to stop, calling tools as many times as it needs.

THE REACT PATTERN:
  Thought → Action → Observation → Thought → Action → ... → Final Answer
  LangGraph's create_react_agent handles this loop for us automatically.

MEMORY:
  We use LangGraph's built-in MemorySaver so the agent remembers
  what was said earlier in the same conversation session.
  Each Streamlit session gets its own thread_id so conversations
  don't bleed into each other.
"""

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, SystemMessage
from bedrock_client import get_llm
from tools import TOOLS


# ── System prompt ────────────────────────────────────────────────────────────
# WHY THIS MATTERS: The system prompt defines the agent's personality,
# constraints, and reasoning style. For financial agents, we want it to:
#   1. Always show its reasoning (educational for you reading the output)
#   2. Never give reckless advice
#   3. Use tools before forming opinions — no hallucinated data

SYSTEM_PROMPT = """You are FinAgent, a professional AI financial analyst assistant.

You have access to real-time stock market tools. Always use them — never
guess or rely on your training data for prices, as markets change daily.

YOUR REASONING PROCESS (always follow this):
1. Understand what the user is asking
2. Identify which tools you need and in what order
3. Call the tools to gather real data
4. Analyze the data carefully
5. Give a clear, structured answer with your reasoning

YOUR RESPONSE FORMAT:
- Start with a brief summary of what you found
- Show key data points
- Give your analysis (trends, risks, opportunities)
- End with a clear recommendation or next step
- Always add a disclaimer that this is educational, not financial advice

IMPORTANT RULES:
- Always fetch fresh data before giving any price-based opinion
- If comparing stocks, use the compare tool rather than calling each separately
- Be specific with numbers — vague answers are not helpful
- If you're uncertain, say so and explain why
"""


def create_agent():
    """
    Builds and returns the LangGraph ReAct agent.

    WHY MemorySaver:
      Stores conversation history in memory (RAM) per thread.
      In production you'd swap this for a database (Redis, DynamoDB).
      For this learning project, RAM is perfect.

    WHY bind tools on the LLM:
      create_react_agent handles tool binding internally.
      It tells Claude: "here are the tools you can call, here are
      their signatures, here is when to use them."
    """
    llm = get_llm(temperature=0.1)
    memory = MemorySaver()

    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT,  # ← changed from state_modifier
    )
    return agent


def run_agent(agent, user_message: str, thread_id: str = "default") -> dict:
    """
    Sends a message to the agent and returns the full response.

    Args:
        agent:        The compiled LangGraph agent
        user_message: What the user typed
        thread_id:    Unique ID per conversation session (enables memory)

    Returns:
        dict with 'response' (final answer) and 'steps' (tool calls made)

    WHY thread_id:
      LangGraph uses this to look up the right memory checkpoint.
      Different thread_ids = different conversation histories.
      We'll generate one per Streamlit session in app.py.
    """

    config = {"configurable": {"thread_id": thread_id}}

    # Stream the response so we can capture intermediate tool steps
    # WHY stream: lets us show the user what tools were called (transparency)
    steps = []
    final_response = ""

    for chunk in agent.stream(
        {"messages": [HumanMessage(content=user_message)]},
        config=config,
        stream_mode="values",
    ):
        messages = chunk.get("messages", [])
        for msg in messages:
            msg_type = type(msg).__name__

            # ToolMessage = the result of a tool call
            if msg_type == "ToolMessage":
                steps.append({
                    "tool": msg.name,
                    "result": msg.content
                })

            # AIMessage = Claude's reasoning or final answer
            elif msg_type == "AIMessage" and msg.content:
                final_response = msg.content

    return {
        "response": final_response,
        "steps": steps,
    }


# ── Quick CLI test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    """
    Test the agent directly from the terminal without the UI.
    Run: python src/agent.py
    """
    print("🤖 FinAgent starting up...\n")
    agent = create_agent()

    test_questions = [
        "What is Apple's current stock price and should I be interested in it?",
    ]

    for question in test_questions:
        print(f"👤 User: {question}")
        print("⏳ Thinking...\n")

        result = run_agent(agent, question, thread_id="test-session")

        # Show which tools were called — this is the agentic transparency
        if result["steps"]:
            print("🔧 Tools called:")
            for step in result["steps"]:
                print(f"   → {step['tool']}")
            print()

        print(f"🤖 FinAgent:\n{result['response']}")
        print("\n" + "="*60 + "\n")