from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import ApiSettings, PlanError, RenderPlan
from .prompts import build_messages


class ApiError(RuntimeError):
    """OpenAI-compatible endpoint failure with secrets excluded."""


def _extract_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            raise PlanError("模型没有返回 JSON 对象") from exc
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as nested:
            raise PlanError("模型返回了无效的 JSON") from nested
    if not isinstance(parsed, dict):
        raise PlanError("模型响应必须是 JSON 对象")
    return parsed


class OpenAICompatibleClient:
    def __init__(self, settings: ApiSettings):
        settings.validate()
        self.settings = settings

    def create_plan(self, user_request: str, width: int, height: int) -> RenderPlan:
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": build_messages(user_request, width, height),
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }
        try:
            response = self._post(payload)
        except ApiError as exc:
            # Some compatible providers implement Chat Completions but not response_format.
            if "HTTP 400" not in str(exc) and "HTTP 422" not in str(exc):
                raise
            payload.pop("response_format", None)
            response = self._post(payload)

        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ApiError("接口响应不符合 Chat Completions 格式") from exc
        if not isinstance(content, str):
            raise ApiError("接口返回了非文本消息内容")
        plan = RenderPlan.from_mapping(_extract_json_object(content))
        if plan.width != width or plan.height != height:
            raise PlanError("模型擅自改变了请求的画布尺寸")
        return plan

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        request = Request(
            self.settings.chat_completions_url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = exc.read(2048).decode("utf-8", errors="replace")
            raise ApiError(f"HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise ApiError(f"无法连接 API 接口：{exc.reason}") from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ApiError("API 接口返回了无效的 JSON") from exc
        if not isinstance(parsed, dict):
            raise ApiError("API 接口返回了非预期的 JSON 内容")
        return parsed
