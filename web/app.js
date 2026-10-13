// SAMv1 specification §1.4. All processing is local to the browser.
export const FLAGS = [
  [1, 'Multiple segments', 'Template has multiple segments'],
  [2, 'Properly aligned', 'Each segment properly aligned according to the aligner'],
  [4, 'Segment unmapped', 'This segment is unmapped'],
  [8, 'Next segment unmapped', 'Next segment in the template is unmapped'],
  [16, 'Reverse complemented', 'SEQ is reverse complemented'],
  [32, 'Next segment reverse complemented', 'SEQ of the next segment is reverse complemented'],
  [64, 'First segment', 'First segment in the template'],
  [128, 'Last segment', 'Last segment in the template'],
  [256, 'Secondary alignment', 'Secondary alignment'],
  [512, 'Failed quality checks', 'Not passing platform/vendor quality checks'],
  [1024, 'Duplicate', 'PCR or optical duplicate'],
  [2048, 'Supplementary alignment', 'Supplementary alignment'],
];
const KNOWN_MASK = FLAGS.reduce((sum, [bit]) => sum | bit, 0);

export function parseFlag(input) {
  const raw = String(input).trim();
  if (!/^(?:[0-9]+|0[xX][0-9a-fA-F]+)$/.test(raw)) {
    throw new Error('FLAG must be an unsigned decimal integer or 0x-prefixed hex.');
  }
  const n = Number(raw);
  if (!Number.isSafeInteger(n) || n < 0 || n > 65535) {
    throw new Error('FLAG must be in the range 0–65535 (16 bits).');
  }
  return n;
}

export function decodeFlag(input) {
  const flag = parseFlag(input);
  const setBits = FLAGS.filter(([bit]) => (flag & bit) !== 0).map(([bit, name, description]) => ({
    bit, hex: '0x' + bit.toString(16).toUpperCase().padStart(3, '0'), name, description,
  }));
  const unknownBits = flag & ~KNOWN_MASK;
  const warnings = [];
  if (unknownBits) warnings.push('Reserved bit(s) 0x' + unknownBits.toString(16).toUpperCase() + ' set; ignore when interpreting current SAM flags.');
  if (!(flag & 1) && (flag & (2 | 8 | 32 | 64 | 128))) warnings.push('0x1 is unset: SAM does not define the interpretation of mate/template bits.');
  if ((flag & 4) && (flag & 2)) warnings.push('0x4 denotes an unmapped segment; do not infer mapped status from 0x2.');
  return {
    flag, hex: '0x' + flag.toString(16).toUpperCase().padStart(4, '0'),
    binary: flag.toString(2).padStart(16, '0'), setBits, unknownBits, warnings,
    summary: setBits.map(v => v.name).join(', ') || 'No SAM FLAG bits set',
  };
}

export function parseCsv(input) {
  const rows = [];
  let row = [], cell = '', quoted = false, afterQuote = false;
  const text = input.replace(/^\uFEFF/, '');
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"' && text[i + 1] === '"') { cell += '"'; i++; }
      else if (char === '"') { quoted = false; afterQuote = true; }
      else cell += char;
    } else if (char === ',' || char === '\n' || char === '\r') {
      row.push(cell); cell = ''; afterQuote = false;
      if (char !== ',') {
        if (row.some(value => value !== '')) rows.push(row);
        row = [];
        if (char === '\r' && text[i + 1] === '\n') i++;
      }
    } else if (char === '"' && !cell && !afterQuote) {
      quoted = true;
    } else if (afterQuote) {
      throw new Error('Unexpected character after CSV closing quote at position ' + (i + 1) + '.');
    } else {
      if (char === '"') throw new Error('Unexpected CSV quote at position ' + (i + 1) + '.');
      cell += char;
    }
  }
  if (quoted) throw new Error('Unterminated quoted CSV field.');
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows;
}

export function exportCsv(rows) {
  return rows.map(row => row.map(cell => {
    const text = String(cell ?? '');
    return /[",\r\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text;
  }).join(',')).join('\r\n') + '\r\n';
}

export function decodeCsv(input) {
  const table = parseCsv(input);
  if (!table.length || !table[0].length || table[0].some(h => !h.trim())) {
    throw new Error('CSV must begin with nonempty column headers, including FLAG.');
  }
  const headers = table[0];
  const lower = headers.map(h => h.trim().toLowerCase());
  const flagColumn = ['flag', 'sam_flag', 'query'].map(h => lower.indexOf(h)).find(i => i >= 0);
  if (flagColumn === undefined) throw new Error('CSV needs a FLAG, sam_flag, or query column.');
  if (table.length > 50001) throw new Error('CSV exceeds the 50,000-row safety limit.');
  const outputHeaders = [...headers];
  const generated = ['top_hit', 'lookup_score', 'flag_decimal', 'flag_hex', 'decoded_flags', 'warnings', 'error'];
  for (const col of generated) if (!outputHeaders.includes(col)) outputHeaders.push(col);
  const results = [];
  for (let i = 1; i < table.length; i++) {
    const row = table[i];
    const entry = Object.fromEntries(headers.map((h, j) => [h, row[j] ?? '']));
    let result, error = '';
    if (row.length !== headers.length) error = 'Row ' + (i + 1) + ' has ' + row.length + ' fields; expected ' + headers.length + '.';
    else { try { result = decodeFlag(row[flagColumn]); } catch (err) { error = err.message; } }
    const additional = {
      top_hit: result?.summary ?? 'Invalid SAM FLAG', lookup_score: result?.setBits.length ?? 0,
      flag_decimal: result?.flag ?? '', flag_hex: result?.hex ?? '',
      decoded_flags: result?.setBits.map(v => v.name).join('; ') ?? '',
      warnings: result?.warnings.join('; ') ?? '', error,
    };
    results.push({ ...entry, ...additional });
  }
  return { headers: outputHeaders, rows: results, invalid: results.filter(r => r.error).length };
}

function byId(id) { return document.getElementById(id); }
function renderSingle() {
  const output = byId('result');
  output.replaceChildren();
  let info;
  try { info = decodeFlag(byId('flag-input').value); }
  catch (err) { output.textContent = err.message; output.className = 'error'; return; }
  output.className = '';
  const meta = document.createElement('p');
  meta.className = 'meta';
  meta.textContent = 'Decimal ' + info.flag + ' • ' + info.hex + ' • binary ' + info.binary;
  output.append(meta);
  const title = document.createElement('p');
  title.className = 'summary'; title.textContent = info.summary;
  output.append(title);
  if (info.warnings.length) {
    const warnings = document.createElement('ul'); warnings.className = 'warning-list';
    for (const msg of info.warnings) {
      const li = document.createElement('li'); li.textContent = msg; warnings.append(li);
    }
    output.append(warnings);
  }
  const list = document.createElement('ul'); list.className = 'flag-list';
  for (const f of info.setBits) {
    const li = document.createElement('li');
    const code = document.createElement('code'); code.textContent = f.bit + ' (' + f.hex + ')';
    const label = document.createElement('span'); label.textContent = ' ' + f.description;
    li.append(code, label); list.append(li);
  }
  output.append(list);
}
let outputBatch;
function renderBatch() {
  const message = byId('batch-status');
  const preview = byId('batch-preview'); preview.replaceChildren();
  outputBatch = undefined;
  try {
    const decoded = decodeCsv(byId('csv-data').value);
    const columns = decoded.headers;
    outputBatch = [columns, ...decoded.rows.map(row => columns.map(c => row[c] ?? ''))];
    message.textContent = decoded.rows.length + ' rows processed, ' + decoded.invalid + ' invalid. Previewing up to 10.';
    for (const row of decoded.rows.slice(0, 10)) {
      const tr = document.createElement('tr');
      for (const col of ['flag_decimal', 'flag_hex', 'top_hit', 'error']) {
        const td = document.createElement('td'); td.textContent = String(row[col]); tr.append(td);
      }
      preview.append(tr);
    }
    byId('export-btn').disabled = false;
  } catch (err) {
    byId('export-btn').disabled = true;
    message.textContent = err.message;
  }
}
function downloadCsv() {
  if (!outputBatch) return;
  const blob = new Blob([exportCsv(outputBatch)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url; link.download = 'sam-flags-decoded.csv';
  document.body.append(link); link.click(); link.remove();
  URL.revokeObjectURL(url);
}
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    byId('decode-form').addEventListener('submit', event => { event.preventDefault(); renderSingle(); });
    for (const btn of document.querySelectorAll('[data-flag]')) {
      btn.addEventListener('click', () => { byId('flag-input').value = btn.dataset.flag; renderSingle(); });
    }
    byId('batch-btn').addEventListener('click', renderBatch);
    byId('export-btn').addEventListener('click', downloadCsv);
    byId('upload').addEventListener('change', async event => {
      const file = event.target.files?.[0];
      if (!file) return;
      if (file.size > 2 * 1024 * 1024) {
        byId('batch-status').textContent = 'File exceeds the 2 MiB upload limit.';
        return;
      }
      byId('csv-data').value = await file.text();
      byId('batch-status').textContent = 'Loaded ' + file.name + ' locally; select Decode CSV.';
    });
    renderSingle();
  });
}
