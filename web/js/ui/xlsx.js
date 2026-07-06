// =========================================================================
// Minimal .xlsx writer — no dependencies, CSP-safe (script-src 'self').
// Builds a real Office Open XML workbook (a ZIP of XML parts, stored/
// uncompressed) so the export opens in Excel/Sheets with sortable, filterable
// columns (an <autoFilter> over the header), numeric fee cells and real date
// cells. CSV can't carry any of that — hence this.
//
//   downloadXLSX(rows, cols, filename, sheetName, titleLines)
//     cols = [{ key, header, type }]  type ∈ 'text' | 'number' | 'date'
//     a 'date' cell reads the raw ISO yyyy-mm-dd value and shows dd-mm-yyyy.
//     titleLines (optional) = string[] written above the table (line 0 bold).
// =========================================================================

// ---- CRC32 (needed for each ZIP entry) ----------------------------------
const _crcTable = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
    t[n] = c >>> 0;
  }
  return t;
})();
function _crc32(bytes) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) c = _crcTable[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}

// ---- helpers ------------------------------------------------------------
function _xmlEsc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
// 0 -> A, 25 -> Z, 26 -> AA …
function _colLetter(n) {
  let s = '';
  n += 1;
  while (n > 0) { const r = (n - 1) % 26; s = String.fromCharCode(65 + r) + s; n = Math.floor((n - 1) / 26); }
  return s;
}
// ISO yyyy-mm-dd -> Excel serial day (days since 1899-12-30), or null.
function _excelSerial(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso || ''));
  if (!m) return null;
  return Math.round((Date.UTC(+m[1], +m[2] - 1, +m[3]) - Date.UTC(1899, 11, 30)) / 86400000);
}

// ---- the worksheet ------------------------------------------------------
// An optional `titleLines` block (a caption + context) is written into column A
// above the table; line 0 is bold. The header + data + <autoFilter> then start
// one blank row below it, so the filter dropdowns still cover only the table.
function _sheetXml(rows, cols, titleLines) {
  const titles = titleLines || [];
  const lastCol = _colLetter(cols.length - 1);
  const headRow = titles.length ? titles.length + 2 : 1;   // blank spacer after titles
  const lastRow = headRow + rows.length;
  const parts = [
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
    '<sheetData>'];

  titles.forEach((t, i) => {
    const s = i === 0 ? ' s="2"' : '';   // 2 = bold title style
    parts.push(`<row r="${i + 1}"><c r="A${i + 1}"${s} t="inlineStr"><is>`
      + `<t xml:space="preserve">${_xmlEsc(t)}</t></is></c></row>`);
  });

  parts.push(`<row r="${headRow}">`);
  cols.forEach((c, ci) => parts.push(
    `<c r="${_colLetter(ci)}${headRow}" s="3" t="inlineStr"><is><t xml:space="preserve">${_xmlEsc(c.header)}</t></is></c>`));
  parts.push('</row>');

  rows.forEach((r, ri) => {
    const rn = headRow + 1 + ri;
    parts.push(`<row r="${rn}">`);
    cols.forEach((c, ci) => {
      const ref = _colLetter(ci) + rn;
      const v = r[c.key];
      if (c.type === 'number') {
        const n = Number(v);
        parts.push((v == null || v === '' || !Number.isFinite(n))
          ? `<c r="${ref}"/>` : `<c r="${ref}" t="n"><v>${n}</v></c>`);
      } else if (c.type === 'date') {
        const s = _excelSerial(v);
        parts.push(s == null ? `<c r="${ref}"/>` : `<c r="${ref}" s="1"><v>${s}</v></c>`);
      } else {
        parts.push((v == null || v === '') ? `<c r="${ref}"/>`
          : `<c r="${ref}" t="inlineStr"><is><t xml:space="preserve">${_xmlEsc(v)}</t></is></c>`);
      }
    });
    parts.push('</row>');
  });

  parts.push('</sheetData>');
  parts.push(`<autoFilter ref="A${headRow}:${lastCol}${lastRow}"/>`);   // sort/filter dropdowns
  parts.push('</worksheet>');
  return parts.join('');
}

const _STYLES = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
  + '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
  + '<numFmts count="1"><numFmt numFmtId="164" formatCode="dd-mm-yyyy"/></numFmts>'
  + '<fonts count="3">'
  + '<font><sz val="11"/><name val="Calibri"/></font>'                 // 0 normal
  + '<font><b/><sz val="11"/><name val="Calibri"/></font>'             // 1 bold (header)
  + '<font><b/><sz val="14"/><name val="Calibri"/></font>'             // 2 bold title
  + '</fonts>'
  + '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
  + '<borders count="1"><border/></borders>'
  + '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
  + '<cellXfs count="4">'
  + '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'                                      // 0 default
  + '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/>'             // 1 date
  + '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1"/>'                       // 2 title
  + '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'                       // 3 header
  + '</cellXfs>'
  + '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
  + '</styleSheet>';

function _workbookXml(sheetName) {
  return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    + '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    + 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    + `<sheets><sheet name="${_xmlEsc(sheetName)}" sheetId="1" r:id="rId1"/></sheets></workbook>`;
}

// ---- ZIP (stored / no compression — Excel accepts it) -------------------
function _zip(files) {
  const enc = new TextEncoder();
  const u16 = (n) => [n & 0xff, (n >>> 8) & 0xff];
  const u32 = (n) => [n & 0xff, (n >>> 8) & 0xff, (n >>> 16) & 0xff, (n >>> 24) & 0xff];
  const chunks = [], central = [];
  let offset = 0;
  files.forEach((f) => {
    const nameBytes = enc.encode(f.name);
    const data = f.data;
    const crc = _crc32(data);
    const local = [].concat(u32(0x04034b50), u16(20), u16(0), u16(0), u16(0), u16(0),
      u32(crc), u32(data.length), u32(data.length), u16(nameBytes.length), u16(0));
    chunks.push(Uint8Array.from(local), nameBytes, data);
    central.push({ crc, len: data.length, nameBytes, offset });
    offset += local.length + nameBytes.length + data.length;
  });
  const cdStart = offset;
  let cdSize = 0;
  central.forEach((c) => {
    const hdr = [].concat(u32(0x02014b50), u16(20), u16(20), u16(0), u16(0), u16(0), u16(0),
      u32(c.crc), u32(c.len), u32(c.len), u16(c.nameBytes.length),
      u16(0), u16(0), u16(0), u16(0), u32(0), u32(c.offset));
    chunks.push(Uint8Array.from(hdr), c.nameBytes);
    cdSize += hdr.length + c.nameBytes.length;
  });
  chunks.push(Uint8Array.from([].concat(u32(0x06054b50), u16(0), u16(0),
    u16(central.length), u16(central.length), u32(cdSize), u32(cdStart), u16(0))));
  let total = 0; chunks.forEach((c) => total += c.length);
  const out = new Uint8Array(total);
  let p = 0; chunks.forEach((c) => { out.set(c, p); p += c.length; });
  return out;
}

// ---- public: build + download ------------------------------------------
function downloadXLSX(rows, cols, filename, sheetName, titleLines) {
  const enc = new TextEncoder();
  // Sheet names: ≤31 chars, none of []:*?/\.
  const sheet = (String(sheetName || 'Sheet1').replace(/[\\/?*[\]:]/g, ' ').trim() || 'Sheet1').slice(0, 31);
  const T = (s) => enc.encode(s);
  const files = [
    { name: '[Content_Types].xml', data: T('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      + '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      + '<Default Extension="xml" ContentType="application/xml"/>'
      + '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
      + '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
      + '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
      + '</Types>') },
    { name: '_rels/.rels', data: T('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
      + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
      + '</Relationships>') },
    { name: 'xl/workbook.xml', data: T(_workbookXml(sheet)) },
    { name: 'xl/_rels/workbook.xml.rels', data: T('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
      + '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
      + '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
      + '</Relationships>') },
    { name: 'xl/styles.xml', data: T(_STYLES) },
    { name: 'xl/worksheets/sheet1.xml', data: T(_sheetXml(rows, cols, titleLines)) },
  ];
  const blob = new Blob([_zip(files)], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
  URL.revokeObjectURL(a.href);
}
