# Security Aggregator

Aggregate domain intel from BuiltWith, MXToolbox, and VirusTotal with a CLI and a drag-and-drop web UI.

## Setup

```
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file:

```
python aggregator_cli.py env-example > .env
# edit .env to add your keys
```

## CLI

```
python aggregator_cli.py aggregate example.com -o result.json
```

## Web UI

```
uvicorn web_server:app --reload --port 8000
```

Open http://localhost:8000 and drag & drop a file with domains or paste domains.
