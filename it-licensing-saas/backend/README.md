# IT Licensing SaaS - Backend

A FastAPI backend for managing IT licenses, vendors, and AI-powered renewal recommendations based on vendors' fiscal and quarter ends.

## Quick Start

- Python 3.11+
- SQLite (bundled)

### Install

```
pip install -r backend/requirements.txt --user
```

### Run Dev Server

```
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open Swagger UI at `http://localhost:8000/docs`.

### API Key Auth

- Create an organization via `POST /orgs` to receive an `api_key`.
- Include `X-API-Key: <key>` header in requests to protected endpoints.

### Import Fiscal Year Ends

- Use `POST /vendors/import-fiscal-csv` with a CSV file containing columns: `vendor_name,fye_month,fye_day`.

### Recommendations

- Get upcoming talk windows: `GET /recommendations/upcoming?days=180`
- Engine aligns with vendor fiscal quarter and year ends to suggest optimal outreach windows.