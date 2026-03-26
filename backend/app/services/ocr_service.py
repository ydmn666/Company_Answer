from io import BytesIO

import fitz
from PIL import Image

from app.core.config import settings


# å¯¹æ«æç PDF å OCR æåï¼è¿åæé¡µæåçææ¬ã
def extract_text_with_ocr(content: bytes) -> list[tuple[int, str]]:
    if not settings.ocr_enabled:
        return []

    if settings.ocr_backend != "rapidocr":
        return []

    try:
        from rapidocr_onnxruntime import RapidOCR
    except Exception:
        return []

    ocr_engine = RapidOCR()
    pages: list[tuple[int, str]] = []
    with fitz.open(stream=content, filetype="pdf") as pdf:
        for index, page in enumerate(pdf, start=1):
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            image = Image.open(BytesIO(pix.tobytes("png")))
            result, _ = ocr_engine(image)
            text = "\n".join(item[1] for item in result or []).strip()
            if text:
                pages.append((index, text))
    return pages
