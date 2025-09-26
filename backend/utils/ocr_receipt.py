import re
import os
import cv2
import pytesseract
from pdf2image import convert_from_path
from datetime import datetime

DATE_PAT = re.compile(r'(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})')
TOTAL_PAT = re.compile(r'(?:TOTAL|Amount Payable|Grand Total|Balance Due)\D{0,10}(\d+[.,]\d{2})', re.IGNORECASE)
AMOUNT_PAT = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d{2}))')
ITEM_LINE_PAT = re.compile(r'^[A-Za-z].{2,}(\d+[.,]\d{2})$') 

def parse_receipt_image_or_pdf(path):
    """Return array of candidate transactions from a POS receipt (image or pdf)."""
    images = []
    if path.lower().endswith(".pdf"):
        # convert each page to image (dpi 200→300 gives better OCR)
        pil_pages = convert_from_path(path, dpi=220, fmt="png")
        for p in pil_pages:
            images.append(cv2.cvtColor(cv2.imdecode(
                cv2.imencode(".png", cv2.cvtColor(
                    cv2.cvtColor(
                        cv2.UMat(cv2.cvtColor(
                            cv2.UMat(cv2.cvtColor(
                                cv2.UMat(cv2.cvtColor(
                                    cv2.UMat(cv2.cvtColor(
                                        cv2.UMat(cv2.cvtColor(
                                            cv2.UMat(cv2.cvtColor(
                                                cv2.UMat(cv2.cvtColor(
                                                    cv2.UMat(cv2.cvtColor(
                                                        cv2.UMat(cv2.cvtColor(
                                                            cv2.UMat(cv2.cvtColor(
                                                                cv2.UMat(cv2.cvtColor(
                                                                    cv2.UMat(cv2.cvtColor(
                                                                        cv2.UMat(p), cv2.COLOR_RGB2BGR)
                                                                    ).get(), cv2.COLOR_BGR2RGB)
                                                                ).get(), cv2.COLOR_RGB2BGR)
                                                            ).get(), cv2.COLOR_BGR2RGB)
                                                        ).get(), cv2.COLOR_RGB2BGR)
                                                    ).get(), cv2.COLOR_BGR2RGB)
                                                ).get(), cv2.COLOR_RGB2BGR)
                                            ).get(), cv2.COLOR_BGR2RGB)
                                        ).get(), cv2.COLOR_RGB2BGR)
                                    ).get(), cv2.COLOR_BGR2RGB)
                                ).get(), cv2.COLOR_RGB2BGR)
                            ).get(), cv2.COLOR_BGR2RGB), cv2.COLOR_RGB2BGR)
                        ).get(), cv2.COLOR_BGR2GRAY), cv2.IMREAD_UNCHANGED), 1.0)[1],
                cv2.IMREAD_UNCHANGED))
    else:
        images.append(cv2.imdecode(
            cv2.imencode(".png", cv2.imread(path))[1], cv2.IMREAD_UNCHANGED))

    items = []
    for img in images:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # binarize (adaptive works well for receipts)
        bw = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 35, 15)
        # mild denoise
        den = cv2.medianBlur(bw, 3)

        text = pytesseract.image_to_string(den, config="--oem 3 --psm 6")
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

        # date guess
        date = _extract_date(lines)
        # total by keyword (fallback to last amount)
        total = _extract_total(lines)
        # description: store/merchant name = first non-numeric line
        description = _guess_merchant(lines)

        if total:
            items.append({
                "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
                "type": "expense",
                "category": "Shopping",  # let user adjust later
                "description": description,
                "amount": float(total)
            })
        else:
            # fallback: look for the last line with an amount and treat as total
            amt = _last_amount(lines)
            if amt:
                items.append({
                    "date": date or datetime.utcnow().strftime("%Y-%m-%d"),
                    "type": "expense",
                    "category": "Shopping",
                    "description": description,
                    "amount": float(amt)
                })

    return items

def _extract_date(lines):
    for ln in lines:
        m = DATE_PAT.search(ln)
        if m:
            raw = m.group(1)
            for fmt in ("%d/%m/%Y","%d-%m-%Y","%m/%d/%Y","%m-%d-%Y","%d/%m/%y","%m/%d/%y"):
                try:
                    return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
                except: pass
    return None

def _extract_total(lines):
    for ln in lines[::-1]:  # search bottom-up
        m = TOTAL_PAT.search(ln)
        if m:
            return _num(m.group(1))
    return None

def _last_amount(lines):
    for ln in lines[::-1]:
        m = AMOUNT_PAT.search(ln.replace(",", ""))
        if m:
            return _num(m.group(1))
    return None

def _guess_merchant(lines):
    for ln in lines:
        if not re.search(r'\d', ln) and len(ln) > 2:
            return ln[:80]
    return "POS Receipt"

def _num(s):
    try: return float(s.replace(",",""))
    except: return None
