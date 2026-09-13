from __future__ import annotations

import json
import os
import re
import time
import uuid
from pathlib import Path
from typing import Any

from .models import RenderJob, RenderPlan


def safe_stem(title: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_-]+", "-", title.strip()).strip("-_").lower()
    return stem[:64] or "krita-artwork"


class FileJobQueue:
    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    def enqueue(self, plan: RenderPlan, output_dir: Path) -> RenderJob:
        output_dir = output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        job_id = f"{int(time.time())}-{uuid.uuid4().hex[:10]}"
        job = RenderJob(job_id, plan.title, plan.width, plan.height, plan.svg, output_dir)
        data = {
            "protocol": 1,
            "job_id": job.job_id,
            "title": job.title,
            "width": job.width,
            "height": job.height,
            "svg": job.svg,
            "output_dir": str(job.output_dir),
            "output_stem": f"{safe_stem(job.title)}-{job.job_id}",
        }
        temporary = self.directory / f"{job_id}.request.json.tmp"
        destination = self.directory / f"{job_id}.request.json"
        temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, destination)
        return job

    def read_result(self, job_id: str) -> dict[str, Any] | None:
        path = self.directory / f"{job_id}.result.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None

