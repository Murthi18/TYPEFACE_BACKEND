import json

def _login(client):
    client.post("/api/auth/signup", json={
        "name":"Importer","email":"imp@test.com","password":"pw"
    })

def test_parse_endpoint_is_mockable(client, monkeypatch, tmp_path):
    """
    Demonstrates how we'd stub the OCR/PDF functions to isolate the route.
    """
    _login(client)

    # Stub parse to return two rows regardless of the uploaded file.
    def fake_parse(_):
        return [
            {"date":"2025-09-03","type":"expense","category":"Travel","description":"Taxi","amount":250},
            {"date":"2025-09-04","type":"income","category":"Refund","description":"Wallet refund","amount":300},
        ]

    import utils.ocr_receipt as ocr
    import utils.pdf_table as pdfp

    monkeypatch.setattr(ocr, "parse_receipt_image_or_pdf", fake_parse)
    monkeypatch.setattr(pdfp, "parse_tabular_pdf", lambda p: fake_parse(p))

    # Upload any file; the parser is stubbed
    sample = tmp_path / "dummy.pdf"
    sample.write_bytes(b"%PDF-1.4 FAKE")

    with open(sample, "rb") as f:
        r = client.post("/api/imports/parse", data={"files": f}, content_type="multipart/form-data")

