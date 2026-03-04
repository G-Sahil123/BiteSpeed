# Bitespeed Identity Reconciliation Service

FastAPI + PostgreSQL service that links customer identities across multiple purchases.

## Setup

```bash
# 1. Clone / copy files, then create a virtual environment
python -m venv .venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure database
cp .env.example .env
# Edit .env and set your DATABASE_URL

# 4. Create the database manually 
CREATE DATABASE bitespeed

# 5. Create the engine
python database.py

# 6. Run the server (tables are auto-created on startup)
uvicorn main:app --reload --port 8000
```

## API

### POST /identify

**Request:**
```json
{
  "email": "mcfly@hillvalley.edu",
  "phoneNumber": "123456"
}
```

**Response:**
```json
{
  "contact": {
    "primaryContatctId": 1,
    "emails": ["lorraine@hillvalley.edu", "mcfly@hillvalley.edu"],
    "phoneNumbers": ["123456"],
    "secondaryContactIds": [23]
  }
}
```

## Logic Summary

| Scenario | Behaviour |
|---|---|
| No existing contact matches | Create new **primary** contact |
| Match found, no new info | Return consolidated response, no DB write |
| Match found, new email/phone | Create new **secondary** contact linked to primary |
| Two separate primaries linked by incoming request | Older one stays primary; newer is demoted to secondary |

