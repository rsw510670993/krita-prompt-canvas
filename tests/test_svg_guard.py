import unittest

from krita_prompt_canvas.models import PlanError
from krita_prompt_canvas.svg_guard import validate_svg


VALID = """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600" viewBox="0 0 800 600"><defs><linearGradient id="g"><stop offset="0" stop-color="#fff"/></linearGradient></defs><g id="scene"><rect width="800" height="600" fill="url(#g)"/></g></svg>"""


class SvgGuardTests(unittest.TestCase):
    def test_accepts_single_scene_group(self):
        output = validate_svg(VALID, 800, 600)
        self.assertIn('id="scene"', output)

    def test_rejects_script(self):
        unsafe = VALID.replace('<g id="scene">', '<script>alert(1)</script><g id="scene">')
        with self.assertRaises(PlanError):
            validate_svg(unsafe, 800, 600)

    def test_rejects_external_url(self):
        unsafe = VALID.replace('fill="url(#g)"', 'fill="url(https://example.com/a.svg)"')
        with self.assertRaises(PlanError):
            validate_svg(unsafe, 800, 600)

    def test_rejects_missing_svg_namespace(self):
        unsafe = VALID.replace(' xmlns="http://www.w3.org/2000/svg"', "")
        with self.assertRaises(PlanError):
            validate_svg(unsafe, 800, 600)

    def test_rejects_multiple_visible_root_children(self):
        unsafe = VALID.replace("</svg>", '<circle cx="1" cy="1" r="1"/></svg>')
        with self.assertRaises(PlanError):
            validate_svg(unsafe, 800, 600)


if __name__ == "__main__":
    unittest.main()
