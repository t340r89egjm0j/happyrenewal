import os
import io
from typing import Any, Dict, List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from aggregator_core import read_env_if_present, aggregate_domains, DEFAULT_TIMEOUT_SECONDS

app = FastAPI(title="Security Aggregator", version="0.1.0")

read_env_if_present()

static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.isdir(static_dir):
	os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/health")
def health() -> Dict[str, Any]:
	return {"ok": True}


@app.post("/aggregate")
async def aggregate(payload: Dict[str, Any]) -> JSONResponse:
	domains = payload.get("domains")
	if not isinstance(domains, list) or not domains:
		raise HTTPException(status_code=400, detail="domains must be a non-empty list")
	timeout = int(payload.get("timeout", DEFAULT_TIMEOUT_SECONDS))
	results = aggregate_domains(domains, timeout)
	return JSONResponse(content={"results": results})


@app.post("/aggregate-file")
async def aggregate_file(file: UploadFile = File(...), timeout: int = DEFAULT_TIMEOUT_SECONDS) -> JSONResponse:
	try:
		data = await file.read()
		text = data.decode("utf-8", errors="ignore")
	finally:
		await file.close()
	# Accept CSV or newline-delimited
	separators = [",", "\n", "\r"]
	for sep in separators:
		text = text.replace(sep, "\n")
	domains = [line.strip() for line in io.StringIO(text) if line.strip()]
	if not domains:
		raise HTTPException(status_code=400, detail="No domains found in file")
	results = aggregate_domains(domains, timeout)
	return JSONResponse(content={"results": results})


@app.get("/")
async def index() -> HTMLResponse:
	index_path = os.path.join(static_dir, "index.html")
	if not os.path.exists(index_path):
		return HTMLResponse(content="<h1>Security Aggregator</h1>")
	with open(index_path, "r", encoding="utf-8") as f:
		return HTMLResponse(content=f.read())