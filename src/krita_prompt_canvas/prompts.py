from __future__ import annotations

import json


SYSTEM_PROMPT = """You are the vector art director for a Krita automation tool.
Return exactly one JSON object and no Markdown. The object must contain:
title (string), width (integer), height (integer), svg (string), palette (array of
hex colors), and notes (short string).

Create a complete, polished SVG illustration. Follow these constraints:
- Root element: <svg xmlns="http://www.w3.org/2000/svg" width="W" height="H"
  viewBox="0 0 W H">.
- Put definitions in one optional <defs>, then put every visible object inside
  exactly one top-level <g id="scene">. This preserves Krita stacking order.
- Within scene, paint back-to-front: background first, foreground details last.
- Allowed elements: svg, g, defs, linearGradient, radialGradient, stop, rect,
  circle, ellipse, line, polyline, polygon, path, text, tspan, clipPath, mask.
- No script, style element, animation, foreignObject, image, external URL,
  JavaScript, embedded data, href, filters, or fonts loaded from the network.
- Use explicit fills/strokes and a coherent palette. Prefer expressive paths,
  silhouettes, lighting, foreground depth, and readable focal hierarchy.
- Make the subject unmistakable and the composition fill the canvas.
- Do not place signatures, watermarks, brand names, or copyrighted characters.
"""


def build_messages(user_request: str, width: int, height: int) -> list[dict[str, str]]:
    request = user_request.strip()
    if not request:
        raise ValueError("Artwork request cannot be empty")
    dynamic = {
        "request": request,
        "canvas": {"width": width, "height": height},
        "instruction": "Design the scene now and return only the JSON object.",
    }
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": json.dumps(dynamic, ensure_ascii=False)},
    ]

