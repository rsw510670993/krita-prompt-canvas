from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


class PlanError(ValueError):
    """Raised when a model response cannot be used as a render plan."""


@dataclass(frozen=True)
class ApiSettings:
    base_url: str
    api_key: str
    model: str
    timeout_seconds: float = 90.0

    @property
    def chat_completions_url(self) -> str:
        base = self.base_url.strip().rstrip("/")
        if not base:
            raise PlanError("必须填写 API 基础地址")
        return f"{base}/chat/completions"

    def validate(self) -> None:
        endpoint = urlsplit(self.chat_completions_url)
        if endpoint.scheme not in {"http", "https"} or not endpoint.netloc:
            raise PlanError("API 基础地址必须是完整的 HTTP 或 HTTPS 地址")
        if not self.model.strip():
            raise PlanError("必须填写模型名称")


@dataclass(frozen=True)
class RenderPlan:
    title: str
    width: int
    height: int
    svg: str
    palette: tuple[str, ...] = ()
    notes: str = ""

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "RenderPlan":
        try:
            title = str(data["title"]).strip()
            width = int(data["width"])
            height = int(data["height"])
            svg = str(data["svg"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise PlanError("模型响应缺少 title、width、height 或 svg 字段") from exc

        if not title:
            raise PlanError("作品标题不能为空")
        if len(title) > 200:
            raise PlanError("作品标题不能超过 200 个字符")
        if not 256 <= width <= 4096 or not 256 <= height <= 4096:
            raise PlanError("画布宽高必须在 256 至 4096 像素之间")
        if not svg:
            raise PlanError("SVG 内容不能为空")

        raw_palette = data.get("palette", [])
        if not isinstance(raw_palette, list):
            raise PlanError("palette 必须是 JSON 数组")
        palette = tuple(str(item) for item in raw_palette[:16])
        return cls(title, width, height, svg, palette, str(data.get("notes", "")))


@dataclass(frozen=True)
class RenderJob:
    job_id: str
    title: str
    width: int
    height: int
    svg: str
    output_dir: Path
