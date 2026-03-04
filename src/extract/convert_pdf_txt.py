import os
import re
import fitz  # pymupdf
import pytesseract
import cv2
import numpy as np

PDF_PATH = "../../data/raw/100.signed_02.pdf"
OUT_TXT = "ND100_02.txt"

# Nếu Windows và pytesseract không tìm thấy tesseract.exe thì bật dòng này và sửa path:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def preprocess(img_bgr: np.ndarray) -> np.ndarray:
    """Tiền xử lý để OCR rõ hơn: gray -> denoise -> threshold"""
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    return thr

def clean_text(t: str) -> str:
    t = t.replace("\x0c", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()

def ocr_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    results = []
    print("Total pages:", doc.page_count)

    for i in range(doc.page_count):
        page = doc.load_page(i)

        # Render page -> image (tăng dpi bằng zoom)
        zoom = 3.0  # ~ 216 dpi * 3 = ~ 300-350 dpi tuỳ base
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        else:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        proc = preprocess(img)

        # OCR: vie+eng để bắt số/điều khoản tốt hơn
        txt = pytesseract.image_to_string(proc, lang="vie+eng", config="--psm 6")

        txt = clean_text(txt)
        results.append(f"\n\n=== PAGE {i+1} ===\n{txt}")

        if (i + 1) % 5 == 0:
            print(f"OCR done page {i+1}/{doc.page_count}")

    return "\n".join(results)

if __name__ == "__main__":
    text = ocr_pdf(PDF_PATH)
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(text)
    print("Saved:", OUT_TXT, "| total chars:", len(text))