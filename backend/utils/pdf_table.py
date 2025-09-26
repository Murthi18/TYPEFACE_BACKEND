import pdfplumber
from datetime import datetime

HEADER_MAP = {
    "date": ["date","txn date","transaction date","value date"],
    "description": ["description","narration","details","particulars"],
    "category": ["category","title"],
    "amount":["amount","txn amount","amt"],
    "type": ["type"]
}

def normalize_header(h):
    return (h or "").strip().lower().replace("\n"," ").replace("  "," ")

def parse_tabular_pdf(path):
    """
    Parses PDFs that contain tabular (bank-like) data.
    Returns list of dict rows with date, description, amount, type.
    """
    rows = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for tbl in tables or []:
                if not tbl or len(tbl) < 2: 
                    continue
                header = [normalize_header(c) for c in (tbl[0] or [])]
                idx = _map_header_indexes(header)
                # if we fail to map essential columns, skip
                if not (idx.get("date") and (idx.get("amount") or (idx.get("debit") or idx.get("credit")))):
                    continue
                for r in tbl[1:]:
                    if not any(r): 
                        continue
                    date = _parse_date(_get(r, idx["date"]))
                    desc = _get(r, idx.get("description"))
                    amt = None
                    if idx.get("amount") is not None:
                        amt = _to_float(_get(r, idx["amount"]))
                    else:
                        debit = _to_float(_get(r, idx.get("debit")))
                        credit = _to_float(_get(r, idx.get("credit")))
                        if credit: amt = abs(credit)
                        elif debit: amt = -abs(debit)
                    if amt is None:
                        continue
                    if idx.get("type") is not None:
                        ttype = _get(r, idx.get("type"))
                    if idx.get("category") is not None:
                        category = _get(r, idx.get("category"))

                    rows.append({
                        "date": date or "",
                        "description": (desc or "").strip(),
                        "amount": abs(amt),
                        "type": ttype,
                        "category": category, 
                    })
    return rows

def _map_header_indexes(header):
    idx = {}
    for want, aliases in HEADER_MAP.items():
        for i, h in enumerate(header):
            if any(a in h for a in aliases):
                idx[want] = i
                break
    return idx

def _get(row, i):
    if i is None: 
        return None
    if i < 0 or i >= len(row):
        return None
    return (row[i] or "").strip()

def _to_float(s):
    if not s: return None
    s = s.replace(",", "").replace("₹","").replace("INR","").strip()
    # handle Dr/Cr suffix
    if s.endswith("Cr"):
        try: return float(s[:-2].strip())
        except: return None
    if s.endswith("Dr"):
        try: return -float(s[:-2].strip())
        except: return None
    try:
        return float(s)
    except:
        return None

def _parse_date(s):
    if not s: return None
    s = s.replace(".", "-").replace("/", "-")
    for fmt in ("%d-%m-%Y","%Y-%m-%d","%d-%m-%y","%d-%b-%Y","%d %b %Y","%m-%d-%Y"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except: pass
    return None
