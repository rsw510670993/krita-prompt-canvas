"""Krita-side bridge. This module intentionally uses only Krita's bundled modules."""

import json
import os
import re
import sys
import time
import traceback
from pathlib import Path

from PyQt5.QtCore import QTimer
from krita import Extension, InfoObject, Krita


MAX_SVG_BYTES = 1_000_000
STEM_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,96}$")
JOB_ID_PATTERN = re.compile(r"^[0-9]{10,13}-[0-9a-f]{10}$")
FORBIDDEN_SVG = re.compile(
    r"(?i)(<\s*script|<\s*style|<\s*foreignObject|<\s*image|javascript:|data:)"
)
EXTERNAL_URL = re.compile(r"(?i)https?://")
SVG_NAMESPACE = 'xmlns="http://www.w3.org/2000/svg"'


def _queue_dir():
    override = os.environ.get("KPC_QUEUE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "krita-prompt-canvas" / "queue"


def _atomic_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    os.replace(str(temporary), str(path))


class PromptCanvasBridge(Extension):
    def __init__(self, parent):
        super().__init__(parent)
        self.queue = _queue_dir()
        self.timer = None
        self.busy = False

    def setup(self):
        self.queue.mkdir(parents=True, exist_ok=True)
        self.timer = QTimer(self)
        self.timer.setInterval(750)
        self.timer.timeout.connect(self.process_next)
        self.timer.start()

    def createActions(self, window):
        action = window.createAction(
            "krita_prompt_canvas_process_next", "Process Prompt Canvas Job"
        )
        action.triggered.connect(self.process_next)

    def process_next(self):
        if self.busy:
            return
        requests = sorted(self.queue.glob("*.request.json"))
        if not requests:
            return
        self.busy = True
        request_path = requests[0]
        processing_path = request_path.with_name(
            request_path.name.replace(".request.json", ".processing.json")
        )
        try:
            os.replace(str(request_path), str(processing_path))
            payload = json.loads(processing_path.read_text(encoding="utf-8"))
            result = self._render(payload)
        except Exception:
            job_id = request_path.name.split(".request.json", 1)[0]
            result = {
                "protocol": 1,
                "job_id": job_id,
                "status": "error",
                "error": traceback.format_exc(limit=12),
            }
        finally:
            try:
                processing_path.unlink(missing_ok=True)
            except Exception:
                pass
            self.busy = False
        result_path = self.queue / (str(result["job_id"]) + ".result.json")
        _atomic_json(result_path, result)

    def _render(self, payload):
        if payload.get("protocol") != 1:
            raise ValueError("Unsupported queue protocol")
        job_id = str(payload["job_id"])
        title = str(payload["title"])
        width, height = int(payload["width"]), int(payload["height"])
        svg = str(payload["svg"])
        stem = str(payload["output_stem"])
        output_dir = Path(str(payload["output_dir"])).expanduser().resolve()
        if not (256 <= width <= 4096 and 256 <= height <= 4096):
            raise ValueError("Canvas dimensions are outside the allowed range")
        if not JOB_ID_PATTERN.fullmatch(job_id):
            raise ValueError("Job id is unsafe")
        svg_without_namespace = svg.replace(SVG_NAMESPACE, "", 1)
        if (
            SVG_NAMESPACE not in svg
            or len(svg.encode("utf-8")) > MAX_SVG_BYTES
            or FORBIDDEN_SVG.search(svg)
            or EXTERNAL_URL.search(svg_without_namespace)
        ):
            raise ValueError("SVG failed the Krita-side safety check")
        if not STEM_PATTERN.fullmatch(stem):
            raise ValueError("Output stem is unsafe")
        output_dir.mkdir(parents=True, exist_ok=True)
        kra_path = output_dir / (stem + ".kra")
        png_path = output_dir / (stem + ".png")

        app = Krita.instance()
        document = app.createDocument(width, height, title, "RGBA", "U8", "", 72.0)
        if document is None:
            raise RuntimeError("Krita.createDocument returned None")
        try:
            vector_layer = document.createVectorLayer("AI-directed vector artwork")
            document.rootNode().addChildNode(vector_layer, None)
            shapes = vector_layer.addShapesFromSvg(svg)
            if not shapes:
                raise RuntimeError("Krita did not create any SVG shapes")
            document.refreshProjection()
            document.waitForDone()
            document.setBatchmode(True)
            if not document.saveAs(str(kra_path)):
                raise RuntimeError("Krita could not save the KRA document")
            if not document.exportImage(str(png_path), InfoObject()):
                raise RuntimeError("Krita could not export the PNG preview")
            document.waitForDone()
        finally:
            try:
                document.close()
            except Exception:
                pass
        return {
            "protocol": 1,
            "job_id": job_id,
            "status": "success",
            "title": title,
            "kra_path": str(kra_path),
            "png_path": str(png_path),
            "completed_at": int(time.time()),
        }


Krita.instance().addExtension(PromptCanvasBridge(Krita.instance()))
