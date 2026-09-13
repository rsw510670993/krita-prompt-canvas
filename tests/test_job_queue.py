import json
import tempfile
import unittest
from pathlib import Path

from krita_prompt_canvas.job_queue import FileJobQueue, safe_stem
from krita_prompt_canvas.models import RenderPlan


class JobQueueTests(unittest.TestCase):
    def test_safe_stem(self):
        self.assertEqual(safe_stem("Morning Warm-up!"), "morning-warm-up")

    def test_enqueue_writes_complete_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            queue = FileJobQueue(root / "queue")
            plan = RenderPlan("Demo", 800, 600, "<svg/>")
            job = queue.enqueue(plan, root / "output")
            request = root / "queue" / f"{job.job_id}.request.json"
            self.assertTrue(request.exists())
            self.assertFalse((request.with_suffix(request.suffix + ".tmp")).exists())
            data = json.loads(request.read_text(encoding="utf-8"))
            self.assertEqual(data["protocol"], 1)
            self.assertEqual(data["width"], 800)


if __name__ == "__main__":
    unittest.main()

