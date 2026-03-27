"""
bedrock_client.py
-----------------
Handles the connection to AWS Bedrock and initializes the Claude LLM.

WHY BEDROCK:
  AWS Bedrock is a managed AI service — you don't host Claude yourself,
  AWS does. You just send API calls. This is how real companies use LLMs.

WHY langchain-aws:
  ChatBedrockConverse is the modern way (2025+) to call Bedrock models.
  It handles message formatting, streaming, and tool binding automatically.
"""

import os
from dotenv import load_dotenv
from langchain_aws import ChatBedrockConverse

# Load environment variables from .env file
# WHY: Keeps secrets out of code. Never hardcode API keys.
load_dotenv()


def get_llm(temperature: float = 0.1):
    """
    Returns a Claude LLM instance connected via AWS Bedrock.

    Args:
        temperature: Controls randomness. 0.1 = focused/deterministic,
                     which is what you want for financial decisions.
                     Higher = more creative but less reliable.

    Returns:
        ChatBedrockConverse: A LangChain-compatible LLM object
    """

    model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-5-haiku-20241022-v1:0")
    region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

    llm = ChatBedrockConverse(
        model=model_id,
        region_name=region,
        temperature=temperature,
        max_tokens=2048,
    )

    return llm


if __name__ == "__main__":
    # Quick test — run this file directly to verify your AWS connection works
    # Command: python src/bedrock_client.py
    print("Testing Bedrock connection...")
    llm = get_llm()
    response = llm.invoke("Say 'Bedrock connection successful!' and nothing else.")
    print(response.content)