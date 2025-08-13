#!/usr/bin/env python3

import os
import json
import sys
import concurrent.futures
from typing import Any, Dict, Optional, Tuple

import requests
import typer
from dotenv import load_dotenv

app = typer.Typer(add_completion=False, help="Aggregate domain intel from BuiltWith, MXToolbox, and VirusTotal")

DEFAULT_TIMEOUT_SECONDS = 30


def _read_env() -> None:
	# Load .env if present
	if os.path.exists(".env"):
		load_dotenv(".env")


def _http_get(url: str, *, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
	try:
		resp = requests.get(url, headers=headers, params=params, timeout=timeout)
		status = resp.status_code
		if resp.headers.get("content-type", "").lower().startswith("application/json"):
			try:
				data = resp.json()
			except Exception:
				data = None
		else:
			# Try to parse JSON even when header is wrong
			try:
				data = resp.json()
			except Exception:
				data = None
		if 200 <= status < 300:
			return data, None, status
		return data, f"HTTP {status}", status
	except requests.RequestException as exc:
		return None, str(exc), 0


# ------------------- BuiltWith -------------------

def fetch_builtwith(domain: str, timeout: int) -> Dict[str, Any]:
	key = os.getenv("BUILTWITH_API_KEY")
	if not key:
		return {"success": False, "error": "BUILTWITH_API_KEY not set"}
	base = os.getenv("BUILTWITH_API_BASE", "https://api.builtwith.com/v21/api.json")
	params = {"KEY": key, "LOOKUP": domain}
	data, err, status = _http_get(base, params=params, timeout=timeout)
	return {
		"success": err is None,
		"status_code": status,
		"error": err,
		"data": data,
		"endpoint": base,
	}


# ------------------- MXToolbox -------------------

def fetch_mxtoolbox(domain: str, timeout: int) -> Dict[str, Any]:
	key = os.getenv("MXTOOLBOX_API_KEY")
	if not key:
		return {"success": False, "error": "MXTOOLBOX_API_KEY not set"}
	base = os.getenv("MXTOOLBOX_BASE_URL", "https://api.mxtoolbox.com/api/v1")
	tool = os.getenv("MXTOOLBOX_TOOL", "dns")
	# Endpoint pattern: /lookup/{tool}/{domain}
	url = f"{base}/lookup/{tool}/{domain}"
	# Auth strategy is not consistently documented publicly; support multiple options via env
	# 1) Authorization: Bearer <key>
	auth_scheme = os.getenv("MXTOOLBOX_AUTH_SCHEME", "Bearer")
	header_name = os.getenv("MXTOOLBOX_AUTH_HEADER", "Authorization")
	headers = {header_name: f"{auth_scheme} {key}"}
	data, err, status = _http_get(url, headers=headers, timeout=timeout)
	if err and status in (401, 403):
		# 2) Try X-API-Key: <key>
		headers2 = {"X-API-Key": key}
		data, err, status = _http_get(url, headers=headers2, timeout=timeout)
	if err and status in (401, 403):
		# 3) Try apikey query param
		data, err, status = _http_get(url, params={"apikey": key}, timeout=timeout)
	return {
		"success": err is None,
		"status_code": status,
		"error": err,
		"data": data,
		"endpoint": url,
	}


# ------------------- VirusTotal -------------------

def fetch_virustotal(domain: str, timeout: int) -> Dict[str, Any]:
	key = os.getenv("VIRUSTOTAL_API_KEY")
	if not key:
		return {"success": False, "error": "VIRUSTOTAL_API_KEY not set"}
	base = os.getenv("VT_BASE_URL", "https://www.virustotal.com/api/v3")
	url = f"{base}/domains/{domain}"
	headers = {"x-apikey": key}
	data, err, status = _http_get(url, headers=headers, timeout=timeout)
	return {
		"success": err is None,
		"status_code": status,
		"error": err,
		"data": data,
		"endpoint": url,
	}


def _summarize(result: Dict[str, Any]) -> Dict[str, Any]:
	summary: Dict[str, Any] = {}
	# BuiltWith: count technologies if present
	bw = result.get("providers", {}).get("builtwith", {}).get("data") or {}
	tech_count = None
	if isinstance(bw, dict):
		# BuiltWith returns {"Results": [{"Result": {"Paths": [..., {"Technologies": [{"Name": ...}] }]}}]} in some versions
		try:
			results = bw.get("Results") or bw.get("results") or []
			if results and isinstance(results, list):
				res0 = results[0]
				if isinstance(res0, dict):
					res = res0.get("Result") or res0.get("result") or {}
					paths = res.get("Paths") or res.get("paths") or []
					techs = []
					for path in paths:
						techs.extend(path.get("Technologies") or path.get("technologies") or [])
					tech_count = len(techs) if techs else None
		except Exception:
			tech_count = None
	if tech_count is not None:
		summary["builtwith_technology_count"] = tech_count
	# VirusTotal: try to pull harmless/malicious stats
	vt = result.get("providers", {}).get("virustotal", {}).get("data") or {}
	if isinstance(vt, dict):
		try:
			data = vt.get("data") or {}
			attributes = data.get("attributes") or {}
			last_analysis_stats = attributes.get("last_analysis_stats")
			if isinstance(last_analysis_stats, dict):
				summary["virustotal_last_analysis_stats"] = last_analysis_stats
		except Exception:
			pass
	return summary


@app.command()
def aggregate(
	domain: str = typer.Argument(..., help="Domain to query, e.g., example.com"),
	output: Optional[str] = typer.Option(None, "--output", "-o", help="Write JSON to file path instead of stdout"),
	timeout: int = typer.Option(DEFAULT_TIMEOUT_SECONDS, "--timeout", help="Per-request timeout (seconds)"),
	include_summary: bool = typer.Option(True, "--summary/--no-summary", help="Include a brief computed summary"),
	pretty: bool = typer.Option(True, "--pretty/--no-pretty", help="Pretty-print JSON output"),
) -> None:
	"""Aggregate results from BuiltWith, MXToolbox, and VirusTotal for a domain."""
	_read_env()

	providers = {
		"builtwith": fetch_builtwith,
		"mxtoolbox": fetch_mxtoolbox,
		"virustotal": fetch_virustotal,
	}

	results: Dict[str, Any] = {"domain": domain, "providers": {}}

	with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
		future_to_name = {executor.submit(func, domain, timeout): name for name, func in providers.items()}
		for future in concurrent.futures.as_completed(future_to_name):
			name = future_to_name[future]
			try:
				res = future.result()
			except Exception as exc:
				res = {"success": False, "error": str(exc)}
			results["providers"][name] = res

	if include_summary:
		results["summary"] = _summarize(results)

	json_kwargs: Dict[str, Any] = {"ensure_ascii": False}
	if pretty:
		json_kwargs.update({"indent": 2, "sort_keys": False})

	text = json.dumps(results, **json_kwargs)
	if output:
		with open(output, "w", encoding="utf-8") as f:
			f.write(text)
	else:
		print(text)


@app.command()
def env_example() -> None:
	"""Print an example .env for configuring API keys and options."""
	example = (
		"# Copy this to .env and fill in your keys\n"
		"BUILTWITH_API_KEY=your_builtwith_key\n"
		"# Optional: override API base for BuiltWith (e.g., free1)\n"
		"# BUILTWITH_API_BASE=https://api.builtwith.com/free1/api.json\n"
		"\n"
		"MXTOOLBOX_API_KEY=your_mxtoolbox_key\n"
		"# Optional overrides for MXToolbox\n"
		"# MXTOOLBOX_BASE_URL=https://api.mxtoolbox.com/api/v1\n"
		"# MXTOOLBOX_TOOL=dns\n"
		"# MXTOOLBOX_AUTH_HEADER=Authorization\n"
		"# MXTOOLBOX_AUTH_SCHEME=Bearer\n"
		"\n"
		"VIRUSTOTAL_API_KEY=your_virustotal_key\n"
		"# Optional: VT_BASE_URL=https://www.virustotal.com/api/v3\n"
	)
	print(example)


if __name__ == "__main__":
	try:
		app()
	except KeyboardInterrupt:
		sys.exit(130)