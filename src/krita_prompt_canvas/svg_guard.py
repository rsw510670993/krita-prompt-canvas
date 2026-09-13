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
        raise PlanError("SVG 超过 1 MB 安全限制")
    if FORBIDDEN_TEXT.search(svg):
        raise PlanError("SVG 包含外部资源或不安全元素")
    try:
        root = ET.fromstring(svg)
    except ET.ParseError as exc:
        raise PlanError(f"SVG 不是有效的 XML：{exc}") from exc
    if _local_name(root.tag) != "svg":
        raise PlanError("根元素必须是 svg")
    if not root.tag.startswith(f"{{{SVG_NS}}}"):
        raise PlanError("根元素必须使用标准 SVG 命名空间")
    if root.attrib.get("width") != str(width) or root.attrib.get("height") != str(height):
        raise PlanError("SVG 尺寸与请求的画布尺寸不一致")
    if root.attrib.get("viewBox") != f"0 0 {width} {height}":
        raise PlanError("SVG viewBox 必须与请求的画布完全一致")

    visible_root_children = []
    for element in root.iter():
        name = _local_name(element.tag)
        if name not in ALLOWED_ELEMENTS:
            raise PlanError(f"不允许使用此 SVG 元素：{name}")
        for attribute, value in element.attrib.items():
            attr_name = _local_name(attribute).lower()
            if attr_name.startswith("on") or attr_name in {"href", "src"}:
                raise PlanError(f"不允许使用此 SVG 属性：{attr_name}")
            if EXTERNAL_URL.search(value):
                raise PlanError("SVG 属性中不允许使用外部 URL")
            if "url(" in value.lower() and not re.fullmatch(r"url\(#[A-Za-z_][\w.-]*\)", value):
                raise PlanError("仅允许 url(#gradient) 形式的本地 SVG 引用")
    for child in list(root):
        if _local_name(child.tag) != "defs":
            visible_root_children.append(child)
    if len(visible_root_children) != 1:
        raise PlanError("SVG 必须且只能包含一个可见的顶层场景分组")
    scene = visible_root_children[0]
    if _local_name(scene.tag) != "g" or scene.attrib.get("id") != "scene":
        raise PlanError('可见的顶层元素必须是 <g id="scene">')

    ET.register_namespace("", SVG_NS)
    return ET.tostring(root, encoding="unicode")
