# 🖥️ Backend – TypeFace Personal Finance

Flask + MongoDB backend for **TypeFace Personal Finance**.  
Handles authentication, transactions, PDF/receipt parsing, and exposes REST APIs consumed by the frontend.

TODO: testing to be furnished and improved, is patchy for now

To run tests:
``` bash
cd backend
pytest
```

NOTE:
``` bash
And ensure you change the variable name email's value in tests/test_auth.py 
of the function test_signup_then_me_and_logout everytime you run the tests
```
---
## 📂 Project Structure

```bash
backend/
├── app.py # Flask entrypoint – creates the app, registers blueprints
├── config.py # Loads environment variables from .env
├── db.py # MongoDB client and collection indexes
├── requirements.txt # Python dependencies
├── .env.example # Example environment variables
├── .env # Local environment (not committed)
├── .gitignore # Git ignore rules
├── README.md # This file
│
├── routes/ # Flask Blueprints
│ ├── auth.py # Signup/Login/Logout, session management
│ ├── imports.py # OCR & PDF parsing for receipts/statements
│ └── transactions.py# CRUD for financial transactions
│── tests/ # Flask Blueprints
│ ├── test_auth.py # test for authentication and user related functionality
│ ├── test_imports.py # test for OCR & PDF parsing for receipts/statements
│ └── tests_transactions.py # test for CRUD for financial transactions
├── utils/ # Helper modules
│ ├── ocr_receipt.py # OCR-based receipt parser
│ └── parse_pdf.py # Tabular PDF parser
│
└── uploads/ # Temporary file uploads
```

## ⚙️ Setup

### 1. Clone repo
```bash
git clone <repo-url>
cd backend
```

### 2. Create virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate   # Mac/Linux
.venv\Scripts\activate      # Windows PowerShell
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
brew install poppler tesseract #macos
sudo apt-get install poppler-utils tesseract-ocr #ubunt/ debian
```

### 4. Configure environment
```bash
Copy .env.example → .env and fill in
```

### 5. Run server
```bash
python app.py
```

## API Endpoints
```bash
Auth :
POST /api/auth/signup → Register
POST /api/auth/login → Login
POST /api/auth/logout → Logout
GET /api/auth/me → Current session user

Transactions :
GET /api/transactions → List transactions (with filters, pagination)
POST /api/transactions → Create new transaction
PUT /api/transactions/<id> → Update transaction
DELETE /api/transactions/<id> → Delete transaction

Imports :
POST /api/imports/parse → Upload PDF/receipt, parse transactions
POST /api/imports/commit → Commit parsed transactions to DB
```