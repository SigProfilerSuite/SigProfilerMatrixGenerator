/* SigProfilerMatrixGenerator Workbench. No framework and no build step: this
   ships inside a Python package. User-supplied strings only ever reach the
   page through textContent. */

'use strict';

const $ = (id) => document.getElementById(id);
const el = (tag, cls, text) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = text;
  return n;
};

const state = {
  env: null, jobs: [], jobId: null, logOffset: 0, logTail: '', step: 0, steps: 3,
  input: null, inputPath: '', projectAuto: true, view: 'run', genomes: null, examples: [],
  results: null, resultsPath: null, ctx: null, file: null,
  job: null, outCheck: null, replaceOutput: false, deleting: null,
};

/* ------------------------------------------------------------- helpers */

async function api(path, opts) {
  const r = await fetch(path, opts);
  let body;
  try { body = await r.json(); } catch (e) { throw new Error(`${r.status} ${r.statusText}`); }
  if (!r.ok || body.ok === false) throw new Error(body.error || `${r.status} ${r.statusText}`);
  return body;
}
const get = (path) => api(path);
// Every action must carry this launch's token, which only this page has.
const TOKEN = document.querySelector('meta[name="workbench-token"]').content;
const post = (path, payload) => api(path, {
  method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Dashboard-Token': TOKEN },
  body: JSON.stringify(payload || {}),
});
const q = (params) => new URLSearchParams(params).toString();

const num = (v) => (v === null || v === undefined || Number.isNaN(v)) ? '–'
  : Number(v).toLocaleString();

function bytes(n) {
  if (n === null || n === undefined) return '–';
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
  return `${n.toFixed(i ? 1 : 0)} ${u[i]}`;
}

function clock(sec) {
  if (sec === null || sec === undefined || Number.isNaN(sec)) return '';
  const s = Math.max(0, Math.round(sec));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60);
  return h ? `${h}h ${m}m` : (m ? `${m}m ${s % 60}s` : `${s}s`);
}

const shortPath = (p, max) => {
  const s = String(p || '');
  return s.length <= max ? s : '…' + s.slice(-(max - 1));
};
const baseName = (p) => String(p || '').replace(/[\\/]+$/, '').split(/[\\/]/).pop();
const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
const joinPath = (dir, name) => String(dir).replace(/[\\/]+$/, '') + '/' + name;

function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

/* Text with inline emphasis, built without innerHTML: parts are plain strings,
   or {b: text} for bold, or {mono: text} for a path. */
function rich(node, parts) {
  parts.forEach((p) => {
    if (typeof p === 'string') node.appendChild(document.createTextNode(p));
    else if (p.b !== undefined) node.appendChild(el('b', null, p.b));
    else if (p.mono !== undefined) node.appendChild(el('span', 'mono', p.mono));
    else if (p.node) node.appendChild(p.node);
  });
  return node;
}
const noteBox = (kind, parts) => rich(el('div', `note-box ${kind || ''}`), parts);

function pill(kind, text) { return el('span', `pill ${kind}`, text); }

let toastTimer = null;
// action: optional { label, fn }, a button in the toast (Undo, say).
function toast(text, action) {
  $('toastText').textContent = text;
  const btn = $('toastAction');
  btn.classList.toggle('hidden', !action);
  btn.onclick = null;
  if (action) {
    btn.textContent = action.label;
    btn.onclick = () => { $('toast').classList.add('hidden'); action.fn(); };
  }
  $('toast').classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $('toast').classList.add('hidden'), action ? 9000 : 3500);
}

// "A", "A and B", "A, B and C"
function listing(items) {
  return items.length < 3 ? items.join(' and ')
    : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}

function whenAt(sec) {
  return new Date(sec * 1000).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

// The server owns each picker's kind and title; the page only names which one.
async function pickPath(purpose) {
  const r = await post('/api/dialog', { purpose });
  return r.path;
}

/* --------------------------------------------------------------- theme */

const THEMES = ['sandiego', 'ualbany', 'sigprofilersuite', 'night'];

function currentTheme() {
  const set = document.documentElement.getAttribute('data-theme');
  if (THEMES.includes(set)) return set;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'night' : 'sandiego';
}

function applyTheme(name) {
  if (!THEMES.includes(name)) return;
  document.documentElement.setAttribute('data-theme', name);
  try { localStorage.setItem('spmg-theme', name); } catch (e) { /* private mode */ }
  $('themeSel').value = currentTheme();
}

(function initTheme() {
  let saved = null;
  try { saved = localStorage.getItem('spmg-theme'); } catch (e) { saved = null; }
  if (THEMES.includes(saved)) document.documentElement.setAttribute('data-theme', saved);
  $('themeSel').value = currentTheme();
  $('themeSel').addEventListener('change', (e) => applyTheme(e.target.value));
})();

/* ----------------------------------------------------------- tab router */

const VIEWS = ['run', 'monitor', 'results', 'help'];
function show(view) {
  state.view = view;
  if (view === 'run' && state.input) checkOutput();
  VIEWS.forEach((v) => {
    $(`view-${v}`).classList.toggle('hidden', v !== view);
    $(`tab-${v}`).setAttribute('aria-selected', String(v === view));
  });
  $('contextLabel').textContent = view === 'results' && state.resultsPath
    ? shortPath(state.resultsPath, 64) : '';
  if (view === 'results' && state.ctx && window.Plotly) {
    const node = $('chart');
    if (node.classList.contains('js-plotly-plot')) window.Plotly.Plots.resize(node);
  }
}
VIEWS.forEach((v) => $(`tab-${v}`).addEventListener('click', () => show(v)));

/* -------------------------------------------------------------- about ? */

function wireAbout(button) {
  button.addEventListener('click', () => {
    const panel = $(button.getAttribute('aria-controls'));
    const open = panel.hasAttribute('hidden');
    panel.toggleAttribute('hidden', !open);
    button.setAttribute('aria-expanded', String(open));
  });
}
document.querySelectorAll('.about-btn').forEach(wireAbout);

function fillAbout(panel, entries) {
  clear(panel);
  const dl = el('dl');
  entries.forEach(([term, text]) => { dl.appendChild(el('dt', null, term)); dl.appendChild(el('dd', null, text)); });
  panel.appendChild(dl);
}

/* ------------------------------------------------------------------ env */

const SBS_COLORS = ['#03BCEE', '#010101', '#E32926', '#CAC9C9', '#A1CE63', '#EBC6C4'];

(function welcomeArt() {
  const art = $('welcomeArt');
  let seed = 7;
  const rand = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
  SBS_COLORS.forEach((color, k) => {
    for (let i = 0; i < 8; i++) {
      const bar = el('i');
      const peak = k === 2 && (i === 2 || i === 6) ? 0.95 : 0.15 + rand() * (k === 2 ? 0.6 : 0.45);
      bar.style.height = `${Math.round(peak * 100)}%`;
      bar.style.background = color;
      art.appendChild(bar);
    }
  });
})();

async function loadEnv() {
  const env = await get('/api/env');
  state.env = env;
  const v = String(env.version || '').split('+')[0];
  $('envVersion').textContent = v ? `v${v}` : '';

  state.examples = env.examples || [];
  if ($('volumePath').value.trim()) await refreshGenomes();
  else applyGenomes(env.genomes);
  return env;
}

function renderExamples() {
  const box = $('examples');
  clear(box);
  // Examples that can run now (genome installed) first.
  const ready = (ex) => (genomeInstalled(ex.reference_genome) ? 0 : 1);
  [...(state.examples || [])].sort((a, b) => ready(a) - ready(b)).forEach((ex) => {
    const row = el('div', 'inline');
    const btn = el('button', 'btn', `Try the ${ex.label}`);
    btn.type = 'button';
    btn.dataset.example = ex.id;
    btn.addEventListener('click', () => useExample(ex));
    row.appendChild(btn);
    const ready = genomeInstalled(ex.reference_genome);
    row.appendChild(el('span', 'hint',
      `${ex.description}, ${ex.reference_genome}${ready ? '' : ' (installs the genome first)'}`));
    box.appendChild(row);
  });
}

async function useExample(ex) {
  $('outputPath').value = ex.output_directory;
  setGenome(ex.reference_genome);
  $('projectName').value = ex.project;
  state.projectAuto = false;
  await setInput(ex.path);
  $('inputCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/* Genome status always describes the install folder the run would use: the
   Advanced field when it is set, otherwise the folder the app started with. */
function applyGenomes(g) {
  state.genomes = { available: g.available, installed: g.installed, assemblies: g.assemblies || {} };
  const { available, installed } = state.genomes;
  const pillNode = $('envPill');
  pillNode.className = `pill ${installed.length ? 'good' : 'warn'}`;
  pillNode.textContent = installed.length
    ? `ready · ${installed.length} genome${installed.length === 1 ? '' : 's'}`
    : 'no genome installed';
  renderGenomeList(installed);
  fillGenomeSelect(available, installed);
  renderExamples();
}

let genomeSeq = 0;
async function refreshGenomes() {
  const seq = ++genomeSeq;
  const volume = $('volumePath').value.trim();
  try {
    const g = await get(`/api/genomes?${q({ volume })}`);
    if (seq === genomeSeq) applyGenomes(g);
  } catch (e) {
    if (seq === genomeSeq) toast(e.message);
  }
}
$('volumePath').addEventListener('change', refreshGenomes);
$('volumePath').addEventListener('keydown', (e) => { if (e.key === 'Enter') refreshGenomes(); });

function renderGenomeList(installed) {
  const list = $('genomeList');
  clear(list);
  $('genomeCount').textContent = installed.length ? String(installed.length) : '';
  const volume = $('volumePath').value.trim();
  if (volume) {
    const where = el('p', 'hint', `in ${shortPath(volume, 34)}`);
    where.title = volume;
    where.style.margin = '0 9px 4px';
    list.appendChild(where);
  }
  if (!installed.length) {
    list.appendChild(el('p', 'empty', 'None installed yet. Pick one in New run.'));
    return;
  }
  installed.forEach((name) => {
    const row = el('button', 'item');
    row.type = 'button';
    row.title = `Use ${name} for the next run`;
    row.appendChild(el('span', 'dot good'));
    const txt = el('span', 'txt');
    txt.appendChild(el('span', 'name mono', name));
    row.appendChild(txt);
    row.addEventListener('click', () => { setGenome(name); show('run'); });
    list.appendChild(row);
  });
}

function fillGenomeSelect(available, installed) {
  const sel = $('genomeSel');
  const keep = sel.value;
  clear(sel);
  const groups = [['Installed', installed], ['Not installed', available.filter((g) => !installed.includes(g))]];
  groups.forEach(([label, names]) => {
    if (!names.length) return;
    const og = el('optgroup');
    og.label = label;
    names.forEach((name) => {
      const o = el('option', null, installed.includes(name) ? name : `${name}  (not installed)`);
      o.value = name;
      og.appendChild(o);
    });
    sel.appendChild(og);
  });
  const fallback = installed[0] || (available.includes('GRCh38') ? 'GRCh38' : available[0]);
  sel.value = available.includes(keep) ? keep : fallback;
  updateGenomeStatus();
}

/* -------------------------------------------------------------- new run */

function setGenome(name) {
  $('genomeSel').value = name;
  updateGenomeStatus();
}

function genomeInstalled(name) {
  return !!state.genomes && state.genomes.installed.includes(name);
}

function updateGenomeStatus() {
  const name = $('genomeSel').value;
  const box = $('genomeStatus');
  clear(box);
  if (!name) return;
  if (genomeInstalled(name)) {
    box.appendChild(pill('good', 'installed'));
  } else {
    box.appendChild(pill('warn', 'not installed'));
    const btn = el('button', 'btn sm', `Install ${name} now`);
    btn.type = 'button';
    btn.addEventListener('click', () => installGenome(name, btn));
    box.appendChild(btn);
  }
  updateGenomeMatch();
  markDone();
}
$('genomeSel').addEventListener('change', updateGenomeStatus);

// The calls name the assembly they were made against (VCF ##reference, the
// genome column of simple text, NCBI_Build in a MAF). A different genome
// fails most reference-base checks, and the run stops, so say so up front.
function updateGenomeMatch() {
  const box = $('genomeMatch');
  clear(box);
  const declared = state.input && state.input.assembly;
  const chosen = $('genomeSel').value;
  if (!declared || !chosen || !state.genomes) return;
  const assemblyOf = (name) => state.genomes.assemblies[name] || name;
  if (assemblyOf(chosen) === declared) return;
  const note = el('div', 'note-box warn row after-grid');
  note.appendChild(rich(el('span'), [
    'These calls say they were made against ', { b: declared }, ', but ', { b: chosen },
    ' is chosen. Each mutation is checked against the genome\'s reference base, so most would ',
    'not match, and the run stops when more than 30% are skipped.']));
  if (state.genomes.available.includes(declared)) {
    const use = el('button', 'btn sm', `Use ${declared}`);
    use.type = 'button';
    use.addEventListener('click', () => setGenome(declared));
    note.appendChild(use);
  }
  box.appendChild(note);
}
$('autoInstall').addEventListener('change', markDone);

async function installGenome(name, btn) {
  if (btn) btn.disabled = true;
  try {
    const { job } = await post('/api/genomes/install', { genome: name, volume: $('volumePath').value || null });
    toast(`Installing ${name}. It downloads once and runs in the background.`);
    await refreshJobs();
    selectJob(job.id);
    show('monitor');
  } catch (e) {
    toast(e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function suggestProject(path) {
  const name = baseName(path).replace(/[^A-Za-z0-9_-]+/g, '_').replace(/^_+|_+$/g, '');
  return name || 'project';
}

function folderIcon() {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 16 16');
  svg.setAttribute('fill', 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', '1.5');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS(ns, 'path');
  path.setAttribute('d', 'M1.5 4.5v8a1 1 0 0 0 1 1h11a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1H8L6.5 3h-4a1 1 0 0 0-1 1z');
  svg.appendChild(path);
  return svg;
}

let inputSeq = 0;
async function setInput(path) {
  path = String(path || '').trim();
  const seq = ++inputSeq;
  state.inputPath = path;
  const chosen = $('inputChosen');
  const info = $('inputInfo');
  clear(chosen); clear(info);
  state.input = null;
  updateGenomeMatch(); markDone(); updateOutPreview(); updateSummary();
  if (!path) return;

  chosen.appendChild(folderIcon());
  chosen.appendChild(rich(el('div'), [{ b: baseName(path) }, { node: el('span', 'in', path) }]));
  const loading = el('div', 'inline muted');
  loading.style.marginTop = '10px';
  loading.appendChild(el('span', 'spin'));
  loading.appendChild(el('span', null, 'Reading the folder…'));
  info.appendChild(loading);

  try {
    const r = await get(`/api/inspect?${q({ path })}`);
    if (seq !== inputSeq) return;
    state.input = r;
    $('inputPath').value = '';
    $('inputPath').placeholder = 'or paste a different folder path, then Enter';
    clear(info);
    const tiles = el('div', 'tiles in-card');
    const preview = r.samples_preview.join(', ') + (r.sample_count > r.samples_preview.length ? ', …' : '');
    [['Format', r.format, r.format === 'Txt' ? 'simple text' : ''],
     ['Samples', num(r.sample_count), preview],
     ['Mutations', num(r.records), r.indels === undefined ? 'calls read' : `${num(r.indels)} indel${r.indels === 1 ? '' : 's'}`],
     ['Files', num(r.file_count), r.source !== r.path ? 'in input/' : '']].forEach(([k, v, d]) => {
      const t = el('div', 'tile');
      t.appendChild(el('div', 'k', k));
      t.appendChild(el('div', 'v', v));
      const dn = el('div', 'd', d || ' ');
      dn.title = d || '';
      t.appendChild(dn);
      tiles.appendChild(t);
    });
    info.appendChild(tiles);
    if (r.other_count) {
      const extra = noteBox('warn', [
        `${r.other_count} other file${r.other_count === 1 ? ' is' : 's are'} in this folder (`,
        { mono: r.other_files.join(', ') }, r.other_count > r.other_files.length ? ', …' : '',
        '). The run reads every file, so move them out if they are not mutation calls.']);
      extra.style.marginTop = '10px';
      info.appendChild(extra);
    }
    if (state.projectAuto || !$('projectName').value.trim()) {
      $('projectName').value = suggestProject(r.source !== r.path ? r.path : path);
      state.projectAuto = true;
    }
  } catch (e) {
    if (seq !== inputSeq) return;
    $('inputPath').value = path;
    clear(info);
    const box = noteBox('crit', [e.message]);
    box.style.marginTop = '10px';
    info.appendChild(box);
  }
  updateGenomeMatch(); updateIdNote(); markDone(); updateOutPreview(); updateSummary();
}

// ID89 and ID476 classify indels. Calls without any still get those two
// files, all zeros, and no ID83 at all: say so before the run.
function updateIdNote() {
  const box = $('idNote');
  clear(box);
  const wanted = $('optId89').checked || $('optId476').checked;
  if (!wanted || !state.input || state.input.indels !== 0) return;
  const note = noteBox('warn', [{ b: 'These calls hold no insertions or deletions. ' },
    'The run makes no ID matrices from them: no ID83, and ID89 and ID476 would be all zeros.']);
  note.classList.add('after-grid');
  box.appendChild(note);
}
['optId89', 'optId476'].forEach((id) => $(id).addEventListener('change', updateIdNote));

$('inputChoose').addEventListener('click', async () => {
  const btn = $('inputChoose');
  btn.disabled = true;
  try {
    const path = await pickPath('input');
    if (path) await setInput(path);
  } catch (e) { toast(e.message); } finally { btn.disabled = false; }
});
// A recognised path is cleared from this box (the Input card shows it), so an
// empty value here means "nothing new typed", never "forget the input".
$('inputPath').addEventListener('keydown', (e) => {
  const v = e.target.value.trim();
  if (e.key === 'Enter' && v) setInput(v);
});
$('inputPath').addEventListener('change', (e) => {
  const v = e.target.value.trim();
  if (v && v !== state.inputPath) setInput(v);
});
$('projectName').addEventListener('input', () => {
  state.projectAuto = false; markDone(); updateSummary();
});
$('outputPath').addEventListener('input', updateOutPreview);

function wireBrowse(buttonId, inputId, purpose, after) {
  $(buttonId).addEventListener('click', async () => {
    try {
      const path = await pickPath(purpose);
      if (path) { $(inputId).value = path; if (after) after(); }
    } catch (e) { toast(e.message); }
  });
}
wireBrowse('outputBrowse', 'outputPath', 'output', updateOutPreview);
wireBrowse('bedBrowse', 'bedPath', 'bed');
wireBrowse('volumeBrowse', 'volumePath', 'volume', refreshGenomes);

function outputDir() {
  const custom = $('outputPath').value.trim();
  if (custom) return custom;
  return state.inputPath ? joinPath(state.inputPath, 'output') : '';
}

function updateOutPreview() {
  const box = $('outPreview');
  clear(box);
  const out = outputDir();
  clearTimeout(outTimer);
  outTimer = setTimeout(checkOutput, 250);
  if (!out) { box.textContent = 'The output folder appears here once an input is chosen.'; return; }
  rich(box, ['Matrices will be written to ', { mono: out },
    ', with a subfolder (SBS, DBS, ID) for each type of mutation found.']);
}

// A run writing into a folder that already holds results would leave the
// earlier run's files (plots it drew, matrices it alone made) beside its own,
// looking like part of it. So such a folder needs a choice: a new folder, or
// replacing what is there.
let outTimer = null;
let outSeq = 0;
async function checkOutput() {
  const out = outputDir();
  const seq = ++outSeq;
  if (!out) { state.outCheck = null; renderOutCheck(); return; }
  let r;
  try { r = await get(`/api/output?${q({ path: out, input: state.inputPath || '' })}`); }
  catch (e) { r = null; }
  if (seq !== outSeq) return;
  if (!r || !state.outCheck || state.outCheck.path !== r.path) state.replaceOutput = false;
  state.outCheck = r;
  renderOutCheck();
  updateSummary();
}

function renderOutCheck() {
  const box = $('outCheck');
  clear(box);
  const r = state.outCheck;
  if (!r || !r.found) return;
  const what = listing(r.folders);
  if (state.replaceOutput) {
    const note = el('div', 'note-box warn row after-grid');
    note.appendChild(rich(el('span'), [{ b: 'The earlier results here are deleted when the run starts' },
      ` (${what}, with their logs and SigProfilerMatrixGenerator's copies of the input). `,
      'Other files in this folder are kept. This cannot be undone.']));
    const keep = el('button', 'btn sm', 'Keep them');
    keep.type = 'button';
    keep.addEventListener('click', () => { state.replaceOutput = false; renderOutCheck(); updateSummary(); });
    note.appendChild(keep);
    box.appendChild(note);
    return;
  }
  const note = el('div', 'note-box warn after-grid');
  note.appendChild(rich(el('p'), [{ b: 'This folder already holds results from an earlier run' },
    ` (${what}). Files the new run does not rewrite would stay beside its own and look like part of it.`]));
  const acts = el('div', 'actions');
  if (r.suggested) {
    const fresh = el('button', 'btn sm primary', `Use a new folder: ${baseName(r.suggested)}`);
    fresh.type = 'button';
    fresh.dataset.choice = 'new';
    fresh.addEventListener('click', () => { $('outputPath').value = r.suggested; updateOutPreview(); });
    acts.appendChild(fresh);
  }
  const replace = el('button', 'btn sm danger', 'Replace the earlier results');
  replace.type = 'button';
  replace.dataset.choice = 'replace';
  replace.disabled = !!r.replace_problem;
  replace.addEventListener('click', () => { state.replaceOutput = true; renderOutCheck(); updateSummary(); });
  acts.appendChild(replace);
  note.appendChild(acts);
  if (r.replace_problem) note.appendChild(rich(el('p'), [r.replace_problem]));
  box.appendChild(note);
}

function markDone() {
  $('inputCard').classList.toggle('done', !!state.input);
  $('projectCard').classList.toggle('done', !!$('projectName').value.trim());
  const g = $('genomeSel').value;
  $('genomeCard').classList.toggle('done', !!g && (genomeInstalled(g) || $('autoInstall').checked));
}

function updateSummary() {
  const s = $('launchSummary');
  clear(s);
  if (!state.input) { s.textContent = 'Choose an input folder to start.'; return; }
  rich(s, [{ b: $('projectName').value.trim() || 'project' }, ` · ${num(state.input.sample_count)} samples · `,
    { b: $('genomeSel').value }, replacing() ? ' · replaces earlier results' : '']);
}
$('genomeSel').addEventListener('change', updateSummary);

const replacing = () => !!(state.replaceOutput && state.outCheck && state.outCheck.found);

function runConfig() {
  const config = {
    project: $('projectName').value.trim(),
    reference_genome: $('genomeSel').value,
    path_to_input_files: state.inputPath || '',
    exome: $('optExome').checked,
    bed_file: $('bedPath').value.trim() || null,
    tsb_stat: $('optTsb').checked,
    plot: $('optPlot').checked,
    output_directory: $('outputPath').value.trim() || null,
    volume: $('volumePath').value.trim() || null,
    install_genome_if_missing: $('autoInstall').checked,
    replace_existing: replacing(),
  };
  const indel = [];
  if ($('optId89').checked) indel.push('89');
  if ($('optId476').checked) indel.push('476');
  if (indel.length) config.indel_contexts = indel;
  return config;
}

$('startBtn').addEventListener('click', async () => {
  const errorBox = $('startError');
  clear(errorBox);
  const config = runConfig();
  const missing = [];
  if (!config.path_to_input_files) missing.push('an input folder');
  if (!config.project) missing.push('a project name');
  if (!config.reference_genome) missing.push('a reference genome');
  if (missing.length) {
    errorBox.appendChild(noteBox('crit', [{ b: 'Not ready yet. ' }, `Choose ${missing.join(', ')} first.`]));
    return;
  }
  if (!state.input) {
    errorBox.appendChild(noteBox('crit', [{ b: 'The input folder was not recognised. ' },
      'Fix the problem shown in the Input card, then start again.']));
    return;
  }
  if (!genomeInstalled(config.reference_genome) && !config.install_genome_if_missing) {
    errorBox.appendChild(noteBox('crit', [{ b: `${config.reference_genome} is not installed. ` },
      'Install it from the genome card, or tick the box that installs it when the run starts.']));
    return;
  }
  await checkOutput();  // the folder may have changed since it was last looked at
  if (state.outCheck && state.outCheck.found && !state.replaceOutput) {
    errorBox.appendChild(noteBox('crit', [{ b: 'The output folder already holds results from an earlier run. ' },
      'Choose a new folder, or replace the earlier results, in the Project card.']));
    $('projectCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }
  config.replace_existing = replacing();
  const btn = $('startBtn');
  btn.disabled = true;
  try {
    const { job } = await post('/api/run', { config, name: config.project });
    state.replaceOutput = false;
    checkOutput();
    toast(`Started ${config.project}.`);
    await refreshJobs();
    selectJob(job.id);
    show('monitor');
  } catch (e) {
    errorBox.appendChild(noteBox('crit', [{ b: 'The run did not start. ' }, e.message]));
  } finally {
    btn.disabled = false;
  }
});

$('newRunBtn').addEventListener('click', () => show('run'));

/* --------------------------------------------------------------- jobs */

const STATUS_PILL = { running: 'live', done: 'good', failed: 'crit', stopped: 'flat' };
const STATUS_DOT = { running: 'live', done: 'good', failed: 'crit', stopped: '' };
const RUN_STEPS = ['Reference genome', 'Matrices', 'Summary'];

function elapsed(job) {
  if (job.elapsed_seconds !== undefined) return job.elapsed_seconds;
  if (job.status === 'running') return Date.now() / 1000 - job.created_at;
  return null;
}

function jobMeta(job) {
  const parts = [job.status];
  if (job.kind === 'run' && job.reference_genome) parts.push(job.reference_genome);
  const t = clock(elapsed(job));
  if (t && job.status !== 'stopped') parts.push(t);
  return parts.join(' · ');
}

async function refreshJobs() {
  let r;
  try { r = await get('/api/jobs'); } catch (e) { return; }
  const before = new Map(state.jobs.map((j) => [j.id, j.status]));
  state.jobs = r.jobs;
  renderJobList();
  const live = state.jobs.filter((j) => j.status === 'running').length;
  $('liveCount').textContent = String(live);
  $('liveCount').classList.toggle('hidden', !live);
  const finishedInstall = state.jobs.some((j) => j.kind === 'install' && before.get(j.id) === 'running' && j.status !== 'running');
  if (finishedInstall) refreshGenomes();
}

function renderJobList() {
  const list = $('jobList');
  clear(list);
  if (!state.jobs.length) { list.appendChild(el('p', 'empty', 'No runs yet.')); return; }
  state.jobs.forEach((job) => {
    const wrap = el('div', 'runrow');
    wrap.dataset.job = job.id;
    const row = el('button', `item${job.id === state.jobId ? ' on' : ''}`);
    row.type = 'button';
    row.appendChild(el('span', `dot ${STATUS_DOT[job.status] || ''}`));
    const txt = el('span', 'txt');
    txt.appendChild(el('span', 'name', job.name));
    txt.appendChild(el('span', 'meta', jobMeta(job)));
    row.appendChild(txt);
    row.addEventListener('click', () => { selectJob(job.id); show('monitor'); });
    wrap.appendChild(row);
    if (job.status !== 'running') {
      wrap.classList.add('has-actions');
      if (job.kind === 'run') {
        const del = el('button', 'rm del');
        del.type = 'button';
        del.title = 'Delete this run and its results for good';
        del.setAttribute('aria-label', `Delete ${job.name}`);
        del.appendChild(trashIcon());
        del.addEventListener('click', (e) => { e.stopPropagation(); askDelete(job); });
        wrap.appendChild(del);
      }
      const hide = el('button', 'rm hide', '×');
      hide.type = 'button';
      hide.title = 'Remove from the list (its results stay on disk)';
      hide.setAttribute('aria-label', `Remove ${job.name} from the list`);
      hide.addEventListener('click', (e) => { e.stopPropagation(); removeFromList(job); });
      wrap.appendChild(hide);
    }
    list.appendChild(wrap);
  });
}

function trashIcon() {
  const ns = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 16 16');
  svg.setAttribute('width', '13');
  svg.setAttribute('height', '13');
  svg.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS(ns, 'path');
  path.setAttribute('fill', 'currentColor');
  path.setAttribute('d', 'M6 1h4l.5 1H14v1.5H2V2h3.5L6 1zm-2.5 3.5h9l-.7 9.6c-.06.8-.7 1.4-1.5 1.4H5.7c-.8 0-1.44-.6-1.5-1.4L3.5 4.5zm3 1.5v7h1.2V6H6.5zm2.8 0v7h1.2V6H9.3z');
  svg.appendChild(path);
  return svg;
}

function leaveMonitor() {
  state.jobId = null;
  state.job = null;
  clearInterval(jobTimer);
  $('monitorBody').classList.add('hidden');
  $('monitorEmpty').classList.remove('hidden');
}

// Off the list only: the record and the results stay, and Undo brings it back.
async function removeFromList(job) {
  try { await post(`/api/jobs/${job.id}/hide`); } catch (e) { toast(e.message); return; }
  if (state.jobId === job.id) leaveMonitor();
  await refreshJobs();
  toast(`Removed ${job.name} from the list. Its results stay on disk.`, {
    label: 'Undo',
    fn: async () => {
      try { await post(`/api/jobs/${job.id}/unhide`); await refreshJobs(); }
      catch (e) { toast(e.message); }
    },
  });
}

// For good: asks first, saying exactly what goes.
async function askDelete(job) {
  let plan;
  try { plan = await get(`/api/jobs/${job.id}/delete-preview`); } catch (e) { toast(e.message); return; }
  state.deleting = { job, plan };
  $('deleteTitle').textContent = `Delete ${job.name} for good?`;
  const msg = $('deleteText');
  clear(msg);
  if (plan.deletes_files) {
    msg.appendChild(rich(el('p'), ['This deletes the run and its results: ',
      { b: `${num(plan.files)} file${plan.files === 1 ? '' : 's'}, ${bytes(plan.bytes)}` },
      ' that SigProfilerMatrixGenerator wrote (matrices, plots, logs and its copies of the input) in']));
    msg.appendChild(el('p', 'mono path', plan.output_dir));
    msg.appendChild(el('p', null, 'Other files in that folder are kept.'));
  } else {
    msg.appendChild(el('p', null, 'This deletes the run from the list for good.'));
    if (plan.kept_because) msg.appendChild(el('p', null, plan.kept_because));
  }
  msg.appendChild(rich(el('p'), [{ b: 'This cannot be undone' },
    ': the files do not go to the Trash or Recycle Bin. To only take the run off the list, use × (Remove from list) instead.']));
  $('deleteGo').disabled = false;
  $('deleteDialog').showModal();
}
$('deleteCancel').addEventListener('click', () => $('deleteDialog').close());
$('deleteGo').addEventListener('click', async () => {
  const { job, plan } = state.deleting || {};
  if (!job) return;
  $('deleteGo').disabled = true;
  try {
    const r = await post(`/api/jobs/${job.id}/delete`);
    $('deleteDialog').close();
    if (state.jobId === job.id) leaveMonitor();
    await refreshJobs();
    if (plan.output_dir && state.resultsPath && r.removed) {
      $('resultsBody').classList.add('hidden');
      $('resultsEmpty').classList.remove('hidden');
      state.resultsPath = null;
    }
    toast(r.removed ? `Deleted ${job.name} and its results.` : `Deleted ${job.name}.`);
  } catch (e) {
    $('deleteGo').disabled = false;
    toast(e.message);
  }
});
$('hideBtn').addEventListener('click', () => { if (state.job) removeFromList(state.job); });
$('deleteBtn').addEventListener('click', () => { if (state.job) askDelete(state.job); });

let jobTimer = null;
function selectJob(id) {
  state.jobId = id;
  state.logOffset = 0;
  state.logTail = '';
  state.step = 0;
  clear($('jobLog'));
  $('monitorEmpty').classList.add('hidden');
  $('monitorBody').classList.remove('hidden');
  renderJobList();
  clearInterval(jobTimer);
  pollJob();
  jobTimer = setInterval(pollJob, 1000);
}

function appendLog(text) {
  const log = $('jobLog');
  const lines = (state.logTail + text).split('\n');
  state.logTail = lines.pop();
  lines.forEach((line) => {
    const m = line.match(/^== step (\d+)\/(\d+): (.*)$/);
    let node;
    if (m) {
      state.step = Math.max(state.step, Number(m[1]));
      state.steps = Number(m[2]);
      node = el('span', 'step-line', line);
    } else if (/Traceback|Error|error:/.test(line)) {
      node = el('span', 'err-line', line);
    } else {
      node = document.createTextNode(line);
    }
    log.appendChild(node);
    log.appendChild(document.createTextNode('\n'));
  });
  if ($('followLog').checked) log.scrollTop = log.scrollHeight;
}

async function pollJob() {
  const id = state.jobId;
  if (!id) return;
  let job;
  try { job = (await get(`/api/jobs/${id}`)).job; } catch (e) { return; }
  if (!job || id !== state.jobId) return;
  try {
    const chunk = await get(`/api/jobs/${id}/log?offset=${state.logOffset}`);
    if (id !== state.jobId) return;
    if (chunk.text) appendLog(chunk.text);
    state.logOffset = chunk.offset;
  } catch (e) { /* log not written yet */ }
  renderJob(job);
  if (job.status !== 'running') {
    clearInterval(jobTimer);
    if (state.logTail) { appendLog('\n'); }
    refreshJobs();
  }
}

function renderJob(job) {
  $('jobTitle').textContent = job.name;
  const p = $('jobPill');
  p.className = `pill ${STATUS_PILL[job.status] || 'flat'}`;
  p.textContent = job.status;
  $('jobNote').textContent = job.kind === 'install' ? 'reference genome install' : `run ${job.id}`;
  state.job = job;
  $('stopBtn').classList.toggle('hidden', job.status !== 'running');
  $('hideBtn').classList.toggle('hidden', job.status === 'running');
  $('deleteBtn').classList.toggle('hidden', job.status === 'running' || job.kind !== 'run');
  $('jobClock').textContent = clock(elapsed(job));

  const bar = $('jobBar');
  bar.className = '';
  const steps = $('jobSteps');
  clear(steps);
  const install = job.kind === 'install';
  const labels = install ? [`Download and install ${job.reference_genome || ''}`] : RUN_STEPS;
  const total = install ? 1 : state.steps;
  const current = install ? 1 : Math.max(state.step, 1);

  if (job.status === 'done') { bar.style.width = '100%'; bar.classList.add('done'); }
  else if (job.status === 'failed') { bar.style.width = `${Math.max(8, (current - 0.5) / total * 100)}%`; bar.classList.add('failed'); }
  else if (job.status === 'running' && install) { bar.classList.add('indeterminate'); }
  else if (job.status === 'running') { bar.style.width = `${Math.max(4, (current - 0.5) / total * 100)}%`; }
  else { bar.style.width = `${(current - 1) / total * 100}%`; }

  const phase = $('jobPhase');
  clear(phase);
  if (job.status === 'running') rich(phase, [{ b: `Step ${current} of ${total}` }, `: ${labels[current - 1] || ''}`]);
  else if (job.status === 'done') rich(phase, [{ b: 'Finished' }]);
  else if (job.status === 'failed') rich(phase, [{ b: 'Failed' }, ` at step ${current} of ${total}`]);
  else rich(phase, [{ b: 'Stopped' }]);

  labels.forEach((label, i) => {
    const n = i + 1;
    let cls = '';
    if (job.status === 'done' || n < current) cls = 'done';
    else if (n === current) cls = job.status === 'failed' ? 'failed' : (job.status === 'running' ? 'active' : '');
    const s = el('div', `s ${cls}`);
    s.appendChild(el('span', 'n', cls === 'done' ? '✓' : String(n)));
    s.appendChild(el('span', null, label));
    steps.appendChild(s);
  });

  const facts = $('jobFacts');
  clear(facts);
  const rows = install
    ? [['Genome', job.reference_genome], ['Started', new Date(job.created_at * 1000).toLocaleString()]]
    : [['Project', job.project], ['Genome', job.reference_genome], ['Input', job.input, true],
       ['Output', job.output_dir, true], ['Started', new Date(job.created_at * 1000).toLocaleString()]];
  rows.forEach(([k, v, mono]) => {
    if (!v) return;
    facts.appendChild(el('dt', null, k));
    facts.appendChild(el('dd', mono ? 'mono' : null, v));
  });

  const result = $('jobResult');
  clear(result);
  result.classList.toggle('hidden', job.status === 'running');
  if (job.status === 'done' && !install) {
    const box = el('div', 'note-box good row');
    box.appendChild(rich(el('span'), [{ b: 'Matrices are ready' }, ' in ', { mono: job.output_dir || '' }, '.']));
    const open = el('button', 'btn sm primary', 'Open results');
    open.type = 'button';
    open.addEventListener('click', () => openResults(job.output_dir));
    box.appendChild(open);
    result.appendChild(box);
    if (job.skipped_total) result.appendChild(skippedNote(job, ''));
  } else if (job.status === 'done') {
    result.appendChild(noteBox('good', [{ b: `${job.reference_genome} is installed. ` }, 'It is ready for runs.']));
  } else if (job.status === 'failed') {
    result.appendChild(noteBox('crit', [{ b: 'The run failed. ' }, job.error || '',
      job.skipped_total ? '' : ' The log below has the details.']));
    if (job.skipped_total) result.appendChild(skippedNote(job, 'warn'));
    if (job.kind === 'run' && job.output_dir) {
      const left = noteBox('', ['Anything this run wrote to ', { mono: job.output_dir },
        ' before it stopped (matrices, plots) may be incomplete or wrong, so do not use it. ',
        'A new run into that folder offers to replace it, or Delete removes it.']);
      left.style.marginTop = '10px';
      result.appendChild(left);
    }
  } else if (job.status === 'stopped') {
    result.appendChild(noteBox('', ['Stopped before it finished. Files already written stay where they are.']));
  }
}

// Why mutations were skipped. SigProfilerMatrixGenerator writes one line per
// skipped mutation to its own log, not to the run's output shown below, so
// the runner counts them by reason.
function skippedNote(job, kind) {
  const reasons = Object.entries(job.skipped || {}).sort((a, b) => b[1] - a[1]);
  const total = job.skipped_total;
  const box = noteBox(kind, [{ b: `${num(total)} mutation${total === 1 ? ' was' : 's were'} skipped.` }]);
  box.classList.add('skips');
  const list = el('ul');
  reasons.slice(0, 4).forEach(([reason, n]) => {
    list.appendChild(rich(el('li'), [`${reason}: `, { b: num(n) }]));
  });
  box.appendChild(list);
  const [top] = reasons[0] || [];
  if (top && /reference base does not match/i.test(top) && reasons[0][1] > total / 2) {
    box.appendChild(rich(el('p'), [
      'Most of the calls do not match ', { b: job.reference_genome },
      '. This usually means they were made against a different genome: choose the one they were called against and run again.']));
  }
  if (job.generator_log) {
    box.appendChild(rich(el('p'), ['Each one is listed in ', { mono: job.generator_log }, '.']));
  }
  return box;
}

$('stopBtn').addEventListener('click', async () => {
  if (!state.jobId) return;
  $('stopBtn').disabled = true;
  try { await post(`/api/jobs/${state.jobId}/stop`); toast('Stopped.'); }
  catch (e) { toast(e.message); }
  finally { $('stopBtn').disabled = false; pollJob(); }
});

/* -------------------------------------------------------------- results */

const FAMILY_ORDER = ['SBS', 'DBS', 'ID', 'SV', 'CNV'];

const CONTEXT_INFO = {
  SBS6: 'Single base substitutions in six classes, named by the pyrimidine of the mutated base pair: C>A, C>G, C>T, T>A, T>C and T>G.',
  SBS18: 'The six substitution classes split by transcriptional strand: transcribed (T), untranscribed (U) and non-transcribed (N). Bidirectional mutations are shared between T and U.',
  SBS24: 'The six substitution classes in four strand categories: transcribed (T), untranscribed (U), bidirectional (B) and non-transcribed (N).',
  SBS96: 'Each substitution with the base on either side of it: 4 x 6 x 4 = 96 channels, the standard view for mutational signatures. Bars are grouped and coloured by substitution class.',
  SBS288: 'The 96 trinucleotide channels split by transcriptional strand into T, U and N, with bidirectional mutations shared between T and U.',
  SBS384: 'The 96 trinucleotide channels in all four strand categories: T, U, B and N.',
  SBS1536: 'Each substitution with two bases on either side: 16 x 6 x 16 = 1,536 pentanucleotide channels.',
  SBS4608: 'The 1,536 pentanucleotide channels split by strand into T, U and N.',
  SBS6144: 'The 1,536 pentanucleotide channels in all four strand categories.',
  DBS78: 'Doublet base substitutions, two adjacent bases changed together, in 78 classes oriented by the pyrimidine content of the reference doublet.',
  DBS186: 'Doublets whose reference is all pyrimidines or all purines, in four strand categories, plus the remaining doublets in a questionable (Q) category.',
  DBS1248: 'The 78 doublet classes with the base on either side: 4 x 78 x 4 channels.',
  ID28: 'Single base insertions and deletions of C or T by homopolymer length, with longer indels pooled as repeats, microhomology or complex.',
  ID83: 'Indels by type (deletion or insertion), size, the base or repeat involved, and how often it repeats, or the microhomology length for deletions. The standard view for indel signatures.',
  ID415: 'The 83 indel channels in five transcriptional strand categories: T, U, B, N and Q.',
  ID89: 'The Koh et al. (2025) indel classification in 89 categories, which separates indels by flanking sequence and repeat context. ID83 is unchanged.',
  ID476: 'The detailed Koh et al. (2025) indel classification in 476 categories. ID83 is unchanged.',
  SV32: 'Structural variants by type (deletion, tandem duplication, inversion, translocation), size, and whether they are clustered.',
  CNV48: 'Copy number segments by total copy number, heterozygosity and segment size.',
};
const FAMILY_INFO = {
  SBS: 'single base substitutions', DBS: 'doublet base substitutions', ID: 'small insertions and deletions',
  SV: 'structural variants', CNV: 'copy number segments',
};

const family = (ctx) => (ctx.match(/^[A-Z]+/) || [''])[0];
const channels = (ctx) => Number((ctx.match(/\d+$/) || ['0'])[0]);
const projectOf = (file) => (String(file).match(/^(.+)\.[A-Z]+\d+(\.|$)/) || [null, file])[1];

function sortedContexts(contexts) {
  return Object.keys(contexts).sort((a, b) => {
    const fa = FAMILY_ORDER.indexOf(family(a)), fb = FAMILY_ORDER.indexOf(family(b));
    return fa !== fb ? fa - fb : channels(a) - channels(b);
  });
}

function tile(k, v, d) {
  const t = el('div', 'tile');
  t.appendChild(el('div', 'k', k));
  t.appendChild(el('div', 'v', v));
  t.appendChild(el('div', 'd', d || ' '));
  return t;
}

async function openResults(path) {
  path = String(path || '').trim();
  if (!path) return;
  let r;
  try { r = await get(`/api/results?${q({ path })}`); }
  catch (e) { toast(e.message); return; }
  state.results = r;
  state.resultsPath = path;
  $('openPath').value = path;
  $('resultsEmpty').classList.add('hidden');
  $('resultsBody').classList.remove('hidden');
  show('results');

  const ctxs = sortedContexts(r.contexts);
  const files = ctxs.flatMap((c) => r.contexts[c]);
  const size = files.reduce((s, f) => s + f.size, 0);
  const fams = FAMILY_ORDER.filter((f) => ctxs.some((c) => family(c) === f));
  const tiles = $('resTiles');
  clear(tiles);
  tiles.appendChild(tile('Contexts', num(ctxs.length), fams.join(' · ')));
  tiles.appendChild(tile('Matrix files', num(files.length), bytes(size)));
  const samplesTile = tile('Samples', '…', '');
  samplesTile.id = 'samplesTile';
  tiles.appendChild(samplesTile);
  tiles.appendChild(tile('Project', files.length ? projectOf(files[0].name) : '–', baseName(path)));

  const alert = $('resAlert');
  clear(alert);
  alert.classList.toggle('hidden', !!r.plotting_available || !files.length);
  if (!r.plotting_available) {
    rich(alert, [{ b: 'Charts need SigProfilerPlotting 1.5.0 or later. ' },
      'The matrices can still be downloaded below.']);
  }

  renderResultNotes(r, ctxs);
  renderContextChips(ctxs);
  renderFileList(ctxs);
  renderPlotList(r.plots || []);
  $('chartCard').classList.toggle('hidden', !files.length || !r.plotting_available);
  if (!files.length) {
    $('ctxNote').textContent = 'no matrix files in SBS, DBS, ID, SV or CNV here';
    $('samplesTile').querySelector('.v').textContent = '–';
    return;
  }
  $('ctxNote').textContent = 'choose a context to plot';
  selectContext(ctxs.includes('SBS96') ? 'SBS96' : ctxs[0]);
}

// What in this folder should not be read as this run's result: files an
// earlier run left, plots older than their matrices, matrices with no counts.
function renderResultNotes(r, ctxs) {
  const box = $('resNotes');
  clear(box);
  const every = (ctx, key) => r.contexts[ctx].every((f) => f[key]);
  const plots = r.plots || [];
  const earlierCtx = ctxs.filter((c) => every(c, 'earlier'));
  const earlierPlots = plots.filter((p) => p.earlier);
  const olderPlots = plots.filter((p) => !p.earlier && p.older_than_matrix);
  const emptyCtx = ctxs.filter((c) => every(c, 'empty'));
  const run = r.run;
  if (run && run.status === 'failed') {
    box.appendChild(noteBox('crit', [{ b: 'The newest files here come from a run that failed' },
      ` (${run.name}, ${run.reference_genome}, started ${whenAt(run.created_at)}). `,
      'They may be incomplete or wrong, so do not use them. Run again, replacing them.']));
  }
  if (run && (earlierCtx.length || earlierPlots.length)) {
    const parts = [];
    if (earlierCtx.length) parts.push(`the ${listing(earlierCtx)} matri${earlierCtx.length === 1 ? 'x' : 'ces'}`);
    if (earlierPlots.length) parts.push(`${earlierPlots.length} PDF plot${earlierPlots.length === 1 ? '' : 's'}`);
    box.appendChild(noteBox('warn', [{ b: 'Some files here come from an earlier run. ' },
      `The latest run in this folder (${run.name}, ${run.reference_genome}, started ${whenAt(run.created_at)}) `,
      `did not write ${listing(parts)}, so they may not match it. They are marked "earlier" below.`]));
  }
  if (olderPlots.length) {
    box.appendChild(noteBox('warn', [{ b: `${olderPlots.length} PDF plot${olderPlots.length === 1 ? ' is' : 's are'} older than ${olderPlots.length === 1 ? 'its matrix' : 'their matrices'}, ` },
      'so an earlier run drew them and they may not show the matrices here. They are marked below.']));
  }
  if (emptyCtx.length) {
    box.appendChild(noteBox('', [{ b: `${listing(emptyCtx)} ${emptyCtx.length === 1 ? 'is' : 'are'} empty: ` },
      'every count is zero, because the input had no mutations of that type.']));
  }
}

function renderContextChips(ctxs) {
  const box = $('ctxGroups');
  clear(box);
  FAMILY_ORDER.forEach((fam) => {
    const mine = ctxs.filter((c) => family(c) === fam);
    if (!mine.length) return;
    const g = el('div', 'ctx-group');
    g.appendChild(el('div', 'fam', fam));
    const chips = el('div', 'chips');
    mine.forEach((ctx) => {
      const b = el('button', 'chip');
      b.type = 'button';
      b.dataset.ctx = ctx;
      b.setAttribute('aria-pressed', 'false');
      b.appendChild(document.createTextNode(ctx));
      const files = state.results.contexts[ctx];
      const n = files.length;
      if (n > 1) b.appendChild(el('span', 'n', `×${n}`));
      const earlier = files.every((f) => f.earlier), empty = files.every((f) => f.empty);
      if (earlier) { b.classList.add('earlier'); b.appendChild(el('span', 'n', 'earlier')); }
      if (empty) b.classList.add('empty');
      b.title = [`${n} file${n === 1 ? '' : 's'}`, earlier && 'from an earlier run',
        empty && 'empty: every count is zero'].filter(Boolean).join(' · ');
      b.addEventListener('click', () => selectContext(ctx));
      chips.appendChild(b);
    });
    g.appendChild(chips);
    box.appendChild(g);
  });
}

function renderFileList(ctxs) {
  const list = $('fileList');
  clear(list);
  let count = 0;
  ctxs.forEach((ctx) => state.results.contexts[ctx].forEach((f) => {
    count++;
    const row = el('div', 'f');
    row.appendChild(el('span', 'badge', ctx));
    const nm = el('span', 'nm', f.name);
    nm.title = f.path;
    row.appendChild(nm);
    if (f.earlier) row.appendChild(el('span', 'flag', 'earlier run'));
    if (f.empty) row.appendChild(el('span', 'flag flat', 'empty'));
    row.appendChild(el('span', 's', bytes(f.size)));
    const a = el('a', 'btn sm', 'Download');
    a.href = `/api/results/download?${q({ path: f.path })}`;
    a.setAttribute('download', f.name);
    row.appendChild(a);
    list.appendChild(row);
  }));
  $('filesNote').textContent = count ? `${count} file${count === 1 ? '' : 's'} in ${baseName(state.resultsPath)}` : '';
}

// SigProfilerPlotting names its PDFs like SBS_96_plots_<project>.pdf.
const plotContext = (name) => {
  const m = String(name).match(/^([A-Z]+)_(\d+)_plots_/);
  return m ? `${m[1]}${m[2]}` : 'PDF';
};

function renderPlotList(plots) {
  const list = $('plotList');
  clear(list);
  $('plotsNote').textContent = plots.length
    ? `${plots.length} figure${plots.length === 1 ? '' : 's'} drawn by SigProfilerPlotting`
    : '';
  if (!plots.length) {
    const empty = el('p', 'empty', 'No PDF plots in this folder. Tick PDF plots when you start a run, and SigProfilerPlotting draws every matrix here.');
    empty.style.padding = '12px 16px';
    list.appendChild(empty);
    return;
  }
  const order = (p) => {
    const ctx = plotContext(p.name);
    const fam = FAMILY_ORDER.indexOf(family(ctx));
    return [fam < 0 ? FAMILY_ORDER.length : fam, channels(ctx)];
  };
  [...plots].sort((a, b) => {
    const [fa, ca] = order(a), [fb, cb] = order(b);
    return fa !== fb ? fa - fb : ca - cb;
  }).forEach((p) => {
    const row = el('div', 'f');
    row.appendChild(el('span', 'badge', plotContext(p.name)));
    const nm = el('span', 'nm', p.name);
    nm.title = p.path;
    row.appendChild(nm);
    if (p.earlier) row.appendChild(el('span', 'flag', 'earlier run'));
    else if (p.older_than_matrix) row.appendChild(el('span', 'flag', 'older than its matrix'));
    row.appendChild(el('span', 's', bytes(p.size)));
    const open = el('a', 'btn sm primary', 'Open');
    open.href = `/api/results/view?${q({ path: p.path })}`;
    open.target = '_blank';
    open.rel = 'noopener';
    row.appendChild(open);
    const dl = el('a', 'btn sm', 'Download');
    dl.href = `/api/results/download?${q({ path: p.path })}`;
    dl.setAttribute('download', p.name);
    row.appendChild(dl);
    list.appendChild(row);
  });
}

async function selectContext(ctx) {
  state.ctx = ctx;
  document.querySelectorAll('#ctxGroups .chip').forEach((b) =>
    b.setAttribute('aria-pressed', String(b.dataset.ctx === ctx)));
  const files = state.results.contexts[ctx];
  const fileSel = $('fileSel');
  clear(fileSel);
  files.forEach((f) => { const o = el('option', null, f.name); o.value = f.path; fileSel.appendChild(o); });
  $('fileWrap').classList.toggle('hidden', files.length < 2);
  $('chartTitle').textContent = `${ctx} profile`;
  const fam = family(ctx);
  fillAbout($('about-chart'), [
    ['What it shows', CONTEXT_INFO[ctx] || `${FAMILY_INFO[fam] ? FAMILY_INFO[fam][0].toUpperCase() + FAMILY_INFO[fam].slice(1) : 'Mutations'} in the ${ctx} classification, ${num(channels(ctx))} channels.`],
    ['How to read it', 'Each bar is one channel for the chosen sample. Counts are raw; Percent and Proportion rescale each sample to its own total, which makes samples with different burdens comparable.'],
    ['Export', 'The camera button above the chart saves it as SVG, named after the project, context and sample.'],
  ]);
  await selectFile(files[0].path);
}

async function selectFile(path) {
  state.file = path;
  $('fileSel').value = path;
  const name = baseName(path);
  $('downloadBtn').href = `/api/results/download?${q({ path })}`;
  $('downloadBtn').setAttribute('download', name);
  const sampleSel = $('sampleSel');
  const keep = sampleSel.value;
  clear(sampleSel);
  chartMessage([{ node: el('span', 'spin') }, ' Loading samples…']);
  try {
    const r = await get(`/api/results/samples?${q({ path })}`);
    if (state.file !== path) return;
    r.samples.forEach((s) => { const o = el('option', null, s); o.value = s; sampleSel.appendChild(o); });
    if (r.samples.includes(keep)) sampleSel.value = keep;
    const st = $('samplesTile');
    if (st) {
      st.querySelector('.v').textContent = num(r.samples.length);
      st.querySelector('.d').textContent = `in ${state.ctx}`;
    }
    const info = (state.results.contexts[state.ctx] || []).find((f) => f.path === path);
    if (info && info.empty) {
      chartMessage([{ b: 'Every count in this matrix is zero. ' },
        'The input had no mutations of this type, so there is nothing to draw.']);
      return;
    }
    await renderChart();
  } catch (e) {
    chartMessage([e.message]);
  }
}

function chartMessage(parts) {
  const node = $('chart');
  if (window.Plotly) window.Plotly.purge(node);
  clear(node);
  const msg = el('div', 'chart-msg');
  rich(msg, parts);
  node.appendChild(msg);
}

function currentUnit() {
  const checked = document.querySelector('input[name="unit"]:checked');
  return checked ? checked.value : 'percent';
}

async function renderChart() {
  const path = state.file, sample = $('sampleSel').value, unit = currentUnit();
  if (!path || !sample) return;
  let r;
  try { r = await get(`/api/results/render?${q({ path, sample, unit })}`); }
  catch (e) { chartMessage([e.message]); return; }
  if (path !== state.file || sample !== $('sampleSel').value || unit !== currentUnit()) return;
  if (r.kind !== 'standard') {
    chartMessage([{ b: `${state.ctx} uses a multi-panel layout that is not drawn here. ` },
      'Download the matrix and open it in the SigProfilerPlotting dashboard to view it.']);
    return;
  }
  const node = $('chart');
  const fig = r.figure;
  if (!node.classList.contains('js-plotly-plot')) clear(node);
  // A "Loading samples..." message from before may still sit beside a chart
  // being redrawn in place (purge() keeps the node's plotly class).
  node.querySelectorAll('.chart-msg').forEach((m) => m.remove());
  const config = Object.assign({}, fig.config, {
    displaylogo: false, responsive: true,
    modeBarButtonsToRemove: ['select2d', 'lasso2d', 'autoScale2d'],
    toImageButtonOptions: { format: 'svg', filename: `${slug(projectOf(baseName(path)))}_${state.ctx}_${slug(sample)}` },
  });
  window.Plotly.react(node, fig.traces, fig.layout, config);
}

$('fileSel').addEventListener('change', (e) => selectFile(e.target.value));
$('sampleSel').addEventListener('change', renderChart);
document.querySelectorAll('input[name="unit"]').forEach((r) => r.addEventListener('change', renderChart));

async function chooseResults() {
  try {
    const path = await pickPath('results');
    if (path) openResults(path);
  } catch (e) { toast(e.message); }
}
$('openResultsBtn').addEventListener('click', chooseResults);
$('resultsChoose').addEventListener('click', chooseResults);
['openPath', 'resultsPath'].forEach((id) =>
  $(id).addEventListener('keydown', (e) => { if (e.key === 'Enter') openResults(e.target.value); }));

/* ----------------------------------------------------------------- quit */

$('quitBtn').addEventListener('click', () => {
  const live = state.jobs.filter((j) => j.status === 'running');
  $('quitText').textContent = live.length
    ? `This stops the app and ${live.length === 1 ? 'the run' : `the ${live.length} runs`} still in progress. Matrices already written stay where they are.`
    : 'This stops the app. Your results stay where they are.';
  $('quitGo').textContent = live.length ? 'Stop and quit' : 'Quit';
  $('quitDialog').showModal();
});
$('quitCancel').addEventListener('click', () => $('quitDialog').close());
$('quitGo').addEventListener('click', async () => {
  try { await post('/api/quit'); } catch (e) { /* the server may close the socket as it stops */ }
  $('quitDialog').close();
  const app = $('app');
  clear(app);
  const box = el('div', 'stopped');
  box.appendChild(el('h2', null, 'The workbench has stopped.'));
  box.appendChild(el('p', null, 'You can close this tab. Start it again with launch_web.sh, or with sigprofilermatrixgenerator-web.'));
  app.appendChild(box);
});

/* ----------------------------------------------------------------- init */

updateOutPreview();
updateSummary();
loadEnv().catch((e) => {
  $('startError').appendChild(noteBox('crit', [{ b: 'Could not reach the server. ' }, e.message]));
});
refreshJobs();
setInterval(refreshJobs, 3000);
