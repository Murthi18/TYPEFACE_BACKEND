from flask import Blueprint, request, jsonify, session
from datetime import datetime, date, timedelta
from pymongo import DESCENDING
from db import transactions

bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")

# ---------- helpers ----------
def _uid():
    uid = session.get("user_id")
    return str(uid) if uid else None

def _norm_date_str(x):
    # accept datetime/date/str and return 'YYYY-MM-DD' or None
    if isinstance(x, (datetime, date)):
        return x.isoformat()[:10]
    if isinstance(x, str):
        return x[:10] if len(x) >= 10 else None
    return None

def _pages(total, size):
    return (total + size - 1) // size if size > 0 else 1

def _build_filter(uid, start=None, end=None, cat=None, q=None):
    f = {"user_id": uid}
    if start:
        f["date"] = {"$gte": start}
    if end:
        f.setdefault("date", {}).update({"$lte": end})
    if cat:
        f["category"] = cat
    if q:
        f["description"] = {"$regex": q, "$options": "i"}
    return f

# ---------- API ----------
@bp.get("")
def list_transactions():
    uid = _uid()
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    # filters from querystring
    q       = (request.args.get("q") or "").strip()
    start   = _norm_date_str(request.args.get("start"))
    end     = _norm_date_str(request.args.get("end"))
    cat     = (request.args.get("category") or "").strip()
    page    = max(1, int(request.args.get("page", 1)))
    size    = max(1, min(200, int(request.args.get("page_size", 20))))

    # base filter for current list/summary
    cur_filter = _build_filter(uid, start, end, cat, q)

    # ---- paged items ----
    total = transactions.count_documents(cur_filter)
    cursor = (transactions.find(cur_filter)
              .sort("date", DESCENDING)
              .skip((page-1)*size)
              .limit(size))

    items = []
    for doc in cursor:
        items.append({
            "id": str(doc["_id"]),
            "date": _norm_date_str(doc.get("date")),
            "description": doc.get("description", ""),
            "type": doc.get("type", "expense"),
            "category": doc.get("category", ""),
            "amount": float(doc.get("amount", 0))
        })

    # ---- totals under current filters (all pages) ----
    pipeline_totals = [
        {"$match": cur_filter},
        {"$group": {"_id": "$type", "total": {"$sum": "$amount"}}}
    ]
    agg = {row["_id"]: float(row["total"]) for row in transactions.aggregate(pipeline_totals)}
    total_income = float(agg.get("income", 0.0))
    total_expense = float(agg.get("expense", 0.0))
    totals = {
        "income": total_income,
        "expense": total_expense,
        "net": total_income - total_expense
    }

    # ---- server-side series so charts match KPIs exactly ----
    # by month (YYYY-MM) within the current filter window
    by_month_pipeline = [
        {"$match": cur_filter},
        {"$addFields": {"month": {"$substr": ["$date", 0, 7]}}},
        {"$group": {
            "_id": "$month",
            "income":  {"$sum": {"$cond": [{"$eq": ["$type", "income"]}, "$amount", 0]}},
            "expense": {"$sum": {"$cond": [{"$eq": ["$type", "expense"]}, "$amount", 0]}},
        }},
        {"$sort": {"_id": 1}}
    ]
    by_month = []
    for r in transactions.aggregate(by_month_pipeline):
        by_month.append({
            "month": r["_id"],
            "income": float(r.get("income", 0)),
            "expense": float(r.get("expense", 0))
        })

    # expenses by category within the current filter window
    by_category_pipeline = [
        {"$match": {**cur_filter, "type": "expense"}},
        {"$group": {
            "_id": {"$ifNull": ["$category", "Uncategorized"]},
            "total": {"$sum": "$amount"}
        }},
        {"$sort": {"total": -1}}
    ]
    by_category = []
    for r in transactions.aggregate(by_category_pipeline):
        by_category.append({
            "category": r["_id"],
            "total": float(r.get("total", 0))
        })

    series = {"by_month": by_month, "by_category": by_category}

    # ---- MoM deltas (compare current vs previous month) ----
    # IMPORTANT: apply the SAME non-date filters (category + q) so MoM aligns with what user is viewing,
    # but we set our own date windows for the comparison.
    today = date.today()
    cur_start = today.replace(day=1)  # current month start
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)

    base_filter_mom = _build_filter(uid, None, None, cat, q)  # include cat + q, exclude start/end
    cur_month_filter = {**base_filter_mom,
                        "date": {"$gte": _norm_date_str(cur_start), "$lte": _norm_date_str(today)}}
    prev_month_filter = {**base_filter_mom,
                         "date": {"$gte": _norm_date_str(prev_start), "$lte": _norm_date_str(prev_end)}}

    def _sum_by_type(flt):
        p = [
            {"$match": flt},
            {"$group": {"_id": "$type", "total": {"$sum": "$amount"}}}
        ]
        d = {r["_id"]: float(r["total"]) for r in transactions.aggregate(p)}
        return d.get("income", 0.0), d.get("expense", 0.0)

    cur_inc, cur_exp = _sum_by_type(cur_month_filter)
    prev_inc, prev_exp = _sum_by_type(prev_month_filter)

    def _pct(cur, prev):
        if prev <= 0 and cur <= 0: return 0.0
        if prev == 0: return 100.0  # from 0 to positive — treat as +100%
        return ((cur - prev) / prev) * 100.0

    kpis = {
        "income": totals["income"],
        "expense": totals["expense"],
        "net": totals["net"],
        "mom_income_pct": _pct(cur_inc, prev_inc),
        "mom_expense_pct": _pct(cur_exp, prev_exp),
        "cur_month_income": cur_inc,
        "cur_month_expense": cur_exp,
        "prev_month_income": prev_inc,
        "prev_month_expense": prev_exp,
    }

    return jsonify({
        "items": items,
        "total": total,
        "pages": _pages(total, size),
        "totals": totals,
        "kpis": kpis,
        "series": series
    })


@bp.post("")
def create_transaction():
    uid = _uid()
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    try:
        doc = {
            "user_id": uid,  # keep as string id
            "date": _norm_date_str(data.get("date")),
            "type": "income" if (data.get("type") == "income") else "expense",
            "category": (data.get("category") or "").strip() or "Uncategorized",
            "description": (data.get("description") or "").strip(),
            "amount": float(data.get("amount") or 0.0),
            "created_at": datetime.utcnow(),
        }
        res = transactions.insert_one(doc)
        return jsonify({"id": str(res.inserted_id)}), 201
    except Exception as e:
        return jsonify({"error": "Insert failed", "detail": str(e)}), 400
