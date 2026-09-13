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
            raise PlanError("API base URL is required")
        return f"{base}/chat/completions"

    def validate(self) -> None:
        endpoint = urlsplit(self.chat_completions_url)
        if endpoint.scheme not in {"http", "https"} or not endpoint.netloc:
            raise PlanError("API base URL must be an absolute HTTP or HTTPS URL")
        if not self.model.strip():
            raise PlanError("Model name is required")


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
            raise PlanError("Model response is missing title, width, height, or svg") from exc

        if not title:
            raise PlanError("Artwork title cannot be empty")
        if len(title) > 200:
            raise PlanError("Artwork title cannot exceed 200 characters")
        if not 256 <= width <= 4096 or not 256 <= height <= 4096:
            raise PlanError("Canvas dimensions must be between 256 and 4096 pixels")
        if not svg:
            raise PlanError("SVG cannot be empty")

        raw_palette = data.get("palette", [])
        if not isinstance(raw_palette, list):
            raise PlanError("palette must be a JSON array")
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
