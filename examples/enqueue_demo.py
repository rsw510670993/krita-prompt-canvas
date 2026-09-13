"""Queue a deterministic SVG without contacting a model provider."""

from pathlib import Path

from krita_prompt_canvas.job_queue import FileJobQueue
from krita_prompt_canvas.models import RenderPlan
from krita_prompt_canvas.paths import queue_dir
from krita_prompt_canvas.svg_guard import validate_svg


SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600">
<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#6cc8ff"/><stop offset="1" stop-color="#ffe0ef"/></linearGradient></defs>
<g id="scene"><rect width="800" height="600" fill="url(#sky)"/><circle cx="620" cy="130" r="64" fill="#ffe38d"/><path d="M0 390 L180 220 L350 390 L500 250 L700 400 L800 300 L800 600 L0 600 Z" fill="#3c5576"/><path d="M0 430 Q220 390 420 430 T800 420 L800 600 L0 600 Z" fill="#4aa7bd"/></g></svg>"""


def main() -> None:
    safe_svg = validate_svg(SVG, 800, 600)
    plan = RenderPlan("Queue Demo", 800, 600, safe_svg, ("#6cc8ff", "#ffe0ef"))
    job = FileJobQueue(queue_dir()).enqueue(plan, Path.cwd() / "outputs")
    print(f"Queued {job.job_id}. Keep Krita open with the bridge enabled.")


if __name__ == "__main__":
    main()

