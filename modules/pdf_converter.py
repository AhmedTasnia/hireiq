import io
import re
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams


def pdf_to_text(pdf_bytes: bytes) -> str:
    """Convert PDF bytes to plain text string."""
    output = io.StringIO()
    with io.BytesIO(pdf_bytes) as pdf_file:
        extract_text_to_fp(pdf_file, output, laparams=LAParams(), output_type="text", codec="utf-8")
    raw = output.getvalue()
    return _clean_text(raw)


def _clean_text(text: str) -> str:
    """Remove excessive whitespace, page numbers, and artifact characters."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = line.strip()
        # skip blank lines, lone page numbers, and very short artifacts
        if not line:
            continue
        if re.match(r"^\d{1,3}$", line):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)
