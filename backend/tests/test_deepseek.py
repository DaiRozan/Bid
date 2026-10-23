import asyncio

import httpx
import pytest
from pydantic import BaseModel

from app.adapters.deepseek import DeepSeekClient, ModelConfigurationError, ModelResponseError
from app.config import get_settings


class Answer(BaseModel):
    value: str


def test_missing_key_returns_configuration_error():
    settings = get_settings()
    settings.deepseek_api_key = None
    with pytest.raises(ModelConfigurationError):
        asyncio.run(DeepSeekClient(settings=settings).complete_json("system", {}, Answer))


def test_http_timeout_is_reported():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    settings = get_settings()
    settings.deepseek_api_key = "test-key"
    client = DeepSeekClient(settings=settings, transport=httpx.MockTransport(handler))
    with pytest.raises(ModelResponseError, match="超时"):
        asyncio.run(client.complete_json("system", {}, Answer))


def test_invalid_model_json_fails_without_fallback():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": [{"message": {"content": "not-json"}}]})

    settings = get_settings()
    settings.deepseek_api_key = "test-key"
    client = DeepSeekClient(settings=settings, transport=httpx.MockTransport(handler))
    with pytest.raises(ModelResponseError, match="结构化响应"):
        asyncio.run(client.complete_json("system", {}, Answer))

