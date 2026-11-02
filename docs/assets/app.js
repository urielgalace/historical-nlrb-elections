/* Page logic. Hash routes (#overview, #data, #statistics, #methods, #versions, #contribute) show
   one page at a time. Text pages are Markdown files in content/: {{tokens}} are filled from the
   current release's statistics, and live components go where a line reads
   <div data-component="name"></div>. Everything else is built here from the JSON in data/site/. */
(function () {
  'use strict';

  const ROUTES = ['overview', 'data', 'statistics', 'methods', 'versions', 'contribute'];
  const TITLES = { overview: 'Overview', data: 'Data', statistics: 'Statistics', methods: 'Methods',
    versions: 'Versions', contribute: 'Contribute' };
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September',
    'October', 'November', 'December'];
  const FIRST_YEAR = 1936, LAST_YEAR = 1960;
  const fmt = d3.format(',');
  const page = document.getElementById('page');

  const S = {
    config: {}, agg: null, versions: null, codebook: null,
    browseState: { q: '', year: '', state: '', outcome: '', status: '', page: 0 },
    period: 'all', industryMode: 'divisions', selectedVersion: null, prefill: null,
  };
  let pending = [];
  let routeSeq = 0;
  let firstRoute = true;

  // ---------- small helpers ----------
  function h(tag, attrs, ...kids) {
    const e = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v == null || v === false) continue;
        if (k === 'class') e.className = v;
        else if (k.startsWith('on') && typeof v === 'function') e.addEventListener(k.slice(2), v);
        else e.setAttribute(k, v === true ? '' : String(v));
      }
    }
    for (const k of kids.flat(Infinity)) {
      if (k == null || k === false || k === '') continue;
      e.append(k instanceof Node ? k : String(k));
    }
    return e;
  }
  // replaceChildren() turns null into the text "null", so drop empty slots first.
  const fill = (el, ...kids) => el.replaceChildren(...kids.flat(Infinity).filter(k => k != null && k !== false && k !== ''));
  const later = fn => pending.push(fn);
  function flush() {
    const q = pending;
    pending = [];
    q.forEach(fn => { try { fn(); } catch (err) { console.error(err); } });
  }
  const share = (a, b) => (b ? `${(100 * a / b).toFixed(1)}%` : '0.0%');
  function longDate(iso) {
    const [y, m, d] = String(iso).split('-').map(Number);
    if (d) return `${MONTHS[m - 1]} ${d}, ${y}`;
    if (m) return `${MONTHS[m - 1]} ${y}`;
    return String(y);
  }
  const bytes = b => (b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1e3))} KB`);
  const vparts = v => String(v).split('.').map(Number);
  const vcmp = (a, b) => {
    const x = vparts(a), y = vparts(b);
    for (let i = 0; i < Math.max(x.length, y.length); i++) if ((x[i] || 0) !== (y[i] || 0)) return (x[i] || 0) - (y[i] || 0);
    return 0;
  };

  // no-cache: GitHub Pages lets browsers reuse files for 10 minutes; this asks the server first, so a reload shows the latest.
  async function getJSON(path) {
    const r = await fetch(path, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`${path} returned ${r.status}`);
    return r.json();
  }
  async function getText(path) {
    const r = await fetch(path, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`${path} returned ${r.status}`);
    return r.text();
  }
  function once(fn) {
    let p = null;
    return () => (p = p || fn().catch(err => { p = null; throw err; }));
  }
  const loadBrowse = once(() => getJSON('data/site/browse.json').then(prepBrowse));
  const loadTopo = once(() => getJSON('data/geo/counties-albers-10m.json'));

  const currentRelease = () => S.versions.releases.find(r => r.version === S.versions.current) || S.versions.releases[0];
  const stateNames = () => new Map(S.agg.states.all.map(s => [s.abbrev, s.state]));
  function pagesUrl() {
    const m = (S.config.repo_url || '').match(/github\.com\/([^/]+)\/([^/#?]+)/);
    return m ? `https://${m[1].toLowerCase()}.github.io/${m[2].replace(/\.git$/, '')}/` : '';
  }

  async function copyText(text, statusEl) {
    let ok = false;
    try {
      await navigator.clipboard.writeText(text);
      ok = true;
    } catch (err) {
      const ta = h('textarea', { style: 'position:fixed;top:0;left:0;opacity:0', 'aria-hidden': 'true' });
      ta.value = text;
      document.body.append(ta);
      ta.select();
      try { ok = document.execCommand('copy'); } catch (err2) { ok = false; }
      ta.remove();
    }
    if (statusEl) {
      statusEl.textContent = ok ? 'Copied.' : 'Could not copy. Select the text and copy it by hand.';
      clearTimeout(statusEl._t);
      statusEl._t = setTimeout(() => { statusEl.textContent = ''; }, 4000);
    }
    return ok;
  }

  // ---------- page pieces ----------
  const pageHead = (title, lede) => h('header', { class: 'page-head' }, h('h2', null, title), lede ? h('p', { class: 'lede' }, lede) : null);
  const sectionHead = (title, text, id) => h('div', { class: 'section-head' },
    h('h2', { class: 'section-title', id }, title), text ? h('p', null, text) : null);

  function downloadLink(file, text, cls) {
    if (S.config.preview) {
      return h('button', { class: cls || 'btn btn-small', type: 'button', disabled: true, title: 'Downloads are off in this preview' }, text);
    }
    return h('a', { class: cls || 'btn btn-small', href: file.path, download: file.path.split('/').pop() }, text);
  }

  // A chart card with a title, optional tools and legend, a chart, and a table view.
  function figure(o) {
    const chart = h('div', { class: 'chart' });
    const tableView = h('div', { class: 'table-view', hidden: true });
    const legend = o.legend ? Charts.legend(o.legend) : null;
    const toggle = h('button', { class: 'toggle', type: 'button', 'aria-pressed': 'false' }, 'Table');
    toggle.addEventListener('click', () => {
      const on = toggle.getAttribute('aria-pressed') !== 'true';
      toggle.setAttribute('aria-pressed', String(on));
      chart.hidden = on;
      if (legend) legend.hidden = on;
      tableView.hidden = !on;
      if (on) tableView.replaceChildren(o.table());
      Charts.hideTip();
    });
    const fig = h('figure', { class: 'figure' },
      h('div', { class: 'figure-head' },
        h('div', { class: 'titles' }, h('h3', null, o.title), o.sub ? h('p', { class: 'sub' }, o.sub) : null),
        h('div', { class: 'figure-tools' }, o.tools || [], o.table ? toggle : null)),
      legend, chart, tableView, o.caption ? h('figcaption', null, o.caption) : null);
    later(() => o.draw(chart));
    return fig;
  }

  function segmented(options, value, onChange, label) {
    const box = h('div', { class: 'seg', role: 'group', 'aria-label': label });
    options.forEach(([v, text]) => {
      const b = h('button', { type: 'button', 'aria-pressed': String(v === value) }, text);
      b.addEventListener('click', () => {
        box.querySelectorAll('button').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
        onChange(v);
      });
      box.append(b);
    });
    return box;
  }

  // ---------- Markdown pages ----------
  function tokenValue(key) {
    const s = S.agg.stats, rel = currentRelease();
    const fixed = {
      version: rel.version, release_date: longDate(rel.date), release_status: rel.status,
      n_columns: fmt(S.codebook.length), site_url: pagesUrl() || 'the project website',
    };
    if (key in fixed) return fixed[key];
    if (key.startsWith('gap_')) {
      const v = S.agg.gap_counts[key.slice(4)];
      return v == null ? null : fmt(v);
    }
    if (!(key in s)) return null;
    const v = s[key];
    if (key.startsWith('pct_')) return `${v}%`;
    if (key.endsWith('_year')) return String(v);
    return typeof v === 'number' ? fmt(v) : String(v);
  }
  const fillTokens = text => text.replace(/\{\{\s*([\w.]+)\s*\}\}/g, (m, key) => {
    const v = tokenValue(key);
    if (v == null) console.warn(`Unknown token ${m}`);
    return v == null ? m : v;
  });

  function polishProse(box) {
    box.querySelectorAll('table').forEach(t => {
      const wrap = h('div', { class: 'table-wrap' });
      t.replaceWith(wrap);
      wrap.append(t);
    });
    box.querySelectorAll('a[href^="http"]').forEach(a => { a.target = '_blank'; a.rel = 'noopener'; });
  }

  function renderMarkdown(md, components) {
    const parts = fillTokens(md).split(/^[ \t]*<div data-component="([\w-]+)"><\/div>[ \t]*$/m);
    const out = [];
    let headDone = false;
    parts.forEach((part, i) => {
      if (i % 2 === 1) {
        const make = components[part];
        out.push(make ? make() : h('p', { class: 'error' }, `Missing component: ${part}`));
        return;
      }
      if (!part.trim()) return;
      const box = h('div', { class: 'prose' });
      box.innerHTML = marked.parse(part);
      polishProse(box);
      if (!headDone) {
        const h1 = box.querySelector('h1');
        if (h1) {
          const head = pageHead(h1.textContent);
          const next = h1.nextElementSibling;
          h1.remove();
          if (next && next.tagName === 'P') {
            next.classList.add('lede');
            head.append(next);
          }
          out.push(head);
          headDone = true;
        }
      }
      if (box.childElementCount) out.push(box);
    });
    return h('div', { class: 'page' }, out);
  }

  // ---------- Overview ----------
  async function pageOverview() {
    const md = await getText('content/overview.md');
    return renderMarkdown(md, { kpis: kpiTiles, 'year-chart': yearFigure, start: startLinks, cite: citeBlock });
  }

  function kpiTiles() {
    const s = S.agg.stats;
    const tile = (label, value, sub, accent) => h('div', { class: 'kpi' + (accent ? ' accent' : '') },
      h('div', { class: 'label' }, label), h('div', { class: 'value num' }, value), h('div', { class: 'sub' }, sub));
    return h('div', { class: 'kpis' },
      tile('Election records', fmt(s.n_elections), `${s.n_years} years between ${s.first_year} and ${s.last_year}`),
      tile('With a county', `${s.pct_located}%`, `${fmt(s.n_located)} records in ${fmt(s.n_counties)} counties`),
      tile('With an industry code', `${s.pct_sic}%`, `${fmt(s.n_sic)} records, coded to the 1987 SIC`),
      tile('With a definite result', `${s.pct_definite}%`, `${fmt(s.n_definite)} records. Most results are still being collected.`, true));
  }

  function yearFigure() {
    const A = S.agg;
    return figure({
      title: 'Election records per year',
      sub: `${fmt(A.stats.n_elections)} records from ${A.years.length} years. Shaded years have not been collected yet.`,
      caption: 'These are the elections in the dataset, not every election the NLRB held. The source differs by year (see Methods), so part of the change from one year to the next reflects the source.',
      draw: el => Charts.yearColumns(el, {
        rows: A.by_year, from: FIRST_YEAR, to: LAST_YEAR, unit: 'records', label: 'Election records per year, 1936 to 1960',
        extra: r => [{ value: share(r.located, r.n), label: 'with a county' },
          { value: share(r.outcome_definite, r.n), label: 'with a definite result' }],
      }),
      table: () => Charts.table([
        { label: 'Year', key: 'year' }, { label: 'Records', key: 'n', num: true },
        { label: 'With a county', value: r => share(r.located, r.n), num: true },
        { label: 'With an industry code', value: r => share(r.sic, r.n), num: true },
        { label: 'With a definite result', value: r => share(r.outcome_definite, r.n), num: true },
      ], A.by_year),
    });
  }

  function startLinks() {
    const items = [
      ['#data', 'Download or search the data', 'The current release as a CSV file, with a codebook and a searchable table.'],
      ['#statistics', 'See the summary statistics', 'Elections by year, county, industry, state, union, and result.'],
      ['#methods', 'Read how the data was built', 'Sources, matching, coding rules, audits, and known limits.'],
      ['#versions', 'Check what changed', 'Every release is kept, with a dated list of what changed.'],
      ['#contribute', 'Help fill the gaps', 'Send a missing result, location, or correction, with a source.'],
    ];
    return h('nav', { class: 'start', 'aria-label': 'Start here' },
      items.map(([href, title, text]) => h('a', { href }, h('strong', null, title), h('span', null, text))));
  }

  function citation() {
    const rel = currentRelease();
    const url = pagesUrl() || '[website address]';
    return `Johnson, Matthew S., Uriel Galace, and contributors. ${rel.date.slice(0, 4)}. Historical NLRB Elections, 1936–1960. Version ${rel.version}. ${url}`;
  }
  function citeBlock() {
    const text = citation();
    const status = h('span', { class: 'status-line', role: 'status' });
    return h('div', { class: 'section' },
      h('div', { class: 'cite-box' }, text),
      h('div', { class: 'controls' },
        h('button', { class: 'btn btn-small', type: 'button', onclick: () => copyText(text, status) }, 'Copy citation'),
        status));
  }

  // ---------- Data ----------
  const FILE_NOTES = {
    data: 'One row per election record. Opens in Excel, Stata, R, or Python.',
    codebook: 'What each column means and how complete it is.',
  };
  const mainFiles = files => files.filter(f => f.kind === 'data' || f.kind === 'codebook');
  function fileList(files) {
    return h('div', { class: 'files' }, files.map(f => {
      const name = f.path.split('/').pop();
      return h('div', { class: 'file' },
        h('div', { class: 'name' }, f.label),
        h('div', { class: 'actions' }, downloadLink(f, 'Download', f.kind === 'data' ? 'btn btn-small btn-primary' : 'btn btn-small')),
        h('div', { class: 'meta' }, `${name} · ${bytes(f.bytes)}`),
        FILE_NOTES[f.kind] ? h('div', { class: 'desc' }, FILE_NOTES[f.kind]) : null);
    }));
  }

  async function pageData() {
    const rel = currentRelease();
    const s = S.agg.stats;
    return h('div', { class: 'page' },
      pageHead('Data', `Release ${rel.version} has ${fmt(s.n_elections)} election records and ${S.codebook.length} columns. Download the files, or search the records below.`),
      h('section', { class: 'section', 'aria-labelledby': 'files-title' },
        sectionHead(`Files for release ${rel.version}`, null, 'files-title'),
        S.config.preview ? h('p', { class: 'preview-note' }, 'This is a preview, so downloads are turned off. On the GitHub site each button downloads the file.') : null,
        fileList(mainFiles(rel.files))),
      browseSection(),
      codebookSection());
  }

  function prepBrowse(b) {
    const idx = Object.fromEntries(b.columns.map((c, i) => [c, i]));
    const prefixes = b.url_prefixes || {};
    const rows = b.rows.map(a => {
      const r = {};
      for (const c of b.columns) r[c] = a[idx[c]];
      const m = /^(\w+):(.*)$/.exec(r.url || '');
      if (m && prefixes[m[1]]) r.url = prefixes[m[1]] + m[2];
      r.search = [r.id, r.employer, r.county, r.state, r.union, r.case, r.citation, r.sic_title].join(' ').toLowerCase();
      return r;
    });
    return { rows, byId: new Map(rows.map(r => [r.id, r])), outcomes: b.outcomes, statuses: b.statuses };
  }

  function browseSection() {
    const body = h('div', { class: 'section' }, h('p', { class: 'loading' }, `Loading ${fmt(S.agg.stats.n_elections)} records…`));
    const sec = h('section', { class: 'section', id: 'browse', 'aria-labelledby': 'browse-title' },
      sectionHead('Search the records', 'Search by employer, union, county, case number, or citation, then narrow by year, state, outcome, or location. Select a row for its details and source.', 'browse-title'),
      body);
    loadBrowse().then(B => body.replaceWith(browseUI(B)))
      .catch(err => body.replaceChildren(h('p', { class: 'error' }, `The records could not be loaded (${err.message}).`)));
    return sec;
  }

  const OUTCOME_SHORT = ['Union certified', 'No union', 'Petition dismissed', 'Result not yet found', 'Not in decision'];
  const ROW_TYPE = { listing: 'Listing', ditto: '“Do.” row: same employer as the row above', further_hearing: 'Further hearing of the case above' };
  const TIER = { 1: '1: stated in the NLRB decision', 2: '2: documented by an independent source', 3: '3: inferred or uncertain' };

  function outcomePill(i) {
    if (i == null || i < 0) return '';
    return h('span', { class: 'pill' + (i <= 2 ? ' known' : '') }, OUTCOME_SHORT[i]);
  }

  function browseUI(B) {
    const st = S.browseState;
    const PAGE = 25;
    const names = stateNames();
    const divisions = new Map(S.agg.industry.all.divisions.map(d => [d.letter, d.title]));

    const control = (id, label, input) => h('div', { class: 'control' }, h('label', { for: id }, label), input);
    function select(id, options, value) {
      return h('select', { id }, options.map(([v, text]) => {
        const o = h('option', { value: v }, text);
        if (String(v) === String(value)) o.selected = true;
        return o;
      }));
    }
    const q = h('input', { type: 'search', id: 'f-q', placeholder: 'For example: Armour, Local 347, Cook', autocomplete: 'off', value: st.q });
    const year = select('f-year', [['', 'All years'], ...S.agg.years.map(y => [y, y])], st.year);
    const state = select('f-state', [['', 'All states'], ...[...names].sort((a, b) => a[1].localeCompare(b[1]))], st.state);
    const outcome = select('f-outcome', [['', 'Any outcome'], ...B.outcomes.map((o, i) => [i, o]), [-1, 'No outcome information']], st.outcome);
    const status = select('f-status', [['', 'Any'], ...B.statuses.map((o, i) => [i, o])], st.status);
    const clear = h('button', { class: 'link-btn', type: 'button' }, 'Clear');
    const count = h('p', { class: 'note', role: 'status' });
    const tbody = h('tbody');
    const prev = h('button', { class: 'btn btn-small', type: 'button' }, 'Previous');
    const next = h('button', { class: 'btn btn-small', type: 'button' }, 'Next');
    const pos = h('span', { class: 'num' });
    let filtered = B.rows;

    function apply(resetPage) {
      if (resetPage) st.page = 0;
      const terms = st.q.trim().toLowerCase().split(/\s+/).filter(Boolean);
      filtered = B.rows.filter(r =>
        (!st.year || r.year === +st.year) && (!st.state || r.state === st.state)
        && (st.outcome === '' || r.outcome === +st.outcome) && (st.status === '' || r.status === +st.status)
        && terms.every(t => r.search.includes(t)));
      st.page = Math.min(st.page, Math.max(0, Math.ceil(filtered.length / PAGE) - 1));
      draw();
    }
    function draw() {
      const start = st.page * PAGE;
      const rows = filtered.slice(start, start + PAGE);
      tbody.replaceChildren(...rows.map(rowEl));
      if (!rows.length) tbody.append(h('tr', null, h('td', { colspan: 6, class: 'muted' }, 'No records match. Try fewer words or clear the filters.')));
      count.textContent = filtered.length === B.rows.length
        ? `${fmt(B.rows.length)} records`
        : `${fmt(filtered.length)} of ${fmt(B.rows.length)} records match`;
      pos.textContent = filtered.length ? `${fmt(start + 1)}–${fmt(start + rows.length)} of ${fmt(filtered.length)}` : '';
      prev.disabled = st.page === 0;
      next.disabled = start + PAGE >= filtered.length;
    }
    function rowEl(r) {
      const tr = h('tr', { class: 'row', tabindex: '0', 'aria-expanded': 'false' },
        h('td', { class: 'id' }, r.id),
        h('td', null, r.employer, r.row_type === 'ditto' ? h('span', { class: 'pill' }, 'Do.') : null,
          r.row_type === 'further_hearing' ? h('span', { class: 'pill' }, 'Further hearing') : null),
        h('td', null, r.county ? `${r.county}, ${r.state}` : h('span', { class: 'muted' }, 'Not located yet')),
        h('td', { class: 'hide-sm' }, r.sic_title || ''),
        h('td', { class: 'hide-sm wrap' }, r.union || ''),
        h('td', null, outcomePill(r.outcome)));
      const toggle = () => {
        const open = tr.getAttribute('aria-expanded') === 'true';
        if (open) {
          if (tr.nextElementSibling && tr.nextElementSibling.classList.contains('detail')) tr.nextElementSibling.remove();
        } else {
          tr.after(detailRow(r));
        }
        tr.setAttribute('aria-expanded', String(!open));
      };
      tr.addEventListener('click', e => { if (!e.target.closest('a, button')) toggle(); });
      tr.addEventListener('keydown', e => {
        if (e.target === tr && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); toggle(); }
      });
      return tr;
    }
    function detailRow(r) {
      const tally = (r.votes_for || r.votes_against)
        ? `${r.votes_for || 'not stated'} for the union, ${r.votes_against || 'not stated'} against` : '';
      const items = [
        ['Election ID', r.id], ['Source list year', r.year], ['Row type', ROW_TYPE[r.row_type]],
        ['NLRB case number', r.case], ['Citation', r.citation], ['Decision date', r.decided],
        ['County', r.county ? `${r.county}, ${names.get(r.state) || r.state}` : B.statuses[r.status]],
        ['County FIPS', r.fips], ['Location evidence tier', TIER[r.tier]],
        ['Industry (1987 SIC)', r.sic ? `${r.sic} ${r.sic_title}` : ''], ['SIC division', divisions.get(r.division)],
        ['Union', r.union], ['Affiliation', r.affiliation], ['Election type', r.election_type],
        ['Bargaining unit', r.unit ? `About ${fmt(+r.unit)} employees` : ''],
        ['Outcome', r.outcome >= 0 ? B.outcomes[r.outcome] : 'No outcome information'], ['Vote tally', tally],
      ].filter(([, v]) => v !== '' && v != null);
      const isNlrb = /nlrb\.gov/.test(r.url || '');
      return h('tr', { class: 'detail' }, h('td', { colspan: 6 },
        h('dl', { class: 'detail-grid' }, items.map(([k, v]) => h('div', null, h('dt', null, k), h('dd', null, String(v))))),
        h('div', { class: 'detail-actions' },
          r.url ? h('a', { class: 'btn btn-small', href: r.url, target: '_blank', rel: 'noopener' }, isNlrb ? 'Open the NLRB decision' : 'Open the source') : null,
          h('button', { class: 'btn btn-small', type: 'button', onclick: () => { S.prefill = { election_id: r.id }; location.hash = '#contribute'; } }, 'Suggest a correction')),
        h('p', { class: 'note', style: 'margin-top:10px' }, 'The download has every column for this record, including the quoted passages behind each value.')));
    }

    let timer = 0;
    q.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(() => { st.q = q.value; apply(true); }, 160); });
    year.addEventListener('change', () => { st.year = year.value; apply(true); });
    state.addEventListener('change', () => { st.state = state.value; apply(true); });
    outcome.addEventListener('change', () => { st.outcome = outcome.value; apply(true); });
    status.addEventListener('change', () => { st.status = status.value; apply(true); });
    clear.addEventListener('click', () => {
      Object.assign(st, { q: '', year: '', state: '', outcome: '', status: '', page: 0 });
      q.value = ''; year.value = ''; state.value = ''; outcome.value = ''; status.value = '';
      apply(true);
    });
    prev.addEventListener('click', () => { st.page = Math.max(0, st.page - 1); draw(); });
    next.addEventListener('click', () => { st.page += 1; draw(); });

    const ui = h('div', { class: 'section' },
      h('div', { class: 'controls' },
        h('div', { class: 'control', style: 'flex:1 1 260px' }, h('label', { for: 'f-q' }, 'Search'), q),
        control('f-year', 'Year', year), control('f-state', 'State', state),
        control('f-outcome', 'Outcome', outcome), control('f-status', 'Location', status), clear),
      count,
      h('div', { class: 'table-wrap' }, h('table', { class: 'records' },
        h('thead', null, h('tr', null, h('th', null, 'ID'), h('th', null, 'Employer'), h('th', null, 'County'),
          h('th', { class: 'hide-sm' }, 'Industry'), h('th', { class: 'hide-sm' }, 'Union'), h('th', null, 'Outcome'))),
        tbody)),
      h('div', { class: 'pager' }, pos, h('div', { class: 'controls' }, prev, next)));
    apply(false);
    return ui;
  }

  function codebookSection() {
    return h('section', { class: 'section', id: 'codebook', 'aria-labelledby': 'codebook-title' },
      sectionHead('Codebook', `The ${S.codebook.length} columns of the dataset, in file order, with the share of records that have a value.`, 'codebook-title'),
      h('div', { class: 'table-wrap' }, h('table', null,
        h('thead', null, h('tr', null, h('th', null, 'Column'), h('th', null, 'What it holds'), h('th', null, 'Filled'))),
        h('tbody', null, S.codebook.map(c => h('tr', null,
          h('td', null, h('code', null, c.column)),
          h('td', null, c.description),
          h('td', null, h('div', { class: 'bar-cell' },
            h('div', { class: 'track' }, h('div', { class: 'fill', style: `width:${c.filled_pct}%` })),
            h('span', { class: 'num' }, `${c.filled_pct}%`)))))))));
  }

  // ---------- Statistics ----------
  const AFFILIATION_SERIES = [
    { key: 'AFL', label: 'AFL', color: 'var(--series-1)' },
    { key: 'CIO', label: 'CIO', color: 'var(--series-2)' },
    { key: 'AFL-CIO', label: 'AFL-CIO (after 1955)', color: 'var(--series-3)' },
    { key: 'Independent', label: 'Independent', color: 'var(--series-4)' },
    { key: 'Not identified', label: 'Not identified', color: 'var(--unknown-1)' },
  ];
  const OUTCOME_SERIES = [
    { key: 'Union certified', label: 'Union certified', color: 'var(--series-1)' },
    { key: 'No union', label: 'No union', color: 'var(--series-2)' },
    { key: 'Petition dismissed', label: 'Petition dismissed', color: 'var(--series-3)' },
    { key: 'Election directed, result not yet found', label: 'Election directed, result not yet found', color: 'var(--unknown-1)' },
    { key: 'missing', label: 'No result information', color: 'var(--unknown-2)' },
  ];
  const DIVISION_SHORT = {
    A: 'Agriculture, forestry, fishing', B: 'Mining', C: 'Construction', D: 'Manufacturing',
    E: 'Transportation and utilities', F: 'Wholesale trade', G: 'Retail trade',
    H: 'Finance, insurance, real estate', I: 'Services', J: 'Public administration',
  };

  async function pageStatistics() {
    const s = S.agg.stats;
    const periodBox = h('div', { class: 'section' }, periodFigures());
    const seg = segmented(S.agg.periods.map(p => [p.key, p.label]), S.period, key => {
      S.period = key;
      Charts.hideTip();
      fill(periodBox, periodFigures());
      flush();
    }, 'Years shown');
    return h('div', { class: 'page' },
      pageHead('Statistics', `Summary statistics for release ${currentRelease().version}. Hover over a chart for values, or switch any chart to a table.`),
      h('p', { class: 'callout' }, h('strong', null, 'Results are incomplete. '),
        `Only ${s.pct_definite}% of records have a definite result, and the known results lean toward union wins, because a certification is easier to find than a loss. Do not compute win rates from this release.`),
      yearFigure(),
      h('section', { class: 'section', 'aria-labelledby': 'where-title' },
        sectionHead('Where, and in what industries', 'Choose the years to show. The map and the industry and state charts follow this choice.', 'where-title'),
        h('div', { class: 'controls' }, seg),
        periodBox),
      h('section', { class: 'section', 'aria-labelledby': 'unions-title' },
        sectionHead('Unions and results', 'Shares and counts for each year in the dataset.', 'unions-title'),
        h('div', { class: 'grid-2' }, affiliationFigure(), outcomeFigure())),
      h('section', { class: 'section', 'aria-labelledby': 'size-title' },
        sectionHead('Units, employers, and counties', 'All years together.', 'size-title'),
        h('div', { class: 'grid-2' }, unitFigure(), employersFigure()),
        h('div', { class: 'grid-2' }, countiesFigure(), statesAllNote())),
      h('section', { class: 'section', 'aria-labelledby': 'complete-title' },
        sectionHead('How complete each field is', 'The share of each year’s records with a value. Gaps are listed on the Contribute page.', 'complete-title'),
        completenessFigure()));
  }

  function periodFigures() {
    return [mapFigure(S.period), h('div', { class: 'grid-2' }, industryFigure(S.period), statesFigure(S.period))];
  }

  function mapFigure(key) {
    const C = S.agg.counties[key];
    const names = S.agg.county_names;
    const entries = Object.entries(C.counts);
    const notDrawn = entries.filter(([f]) => f.startsWith('72')).reduce((a, [, n]) => a + n, 0);
    const rows = entries.map(([fips, n]) => ({ fips, name: names[fips] || fips, n }))
      .sort((a, b) => b.n - a.n || a.name.localeCompare(b.name));
    const when = key === 'all' ? 'all years' : C.label;
    return figure({
      title: `Elections by county, ${when}`,
      sub: `${fmt(C.mapped)} of ${fmt(C.total)} records are placed in ${fmt(entries.length)} counties. White counties have no elections in the data.`,
      caption: `Present-day county lines (U.S. Census, through us-atlas). Connecticut is shown by its eight historical counties.${notDrawn ? ` Puerto Rico (${notDrawn} ${notDrawn === 1 ? 'record' : 'records'}) is not drawn.` : ''}`,
      draw: el => {
        el.replaceChildren(h('p', { class: 'loading' }, 'Loading the county map…'));
        loadTopo().then(topo => {
          if (!el.isConnected) return;
          Charts.countyMap(el, { topo, counts: C.counts, names, label: `Map of elections by county, ${when}` });
        }).catch(err => el.replaceChildren(h('p', { class: 'error' }, `The map could not be loaded (${err.message}).`)));
      },
      table: () => Charts.table([{ label: 'County', key: 'name' }, { label: 'FIPS', key: 'fips' },
        { label: 'Elections', key: 'n', num: true }], rows),
    });
  }

  function industryFigure(key) {
    const I = S.agg.industry[key];
    const mode = S.industryMode;
    const divRows = I.divisions.map(d => ({ label: DIVISION_SHORT[d.letter] || d.title, title: `${d.letter} ${d.title}`, value: d.n }))
      .sort((a, b) => b.value - a.value);
    const groupRows = I.groups.map(g => ({ label: g.label, title: `${g.code} ${g.title}`, value: g.n }));
    const rows = mode === 'divisions' ? divRows : groupRows.slice(0, 15);
    const seg = segmented([['divisions', 'Divisions'], ['groups', 'Major groups']], mode, m => {
      S.industryMode = m;
      fig.replaceWith(industryFigure(key));
      flush();
    }, 'Industry level');
    const coded = `${fmt(I.classified)} of ${fmt(I.total)} records have an industry code.`;
    const fig = figure({
      title: 'Industry',
      sub: mode === 'divisions' ? `SIC divisions. ${coded}` : `The 15 largest of ${I.groups.length} SIC major groups. ${coded}`,
      tools: [seg],
      draw: el => Charts.hbars(el, { rows, total: I.classified, totalLabel: 'of records with a code', label: 'Elections by industry' }),
      table: () => Charts.table([
        { label: mode === 'divisions' ? 'Division' : 'Major group', key: 'title' },
        { label: 'Elections', key: 'value', num: true },
        { label: 'Share', value: r => share(r.value, I.classified), num: true },
      ], mode === 'divisions' ? divRows : groupRows),
      caption: 'Codes follow the 1987 Standard Industrial Classification. Shares are of records with a code.',
    });
    return fig;
  }

  function statesFigure(key) {
    const list = S.agg.states[key];
    const total = d3.sum(list, x => x.n);
    const rows = list.slice(0, 15).map(x => ({ label: x.state, value: x.n }));
    return figure({
      title: 'States',
      sub: `The 15 with the most elections, of ${list.length} states and territories in the data.`,
      draw: el => Charts.hbars(el, { rows, total, totalLabel: 'of located records', label: 'Elections by state' }),
      table: () => Charts.table([{ label: 'State', key: 'state' }, { label: 'Elections', key: 'n', num: true },
        { label: 'Share', value: x => share(x.n, total), num: true }], list),
    });
  }

  function affiliationFigure() {
    const rows = S.agg.affiliation_by_year;
    return figure({
      title: 'Union affiliation',
      sub: 'Share of each year’s records, by the affiliation of the petitioning union.',
      legend: AFFILIATION_SERIES,
      draw: el => Charts.stacked(el, { rows, series: AFFILIATION_SERIES, from: FIRST_YEAR, to: LAST_YEAR, mode: 'share', label: 'Union affiliation by year' }),
      table: () => Charts.table([{ label: 'Year', key: 'year' },
        ...AFFILIATION_SERIES.map(sr => ({ label: sr.label, key: sr.key, num: true }))], rows),
      caption: 'The AFL and the CIO merged in December 1955. Independent unions belonged to neither.',
    });
  }

  function outcomeFigure() {
    const rows = S.agg.outcome_by_year.map(r => ({ ...r, missing: (r['Not found in decision'] || 0) + (r['No outcome information'] || 0) }));
    return figure({
      title: 'What is known of the result',
      sub: 'Records per year, by outcome.',
      legend: OUTCOME_SERIES,
      draw: el => Charts.stacked(el, { rows, series: OUTCOME_SERIES, from: FIRST_YEAR, to: LAST_YEAR, mode: 'count', label: 'Outcome by year' }),
      table: () => Charts.table([{ label: 'Year', key: 'year' },
        ...S.agg.outcomes.map(o => ({ label: o, key: o, num: true }))], rows),
      caption: '“Election directed” means the Board ordered an election and the result is in a later document not found yet. These are not losses.',
    });
  }

  function unitFigure() {
    const s = S.agg.stats;
    const rows = S.agg.unit_bins.map(b => ({ label: `${b.label} employees`, value: b.n }));
    return figure({
      title: 'Size of the bargaining unit',
      sub: `${fmt(s.n_unit_size)} records (${s.pct_unit_size}%) state a unit size. The median is ${fmt(s.median_unit_size)} employees.`,
      draw: el => Charts.hbars(el, { rows, total: s.n_unit_size, totalLabel: 'of records with a size', label: 'Bargaining unit sizes' }),
      table: () => Charts.table([{ label: 'Unit size', key: 'label' }, { label: 'Elections', key: 'value', num: true },
        { label: 'Share', value: r => share(r.value, s.n_unit_size), num: true }], rows),
    });
  }

  function employersFigure() {
    const list = S.agg.top_employers;
    const rows = list.slice(0, 15).map(e => ({ label: e.name, value: e.n }));
    return figure({
      title: 'Employers with the most elections',
      sub: 'Names are grouped after dropping words like Inc. and Co., so plants of one company count together.',
      draw: el => Charts.hbars(el, { rows, label: 'Employers with the most elections' }),
      table: () => Charts.table([{ label: 'Employer', key: 'name' }, { label: 'Elections', key: 'n', num: true }], list),
    });
  }

  function countiesFigure() {
    const list = S.agg.top_counties;
    const rows = list.slice(0, 15).map(c => ({ label: c.name, value: c.n }));
    return figure({
      title: 'Counties with the most elections',
      sub: 'All years. Choose a period above to see any county on the map.',
      draw: el => Charts.hbars(el, { rows, total: S.agg.stats.n_fips, totalLabel: 'of located records', label: 'Counties with the most elections' }),
      table: () => Charts.table([{ label: 'County', key: 'name' }, { label: 'FIPS', key: 'fips' }, { label: 'Elections', key: 'n', num: true }], list),
    });
  }

  function statesAllNote() {
    const s = S.agg.stats;
    const tiers = [['1', 'Stated in the NLRB decision', s.n_tier1], ['2', 'Documented by another source', s.n_tier2], ['3', 'Inferred or uncertain', s.n_tier3]];
    return h('figure', { class: 'figure' },
      h('div', { class: 'figure-head' }, h('div', { class: 'titles' },
        h('h3', null, 'How locations are supported'),
        h('p', { class: 'sub' }, `Evidence tier of the ${fmt(s.n_located)} records with a county.`))),
      Charts.table([{ label: 'Tier', key: 0 }, { label: 'Evidence', key: 1 }, { label: 'Records', key: 2, num: true },
        { label: 'Share', value: r => share(r[2], s.n_located), num: true }], tiers),
      h('figcaption', null, `${fmt(s.n_no_county)} records have no county yet. Of these, ${fmt(s.n_loc_nodecision)} have no matching decision, ${fmt(s.n_loc_extract)} have a decision whose location has not been read yet, and ${fmt(s.n_loc_rejected)} had a decision match rejected on review.`));
  }

  function completenessFigure() {
    const A = S.agg;
    const cols = A.years;
    const rows = A.completeness.map(c => ({ label: c.label, all: c.all,
      values: Object.fromEntries(cols.map(y => [y, c.by_year[String(y)] || 0])) }));
    const steps = Charts.heatSteps;
    const legend = steps.map((v, i) => ({ label: i === 0 ? `Under ${v}%` : `${steps[i - 1]}–${v - 1}%`, color: `var(--heat-${i})` }))
      .concat([{ label: `${steps[steps.length - 1]}% or more`, color: `var(--heat-${steps.length})` }]);
    return figure({
      title: 'Share of records with each field, by year',
      sub: 'Each cell is the share of that year’s records with the field filled.',
      legend,
      draw: el => Charts.heatmap(el, { rows, cols, label: 'Completeness of each field by year' }),
      table: () => Charts.table([{ label: 'Field', key: 'label' },
        ...cols.map(y => ({ label: String(y), value: r => `${Math.round(r.values[y])}%`, num: true })),
        { label: 'All years', value: r => `${r.all}%`, num: true }], rows),
      caption: 'A definite result is Union certified, No union, or Petition dismissed. NLRB region is blank for case numbers without a regional prefix, which covers most cases before about 1943.',
    });
  }

  // ---------- Methods ----------
  async function pageMethods() {
    const md = await getText('content/methods.md');
    return renderMarkdown(md, {});
  }

  // ---------- Versions ----------
  async function pageVersions() {
    const V = S.versions;
    const items = [
      ...(V.planned || []).slice().sort((a, b) => vcmp(b.version, a.version)).map(p => ({
        group: 'Planned', key: `p${p.version}`, date: p.status, title: `Version ${p.version}`, sub: p.title, kind: 'planned', data: p })),
      ...V.releases.map(r => ({
        group: 'Releases', key: `r${r.version}`, date: longDate(r.date), title: `Version ${r.version}`, sub: r.status, kind: 'release', data: r })),
      ...(V.history || []).map((m, i) => ({
        group: 'Before the first release', key: `h${i}`, date: longDate(m.date), title: m.title, kind: 'history', data: m })),
    ];
    const sel = items.find(i => i.key === S.selectedVersion) || items.find(i => i.key === `r${V.current}`) || items[0];
    const detail = h('div', { class: 'version-detail', id: 'version-detail', tabindex: '-1' });
    const buttons = [];
    const groups = ['Planned', 'Releases', 'Before the first release'].map(g => {
      const its = items.filter(i => i.group === g);
      if (!its.length) return null;
      return h('div', null, h('h3', null, g), h('ol', null, its.map(it => {
        const b = h('button', { type: 'button', 'aria-current': String(it === sel), 'aria-controls': 'version-detail' },
          h('span', { class: 't-date' }, it.date), h('span', { class: 't-title' }, it.title),
          it.sub ? h('span', { class: 't-sub' }, it.sub) : null);
        b.addEventListener('click', () => {
          S.selectedVersion = it.key;
          buttons.forEach(x => x.setAttribute('aria-current', String(x === b)));
          fill(detail, versionDetail(it));
          flush();
          if (window.matchMedia('(max-width: 760px)').matches) detail.scrollIntoView({ block: 'start' });
        });
        buttons.push(b);
        return h('li', null, b);
      })));
    });
    fill(detail, versionDetail(sel));
    return h('div', { class: 'page' },
      pageHead('Version history', 'Each release is frozen: its files never change once published. Corrections go into the next release, which lists every value that changed, with the old value, the new value, and the source.'),
      h('div', { class: 'versions' }, h('nav', { class: 'timeline', 'aria-label': 'Versions' }, groups), detail),
      howVersionsWork());
  }

  function versionDetail(it) {
    if (it.kind === 'planned') {
      const p = it.data;
      return [
        h('div', { class: 'vhead' }, h('div', { class: 'docket' }, h('span', { class: 'stamp' }, p.status)),
          h('div', { class: 'vnum' }, `v${p.version}`), h('h3', { class: 'section-title' }, p.title), h('p', { class: 'lede' }, p.summary)),
        h('p', { class: 'note' }, 'Planned releases are listed so users know what is coming. Timing depends on the work described.'),
      ];
    }
    if (it.kind === 'history') {
      const m = it.data;
      return [
        h('div', { class: 'vhead' }, h('div', { class: 'docket' }, h('span', null, longDate(m.date))),
          h('h3', { class: 'section-title' }, m.title), h('p', { class: 'lede' }, m.summary)),
        h('p', { class: 'note' }, 'A step in building the dataset before the first public release. Files from these working steps are not published separately; their results are in release 1.0.'),
      ];
    }
    const r = it.data;
    const n = r.coverage.Elections;
    const prepared = /candidate|draft/i.test(r.status) ? 'Prepared' : 'Released';
    return [
      h('div', { class: 'vhead' },
        h('div', { class: 'docket' }, h('span', null, `${prepared} ${longDate(r.date)}`), h('span', { class: 'stamp' }, r.status)),
        h('div', { class: 'vnum' }, `v${r.version}`), h('h3', { class: 'section-title' }, r.title), h('p', { class: 'lede' }, r.summary)),
      h('div', { class: 'section' }, h('h3', null, 'Coverage'),
        Charts.table([{ label: 'Records', key: 0 }, { label: 'Count', key: 1, num: true },
          { label: 'Share', value: x => share(x[1], n), num: true }], Object.entries(r.coverage))),
      h('div', { class: 'section' }, h('h3', null, 'What changed'), changesView(r)),
      r.notes && r.notes.length ? h('div', { class: 'section' }, h('h3', null, 'Notes on this release'),
        h('ul', { class: 'notes-list' }, r.notes.map(x => h('li', null, x)))) : null,
      h('div', { class: 'section' }, h('h3', null, 'Files'), fileList([...mainFiles(r.files), ...r.files.filter(f => f.kind === 'changes')])),
    ].filter(Boolean);
  }

  function changesView(r) {
    const c = r.changes;
    if (!c) {
      return h('p', null, 'This is the first release, so there is nothing to compare it with. Each later release will list here every value that changed since the release before it: the record, the field, the old value, the new value, and the source, with the full list as a download.');
    }
    const byField = (c.by_field || []).map(f => ({ label: f.field, value: f.n }));
    const changeFile = (r.files || []).find(f => f.kind === 'changes');
    return h('div', { class: 'section' },
      h('p', null, `${fmt(c.n_values)} values changed in ${fmt(c.n_records)} records since version ${c.from}.`
        + (c.contributors && c.contributors.length ? ` Contributors: ${c.contributors.join(', ')}.` : '')),
      byField.length ? figure({ title: 'Changed values by field', draw: el => Charts.hbars(el, { rows: byField, unit: 'values', label: 'Changed values by field' }),
        table: () => Charts.table([{ label: 'Field', key: 'label' }, { label: 'Values changed', key: 'value', num: true }], byField) }) : null,
      c.sample && c.sample.length ? h('div', { class: 'table-wrap' }, h('table', { class: 'diff' },
        h('thead', null, h('tr', null, h('th', null, 'Record'), h('th', null, 'Field'), h('th', null, 'Before'), h('th', null, 'After'), h('th', null, 'Source'))),
        h('tbody', null, c.sample.map(x => h('tr', null, h('td', { class: 'id' }, x.election_id), h('td', null, h('code', null, x.field)),
          h('td', null, x.old ? h('del', null, x.old) : h('span', { class: 'muted' }, 'blank')), h('td', null, h('ins', null, x.new)), h('td', null, x.source)))))) : null,
      c.sample && changeFile && c.sample.length < c.n_values ? h('p', { class: 'note' }, `Showing ${fmt(c.sample.length)} of ${fmt(c.n_values)} changes. The full list is in the change file below.`) : null);
  }

  function howVersionsWork() {
    return h('section', { class: 'section', 'aria-labelledby': 'how-title' },
      sectionHead('How a correction becomes a release', null, 'how-title'),
      h('ol', { class: 'steps' },
        h('li', null, h('span', null, 'Someone suggests a fix with a source, through the Contribute page or GitHub.')),
        h('li', null, h('span', null, 'A project member checks the source and records the accepted change in the corrections folder, with the contributor’s name if they want credit.')),
        h('li', null, h('span', null, 'Accepted changes are applied together to make the next release, with a new number and date. Small fixes raise the number after the point (1.1); new sources that change many records raise the first number (2.0).')),
        h('li', null, h('span', null, 'The new release lists each change. Earlier releases stay available, so work that used them can still be checked.'))));
  }

  // ---------- Contribute ----------
  async function pageContribute() {
    const md = await getText('content/contribute.md');
    return renderMarkdown(md, { 'gap-tiles': gapTiles, 'correction-form': correctionForm });
  }

  function gapTiles() {
    const s = S.agg.stats, g = S.agg.gap_counts;
    const files = currentRelease().files;
    const file = name => files.find(f => f.path.endsWith(name));
    const tile = (value, label, sub, f) => h('div', { class: 'gap-tile' },
      h('div', { class: 'value num' }, fmt(value)), h('div', { class: 'label' }, label), h('div', { class: 'sub' }, sub),
      f ? h('div', null, downloadLink(f, 'Download the list')) : null);
    return h('div', { class: 'gap-tiles' },
      tile(g.result, 'elections with no result yet', 'The Board ordered an election, but the result is in a later document we have not found.', file('missing_result.csv')),
      tile(g.county, 'elections without a county', `Another ${fmt(s.n_other_no_county)} “Do.” and further-hearing rows have no county; ${fmt(s.n_other_parent_county)} of them refer to a row that has one.`, file('missing_county.csv')),
      tile(g.industry, 'elections without an industry code', 'Usually because no decision was matched, or the decision does not describe the business.', file('missing_industry.csv')),
      tile(s.n_tally_held_back, 'vote tallies held back', 'Counts that failed a consistency check, such as more votes than eligible voters.', file('review_held_back_tallies.csv')));
  }

  const FIELD_CHOICES = [
    ['county', 'County'], ['state', 'State'], ['outcome', 'Outcome'], ['votes_for', 'Votes for the union'],
    ['votes_against', 'Votes against'], ['eligible_voters', 'Eligible voters'], ['challenged_ballots', 'Challenged ballots'],
    ['union_name', 'Union name'], ['union_affiliation', 'Union affiliation'], ['election_type', 'Election type'],
    ['bargaining_unit_size', 'Bargaining unit size'], ['sic_code', 'Industry (SIC code)'],
    ['industry_description', 'Industry description'], ['employer', 'Employer name'], ['nlrb_case_number', 'NLRB case number'],
    ['nlrb_citation', 'NLRB citation'], ['nlrb_decision_date', 'Decision date'], ['plant_or_hq', 'Plant or headquarters'],
    ['additional_counties', 'Additional counties'], ['other', 'Something else (explain in the notes)'],
  ];

  function correctionForm() {
    const cfg = S.config;
    const names = stateNames();
    let B = null;
    const current = {
      county: r => r.county, state: r => names.get(r.state) || r.state, outcome: r => (r.outcome >= 0 ? B.outcomes[r.outcome] : ''),
      votes_for: r => r.votes_for, votes_against: r => r.votes_against, union_name: r => r.union,
      union_affiliation: r => r.affiliation, election_type: r => r.election_type, bargaining_unit_size: r => r.unit,
      sic_code: r => (r.sic ? `${r.sic} ${r.sic_title}` : ''), employer: r => r.employer, nlrb_case_number: r => r.case,
      nlrb_citation: r => r.citation, nlrb_decision_date: r => r.decided,
    };
    const input = (id, attrs) => h('input', { id, name: id, type: 'text', autocomplete: 'off', ...attrs });
    const f = {
      election_id: input('c-id', { placeholder: '1944-0123', inputmode: 'numeric' }),
      field: h('select', { id: 'c-field', name: 'c-field' }, h('option', { value: '' }, 'Choose a field'),
        FIELD_CHOICES.map(([v, t]) => h('option', { value: v }, t))),
      current_value: input('c-current'),
      proposed_value: input('c-proposed'),
      source: input('c-source', { placeholder: 'For example: 45 NLRB 123, or the newspaper and date' }),
      source_url: input('c-url', { type: 'url', placeholder: 'https://' }),
      notes: h('textarea', { id: 'c-notes', name: 'c-notes', rows: '3' }),
      credit: input('c-credit', { placeholder: 'Leave blank to stay anonymous' }),
    };
    const summary = h('p', { class: 'record-summary note', 'aria-live': 'polite' });
    const error = h('p', { class: 'error', role: 'alert' });
    const status = h('span', { class: 'status-line', role: 'status' });
    const label = (id, text, req, help) => h('div', { class: 'control' },
      h('label', { for: id }, text, req ? h('span', { class: 'req', 'aria-hidden': 'true' }, ' *') : null),
      f[Object.keys(f).find(k => f[k].id === id)], help ? h('span', { class: 'help' }, help) : null);

    function lookup() {
      const id = f.election_id.value.trim();
      if (!B || !/^\d{4}-\d{4}$/.test(id)) { summary.textContent = ''; return null; }
      const r = B.byId.get(id);
      if (!r) { summary.textContent = `No record has the ID ${id}.`; return null; }
      summary.textContent = `${r.id}: ${r.employer}${r.county ? `, ${r.county}, ${r.state}` : ''} (list year ${r.year})`;
      return r;
    }
    function fillCurrent() {
      const r = lookup();
      const get = current[f.field.value];
      if (r && get) f.current_value.value = get(r) || '';
    }
    f.election_id.addEventListener('input', fillCurrent);
    f.field.addEventListener('change', fillCurrent);
    loadBrowse().then(b => { B = b; fillCurrent(); }).catch(() => {});
    if (S.prefill) {
      f.election_id.value = S.prefill.election_id || '';
      S.prefill = null;
      later(() => f.field.focus());
    }

    const values = () => Object.fromEntries(Object.entries(f).map(([k, el]) => [k, el.value.trim()]));
    function validate() {
      const v = values();
      const missing = [];
      if (!/^\d{4}-\d{4}$/.test(v.election_id)) missing.push('an election ID like 1944-0123');
      else if (B && !B.byId.has(v.election_id)) missing.push('an election ID that exists');
      if (!v.field) missing.push('the field to change');
      if (!v.proposed_value) missing.push('the proposed value');
      if (!v.source) missing.push('a source');
      const list = missing.length > 1 ? `${missing.slice(0, -1).join(', ')} and ${missing[missing.length - 1]}` : missing[0];
      error.textContent = missing.length ? `Please add ${list}.` : '';
      return missing.length ? null : v;
    }
    const fieldLabel = v => (FIELD_CHOICES.find(([k]) => k === v.field) || [v.field, v.field])[1];
    const asText = v => [
      `Correction for election ${v.election_id}`,
      `Field: ${fieldLabel(v)} (${v.field})`,
      `Current value: ${v.current_value || '(blank)'}`,
      `Proposed value: ${v.proposed_value}`,
      `Source: ${v.source}`,
      v.source_url ? `Source link: ${v.source_url}` : '',
      v.notes ? `Notes: ${v.notes}` : '',
      `Credit as: ${v.credit || '(anonymous)'}`,
    ].filter(Boolean).join('\n');

    const buttons = [];
    if (cfg.repo_url) {
      buttons.push(h('button', { class: 'btn btn-primary', type: 'button', onclick: () => {
        const v = validate();
        if (!v) return;
        const p = new URLSearchParams({ template: 'data-correction.yml', title: `Correction: ${v.election_id}, ${fieldLabel(v)}` });
        for (const k of ['election_id', 'field', 'current_value', 'proposed_value', 'source', 'source_url', 'notes', 'credit']) {
          if (v[k]) p.set(k, v[k]);
        }
        window.open(`${cfg.repo_url.replace(/\/$/, '')}/issues/new?${p}`, '_blank', 'noopener');
      } }, 'Open as a GitHub issue'));
    }
    if (cfg.form_url_template) {
      buttons.push(h('button', { class: 'btn', type: 'button', onclick: () => {
        const v = validate();
        if (!v) return;
        const url = cfg.form_url_template.replace(/\{(\w+)\}/g, (m, k) => encodeURIComponent(v[k] || ''));
        window.open(url, '_blank', 'noopener');
      } }, 'Open in the Google Form'));
    }
    if (cfg.contact_email) {
      buttons.push(h('button', { class: 'btn', type: 'button', onclick: () => {
        const v = validate();
        if (!v) return;
        location.href = `mailto:${cfg.contact_email}?subject=${encodeURIComponent(`Correction: ${v.election_id}`)}&body=${encodeURIComponent(asText(v))}`;
      } }, 'Email it'));
    }
    buttons.push(h('button', { class: 'btn', type: 'button', onclick: () => {
      const v = validate();
      if (v) copyText(asText(v), status);
    } }, 'Copy as text'));

    const form = h('form', { class: 'form panel', novalidate: true, onsubmit: e => e.preventDefault() },
      h('div', { class: 'row' },
        label('c-id', 'Election ID', true, 'Shown on the Data page, for example 1944-0123.'),
        label('c-field', 'What should change?', true)),
      summary,
      h('div', { class: 'row' },
        label('c-current', 'Current value', false, 'Filled in from the current release when possible.'),
        label('c-proposed', 'Proposed value', true)),
      h('div', { class: 'row' }, label('c-source', 'Source', true), label('c-url', 'Link to the source', false)),
      label('c-notes', 'Notes', false),
      label('c-credit', 'Name for credit', false),
      error,
      h('div', { class: 'controls' }, buttons, status),
      h('p', { class: 'note' }, cfg.repo_url
        ? 'The GitHub button opens a prefilled issue for you to review and submit; nothing is sent until you do. Copy as text works for email.'
        : 'Copy the correction as text and email it to the project. The GitHub and form buttons will appear here once those are set up.'));
    return form;
  }

  // ---------- frame ----------
  function renderChrome() {
    const rel = currentRelease();
    const s = S.agg.stats;
    fill(document.getElementById('docket'),
      h('span', null, 'NLRB representation elections'), h('span', { class: 'sep' }, '/'),
      h('span', null, `${s.first_year}–${s.last_year}`), h('span', { class: 'sep' }, '/'),
      h('span', null, `Release ${rel.version}`),
      /published/i.test(rel.status) ? null : h('span', { class: 'stamp' }, rel.status));
    fill(document.getElementById('footer'),
      h('p', null, `Release ${rel.version} (${rel.status.toLowerCase()}), ${longDate(rel.date)}. `, h('a', { href: '#versions' }, 'Version history'), '.'),
      h('p', null, 'Proposed licenses: data under CC BY 4.0, code under the MIT License.'),
      h('p', null, 'An independent academic research project, not affiliated with or endorsed by the National Labor Relations Board. NLRB decisions are public records.'),
      (S.config.contacts || []).length ? h('p', null, 'Contact: ', S.config.contacts.map((c, i) => [i ? ' and ' : '', `${c.name}, `, h('a', { href: `mailto:${c.email}` }, c.email)]), '.') : null,
      S.config.repo_url ? h('p', null, h('a', { href: S.config.repo_url }, 'Data and code on GitHub')) : null);
  }

  const PAGES = { overview: pageOverview, data: pageData, statistics: pageStatistics, methods: pageMethods,
    versions: pageVersions, contribute: pageContribute };
  const routeKey = () => { const k = location.hash.replace(/^#/, ''); return ROUTES.includes(k) ? k : 'overview'; };

  async function route() {
    const key = routeKey();
    const seq = ++routeSeq;
    Charts.clear();
    pending = [];
    document.querySelectorAll('.tabs a').forEach(a => {
      if (a.dataset.route === key) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
    document.title = key === 'overview' ? 'Historical NLRB Elections' : `${TITLES[key]} | Historical NLRB Elections`;
    let node;
    try {
      node = await PAGES[key]();
    } catch (err) {
      console.error(err);
      node = h('p', { class: 'error' }, `This page could not be loaded (${err.message}).`);
    }
    if (seq !== routeSeq) return;
    page.replaceChildren(node);
    if (!firstRoute) {
      window.scrollTo(0, 0);
      page.focus({ preventScroll: true });
    }
    firstRoute = false;
    flush();
  }

  async function init() {
    try {
      const [config, agg, versions, codebook] = await Promise.all([
        getJSON('data/site/config.json').catch(() => ({})), getJSON('data/site/aggregates.json'),
        getJSON('data/site/versions.json'), getJSON('data/site/codebook.json')]);
      Object.assign(S, { config, agg, versions, codebook });
    } catch (err) {
      page.replaceChildren(h('p', { class: 'error' },
        `The release data could not be loaded (${err.message}). If you opened index.html directly from disk, serve the docs folder with a local web server instead.`));
      return;
    }
    renderChrome();
    window.addEventListener('hashchange', route);
    route();
  }

  init();
})();
