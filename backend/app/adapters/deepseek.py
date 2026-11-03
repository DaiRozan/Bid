import json
from typing import TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class ModelConfigurationError(RuntimeError):
    pass


class ModelResponseError(RuntimeError):
    pass


class DeepSeekClient:
    def __init__(self, settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None, *, max_tokens: int = 4096, timeout_seconds: float = 45):
        self.settings = settings or get_settings()
        self.transport = transport
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds

    async def complete_json(self, system: str, payload: dict, response_model: type[T]) -> T:
        if not self.settings.deepseek_api_key:
            raise ModelConfigurationError("未配置 DeepSeek API 密钥")
        request = {
            "model": self.settings.deepseek_model,
            "messages": [
                {"role": "system", "content": system + "\n必须返回一个 JSON 对象，严格符合以下 JSON Schema；不要输出 Markdown 围栏或额外说明：\n" + json.dumps(response_model.model_json_schema(), ensure_ascii=False)},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.max_tokens,
        }
        headers = {"Authorization": f"Bearer {self.settings.deepseek_api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(base_url=self.settings.deepseek_base_url, transport=self.transport, timeout=self.timeout_seconds) as client:
                response = await client.post("/chat/completions", headers=headers, json=request)
                response.raise_for_status()
        except httpx.ReadTimeout as exc:
            raise ModelResponseError("DeepSeek 请求超时") from exc
        except httpx.HTTPError as exc:
            raise ModelResponseError(f"DeepSeek 请求失败：{exc}") from exc
        try:
            content = response.json()["choices"][0]["message"]["content"]
            return response_model.model_validate_json(content)
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
            raise ModelResponseError("DeepSeek 返回的结构化响应无效") from exc

