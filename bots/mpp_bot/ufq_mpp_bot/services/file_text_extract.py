"""
services/file_text_extract.py
------------------------------
Extracts plain text from a mentor-uploaded weekly-plan file so it can be
fed to services/plan_parser.py. Supports .txt (utf-8) and .docx.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("ufq_mpp_bot")


def extract_text_from_bytes(data: bytes, file_name: str) -> str:
    name = (file_name or "").lower()
    if name.endswith(".docx"):
        return _extract_docx(data)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="ignore")


def _extract_docx(data: bytes) -> str:
    import io
    import zipfile
    from xml.etree import ElementTree

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            xml_bytes = z.read("word/document.xml")
    except Exception:
        logger.exception("Failed to open docx as zip")
        return ""

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    tree = ElementTree.fromstring(xml_bytes)
    paragraphs = []
    for p in tree.iter(f"{{{ns['w']}}}p"):
        texts = [node.text or "" for node in p.iter(f"{{{ns['w']}}}t")]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)
