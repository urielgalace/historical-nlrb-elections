/* Chart kit for the Statistics and Overview pages.
   Small d3 renderers that share one tooltip, size themselves to their container, redraw on
   resize, and take every color from the CSS tokens so both themes work. */
(function () {
  'use strict';
  const fmt = d3.format(',');
  const C = {};
  const observers = [];

  // ---------- tooltip (values lead, labels follow; text set with textContent) ----------
  const tip = document.createElement('div');
  tip.className = 'tip';
  tip.hidden = true;
  document.body.appendChild(tip);

  function showTip(evt, title, rows) {
    tip.replaceChildren();
    if (title) {
      const t = document.createElement('div');
      t.className = 'tip-title';
      t.textContent = title;
      tip.appendChild(t);
    }
    rows.forEach(r => {
      const row = document.createElement('div');
      row.className = 'tip-row';
      if (r.color) {
        const k = document.createElement('span');
        k.className = 'tip-key';
        k.style.background = r.color;
        row.appendChild(k);
      }
      const v = document.createElement('span');
      v.className = 'v';
      v.textContent = r.value;
      row.appendChild(v);
      if (r.label) {
        const l = document.createElement('span');
        l.className = 'k';
        l.textContent = r.label;
        row.appendChild(l);
      }
      tip.appendChild(row);
    });
    tip.hidden = false;
    placeTip(evt);
  }
  function placeTip(evt) {
    let x = 0, y = 0;
    if (evt && evt.type && evt.type.startsWith('pointer')) {
      x = evt.clientX; y = evt.clientY;
    } else if (evt && evt.target && evt.target.getBoundingClientRect) {
      const b = evt.target.getBoundingClientRect();
      x = b.left + b.width / 2; y = b.top;
    }
    const w = tip.offsetWidth, h = tip.offsetHeight, vw = window.innerWidth;
    let left = x + 14, top = y - h - 12;
    if (left + w > vw - 8) left = x - w - 14;
    if (left < 8) left = 8;
    if (top < 8) top = y + 18;
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }
  function hideTip() { tip.hidden = true; }
  window.addEventListener('scroll', hideTip, { passive: true });
  C.hideTip = hideTip;

  function bindTip(sel, getTitle, getRows) {
    sel.on('pointerenter pointermove', (e, d) => showTip(e, getTitle(d), getRows(d)))
      .on('pointerleave', hideTip)
      .on('focus', (e, d) => showTip(e, getTitle(d), getRows(d)))
      .on('blur', hideTip);
  }

  // ---------- sizing ----------
  function mount(el, draw) {
    let last = 0;
    const render = () => {
      const w = Math.floor(el.clientWidth);
      if (!w || w === last) return;
      last = w;
      el.replaceChildren();
      draw(w);
    };
    render();
    const ro = new ResizeObserver(() => {
      clearTimeout(el._resizeTimer);
      el._resizeTimer = setTimeout(render, 120);
    });
    ro.observe(el);
    observers.push(ro);
    return { redraw() { last = 0; render(); } };
  }
  C.clear = function () {
    observers.splice(0).forEach(o => o.disconnect());
    hideTip();
  };

  function svgIn(el, w, h, label) {
    return d3.select(el).append('svg')
      .attr('viewBox', `0 0 ${w} ${h}`).attr('width', w).attr('height', h)
      .attr('role', 'img').attr('aria-label', label);
  }
  const compact = v => (v >= 1000 ? `${+(v / 1000).toFixed(1)}K` : `${v}`);
  C.compact = compact;

  // Column with rounded data-end (top) and a square baseline.
  function colPath(x, y, w, h, r) {
    if (h <= 0) return '';
    r = Math.min(r, w / 2, h);
    return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
  }
  // Horizontal bar with rounded data-end (right) and a square baseline.
  function barPath(x, y, w, h, r) {
    if (w <= 0) return '';
    r = Math.min(r, h / 2, w);
    return `M${x},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h - r}Q${x + w},${y + h} ${x + w - r},${y + h}H${x}Z`;
  }

  // Text measuring for truncation of long category labels.
  const measureCtx = document.createElement('canvas').getContext('2d');
  function textWidth(s, size = 12.5) {
    measureCtx.font = `${size}px "Public Sans", system-ui, sans-serif`;
    return measureCtx.measureText(s).width;
  }
  function fit(s, maxW, size) {
    if (textWidth(s, size) <= maxW) return s;
    let t = s;
    while (t.length > 3 && textWidth(t + '…', size) > maxW) t = t.slice(0, -1);
    return t.trimEnd() + '…';
  }

  // Year labels that fit: every year when bands are wide, else even years or multiples of five,
  // plus isolated years (like 1955) and the first year when there is room for it.
  function yearTicks(years, present, step) {
    const every = step >= 36 ? 1 : step >= 18 ? 2 : 5;
    const gap = every === 1 ? 1 : 2;
    const out = [];
    years.forEach(y => {
      if (!present.has(y)) return;
      const isolated = !present.has(y - 1) && !present.has(y + 1);
      if (!(every === 1 || y % every === 0 || isolated)) return;
      if (out.length && y - out[out.length - 1] < gap) return;
      out.push(y);
    });
    const first = years.find(y => present.has(y));
    if (first !== undefined && out.length && out[0] !== first && (out[0] - first) * step >= 40) out.unshift(first);
    return out;
  }

  // ---------- 1. Columns over a year span, with labelled gaps for uncollected years ----------
  C.yearColumns = function (el, opt) {
    const { rows, from, to, label, valueKey = 'n', unit = 'elections', extra } = opt;
    return mount(el, w => {
      const years = d3.range(from, to + 1);
      const present = new Set(rows.map(r => r.year));
      const h = Math.round(Math.max(210, Math.min(290, w * 0.4)));
      const m = { t: 24, r: 6, b: 28, l: 42 };
      const x = d3.scaleBand().domain(years).range([m.l, w - m.r]).paddingInner(0.3).paddingOuter(0.1);
      const max = d3.max(rows, r => r[valueKey]) || 1;
      const y = d3.scaleLinear().domain([0, max]).nice(4).range([h - m.b, m.t]);
      const s = svgIn(el, w, h, label);

      // uncollected spans
      const runs = [];
      years.forEach(yr => {
        if (present.has(yr)) return;
        const last = runs[runs.length - 1];
        if (last && last[1] === yr - 1) last[1] = yr; else runs.push([yr, yr]);
      });
      const half = x.step() * x.paddingInner() / 2;
      runs.forEach(([a, b]) => {
        const x0 = x(a) - half, x1 = x(b) + x.bandwidth() + half;
        s.append('rect').attr('class', 'gap-band').attr('x', x0).attr('y', m.t)
          .attr('width', x1 - x0).attr('height', h - m.b - m.t);
        const cx = (x0 + x1) / 2, cy = (m.t + h - m.b) / 2;
        if (x1 - x0 > 96) {
          s.append('text').attr('class', 'gap-label').attr('x', cx).attr('y', cy).attr('text-anchor', 'middle').text('Not yet collected');
        } else {
          s.append('text').attr('class', 'gap-label').attr('x', cx).attr('y', cy)
            .attr('text-anchor', 'middle').attr('transform', `rotate(-90 ${cx} ${cy})`).attr('dy', '0.35em').text('Not yet collected');
        }
      });

      const grid = s.append('g').attr('class', 'grid');
      y.ticks(4).forEach(t => {
        grid.append('line').attr('x1', m.l).attr('x2', w - m.r).attr('y1', y(t)).attr('y2', y(t));
        s.append('text').attr('x', m.l - 8).attr('y', y(t) + 4).attr('text-anchor', 'end').text(compact(t));
      });

      const bw = Math.min(24, x.bandwidth());
      s.append('g').selectAll('path').data(rows).join('path')
        .attr('d', r => colPath(x(r.year) + (x.bandwidth() - bw) / 2, y(r[valueKey]), bw, y(0) - y(r[valueKey]), 4))
        .style('fill', 'var(--series-1)').style('pointer-events', 'none');
      s.append('line').attr('class', 'axis').attr('x1', m.l).attr('x2', w - m.r)
        .attr('y1', y(0)).attr('y2', y(0)).style('stroke', 'var(--axis)');

      const top = rows.reduce((a, b) => (b[valueKey] > a[valueKey] ? b : a));
      s.append('text').attr('class', 'value-label').attr('text-anchor', 'middle')
        .attr('x', x(top.year) + x.bandwidth() / 2).attr('y', y(top[valueKey]) - 7).text(fmt(top[valueKey]));

      yearTicks(years, present, x.step()).forEach(yr => {
        s.append('text').attr('x', x(yr) + x.bandwidth() / 2).attr('y', h - m.b + 18).attr('text-anchor', 'middle').text(yr);
      });

      const hits = s.append('g').selectAll('rect').data(rows).join('rect')
        .attr('class', 'hit mark').attr('x', r => x(r.year) - half).attr('y', m.t)
        .attr('width', x.step()).attr('height', h - m.b - m.t)
        .attr('tabindex', 0).attr('aria-label', r => `${r.year}: ${fmt(r[valueKey])} ${unit}`);
      bindTip(hits, r => String(r.year),
        r => [{ value: fmt(r[valueKey]), label: unit, color: 'var(--series-1)' }, ...(extra ? extra(r) : [])]);
    });
  };

  // ---------- 2. Horizontal bars (ranked lists, or ordered bins when sort is off) ----------
  C.hbars = function (el, opt) {
    const { rows, label, valueFormat = fmt, unit = 'elections', total, totalLabel = 'of the total', tipTitle } = opt;
    return mount(el, w => {
      const labelW = Math.round(Math.min(230, Math.max(104, w * 0.36)));
      const rowH = 26, barH = 14;
      const valueW = 58;
      const m = { t: 2, r: valueW, b: 2, l: labelW };
      const h = m.t + m.b + rows.length * rowH;
      const max = d3.max(rows, r => r.value) || 1;
      const x = d3.scaleLinear().domain([0, max]).range([m.l, w - m.r]);
      const s = svgIn(el, w, h, label);
      rows.forEach((r, i) => {
        const yc = m.t + i * rowH + rowH / 2;
        s.append('text').attr('class', 'cat-label').attr('x', m.l - 10).attr('y', yc + 4)
          .attr('text-anchor', 'end').text(fit(r.label, labelW - 14, 12.5));
        const bw = Math.max(x(r.value) - m.l, r.value > 0 ? 2 : 0);
        s.append('path').attr('d', barPath(m.l, yc - barH / 2, bw, barH, 4))
          .style('fill', r.color || 'var(--series-1)').style('pointer-events', 'none');
        s.append('text').attr('class', 'value-label').attr('x', m.l + bw + 6).attr('y', yc + 4)
          .text(valueFormat(r.value));
      });
      s.append('line').attr('x1', m.l).attr('x2', m.l).attr('y1', 0).attr('y2', h).style('stroke', 'var(--axis)');
      const hits = s.append('g').selectAll('rect').data(rows).join('rect')
        .attr('class', 'hit mark').attr('x', 0).attr('width', w)
        .attr('y', (r, i) => m.t + i * rowH).attr('height', rowH)
        .attr('tabindex', 0).attr('aria-label', r => `${r.title || r.label}: ${valueFormat(r.value)}`);
      bindTip(hits, r => (tipTitle ? tipTitle(r) : (r.title || r.label)), r => {
        const out = [{ value: valueFormat(r.value), label: unit, color: r.color || 'var(--series-1)' }];
        if (total) out.push({ value: `${(100 * r.value / total).toFixed(1)}%`, label: totalLabel });
        return out;
      });
    });
  };

  // ---------- 3. Stacked columns by year (counts or shares) ----------
  C.stacked = function (el, opt) {
    const { rows, series, from, to, mode = 'count', label } = opt;
    return mount(el, w => {
      const years = d3.range(from, to + 1);
      const present = new Set(rows.map(r => r.year));
      const h = Math.round(Math.max(230, Math.min(300, w * 0.42)));
      const m = { t: 14, r: 6, b: 28, l: 44 };
      const x = d3.scaleBand().domain(years).range([m.l, w - m.r]).paddingInner(0.3).paddingOuter(0.1);
      const totals = new Map(rows.map(r => [r.year, d3.sum(series, sr => r[sr.key] || 0)]));
      const y = mode === 'share'
        ? d3.scaleLinear().domain([0, 1]).range([h - m.b, m.t])
        : d3.scaleLinear().domain([0, d3.max([...totals.values()]) || 1]).nice(4).range([h - m.b, m.t]);
      const s = svgIn(el, w, h, label);
      const half = x.step() * x.paddingInner() / 2;
      // uncollected spans
      let run = null;
      const runs = [];
      years.forEach(yr => {
        if (present.has(yr)) { run = null; return; }
        if (run && run[1] === yr - 1) run[1] = yr; else { run = [yr, yr]; runs.push(run); }
      });
      runs.forEach(([a, b]) => {
        s.append('rect').attr('class', 'gap-band').attr('x', x(a) - half).attr('y', m.t)
          .attr('width', x(b) + x.bandwidth() + half - (x(a) - half)).attr('height', h - m.b - m.t);
      });
      const grid = s.append('g').attr('class', 'grid');
      const ticks = mode === 'share' ? [0, 0.25, 0.5, 0.75, 1] : y.ticks(4);
      ticks.forEach(t => {
        grid.append('line').attr('x1', m.l).attr('x2', w - m.r).attr('y1', y(t)).attr('y2', y(t));
        s.append('text').attr('x', m.l - 8).attr('y', y(t) + 4).attr('text-anchor', 'end')
          .text(mode === 'share' ? `${Math.round(t * 100)}%` : compact(t));
      });
      const bw = Math.min(24, x.bandwidth());
      const marks = s.append('g');
      rows.forEach(r => {
        const total = totals.get(r.year) || 1;
        let acc = 0;
        const bx = x(r.year) + (x.bandwidth() - bw) / 2;
        const segs = series.filter(sr => (r[sr.key] || 0) > 0);
        segs.forEach((sr, i) => {
          const v = mode === 'share' ? r[sr.key] / total : r[sr.key];
          const y0 = y(acc), y1 = y(acc + v);
          acc += v;
          const topSeg = i === segs.length - 1;
          const hgt = Math.max(0, (y0 - y1) - (topSeg ? 0 : 2));
          if (hgt <= 0) return;
          marks.append('path')
            .attr('d', topSeg ? colPath(bx, y1, bw, hgt, 3) : `M${bx},${y1 + 2}h${bw}v${hgt}h${-bw}Z`)
            .style('fill', sr.color).style('pointer-events', 'none');
        });
      });
      s.append('line').attr('x1', m.l).attr('x2', w - m.r).attr('y1', y(0)).attr('y2', y(0)).style('stroke', 'var(--axis)');
      yearTicks(years, present, x.step()).forEach(yr => {
        s.append('text').attr('x', x(yr) + x.bandwidth() / 2).attr('y', h - m.b + 18).attr('text-anchor', 'middle').text(yr);
      });
      const hits = s.append('g').selectAll('rect').data(rows).join('rect')
        .attr('class', 'hit mark').attr('x', r => x(r.year) - half).attr('y', m.t)
        .attr('width', x.step()).attr('height', h - m.b - m.t).attr('tabindex', 0)
        .attr('aria-label', r => `${r.year}: ` + series.map(sr => `${sr.label} ${fmt(r[sr.key] || 0)}`).join(', '));
      bindTip(hits, r => `${r.year} · ${fmt(totals.get(r.year))} elections`, r => series.slice().reverse().map(sr => ({
        value: mode === 'share' ? `${(100 * (r[sr.key] || 0) / (totals.get(r.year) || 1)).toFixed(0)}%` : fmt(r[sr.key] || 0),
        label: sr.label, color: sr.color,
      })));
    });
  };

  // ---------- 4. Heatmap of shares (field x year) ----------
  const HEAT_STEPS = [10, 25, 40, 55, 70, 85];
  const heatStep = v => HEAT_STEPS.filter(s => v >= s).length;
  C.heatSteps = HEAT_STEPS;
  C.heatmap = function (el, opt) {
    const { rows, cols, label } = opt;
    return mount(el, w => {
      const labelW = Math.round(Math.min(150, Math.max(100, w * 0.2)));
      const m = { t: 24, r: 2, b: 2, l: labelW };
      const cw = (w - m.l - m.r) / cols.length;
      const ch = Math.round(Math.max(24, Math.min(30, cw * 0.95)));
      const h = m.t + rows.length * ch + m.b;
      const s = svgIn(el, w, h, label);
      cols.forEach((c, j) => {
        const txt = cw >= 36 ? c : `’${String(c).slice(2)}`;
        s.append('text').attr('x', m.l + j * cw + cw / 2).attr('y', m.t - 8).attr('text-anchor', 'middle')
          .style('font-size', cw >= 30 ? '11.5px' : '10.5px').text(txt);
      });
      const cells = [];
      rows.forEach((r, i) => {
        s.append('text').attr('class', 'cat-label').attr('x', m.l - 10).attr('y', m.t + i * ch + ch / 2 + 4)
          .attr('text-anchor', 'end').text(fit(r.label, labelW - 14, 12.5));
        cols.forEach((c, j) => cells.push({ row: r, col: c, v: r.values[c] ?? 0, i, j }));
      });
      const g = s.append('g').selectAll('g').data(cells).join('g');
      g.append('rect').attr('x', d => m.l + d.j * cw + 1).attr('y', d => m.t + d.i * ch + 1)
        .attr('width', Math.max(1, cw - 2)).attr('height', ch - 2).attr('rx', 2)
        .style('fill', d => `var(--heat-${heatStep(d.v)})`);
      if (cw >= 24) {
        g.append('text').attr('x', d => m.l + d.j * cw + cw / 2).attr('y', d => m.t + d.i * ch + ch / 2 + 4)
          .attr('text-anchor', 'middle').style('font-size', cw >= 32 ? '11.5px' : '10px')
          .style('font-variant-numeric', 'tabular-nums').style('pointer-events', 'none')
          .style('fill', d => `var(--heat-t${heatStep(d.v)})`).text(d => Math.round(d.v));
      }
      const hits = s.append('g').selectAll('rect').data(cells).join('rect')
        .attr('class', 'hit mark').attr('x', d => m.l + d.j * cw).attr('y', d => m.t + d.i * ch)
        .attr('width', cw).attr('height', ch)
        .attr('aria-label', d => `${d.row.label}, ${d.col}: ${d.v.toFixed(1)}%`);
      bindTip(hits, d => `${d.row.label} · ${d.col}`, d => [{ value: `${d.v.toFixed(1)}%`, label: 'of records filled' }]);
    });
  };

  // ---------- 5. County map: white = no elections, then gray to dark ----------
  const MAP_BINS = [
    { lo: 0, hi: 0, label: '0', color: '#ffffff' },
    { lo: 1, hi: 1, label: '1', color: '#e4e4e4' },
    { lo: 2, hi: 4, label: '2–4', color: '#c6c6c6' },
    { lo: 5, hi: 9, label: '5–9', color: '#a1a1a1' },
    { lo: 10, hi: 24, label: '10–24', color: '#7b7b7b' },
    { lo: 25, hi: 49, label: '25–49', color: '#555555' },
    { lo: 50, hi: 99, label: '50–99', color: '#323232' },
    { lo: 100, hi: Infinity, label: '100+', color: '#111111' },
  ];
  C.mapBins = MAP_BINS;
  const binFor = n => MAP_BINS.find(b => n >= b.lo && n <= b.hi) || MAP_BINS[0];

  C.countyMap = function (el, opt) {
    const { topo, counts, names, label } = opt;
    el.replaceChildren();
    const W = 975, H = 610;
    const plate = document.createElement('div');
    plate.className = 'map-plate';
    el.appendChild(plate);
    const s = d3.select(plate).append('svg').attr('viewBox', `0 0 ${W} ${H}`)
      .attr('role', 'img').attr('aria-label', label);
    const stateNames = new Map(topo.objects.states.geometries.map(g => [g.id, g.properties.name]));
    const counties = topojson.feature(topo, topo.objects.counties).features;
    const path = d3.geoPath();
    const paths = s.append('g').selectAll('path').data(counties).join('path')
      .attr('d', path)
      .attr('fill', d => binFor(counts[d.id] || 0).color)
      .attr('stroke', '#dcdcd6').attr('stroke-width', 0.3);
    s.append('path').datum(topojson.mesh(topo, topo.objects.states, (a, b) => a !== b))
      .attr('fill', 'none').attr('stroke', '#8c8e93').attr('stroke-width', 0.7).attr('d', path)
      .style('pointer-events', 'none');
    s.append('path').datum(topojson.mesh(topo, topo.objects.nation))
      .attr('fill', 'none').attr('stroke', '#6b6d72').attr('stroke-width', 0.9).attr('d', path)
      .style('pointer-events', 'none');
    paths.on('pointerenter pointermove', (e, d) => {
      const n = counts[d.id] || 0;
      const title = names[d.id] || `${d.properties.name}, ${stateNames.get(d.id.slice(0, 2)) || ''}`;
      showTip(e, title, [{ value: fmt(n), label: n === 1 ? 'election' : 'elections' }]);
    }).on('pointerleave', hideTip);

    const legend = document.createElement('div');
    legend.className = 'map-legend';
    const ttl = document.createElement('div');
    ttl.className = 'ttl';
    ttl.textContent = 'Elections per county';
    legend.appendChild(ttl);
    MAP_BINS.forEach(b => {
      const step = document.createElement('div');
      step.className = 'step';
      const chip = document.createElement('span');
      chip.className = 'chip';
      chip.style.background = b.color;
      const t = document.createElement('span');
      t.textContent = b.label;
      step.append(chip, t);
      legend.appendChild(step);
    });
    el.appendChild(legend);
  };

  // ---------- legends and tables ----------
  C.legend = function (items) {
    const box = document.createElement('div');
    box.className = 'legend';
    items.forEach(it => {
      const k = document.createElement('span');
      k.className = 'key';
      const sw = document.createElement('span');
      sw.className = 'swatch' + (it.kind === 'line' ? ' line' : '');
      sw.style.background = it.color;
      const t = document.createElement('span');
      t.textContent = it.label;
      k.append(sw, t);
      box.appendChild(k);
    });
    return box;
  };

  C.table = function (columns, rows) {
    const wrap = document.createElement('div');
    wrap.className = 'table-wrap';
    const table = document.createElement('table');
    const thead = table.createTHead().insertRow();
    columns.forEach(c => {
      const th = document.createElement('th');
      th.textContent = c.label;
      if (c.num) th.className = 'num';
      thead.appendChild(th);
    });
    const tb = table.createTBody();
    rows.forEach(r => {
      const tr = tb.insertRow();
      columns.forEach(c => {
        const td = tr.insertCell();
        const v = typeof c.value === 'function' ? c.value(r) : r[c.key];
        td.textContent = v == null ? '' : (c.num && typeof v === 'number' ? fmt(v) : v);
        if (c.num) td.className = 'num';
      });
    });
    wrap.appendChild(table);
    return wrap;
  };

  window.Charts = C;
})();
