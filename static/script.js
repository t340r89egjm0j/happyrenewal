const dropzone = document.getElementById('dropzone');
const textarea = document.getElementById('domains');
const statusEl = document.getElementById('status');
const aggregateBtn = document.getElementById('aggregateBtn');
const exportBtn = document.getElementById('exportBtn');
const resultsEl = document.getElementById('results');

function setStatus(msg) {
	statusEl.textContent = msg || '';
}

function parseDomains(text) {
	if (!text) return [];
	let t = text.replace(/,|\r/g, '\n');
	return [...new Set(t.split('\n').map(s => s.trim()).filter(Boolean))];
}

dropzone.addEventListener('dragover', (e) => {
	e.preventDefault();
	dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
	dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', async (e) => {
	e.preventDefault();
	dropzone.classList.remove('dragover');
	const file = e.dataTransfer.files[0];
	if (!file) return;
	const text = await file.text();
	const domains = parseDomains(text);
	const existing = parseDomains(textarea.value);
	const merged = [...new Set([...existing, ...domains])];
	textarea.value = merged.join('\n');
});

function renderResults(items) {
	resultsEl.innerHTML = '';
	for (const item of items) {
		const card = document.createElement('div');
		card.className = 'card';
		const vendors = (item.security?.vendors || []).map(v => `<span class="badge">${v.name}</span>`).join(' ');
		const vt = item.security?.virustotal || {};
		const stats = vt.last_analysis_stats || {};
		const bad = (stats.malicious || 0) + (stats.suspicious || 0);
		const vtClass = bad > 0 ? 'status-bad' : 'status-ok';
		const mxt = item.security?.mxtoolbox || {};
		const dmarcPolicy = (mxt.dmarc_record || '').toString();
		const spfInfo = (mxt.spf_record || '').toString();
		const bl = mxt.blacklist_summary || [];
		card.innerHTML = `
			<h3>${item.domain}</h3>
			<div><strong>Security Vendors (BuiltWith):</strong> ${vendors || '<em>None detected</em>'}</div>
			<div><strong>VirusTotal:</strong> <span class="${vtClass}">malicious=${stats.malicious||0}, suspicious=${stats.suspicious||0}, harmless=${stats.harmless||0}</span></div>
			<div><strong>DMARC:</strong> ${dmarcPolicy || '<em>n/a</em>'}</div>
			<div><strong>SPF:</strong> ${spfInfo || '<em>n/a</em>'}</div>
			<div><strong>Blacklist summary:</strong> ${bl.length? JSON.stringify(bl) : '<em>n/a</em>'}</div>
		`;
		resultsEl.appendChild(card);
	}
}

function toCSV(items) {
	const headers = ['domain','vendors','vt_malicious','vt_suspicious','vt_harmless','dmarc','spf','blacklist'];
	let rows = [headers.join(',')];
	for (const item of items) {
		const vendors = (item.security?.vendors || []).map(v=>v.name).join(';');
		const stats = item.security?.virustotal?.last_analysis_stats || {};
		const dmarc = (item.security?.mxtoolbox?.dmarc_record || '').toString().replace(/,/g,';');
		const spf = (item.security?.mxtoolbox?.spf_record || '').toString().replace(/,/g,';');
		const bl = JSON.stringify(item.security?.mxtoolbox?.blacklist_summary || []).replace(/,/g,';');
		const fields = [
			item.domain,
			`"${vendors}"`,
			stats.malicious||0,
			stats.suspicious||0,
			stats.harmless||0,
			`"${dmarc}"`,
			`"${spf}"`,
			`"${bl}"`,
		];
		rows.push(fields.join(','));
	}
	return rows.join('\n');
}

async function callAggregate(domains) {
	const resp = await fetch('/aggregate', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ domains })
	});
	if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
	return await resp.json();
}

aggregateBtn.addEventListener('click', async () => {
	const domains = parseDomains(textarea.value);
	if (!domains.length) { setStatus('Please add at least one domain.'); return; }
	setStatus(`Processing ${domains.length} domain(s)...`);
	aggregateBtn.disabled = true;
	exportBtn.disabled = true;
	try {
		const data = await callAggregate(domains);
		const items = data.results || [];
		renderResults(items);
		window.__lastResults = items;
		exportBtn.disabled = items.length === 0;
		setStatus(`Done. Processed ${items.length} domain(s).`);
	} catch (e) {
		console.error(e);
		setStatus(`Error: ${e.message}`);
	} finally {
		aggregateBtn.disabled = false;
	}
});

exportBtn.addEventListener('click', () => {
	const items = window.__lastResults || [];
	if (!items.length) return;
	const csv = toCSV(items);
	const blob = new Blob([csv], {type: 'text/csv'});
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = 'security_aggregator.csv';
	document.body.appendChild(a);
	a.click();
	URL.revokeObjectURL(url);
	a.remove();
});