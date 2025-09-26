import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify, session, current_app

from db import transactions
from bson.objectid import ObjectId

from utils.ocr_receipt import parse_receipt_image_or_pdf
from utils.pdf_table import parse_tabular_pdf

bp = Blueprint("imports", __name__, url_prefix="/api/imports")

def _user_id():
    uid = session.get("user_id")
    if not uid:
        return None
    return ObjectId(uid)

def _allowed(filename):
    ext = (filename.rsplit(".",1)[-1] or "").lower()
    return ext in (current_app.config.get("ALLOWED_EXTS") or set())

@bp.post("/parse")
def parse_upload():
    """Accept one or more files, auto-detect type, return candidate txns (not committed)."""
    uid = _user_id()
    if not uid:
        return jsonify({"error":"Unauthorized"}), 401

    if "files" not in request.files:
        return jsonify({"error":"No files field"}), 400

    files = request.files.getlist("files")
    if not files:
        return jsonify({"error":"No files uploaded"}), 400

    os.makedirs(current_app.config["UPLOAD_DIR"], exist_ok=True)

    all_candidates = []
    for f in files:
        if not f.filename or not _allowed(f.filename):
            continue

        # Save to temp path
        fname = f"{uuid.uuid4().hex}_{secure_filename(f.filename)}"
        fpath = os.path.join(current_app.config["UPLOAD_DIR"], fname)
        f.save(fpath)

        ext = fname.split(".")[-1].lower()
        try:
            if ext == "pdf":
                # Heuristic: try to parse as table first; if no rows, treat pages as images (OCR)
                rows = parse_tabular_pdf(fpath)
                if rows:
                    # normalize to unified schema
                    for r in rows:
                        all_candidates.append({
                            "date": r.get("date"),
                            "type": r.get("type"),
                            "category": r.get("category") or "",  # user can adjust
                            "description": r.get("description") or "",
                            "amount": float(r.get("amount") or 0),
                            "_source": {"file": f.filename, "mode": "pdf_table"}
                        })
                else:
                    ocr_items = parse_receipt_image_or_pdf(fpath)  # it can handle pdf->images
                    for it in ocr_items:
                        all_candidates.append({
                            "date": it.get("date"),
                            "type": it.get("type") or "expense",
                            "category": it.get("category") or "",
                            "description": it.get("description") or "",
                            "amount": float(it.get("amount") or 0),
                            "_source": {"file": f.filename, "mode": "ocr_pdf"}
                        })
            else:
                # image types → OCR
                ocr_items = parse_receipt_image_or_pdf(fpath)
                for it in ocr_items:
                    all_candidates.append({
                        "date": it.get("date"),
                        "type": it.get("type") or "expense",
                        "category": it.get("category") or "",
                        "description": it.get("description") or "",
                        "amount": float(it.get("amount") or 0),
                        "_source": {"file": f.filename, "mode": "ocr_image"}
                    })
        finally:
            # clean up temp file
            try: os.remove(fpath)
            except: pass

    # Basic sanitization: drop empties
    all_candidates = [c for c in all_candidates if c.get("amount")]
    return jsonify({"items": all_candidates})
