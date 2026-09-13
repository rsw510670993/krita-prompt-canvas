import json
import unittest

from krita_prompt_canvas.llm import _extract_json_object
from krita_prompt_canvas.models import ApiSettings


class LlmTests(unittest.TestCase):
    def test_endpoint_join(self):
        settings = ApiSettings("https://provider.example/v1/", "secret", "model")
        self.assertEqual(
            settings.chat_completions_url,
            "https://provider.example/v1/chat/completions",
        )

    def test_extracts_fenced_json(self):
        payload = {"title": "Demo", "width": 800, "height": 600, "svg": "<svg/>"}
        parsed = _extract_json_object("```json\n" + json.dumps(payload) + "\n```")
        self.assertEqual(parsed["title"], "Demo")


if __name__ == "__main__":
    unittest.main()

