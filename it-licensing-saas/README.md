# IT Licensing SaaS

Backend service to help CIOs and IT Procurement manage software licenses and get AI recommendations for optimal vendor outreach around fiscal and quarter ends.

## Features

- Organization-scoped API key auth
- Vendors registry with fiscal year-end data (CSV importer)
- Licenses per organization
- Recommendation engine for outreach windows (quarter/FYE aware)
- Notifications API to persist suggestions
- Swagger UI

## Quickstart (Backend)

Requirements: Python 3.11+

```
pip install --user -r backend/requirements.txt
PYTHONPATH=backend python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: `http://localhost:8000/docs`

### Seed sample vendors

```
SEED_SAMPLE=1 PYTHONPATH=backend python -m uvicorn app.main:app --reload
```

### Typical flow (cURL)

```
# 1) Create org -> get API key
curl -s -X POST http://localhost:8000/orgs/ -H 'Content-Type: application/json' \
  -d '{"name":"Acme Corp","domain":"acme.com"}'

# Suppose the response api_key is ABC123...
API=ABC123

# 2) Import vendor fiscal data (CSV)
curl -s -X POST "http://localhost:8000/vendors/import-fiscal-csv" \
  -H "X-API-Key: $API" -F file=@backend/app/seeds/fiscal_year_sample.csv

# 3) Create a license
curl -s -X POST http://localhost:8000/licenses/ -H "X-API-Key: $API" -H 'Content-Type: application/json' \
  -d '{"vendor_id":1,"product_name":"Example Suite","annual_cost":120000,"currency":"USD"}'

# 4) Get recommendations
curl -s -X GET "http://localhost:8000/recommendations/upcoming?days=180" -H "X-API-Key: $API"

# 5) Generate notifications
curl -s -X POST "http://localhost:8000/recommendations/generate-notifications?days=90" -H "X-API-Key: $API"

# 6) List notifications
curl -s -X GET http://localhost:8000/notifications/ -H "X-API-Key: $API"
```

## Roadmap

- Background scheduler to auto-generate and dispatch notifications
- OAuth SSO and multi-user roles
- Frontend dashboard (React/Vite) for license and vendor insights
- Enrichment feed of vendor fiscal data