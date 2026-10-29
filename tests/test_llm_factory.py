import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


class LlmFactoryEnvironmentTests(unittest.TestCase):
    def test_factory_loads_project_root_dotenv_without_overriding_exported_values(self):
        sys.modules.pop("llm.factory", None)

        with patch("dotenv.load_dotenv") as load_dotenv:
            importlib.import_module("llm.factory")

        expected_path = Path(__file__).resolve().parents[1] / ".env"
        load_dotenv.assert_called_once_with(dotenv_path=expected_path, override=False)

    def test_azure_uses_project_configuration_and_normalizes_v1_endpoint(self):
        from llm.factory import create_chat_llm

        environment = {
            "AZURE_OPENAI_API_VERSION": "2024-02-15-preview",
            "AZURE_OPENAI_DEPLOYMENT": "test-deployment",
            "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/openai/v1",
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch("llm.factory.AzureChatOpenAI") as azure_chat:
                create_chat_llm(provider="azure", model="default")

        azure_chat.assert_called_once_with(
            azure_deployment="test-deployment",
            api_version="2024-02-15-preview",
            azure_endpoint="https://example.openai.azure.com",
            temperature=0.0,
        )


if __name__ == "__main__":
    unittest.main()
