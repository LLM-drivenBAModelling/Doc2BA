import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_anthropic import ChatAnthropic


load_dotenv(
    dotenv_path=Path(__file__).resolve().parent.parent / ".env",
    override=False,
)


def create_chat_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
):
    """Return a provider-agnostic LangChain chat model.

    Provider selection precedence: explicit arg -> env LLM_PROVIDER -> 'openai'.
    
    For GPT-5 and newer models, structured output mode is automatically enabled
    when using .with_structured_output() method.
    """
    selected_provider = (provider or os.getenv("LLM_PROVIDER") or "openai").lower()

    if selected_provider == "openai":
        chosen_model = model or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        # GPT-5 and newer models support strict structured outputs
        # The strict mode is enabled automatically by with_structured_output()
        return ChatOpenAI(
            model=chosen_model, 
            temperature=temperature,
            model_kwargs={"response_format": {"type": "json_object"}} if "gpt-3.5" in chosen_model else {}
        )

    if selected_provider == "anthropic":
        chosen_model = model or os.getenv("DEFAULT_MODEL", "claude-3-5-sonnet-latest")
        return ChatAnthropic(model=chosen_model, temperature=temperature)

    if selected_provider == "azure":
        deployment = (
            os.getenv("AZURE_OPENAI_DEPLOYMENT")
            if not model or model.lower() == "default"
            else model
        )
        if not deployment:
            raise ValueError("AZURE provider requires --model or AZURE_OPENAI_DEPLOYMENT")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION") or os.getenv("OPENAI_API_VERSION")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        if azure_endpoint:
            azure_endpoint = azure_endpoint.rstrip("/").removesuffix("/openai/v1")
        return AzureChatOpenAI(
            azure_deployment=deployment,
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            temperature=temperature,
        )

    raise ValueError(f"Unsupported provider: {selected_provider}")
