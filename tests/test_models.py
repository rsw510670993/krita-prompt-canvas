import unittest

from krita_prompt_canvas.models import ApiSettings, PlanError, RenderPlan


class RenderPlanTests(unittest.TestCase):
    def test_from_mapping(self):
        plan = RenderPlan.from_mapping(
            {"title": "Demo", "width": 800, "height": 600, "svg": "<svg/>", "palette": []}
        )
        self.assertEqual(plan.title, "Demo")
        self.assertEqual(plan.width, 800)

    def test_rejects_large_canvas(self):
        with self.assertRaises(PlanError):
            RenderPlan.from_mapping(
                {"title": "Demo", "width": 9000, "height": 600, "svg": "<svg/>"}
            )

    def test_rejects_non_http_api_url(self):
        with self.assertRaises(PlanError):
            ApiSettings("file:///tmp/provider", "", "model").validate()


if __name__ == "__main__":
    unittest.main()
