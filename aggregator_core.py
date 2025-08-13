import os
import json
import concurrent.futures
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

DEFAULT_TIMEOUT_SECONDS = 30


def read_env_if_present() -> None:
	if os.path.exists(".env"):
		load_dotenv(".env")


def http_get(url: str, *, headers: Optional[Dict[str, str]] = None, params: Optional[Dict[str, Any]] = None, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Tuple[Optional[Dict[str, Any]], Optional[str], int]:
	try:
		resp = requests.get(url, headers=headers, params=params, timeout=timeout)
		status = resp.status_code
		if resp.headers.get("content-type", "").lower().startswith("application/json"):
			try:
				data = resp.json()
			except Exception:
				data = None
		else:
			try:
				data = resp.json()
			except Exception:
				data = None
		if 200 <= status < 300:
			return data, None, status
		return data, f"HTTP {status}", status
	except requests.RequestException as exc:
		return None, str(exc), 0


# ------------------- Providers -------------------

def fetch_builtwith(domain: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
	key = os.getenv("BUILTWITH_API_KEY")
	if not key:
		return {"success": False, "error": "BUILTWITH_API_KEY not set"}
	base = os.getenv("BUILTWITH_API_BASE", "https://api.builtwith.com/v21/api.json")
	params = {"KEY": key, "LOOKUP": domain}
	data, err, status = http_get(base, params=params, timeout=timeout)
	return {"success": err is None, "status_code": status, "error": err, "data": data, "endpoint": base}


def fetch_mxtoolbox(domain: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
	key = os.getenv("MXTOOLBOX_API_KEY")
	if not key:
		return {"success": False, "error": "MXTOOLBOX_API_KEY not set"}
	base = os.getenv("MXTOOLBOX_BASE_URL", "https://api.mxtoolbox.com/api/v1")
	tools = os.getenv("MXTOOLBOX_TOOLS", "dns,spf,dmarc,mx,blacklist").split(",")
	tools = [t.strip() for t in tools if t.strip()]
	results: Dict[str, Any] = {"tools": {}, "endpoint_base": base}
	# Try multiple auth methods
	auth_scheme = os.getenv("MXTOOLBOX_AUTH_SCHEME", "Bearer")
	header_name = os.getenv("MXTOOLBOX_AUTH_HEADER", "Authorization")
	primary_headers = {header_name: f"{auth_scheme} {key}"}
	secondary_headers = {"X-API-Key": key}

	def _single_tool(tool: str) -> Tuple[str, Dict[str, Any]]:
		url = f"{base}/lookup/{tool}/{domain}"
		data, err, status = http_get(url, headers=primary_headers, timeout=timeout)
		if err and status in (401, 403):
			data, err, status = http_get(url, headers=secondary_headers, timeout=timeout)
		if err and status in (401, 403):
			data, err, status = http_get(url, params={"apikey": key}, timeout=timeout)
		return tool, {"success": err is None, "status_code": status, "error": err, "data": data, "endpoint": url}

	with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(tools) or 1)) as pool:
		for tool, payload in pool.map(_single_tool, tools):
			results["tools"][tool] = payload
	return {"success": True, "data": results}


def fetch_virustotal(domain: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
	key = os.getenv("VIRUSTOTAL_API_KEY")
	if not key:
		return {"success": False, "error": "VIRUSTOTAL_API_KEY not set"}
	base = os.getenv("VT_BASE_URL", "https://www.virustotal.com/api/v3")
	url = f"{base}/domains/{domain}"
	headers = {"x-apikey": key}
	data, err, status = http_get(url, headers=headers, timeout=timeout)
	return {"success": err is None, "status_code": status, "error": err, "data": data, "endpoint": url}


# ------------------- Security extraction -------------------

SECURITY_KEYWORDS = [
	"security",
	"waf",
	"firewall",
	"ddos",
	"captcha",
	"bot",
	"malware",
	"threat",
	"vulnerability",
	"scan",
	"antivirus",
	"tls",
	"ssl",
	"sso",
	"auth",
	"iam",
]

KNOWN_SECURITY_VENDORS = {
	"Cloudflare",
	"Imperva",
	"Akamai",
	"F5",
	"Fortinet",
	"Barracuda",
	"Reblaze",
	"Sucuri",
	"Wordfence",
	"PerimeterX",
	"Human Security",
	"Fastly",
	"AWS WAF",
	"Azure Front Door",
	"Google reCAPTCHA",
	"hCaptcha",
	"Cloudflare Bot Management",
	"Datadog Security",
}


def normalize_text(val: Optional[str]) -> str:
	return (val or "").strip()


def extract_builtwith_security(bw_data: Any) -> List[Dict[str, Any]]:
	vendors: List[Dict[str, Any]] = []
	if not isinstance(bw_data, dict):
		return vendors
	results = bw_data.get("Results") or bw_data.get("results") or []
	if not isinstance(results, list) or not results:
		return vendors
	res0 = results[0] if isinstance(results[0], dict) else {}
	res = res0.get("Result") or res0.get("result") or {}
	paths = res.get("Paths") or res.get("paths") or []
	for path in paths:
		techs = path.get("Technologies") or path.get("technologies") or []
		for tech in techs:
			name = normalize_text(tech.get("Name") or tech.get("name"))
			cat_list = tech.get("Categories") or tech.get("categories") or []
			categories = []
			for c in cat_list:
				label = normalize_text(c.get("Name") or c.get("name"))
				if label:
					categories.append(label)
			is_security = False
			if categories:
				for cat in categories:
					lc = cat.lower()
					if any(k in lc for k in SECURITY_KEYWORDS):
						is_security = True
						break
			if not is_security and name:
				lcname = name.lower()
				if any(k in lcname for k in SECURITY_KEYWORDS):
					is_security = True
			if not is_security and name in KNOWN_SECURITY_VENDORS:
				is_security = True
			if is_security and name:
				vendors.append({"name": name, "categories": categories})
	return vendors


def extract_mxtoolbox_security(mxt_data: Any) -> Dict[str, Any]:
	out: Dict[str, Any] = {}
	if not isinstance(mxt_data, dict):
		return out
	tools = mxt_data.get("tools") or {}
	# DMARC
	dmarc = tools.get("dmarc", {})
	if isinstance(dmarc, dict):
		data = dmarc.get("data") or {}
		if isinstance(data, dict):
			out["dmarc_record"] = data.get("Information") or data.get("information")
	# SPF
	spf = tools.get("spf", {})
	if isinstance(spf, dict):
		data = spf.get("data") or {}
		if isinstance(data, dict):
			out["spf_record"] = data.get("Information") or data.get("information")
	# Blacklist
	black = tools.get("blacklist", {})
	if isinstance(black, dict):
		data = black.get("data") or {}
		if isinstance(data, dict):
			issues = []
			# MXToolbox blacklist API structures differ; try common fields
			for k in ("ErrorCode", "Failed" , "FailureCount", "Blacklists"):
				if k in data:
					issues.append((k, data.get(k)))
			out["blacklist_summary"] = issues
	return out


def extract_virustotal_security(vt_data: Any) -> Dict[str, Any]:
	out: Dict[str, Any] = {}
	if not isinstance(vt_data, dict):
		return out
	data = vt_data.get("data") or {}
	if not isinstance(data, dict):
		return out
	attributes = data.get("attributes") or {}
	if isinstance(attributes, dict):
		stats = attributes.get("last_analysis_stats")
		if isinstance(stats, dict):
			out["last_analysis_stats"] = stats
		rep = attributes.get("reputation")
		if isinstance(rep, int):
			out["reputation"] = rep
		cats = attributes.get("categories")
		if isinstance(cats, dict):
			out["categories"] = cats
	return out


def aggregate_domain(domain: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> Dict[str, Any]:
	providers = {
		"builtwith": lambda: fetch_builtwith(domain, timeout),
		"mxtoolbox": lambda: fetch_mxtoolbox(domain, timeout),
		"virustotal": lambda: fetch_virustotal(domain, timeout),
	}

	results: Dict[str, Any] = {"domain": domain, "providers": {}}
	with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
		future_to_name = {pool.submit(func): name for name, func in providers.items()}
		for future in concurrent.futures.as_completed(future_to_name):
			name = future_to_name[future]
			try:
				res = future.result()
			except Exception as exc:
				res = {"success": False, "error": str(exc)}
			results["providers"][name] = res

	# Security-focused projection
	bw_vendors: List[Dict[str, Any]] = extract_builtwith_security(results.get("providers", {}).get("builtwith", {}).get("data"))
	mxt_sec = extract_mxtoolbox_security(results.get("providers", {}).get("mxtoolbox", {}).get("data"))
	vt_sec = extract_virustotal_security(results.get("providers", {}).get("virustotal", {}).get("data"))

	results["security"] = {
		"vendors": bw_vendors,
		"mxtoolbox": mxt_sec,
		"virustotal": vt_sec,
	}
	return results


def aggregate_domains(domains: List[str], timeout: int = DEFAULT_TIMEOUT_SECONDS) -> List[Dict[str, Any]]:
	domains = [d.strip() for d in domains if d and d.strip()]
	items: List[Dict[str, Any]] = []
	with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(domains) or 1)) as pool:
		for res in pool.map(lambda d: aggregate_domain(d, timeout), domains):
			items.append(res)
	return items