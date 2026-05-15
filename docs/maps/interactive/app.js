/* JustHireMe System Map — app.js (SPA router + all page renderers) */
(function() {
'use strict';

/* ─── Route table ─── */
const ROUTES = [
  { path: '/',                     page: 'overview',  label: 'Overview',     group: 'SYSTEM',   data: 'data/overview.json' },
  { path: '/flows',                page: 'flows',     label: 'Flows',        group: 'SYSTEM',   data: 'data/flows.json' },
  { path: '/flags',                page: 'flags',     label: 'Flag Registry', group: 'SYSTEM',  data: 'data/flags.json' },
  { path: '/index',                page: 'index',     label: 'Index',        group: 'SYSTEM',   data: 'data/master-index.json' },
  { path: '/backend/config',       page: 'unit',      label: 'Config',       group: 'BACKEND',  data: 'data/backend-config.json', slug: 'backend-config' },
  { path: '/backend/db',           page: 'unit',      label: 'DB',           group: 'BACKEND',  data: 'data/backend-db.json', slug: 'backend-db' },
  { path: '/backend/evaluators',   page: 'unit',      label: 'Evaluators',   group: 'BACKEND',  data: 'data/backend-evaluators.json', slug: 'backend-evaluators' },
  { path: '/backend/foundations',  page: 'unit',      label: 'Foundations',  group: 'BACKEND',  data: 'data/backend-foundations.json', slug: 'backend-foundations' },
  { path: '/backend/generators',   page: 'unit',      label: 'Generators',   group: 'BACKEND',  data: 'data/backend-generators.json', slug: 'backend-generators' },
  { path: '/backend/integrations', page: 'unit',      label: 'Integrations', group: 'BACKEND',  data: 'data/backend-integrations.json', slug: 'backend-integrations' },
  { path: '/backend/main',         page: 'unit',      label: 'Main',         group: 'BACKEND',  data: 'data/backend-main.json', slug: 'backend-main' },
  { path: '/backend/routes',       page: 'unit',      label: 'Routes',       group: 'BACKEND',  data: 'data/backend-routes.json', slug: 'backend-routes' },
  { path: '/backend/scrapers',     page: 'unit',      label: 'Scrapers',     group: 'BACKEND',  data: 'data/backend-scrapers.json', slug: 'backend-scrapers' },
  { path: '/backend/services',     page: 'unit',      label: 'Services',     group: 'BACKEND',  data: 'data/backend-services.json', slug: 'backend-services' },
  { path: '/backend/tests',        page: 'unit',      label: 'Tests',        group: 'BACKEND',  data: 'data/backend-tests.json', slug: 'backend-tests' },
  { path: '/frontend/components',  page: 'unit',      label: 'Components',   group: 'FRONTEND', data: 'data/frontend-components.json', slug: 'frontend-components' },
  { path: '/frontend/core',        page: 'unit',      label: 'Core',         group: 'FRONTEND', data: 'data/frontend-core.json', slug: 'frontend-core' },
  { path: '/frontend/hooks',       page: 'unit',      label: 'Hooks',        group: 'FRONTEND', data: 'data/frontend-hooks.json', slug: 'frontend-hooks' },
  { path: '/frontend/settings',    page: 'unit',      label: 'Settings',     group: 'FRONTEND', data: 'data/frontend-settings.json', slug: 'frontend-settings' },
  { path: '/frontend/views',       page: 'unit',      label: 'Views',        group: 'FRONTEND', data: 'data/frontend-views.json', slug: 'frontend-views' },
  { path: '/infra/tauri',          page: 'unit',      label: 'Tauri',        group: 'INFRA',    data: 'data/tauri.json', slug: 'tauri' },
  { path: '/infra/build-ci',       page: 'unit',      label: 'Build & CI',  group: 'INFRA',    data: 'data/build-ci.json', slug: 'build-ci' },
];

const content = document.getElementById('content');
const sidebarNav = document.getElementById('sidebar-nav');
const branchDisplay = document.getElementById('branch-display');

/* ─── Data lookup ─── */
function loadData(path) {
  const key = path.replace(/^data\//, '').replace(/\.json$/, '');
  const d = window.__DATA[key];
  if (!d) console.warn('No data for', key);
  return d;
}

/* ─── Sidebar ─── */
function renderSidebar(activePath) {
  const groups = {};
  ROUTES.forEach(r => {
    if (!groups[r.group]) groups[r.group] = [];
    groups[r.group].push(r);
  });
  let html = '';
  for (const [group, items] of Object.entries(groups)) {
    html += `<div class="sidebar-group"><div class="sidebar-group-label">${group}</div>`;
    items.forEach(r => {
      const active = r.path === activePath ? ' active' : '';
      html += `<a class="sidebar-link${active}" data-path="${r.path}">${r.label}</a>`;
    });
    html += `</div>`;
  }
  sidebarNav.innerHTML = html;
  sidebarNav.querySelectorAll('.sidebar-link').forEach(el => {
    el.addEventListener('click', () => navigate(el.dataset.path));
  });
}

/* ─── Branch display ─── */
async function loadBranch() {
  try {
    const r = await fetch('../../.git/HEAD');
    if (r.ok) {
      const text = (await r.text()).trim();
      const m = text.match(/ref:\s+refs\/heads\/(.+)/);
      branchDisplay.textContent = m ? m[1] : text.slice(0, 40);
      return;
    }
  } catch (_) {}
  branchDisplay.textContent = 'linux-base';
}

/* ─── Router ─── */
function navigate(path) {
  if (path === window.location.pathname) return;
  history.pushState(null, '', path);
  renderPage(path);
}

window.addEventListener('popstate', () => renderPage(window.location.pathname));

/* ─── Page transitions ─── */
function transitionOut() {
  return new Promise(resolve => {
    content.classList.add('page-exit');
    setTimeout(() => {
      content.classList.remove('page-exit');
      content.innerHTML = '';
      resolve();
    }, 180);
  });
}

function transitionIn() {
  content.classList.add('page-enter');
  setTimeout(() => content.classList.remove('page-enter'), 200);
}

/* ─── Page rendering ─── */
async function renderPage(path) {
  const route = ROUTES.find(r => r.path === path);
  if (!route) { navigate('/'); return; }

  renderSidebar(path);
  await transitionOut();

  content.innerHTML = '<div class="loading">Loading...</div>';

  try {
    if (route.page === 'overview') await renderOverview();
    else if (route.page === 'flows') await renderFlows();
    else if (route.page === 'flags') await renderFlags();
    else if (route.page === 'index') await renderIndex();
    else if (route.page === 'unit') await renderUnit(route);
    else content.innerHTML = '<div class="loading">Page not found</div>';
  } catch (e) {
    content.innerHTML = `<div class="loading">Error loading page: ${e.message}</div>`;
  }

  transitionIn();
}

/* ═══ OVERVIEW PAGE ═══ */
const FLAG_TYPE_ORDER = ['dead','hardcoded','coupled','stale','suspect','incomplete','clean'];

async function renderOverview() {
  const data = loadData('data/overview.json');
  if (!data) { content.innerHTML = '<div class="loading">Failed to load overview data</div>'; return; }

  let html = '<h1>System Overview</h1>';

  html += '<div class="filter-bar" id="overview-filters">';
  for (const type of FLAG_TYPE_ORDER) {
    const count = data.flagCounts[type] || 0;
    if (count > 0) {
      html += `<button class="filter-chip" data-type="${type}"><span class="flag-dot ${type}"></span> ${type} (${count})</button>`;
    }
  }
  html += '</div>';

  html += '<div class="graph-container" id="graph"></div>';

  html += '<div class="graph-legend">';
  html += '<div class="legend-item"><span class="legend-swatch" style="background:var(--success)"></span> Healthy</div>';
  html += '<div class="legend-item"><span class="legend-swatch" style="background:var(--warning)"></span> Moderate issues</div>';
  html += '<div class="legend-item"><span class="legend-swatch" style="background:var(--flag-dead)"></span> Problematic</div>';
  html += '<div class="legend-item" style="gap:4px"><span style="color:var(--fg-dim);font-family:var(--font-mono)">●</span> Node size = file count</div>';
  html += '<div class="legend-item" style="gap:4px"><span style="color:var(--fg-dim)">→</span> Edge = dependency</div>';
  html += '</div>';

  content.innerHTML = html;
  let activeFilter = null;

  function doRenderGraph() {
    renderGraph(data, activeFilter);
  }

  document.getElementById('overview-filters').addEventListener('click', e => {
    const chip = e.target.closest('.filter-chip');
    if (!chip) return;
    const type = chip.dataset.type;
    if (activeFilter === type) {
      activeFilter = null;
      chip.classList.remove('active');
    } else {
      document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
      activeFilter = type;
      chip.classList.add('active');
    }
    doRenderGraph();
  });

  doRenderGraph();
}

function renderGraph(data, activeFilter) {
  const container = document.getElementById('graph');
  container.innerHTML = '';

  const rect = container.getBoundingClientRect();
  const w = Math.max(600, rect.width || 800);
  const h = Math.max(400, rect.height || 550);

  const svg = d3.select('#graph')
    .append('svg')
    .attr('width', w)
    .attr('height', h)
    .attr('viewBox', [0, 0, 800, 550]);

  const g = svg.append('g');

  const zoom = d3.zoom()
    .scaleExtent([0.4, 4])
    .on('zoom', (event) => g.attr('transform', event.transform));
  svg.call(zoom);

  const sim = d3.forceSimulation(data.nodes)
    .force('link', d3.forceLink(data.edges).id(d => d.id).distance(130))
    .force('charge', d3.forceManyBody().strength(-350))
    .force('center', d3.forceCenter(400, 275))
    .force('collision', d3.forceCollide().radius(d => Math.sqrt(d.fileCount || 5) * 8 + 24));

  const link = g.append('g')
    .selectAll('line')
    .data(data.edges)
    .join('line')
    .attr('stroke', 'var(--border)')
    .attr('stroke-width', 1)
    .attr('stroke-opacity', 0.5);

  const node = g.append('g')
    .selectAll('g')
    .data(data.nodes)
    .join('g')
    .style('cursor', 'pointer')
    .call(d3.drag()
      .on('start', (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
      .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
      .on('end', (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));

  node.on('click', (event, d) => {
    const route = ROUTES.find(r => r.slug === d.id);
    if (route) navigate(route.path);
  });

  node.append('title').text(d => `${d.name} (${d.fileCount} files)\n${d.summary || ''}`);

  node.each(function(d) {
    const el = d3.select(this);
    const r = Math.sqrt(d.fileCount || 5) * 5 + 10;

    const fc = d.flagCounts || {};
    const total = Object.values(fc).reduce((a, b) => a + b, 0);
    let color = 'var(--success)';
    if (total > 0) {
      const bad = (fc.dead || 0) + (fc.hardcoded || 0) + (fc.coupled || 0);
      const ratio = bad / total;
      if (ratio > 0.3) color = 'var(--flag-dead)';
      else if (ratio > 0.15) color = 'var(--warning)';
    }

    const isDimmed = activeFilter && (!fc[activeFilter] || fc[activeFilter] === 0);
    const opacity = isDimmed ? 0.15 : 1;

    el.append('circle')
      .attr('r', r)
      .attr('fill', color)
      .attr('stroke', isDimmed ? 'var(--border)' : 'var(--bg-surface)')
      .attr('stroke-width', 2)
      .attr('opacity', opacity);

    el.append('text')
      .text(d.name)
      .attr('text-anchor', 'middle')
      .attr('dy', 4)
      .attr('fill', isDimmed ? 'var(--fg-dim)' : 'var(--fg)')
      .attr('font-size', '10px')
      .attr('font-family', 'var(--font-body)')
      .attr('font-weight', isDimmed ? '400' : '600')
      .attr('pointer-events', 'none');
  });

  sim.nodes(data.nodes);
  sim.force('link').links(data.edges);
  sim.on('tick', () => {
    link.attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    node.attr('transform', d => `translate(${d.x},${d.y})`);
  });
}

/* ═══ FLOWS PAGE ═══ */
async function renderFlows() {
  const data = loadData('data/flows.json');
  if (!data || data.length === 0) { content.innerHTML = '<div class="loading">No flow data</div>'; return; }

  let html = '<h1>Application Flows</h1>';
  html += '<div class="flow-layout">';
  html += '<div class="flow-list-panel" id="flow-list"></div>';
  html += '<div class="flow-area"><div class="flow-diagram" id="flow-diagram"></div><div id="flow-steps"></div></div>';
  html += '</div>';
  content.innerHTML = html;

  const listPanel = document.getElementById('flow-list');
  data.forEach((f, i) => {
    const div = document.createElement('div');
    div.className = 'flow-item' + (i === 0 ? ' active' : '');
    div.dataset.flowIndex = i;
    div.textContent = f.name + ' Flow';
    listPanel.appendChild(div);
  });

  let activeFlow = -1;

  function renderFlow(index) {
    const flow = data[index];
    if (!flow || index === activeFlow) return;
    activeFlow = index;
    listPanel.querySelectorAll('.flow-item').forEach((el, i) => el.classList.toggle('active', i === index));
    renderFlowDiagram(flow);
    renderFlowSteps(flow);
  }

  listPanel.addEventListener('click', e => {
    const item = e.target.closest('.flow-item');
    if (item) renderFlow(parseInt(item.dataset.flowIndex));
  });

  if (data.length > 0) renderFlow(0);
}

function renderFlowDiagram(flow) {
  const container = document.getElementById('flow-diagram');
  container.innerHTML = '';
  if (!flow.steps || flow.steps.length === 0) {
    container.innerHTML = '<div class="loading">No steps data for this flow</div>';
    return;
  }

  const name = flow.name;
  const participants = [];
  const seen = new Set();
  flow.steps.forEach(s => {
    const p = s.participant.trim();
    if (!seen.has(p)) { seen.add(p); participants.push(p); }
  });

  const rect = container.getBoundingClientRect();
  const cw = Math.max(600, rect.width || 700);
  const ch = Math.max(200, participants.length * 56 + 80);
  const n = flow.steps.length;
  const pad = { top: 40, bottom: 20, left: 130, right: 40 };

  const svg = d3.select('#flow-diagram')
    .append('svg')
    .attr('width', '100%')
    .attr('height', ch)
    .attr('viewBox', [0, 0, cw, ch]);

  const defs = svg.append('defs');
  defs.append('marker')
    .attr('id', 'arrowhead')
    .attr('viewBox', '0 0 10 7')
    .attr('refX', 10).attr('refY', 3.5)
    .attr('markerWidth', 8).attr('markerHeight', 6)
    .attr('orient', 'auto')
    .append('polygon')
    .attr('points', '0 0, 10 3.5, 0 7')
    .attr('fill', 'var(--fg-dim)');

  const yScale = d3.scalePoint()
    .domain(participants)
    .range([pad.top, ch - pad.bottom]);

  const stepX = d3.scalePoint()
    .domain(d3.range(n))
    .range([pad.left, cw - pad.right]);

  /* Participant lane lines */
  participants.forEach(p => {
    svg.append('line')
      .attr('x1', pad.left - 10)
      .attr('x2', cw - pad.right)
      .attr('y1', yScale(p))
      .attr('y2', yScale(p))
      .attr('stroke', 'var(--border)')
      .attr('stroke-width', 1)
      .attr('stroke-dasharray', '3,3')
      .attr('opacity', 0.4);
  });

  /* Participant labels */
  svg.selectAll('text.participant')
    .data(participants)
    .join('text')
    .attr('x', pad.left - 16)
    .attr('y', d => yScale(d))
    .attr('dy', 4)
    .attr('text-anchor', 'end')
    .attr('fill', 'var(--fg)')
    .attr('font-size', '11px')
    .attr('font-family', 'var(--font-mono)')
    .text(d => d);

  /* Step circles + edges */
  const edges = [];

  flow.steps.forEach((s, i) => {
    const px = stepX(i);
    const py = yScale(s.participant.trim());

    const isEntry = i === 0;
    const isExit = i === n - 1;

    const g = svg.append('g').attr('opacity', 0);

    g.append('circle')
      .attr('cx', px)
      .attr('cy', py)
      .attr('r', 7)
      .attr('fill', isEntry ? 'var(--success)' : 'var(--bg-surface)')
      .attr('stroke', isEntry ? 'var(--success)' : isExit ? 'var(--fg-dim)' : 'var(--accent)')
      .attr('stroke-width', isEntry ? 3 : isExit ? 2 : 1.5);

    g.append('circle')
      .attr('cx', px)
      .attr('cy', py)
      .attr('r', 3)
      .attr('fill', isEntry ? 'var(--bg-app)' : 'var(--fg)');

    if (isEntry) {
      g.append('text')
        .attr('x', px)
        .attr('y', py - 16)
        .attr('text-anchor', 'middle')
        .attr('fill', 'var(--success)')
        .attr('font-size', '8px')
        .attr('font-family', 'var(--font-mono)')
        .attr('font-weight', '600')
        .text('ENTRY');
    }
    if (isExit) {
      g.append('text')
        .attr('x', px)
        .attr('y', py + 20)
        .attr('text-anchor', 'middle')
        .attr('fill', 'var(--fg-dim)')
        .attr('font-size', '8px')
        .attr('font-family', 'var(--font-mono)')
        .text('EXIT');
    }

    g.append('title').text(`Step ${s.step}: ${s.action}`);

    g.transition().delay(i * 120).duration(200).attr('opacity', 1);

    if (i > 0) {
      const prev = flow.steps[i - 1];
      const prevP = prev.participant.trim();
      const prevX = stepX(i - 1);
      const prevY = yScale(prevP);

      if (prevP !== s.participant.trim()) {
        const edge = svg.append('line')
          .attr('x1', prevX)
          .attr('y1', prevY)
          .attr('x2', prevX)
          .attr('y2', prevY)
          .attr('stroke', 'var(--fg-dim)')
          .attr('stroke-width', 1.5)
          .attr('marker-end', 'url(#arrowhead)')
          .attr('opacity', 0);

        edge.transition()
          .delay(i * 160 + 100)
          .duration(400)
          .attr('x2', prevX + (px - prevX) * 1)
          .attr('y2', prevY + (py - prevY) * 1)
          .attr('opacity', 1);

        const midX = (prevX + px) / 2;
        const midY = (prevY + py) / 2 - 8;

        const label = svg.append('text')
          .attr('x', midX)
          .attr('y', midY)
          .attr('text-anchor', 'middle')
          .attr('fill', 'var(--fg-dim)')
          .attr('font-size', '8px')
          .attr('font-family', 'var(--font-body)')
          .attr('opacity', 0);

        label.transition()
          .delay(i * 160 + 300)
          .duration(300)
          .attr('opacity', 1)
          .text(prev.action.length > 50 ? prev.action.slice(0, 50) + '…' : prev.action);
      }
    }
  });
}

function renderFlowSteps(flow) {
  const container = document.getElementById('flow-steps');
  let html = '<h2 style="margin-top:24px">Step Breakdown</h2><div class="step-list">';
  if (flow.steps) {
    flow.steps.forEach(s => {
      const isEntry = s.step === flow.steps[0].step;
      const isExit = s.step === flow.steps[flow.steps.length - 1].step;
      html += `<div class="step-item" style="${isEntry ? 'border-left:2px solid var(--success);padding-left:8px' : isExit ? 'border-left:2px solid var(--fg-dim);padding-left:8px' : ''}">
        <span class="step-num">${s.step}</span>
        <span class="step-participant">${esc(s.file)}</span>
        <span style="color:var(--fg-muted)">${esc(s.action)}</span>
      </div>`;
    });
  }
  html += '</div>';

  if (flow.flags && flow.flags.length > 0) {
    html += '<h2 style="margin-top:20px;font-size:14px">Flags in this Flow</h2>';
    html += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">';
    flow.flags.forEach(f => {
      html += `<span class="flag-badge ${f.type}" title="${esc(f.reason)}">${esc(f.item)}</span>`;
    });
    html += '</div>';
  }

  container.innerHTML = html;
}

/* ═══ FLAGS PAGE ═══ */
const FLAG_SORT_WEIGHT = { dead:0, hardcoded:1, coupled:2, stale:3, suspect:4, incomplete:5, clean:6 };

async function renderFlags() {
  const data = loadData('data/flags.json');
  if (!data || data.length === 0) { content.innerHTML = '<div class="loading">No flags found</div>'; return; }

  const flagTypes = FLAG_TYPE_ORDER.filter(t => data.some(f => f.type === t));
  const units = [...new Set(data.filter(f => f.unit).map(f => f.unit))].sort();

  let sortBy = 'type';
  let sortDir = 'asc';
  const activeFilters = new Set(flagTypes);

  function getFiltered() {
    let f = data;
    f = f.filter(x => activeFilters.has(x.type));
    const uf = document.getElementById('unit-filter');
    if (uf && uf.value) f = f.filter(x => x.unit === uf.value);
    return f;
  }

  function sortRows(arr) {
    return [...arr].sort((a, b) => {
      let va, vb;
      if (sortBy === 'type') {
        va = FLAG_SORT_WEIGHT[a.type] ?? 99;
        vb = FLAG_SORT_WEIGHT[b.type] ?? 99;
      } else if (sortBy === 'unit') {
        va = (a.unit || '').toLowerCase();
        vb = (b.unit || '').toLowerCase();
      } else if (sortBy === 'item') {
        va = (a.item || '').toLowerCase();
        vb = (b.item || '').toLowerCase();
      } else if (sortBy === 'location') {
        va = (a.location || '').toLowerCase();
        vb = (b.location || '').toLowerCase();
      } else if (sortBy === 'reason') {
        va = (a.reason || '').toLowerCase();
        vb = (b.reason || '').toLowerCase();
      }
      if (va < vb) return sortDir === 'asc' ? -1 : 1;
      if (va > vb) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });
  }

  let html = '<h1>Flag Registry</h1>';

  const total = data.length;
  html += '<div class="prop-bar">';
  for (const type of FLAG_TYPE_ORDER) {
    const count = data.filter(f => f.type === type).length;
    if (count > 0) {
      html += `<div class="prop-segment ${type}" style="width:${(count / total * 100).toFixed(1)}%" title="${type}: ${count} (${(count / total * 100).toFixed(0)}%)"></div>`;
    }
  }
  html += '</div>';

  html += '<div class="filter-bar" id="flag-filters">';
  html += '<span style="font-size:11px;color:var(--fg-dim);margin-right:8px">Filter:</span>';
  for (const type of FLAG_TYPE_ORDER) {
    const count = data.filter(f => f.type === type).length;
    if (count > 0) {
      html += `<button class="filter-btn active" data-type="${type}"><span class="flag-dot ${type}"></span> ${type} (${count})</button>`;
    }
  }
  html += '<span style="margin-left:auto;font-size:11px;color:var(--fg-dim)" id="flag-count"></span>';
  html += '</div>';

  html += '<select id="unit-filter" style="margin-bottom:16px;padding:4px 8px;background:var(--bg-surface);border:1px solid var(--border);color:var(--fg);font-size:12px;font-family:var(--font-mono)">';
  html += '<option value="">All units</option>';
  units.forEach(u => { html += `<option value="${u}">${u}</option>`; });
  html += '</select>';

  html += '<table class="data-table"><thead><tr>';
  const cols = [
    { key: 'type', label: 'Type' },
    { key: 'item', label: 'Item' },
    { key: 'location', label: 'File:Line' },
    { key: 'reason', label: 'Reason' },
    { key: 'unit', label: 'Unit' },
  ];
  cols.forEach(c => {
    const active = sortBy === c.key;
    html += `<th data-sort="${c.key}" style="cursor:pointer">${c.label}<span class="sort-indicator${active ? ' active' : ''}">${active ? (sortDir === 'asc' ? '▲' : '▼') : '▽'}</span></th>`;
  });
  html += '</tr></thead><tbody id="flag-rows"></tbody></table>';
  content.innerHTML = html;

  function renderRows() {
    const tbody = document.getElementById('flag-rows');
    let filtered = getFiltered();
    filtered = sortRows(filtered);
    document.getElementById('flag-count').textContent = filtered.length + ' total';

    tbody.innerHTML = filtered.map(f => {
      const route = ROUTES.find(r => r.slug === f.unitSlug);
      return `<tr class="flag-row" data-unit="${f.unitSlug || ''}">
        <td><span class="flag-dot ${f.type}" title="${f.type}"></span> <span style="font-size:11px;color:var(--fg-dim)">${f.type}</span></td>
        <td class="mono" style="font-size:11px">${esc(f.item)}</td>
        <td class="mono" style="font-size:11px;color:var(--fg-dim)">${esc(f.location)}</td>
        <td style="font-size:11px;color:var(--fg-muted);max-width:300px">${esc(f.reason)}</td>
        <td style="font-size:11px">${route ? `<a style="color:var(--accent);cursor:pointer;text-decoration:none">${esc(f.unit || '')}</a>` : esc(f.unit || '')}</td>
      </tr>`;
    }).join('');
  }

  document.getElementById('flag-filters').addEventListener('click', e => {
    const btn = e.target.closest('.filter-btn');
    if (!btn) return;
    const type = btn.dataset.type;
    if (activeFilters.has(type)) activeFilters.delete(type);
    else activeFilters.add(type);
    btn.classList.toggle('active');
    renderRows();
  });

  document.getElementById('unit-filter').addEventListener('change', renderRows);

  document.querySelector('.data-table thead').addEventListener('click', e => {
    const th = e.target.closest('th');
    if (!th || !th.dataset.sort) return;
    const key = th.dataset.sort;
    if (sortBy === key) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
    else { sortBy = key; sortDir = key === 'type' ? 'asc' : 'asc'; }
    renderRows();
  });

  document.getElementById('flag-rows').addEventListener('click', e => {
    const tr = e.target.closest('.flag-row');
    if (!tr) return;
    const slug = tr.dataset.unit;
    if (slug) {
      const route = ROUTES.find(r => r.slug === slug);
      if (route) navigate(route.path);
    }
  });

  renderRows();
}

/* ═══ INDEX PAGE ═══ */
async function renderIndex() {
  const data = loadData('data/master-index.json');
  if (!data) { content.innerHTML = '<div class="loading">Failed to load index</div>'; return; }

  const EMOJI_MAP = {
    '🟢': 'clean', '🟡': 'suspect', '🟠': 'stale', '🔴': 'dead',
    '🟣': 'coupled', '🔵': 'hardcoded', '⚪': 'incomplete'
  };

  function parseFlag(flagStr) {
    if (!flagStr) return '';
    const emoji = flagStr.trim().slice(0, 2);
    return EMOJI_MAP[emoji] || '';
  }

  let currentFiltered = data;

  let html = '<h1>Master Index</h1>';

  html += '<div class="toolbar">';
  html += '<input type="text" class="search-input" id="index-search" placeholder="Search files, units, purpose..." style="flex:1">';
  html += '<button class="btn" id="export-btn">📋 Export Markdown</button>';
  html += '</div>';

  html += '<table class="data-table"><thead><tr>';
  html += '<th>File</th><th>Unit</th><th class="mono" style="width:60px">Lines</th><th>Purpose</th><th style="width:50px">Flag</th>';
  html += '</tr></thead><tbody id="index-rows"></tbody></table>';

  const dead = data.filter(e => parseFlag(e.flag) === 'dead').slice(0, 5);
  const hardcoded = data.filter(e => parseFlag(e.flag) === 'hardcoded').slice(0, 5);
  const coupled = data.filter(e => parseFlag(e.flag) === 'coupled').slice(0, 5);

  if (dead.length || hardcoded.length || coupled.length) {
    html += '<h2 style="margin-top:40px;font-size:16px">Quick Reference</h2>';
    html += '<div class="ref-panels">';

    html += '<div class="ref-panel dead"><h3>Dead Code <span style="color:var(--flag-dead);font-family:var(--font-mono)">(' + dead.length + ')</span></h3>';
    if (dead.length) {
      dead.forEach(e => {
        html += `<div class="ref-item"><span class="flag-dot dead"></span><span class="mono">${esc(e.file)}</span><span style="color:var(--fg-dim);margin-left:auto">${esc(e.unit)}</span></div>`;
      });
    } else html += '<div style="font-size:11px;color:var(--fg-muted)">None</div>';
    html += '</div>';

    html += '<div class="ref-panel hardcoded"><h3>Hardcoded Values <span style="color:var(--flag-hardcoded);font-family:var(--font-mono)">(' + hardcoded.length + ')</span></h3>';
    if (hardcoded.length) {
      hardcoded.forEach(e => {
        html += `<div class="ref-item"><span class="flag-dot hardcoded"></span><span class="mono">${esc(e.file)}</span><span style="color:var(--fg-dim);margin-left:auto">${esc(e.unit)}</span></div>`;
      });
    } else html += '<div style="font-size:11px;color:var(--fg-muted)">None</div>';
    html += '</div>';

    html += '<div class="ref-panel coupled"><h3>Coupling Risks <span style="color:var(--flag-coupled);font-family:var(--font-mono)">(' + coupled.length + ')</span></h3>';
    if (coupled.length) {
      coupled.forEach(e => {
        html += `<div class="ref-item"><span class="flag-dot coupled"></span><span class="mono">${esc(e.file)}</span><span style="color:var(--fg-dim);margin-left:auto">${esc(e.unit)}</span></div>`;
      });
    } else html += '<div style="font-size:11px;color:var(--fg-muted)">None</div>';
    html += '</div>';

    html += '</div>';
  }

  content.innerHTML = html;

  function renderRows(query) {
    const q = (query || '').toLowerCase();
    currentFiltered = q ? data.filter(e =>
      (e.file || '').toLowerCase().includes(q) ||
      (e.unit || '').toLowerCase().includes(q) ||
      (e.purpose || '').toLowerCase().includes(q)
    ) : data;

    const tbody = document.getElementById('index-rows');
    tbody.innerHTML = currentFiltered.map(e => {
      const flagClass = parseFlag(e.flag);
      return `<tr>
        <td class="mono" style="font-size:11px">${esc(e.file)}</td>
        <td style="font-size:12px">${esc(e.unit)}</td>
        <td class="mono" style="font-size:11px;color:var(--fg-dim)">${esc(e.lines)}</td>
        <td style="font-size:12px;color:var(--fg-muted);max-width:350px">${esc(e.purpose.slice(0, 100))}</td>
        <td>${flagClass ? `<span class="flag-dot ${flagClass}"></span>` : ''}</td>
      </tr>`;
    }).join('');
  }

  document.getElementById('index-search').addEventListener('input', e => renderRows(e.target.value));

  document.getElementById('export-btn').addEventListener('click', () => {
    let md = '# Master Index — JustHireMe\n\n';
    md += '| File | Unit | Lines | Purpose |\n';
    md += '| --- | --- | --- | --- |\n';
    currentFiltered.forEach(e => {
      const f = (e.file || '').replace(/`/g, '');
      md += `| ${f} | ${e.unit || ''} | ${e.lines || ''} | ${(e.purpose || '').replace(/\n/g, ' ')} |\n`;
    });
    navigator.clipboard.writeText(md).then(() => {
      const btn = document.getElementById('export-btn');
      const orig = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => { btn.textContent = orig; }, 1500);
    }).catch(() => {
      const btn = document.getElementById('export-btn');
      btn.textContent = '✗ Failed';
      setTimeout(() => { btn.textContent = '📋 Export Markdown'; }, 1500);
    });
  });

  renderRows('');
}

/* ═══ UNIT PAGE ═══ */
const FLAG_EMOJI_MAP = { '🟢':'clean', '🟡':'suspect', '🟠':'stale', '🔴':'dead', '🟣':'coupled', '🔵':'hardcoded', '⚪':'incomplete' };

function parseFileFlag(file) {
  const raw = file.Flag || file['Overall flag'] || '';
  const emoji = raw.trim().slice(0, 2);
  return FLAG_EMOJI_MAP[emoji] || '';
}

function parseAssessment(text) {
  if (!text) return [];
  if (text.trim().charAt(0) === '|') return parseAssessmentTable(text);

  const sections = [];
  let current = null;
  for (const line of text.split('\n')) {
    const hm = line.match(/^###\s+(.+)/);
    if (hm) {
      if (current) sections.push(current);
      current = { file: hm[1].replace(/`/g, '').trim(), qas: [] };
      continue;
    }
    const qm = line.match(/^(\d+)\.\s+\*\*(.+?)\*\*(.+)/);
    if (qm) {
      if (!current) current = { file: '', qas: [] };
      current.qas.push({ num: qm[1], q: qm[2], a: qm[3].trim() });
    }
  }
  if (current) sections.push(current);
  return sections;
}

function parseAssessmentTable(text) {
  const lines = text.split('\n').filter(function(l) { return l.trim().length > 0; });
  if (lines.length < 3) return [];
  const sections = [];
  for (var i = 2; i < lines.length; i++) {
    var parts = lines[i].split('|').filter(function(p) { return p.trim().length > 0; }).map(function(p) { return p.trim(); });
    if (parts.length >= 5) {
      sections.push({
        file: parts[0].replace(/`/g, '').trim(),
        qas: [
          { num: '1', q: 'Does it need to exist?', a: parts[1] },
          { num: '2', q: 'Does what it claims?', a: parts[2] },
          { num: '3', q: 'Right place?', a: parts[3] },
          { num: '4', q: 'Breaks if deleted?', a: parts[4] },
        ]
      });
    }
  }
  return sections;
}

const SLUG_PATHS = (function buildSlugMap() {
  const m = {};
  const pairs = [
    ['backend/routes', 'backend-routes'], ['backend/config', 'backend-config'],
    ['backend/db', 'backend-db'], ['backend/evaluators', 'backend-evaluators'],
    ['backend/foundations', 'backend-foundations'], ['backend/generators', 'backend-generators'],
    ['backend/integrations', 'backend-integrations'], ['backend/main', 'backend-main'],
    ['backend/services', 'backend-services'], ['backend/scrapers', 'backend-scrapers'],
    ['backend/tests', 'backend-tests'], ['backend/agents', null], ['backend/core', 'backend-main'],
    ['backend/logger.py', 'backend-main'], ['backend/llm.py', 'backend-main'],
    ['backend/graph', 'backend-main'],
    ['src/components', 'frontend-components'], ['src/hooks', 'frontend-hooks'],
    ['src/settings', 'frontend-settings'], ['src/views', 'frontend-views'],
    ['src/App.tsx', 'frontend-core'], ['src/types.ts', 'frontend-core'],
    ['src/lib', 'frontend-core'],
    ['src-tauri', 'tauri'], ['.github', 'build-ci'],
    ['config', 'backend-config'], ['tests', 'backend-tests'], ['e2e', 'backend-tests'],
  ];
  pairs.sort((a, b) => b[0].length - a[0].length);
  pairs.forEach(p => { m[p[0]] = p[1]; });
  return m;
})();

function extractDepSlug(dep) {
  const m = dep.match(/`([^`]+)`/);
  if (!m) return '';
  const path = m[1].toLowerCase();
  for (const [prefix, slug] of Object.entries(SLUG_PATHS)) {
    if (slug && path.includes(prefix)) return slug;
  }
  return '';
}

async function renderUnit(route) {
  const data = loadData(route.data);
  if (!data) { content.innerHTML = '<div class="loading">Failed to load unit data</div>'; return; }

  const totalFlags = Object.values(data.flagCounts || {}).reduce((a, b) => a + b, 0);
  const inboundCount = data.deps?.inbound?.length || 0;
  const outboundCount = data.deps?.outbound?.length || 0;

  let html = '<div class="breadcrumb"><a data-path="/">System Overview</a> / ' + esc(data.name) + '</div>';

  html += '<div class="unit-header">';
  html += '<h1>' + esc(data.name) + '</h1>';
  html += '<div class="unit-summary">' + esc((data.summary || '').slice(0, 300)) + '</div>';
  html += '</div>';

  html += '<div class="stat-bar">';
  html += '<div class="stat-item"><span class="stat-value">' + data.fileCount + '</span><span class="stat-label">files</span></div>';
  html += '<div class="stat-divider"></div>';
  html += '<div class="stat-item"><span class="stat-value">' + totalFlags + '</span><span class="stat-label">flags</span></div>';
  html += '<div class="stat-divider"></div>';
  html += '<div class="stat-item"><span class="stat-value">' + inboundCount + '</span><span class="stat-label">inbound</span></div>';
  html += '<div class="stat-divider"></div>';
  html += '<div class="stat-item"><span class="stat-value">' + outboundCount + '</span><span class="stat-label">outbound</span></div>';
  html += '</div>';

  if (data.flagCounts) {
    html += '<div class="summary-bar">';
    for (const [type, count] of Object.entries(data.flagCounts)) {
      if (count > 0) html += `<span class="flag-badge ${type}"><span class="flag-dot ${type}"></span> ${count} ${type}</span>`;
    }
    html += '<span style="margin-left:auto;font-size:11px;color:var(--fg-dim);font-family:var(--font-mono)">' + data.group + '</span>';
    html += '</div>';
  }

  const assessments = parseAssessment(data.assessment);

  if (data.files && data.files.length > 0) {
    html += '<div class="unit-layout">';
    html += '<div><h3>Files</h3><div id="file-tree" class="file-tree-scroll">';
    data.files.forEach((f, i) => {
      const flagClass = parseFileFlag(f);
      html += `<div class="file-item${i === 0 ? ' active' : ''}" data-file-index="${i}">`;
      if (flagClass) html += `<span class="flag-dot ${flagClass}"></span>`;
      html += `<span>${esc(f.File || '')}</span>`;
      if (f.Lines) html += `<span class="file-lines">${f.Lines}</span>`;
      html += `</div>`;
    });
    html += '</div></div>';

    html += '<div><h3>Details</h3><div id="file-detail">';
    if (data.files[0]) {
      html += renderFileDetail(data.files[0], assessments);
    }
    html += '</div></div>';

    html += '<div><h3>Connections</h3>';
    html += '<div id="unit-deps-graph" class="unit-deps-graph-box"></div>';
    if (data.deps) {
      if (inboundCount > 0) {
        html += '<div style="margin-bottom:12px"><div class="deps-heading">Inbound</div>';
        data.deps.inbound.forEach(d => {
          const slug = extractDepSlug(d);
          html += `<div class="conn-item${slug ? ' clickable' : ''}" data-slug="${slug || ''}">${esc(d)}</div>`;
        });
        html += '</div>';
      }
      if (outboundCount > 0) {
        html += '<div><div class="deps-heading">Outbound</div>';
        data.deps.outbound.forEach(d => {
          const slug = extractDepSlug(d);
          html += `<div class="conn-item${slug ? ' clickable' : ''}" data-slug="${slug || ''}">${esc(d)}</div>`;
        });
        html += '</div>';
      }
    }
    html += '</div></div>';
    html += '</div>';

    if (assessments.length > 0) {
      var assessLabel = assessments.length === 1 && !assessments[0].file ? 'Assessment' : 'File Assessments';
      html += '<h2 style="margin-top:36px;font-size:16px">' + assessLabel + '</h2>';
      html += '<div class="assessments">';
      assessments.forEach(function(a) {
        var a3 = a.qas[3];
        var a0 = a.qas[0];
        var verdict = (a3 && a3.a && a3.a.toLowerCase().includes('would break')) ? 'needed' :
                      (a0 && a0.a && a0.a.toLowerCase().includes('partially')) ? 'partial' : 'needed';
        var fileLabel = a.file || 'Unit Overview';
        html += '<div class="assessment-card ' + verdict + '"><div class="assess-file">' + esc(fileLabel) + '</div>';
        a.qas.forEach(function(qa) {
          html += '<div class="assess-qa"><span class="assess-q">' + esc(qa.q) + '</span><span class="assess-a">' + esc(qa.a.slice(0, 200)) + '</span></div>';
        });
        html += '</div>';
      });
      html += '</div>';
    }

    if (data.flags && data.flags.length > 0) {
      html += '<h2 style="margin-top:36px;font-size:16px">All Flags (' + data.flags.length + ')</h2>';
      html += '<table class="data-table"><thead><tr><th style="width:34px">Prio</th><th style="width:52px">Type</th><th>Item</th><th>Location</th><th>Reason</th></tr></thead><tbody>';
      data.flags.sort((a, b) => ((a.priority || 'P3').localeCompare(b.priority || 'P3') || 0));
      data.flags.forEach(f => {
        const prioColor = f.priority === 'P0' ? 'var(--flag-dead)' : f.priority === 'P1' ? 'var(--warning)' : 'var(--fg-dim)';
        html += `<tr><td><span class="prio-badge" style="color:${prioColor}">${esc(f.priority || '')}</span></td>
          <td><span class="flag-dot ${f.type}"></span></td>
          <td class="mono" style="font-size:11px">${esc(f.item)}</td>
          <td class="mono" style="font-size:11px;color:var(--fg-dim)">${esc(f.location)}</td>
          <td style="font-size:11px;color:var(--fg-muted)">${esc(f.reason)}</td>
        </tr>`;
      });
      html += '</tbody></table>';
    }
  }

  content.innerHTML = html;

  const treeEl = document.getElementById('file-tree');
  if (treeEl) {
    treeEl.addEventListener('click', function(e) {
      const item = e.target.closest('.file-item');
      if (!item) return;
      document.querySelectorAll('.file-item').forEach(function(el) { el.classList.remove('active'); });
      item.classList.add('active');
      const idx = parseInt(item.dataset.fileIndex);
      const file = data.files[idx];
      if (file) {
        document.getElementById('file-detail').innerHTML = renderFileDetail(file, assessments);
      }
    });
  }

  content.querySelectorAll('.conn-item.clickable').forEach(function(el) {
    el.addEventListener('click', function() {
      const slug = el.dataset.slug;
      if (slug) {
        const r = ROUTES.find(function(rt) { return rt.slug === slug; });
        if (r) navigate(r.path);
      }
    });
  });

  content.querySelectorAll('.breadcrumb a').forEach(function(el) {
    el.addEventListener('click', function() { navigate(el.dataset.path); });
  });

  renderUnitDepsGraph(data.slug);
}

function renderFileDetail(file, assessments) {
  const flagClass = parseFileFlag(file);
  const fileName = file.File || '';
  const normalName = fileName.replace(/`/g, '').trim();
  const assess = assessments ? assessments.find(function(a) {
    const af = a.file.replace(/`/g, '').trim();
    return normalName.includes(af) || af.includes(normalName);
  }) : null;

  let html = '<div class="file-detail-header"><span class="mono" style="font-size:13px;font-weight:600">' + esc(fileName) + '</span>';
  if (file.Lines) html += '<span class="file-lines-badge">' + esc(file.Lines) + ' lines</span>';
  html += '</div>';

  if (file.Purpose) html += '<div class="file-purpose">' + esc(file.Purpose) + '</div>';

  if (flagClass) {
    html += '<div style="margin-bottom:8px"><span class="flag-badge ' + flagClass + '">' + flagClass + '</span></div>';
  }

  if (assess && assess.qas.length > 0) {
    html += '<div class="file-assessment">';
    assess.qas.forEach(function(qa) {
      const aLow = qa.a.toLowerCase();
      const isNeeded = aLow.includes('yes') && !aLow.includes('partially') && !aLow.includes('no');
      const isPlace = qa.q.includes('right place');
      const isBreak = qa.q.includes('break');
      let cls = 'qa-neutral';
      if (isBreak) cls = aLow.includes('would break') || aLow.includes('everything') ? 'qa-bad' : 'qa-good';
      else if (isPlace) cls = isNeeded ? 'qa-good' : 'qa-warn';
      else if (qa.q.includes('need to exist')) cls = isNeeded ? 'qa-good' : 'qa-warn';
      else cls = isNeeded ? 'qa-good' : 'qa-neutral';

      html += '<div class="file-qa"><span class="file-qa-icon ' + cls + '"></span>'
        + '<span class="file-qa-text"><strong>' + esc(qa.q) + '</strong> ' + esc(qa.a.slice(0, 200)) + '</span></div>';
    });
    html += '</div>';
  }

  return html;
}

async function renderUnitDepsGraph(slug) {
  const container = document.getElementById('unit-deps-graph');
  if (!container) return;

  const overview = loadData('data/overview.json');
  if (!overview || !overview.nodes) return;

  const center = overview.nodes.find(function(n) { return n.id === slug; });
  if (!center) { container.innerHTML = ''; return; }

  const neighborIds = new Set();
  neighborIds.add(slug);

  overview.edges.forEach(function(e) {
    const sid = e.source && (e.source.id || e.source);
    const tid = e.target && (e.target.id || e.target);
    if (sid === slug) neighborIds.add(tid);
    if (tid === slug) neighborIds.add(sid);
  });

  if (neighborIds.size < 2) { container.innerHTML = ''; return; }

  const nodes = overview.nodes.filter(function(n) { return neighborIds.has(n.id); }).map(function(n) { return Object.assign({}, n); });
  const edges = overview.edges.filter(function(e) {
    const sid = e.source && (e.source.id || e.source);
    const tid = e.target && (e.target.id || e.target);
    return neighborIds.has(sid) && neighborIds.has(tid);
  }).map(function(e) {
    return { source: e.source && (e.source.id || e.source), target: e.target && (e.target.id || e.target) };
  });

  const w = Math.max(container.clientWidth || 280, 280);
  const h = 140;

  container.innerHTML = '';
  const svg = d3.select(container).append('svg').attr('width', '100%').attr('height', h);
  const g = svg.append('g');

  const sim = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(function(d) { return d.id; }).distance(70))
    .force('charge', d3.forceManyBody().strength(-180))
    .force('center', d3.forceCenter(w / 2, h / 2))
    .force('collision', d3.forceCollide().radius(26));

  const link = g.append('g').selectAll('line').data(edges).join('line')
    .attr('stroke', 'var(--border)').attr('stroke-width', 1).attr('stroke-opacity', 0.35);

  const node = g.append('g').selectAll('g').data(nodes).join('g')
    .style('cursor', function(d) { return d.id !== slug ? 'pointer' : 'default'; })
    .on('click', function(event, d) {
      if (d.id !== slug) {
        const r = ROUTES.find(function(rt) { return rt.slug === d.id; });
        if (r) navigate(r.path);
      }
    });

  node.append('circle')
    .attr('r', function(d) { return d.id === slug ? 10 : 6; })
    .attr('fill', function(d) { return d.id === slug ? 'var(--accent)' : 'var(--bg-surface)'; })
    .attr('stroke', function(d) { return d.id === slug ? 'var(--accent)' : 'var(--fg-dim)'; })
    .attr('stroke-width', 2);

  node.append('text')
    .text(function(d) { return d.id === slug ? d.name : d.name.slice(0, 10); })
    .attr('text-anchor', 'middle')
    .attr('dy', function(d) { return d.id === slug ? 20 : 16; })
    .attr('fill', function(d) { return d.id === slug ? 'var(--accent)' : 'var(--fg-dim)'; })
    .attr('font-size', function(d) { return d.id === slug ? '9px' : '8px'; })
    .attr('font-family', 'var(--font-mono)');

  sim.on('tick', function() {
    link.attr('x1', function(d) { return d.source.x; }).attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; }).attr('y2', function(d) { return d.target.y; });
    node.attr('transform', function(d) { return 'translate(' + d.x + ',' + d.y + ')'; });
  });
}

/* ─── Helpers ─── */
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div');
  d.textContent = String(s);
  return d.innerHTML;
}

/* ─── Init ─── */
loadBranch();
const initialPath = window.location.pathname || '/';
renderSidebar(initialPath);
renderPage(initialPath);
})();
