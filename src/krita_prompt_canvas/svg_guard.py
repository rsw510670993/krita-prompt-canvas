from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from .models import PlanError


SVG_NS = "http://www.w3.org/2000/svg"
ALLOWED_ELEMENTS = {
    "svg",
    "g",
    "defs",
    "linearGradient",
    "radialGradient",
    "stop",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "path",
    "text",
    "tspan",
    "clipPath",
    "mask",
}
FORBIDDEN_TEXT = re.compile(
    r"(?i)(<\s*script|<\s*style|<\s*foreignObject|<\s*image|javascript:|data:)"
)
EXTERNAL_URL = re.compile(r"(?i)https?://")


def _local_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def validate_svg(svg: str, width: int, height: int) -> str:
    if len(svg.encode("utf-8")) > 1_000_000:
        raise PlanError("SVG exceeds the 1 MB safety limit")
    if FORBIDDEN_TEXT.search(svg):
        raise PlanError("SVG contains an external resource or unsafe element")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise PlanError(f"SVG is not valid XML: {exc}") from exc
    if _local_name(root.tag) != "svg":
        raise PlanError("Root element must be svg")
    if not root.tag.startswith(f"{{{SVG_NS}}}"):
        raise PlanError("Root element must use the standard SVG namespace")
    if root.attrib.get("width") != str(width) or root.attrib.get("height") != str(height):
        raise PlanError("SVG dimensions do not match the requested canvas")
    if root.attrib.get("viewBox") != f"0 0 {width} {height}":
        raise PlanError("SVG viewBox must exactly match the requested canvas")

    visible_root_children = []
    for element in root.iter():
        name = _local_name(element.tag)
        if name not in ALLOWED_ELEMENTS:
            raise PlanError(f"SVG element is not allowed: {name}")
        for attribute, value in element.attrib.items():
            attr_name = _local_name(attribute).lower()
            if attr_name.startswith("on") or attr_name in {"href", "src"}:
                raise PlanError(f"SVG attribute is not allowed: {attr_name}")
            if EXTERNAL_URL.search(value):
                raise PlanError("External URLs are not allowed in SVG attributes")
            if "url(" in value.lower() and not re.fullmatch(r"url\(#[A-Za-z_][\w.-]*\)", value):
                raise PlanError("Only local SVG paint references such as url(#gradient) are allowed")
    for child in list(root):
        if _local_name(child.tag) != "defs":
            visible_root_children.append(child)
    if len(visible_root_children) != 1:
        raise PlanError("SVG must contain exactly one visible top-level scene group")
    scene = visible_root_children[0]
    if _local_name(scene.tag) != "g" or scene.attrib.get("id") != "scene":
        raise PlanError('The visible top-level element must be <g id="scene">')

    ET.register_namespace("", SVG_NS)
    return ET.tostring(root, encoding="unicode")
