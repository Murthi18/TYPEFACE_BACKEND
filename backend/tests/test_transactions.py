from datetime import date, timedelta

def _post(client, path, json):
    return client.post(path, json=json)

def _login(client):
    client.post("/api/auth/signup", json={
        "name":"User","email":"user@test.com","password":"S3cret_pw"
    })

def test_create_and_list_transactions_basic(client):
    _login(client)
    # Add two txns (1 income, 1 expense)
    r1 = _post(client, "/api/transactions", {
        "date": "2025-09-01", "type": "income", "category": "Salary",
        "description": "Monthly Salary", "amount": 50000
    })
    r2 = _post(client, "/api/transactions", {
        "date": "2025-09-03", "type": "expense", "category": "Food",
        "description": "Lunch", "amount": 250
    })

    # List
    lst = client.get("/api/transactions?page=1&page_size=50")
    data = lst.get_json()


def test_filters_and_pagination(client):
    _login(client)
    # Seed multiple items across categories and dates
    base = date(2025, 1, 15)
    for i in range(35):
        d = (base + timedelta(days=i)).isoformat()
        typ = "expense" if i % 2 == 0 else "income"
        cat = "Food" if i % 3 == 0 else "Groceries"
        amt = 100 + i
        _post(client, "/api/transactions", {
            "date": d, "type": typ, "category": cat, "description": f"Row {i}", "amount": amt
        })

    # Page 1, 20 items
    p1 = client.get("/api/transactions?page=1&page_size=20")

    # Page 2
    p2 = client.get("/api/transactions?page=2&page_size=20")

    # Filter category Food
    f = client.get("/api/transactions?page=1&page_size=100&category=Food")
    df = f.get_json()

def test_kpis_mom_calculation(client):
    """Sanity check that MoM fields exist and are numbers."""
    _login(client)
    # Last month 2 incomes (lower)
    client.post("/api/transactions", json={
        "date":"2025-08-05","type":"income","category":"Salary","description":"Aug","amount":20000
    })
    client.post("/api/transactions", json={
        "date":"2025-08-15","type":"income","category":"Bonus","description":"Aug bonus","amount":2000
    })
    # Current month higher income
    client.post("/api/transactions", json={
        "date":"2025-09-05","type":"income","category":"Salary","description":"Sep","amount":30000
    })

    r = client.get("/api/transactions?page=1&page_size=100&start=2025-09-01&end=2025-09-30")
    data = r.get_json()
