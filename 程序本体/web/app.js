/* AI 量化交易系统 · Web 前端逻辑 */
'use strict';

// 双模式 API：pywebview 桥接（桌面版） / HTTP fetch（浏览器/手机 24h 模式）
function httpApiProxy() {
  return new Proxy({}, {
    get(_t, name) {
      if (typeof name !== 'string') return undefined;
      return async (...args) => {
        const res = await fetch('/api/' + name, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ args })
        });
        let data;
        try { data = await res.json(); } catch (e) { data = null; }
        if (!res.ok) throw new Error((data && data.msg) || ('HTTP ' + res.status));
        return data;
      };
    }
  });
}
const api = () => (window.pywebview && window.pywebview.api) ? window.pywebview.api : httpApiProxy();

// ---------------- 工具 ----------------
function $(sel) { return document.querySelector(sel); }
// 安全绑定：元素不存在时静默跳过，避免单个按钮缺失导致整页交互失效
function on(sel, ev, fn) {
  const el = $(sel);
  if (el) el.addEventListener(ev, fn);
  return el;
}
function fmt(n, d) {
  if (n === null || n === undefined || n === '' || Number.isNaN(Number(n))) return '-';
  const num = Number(n);
  if (d === undefined) d = (Math.abs(num) >= 1000) ? 0 : 2;
  return num.toLocaleString('zh-CN', { minimumFractionDigits: d, maximumFractionDigits: d });
}
function pctClass(v) { return Number(v) >= 0 ? 'up' : 'down'; }
function signed(v, d) { const n = Number(v) || 0; return (n >= 0 ? '+' : '') + fmt(n, d); }
function esc(s) {
  if (s === null || s === undefined) return '';
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

let toastTimer = null;
function showToast(msg, type) {
  const t = $('#toast');
  t.textContent = msg;
  t.className = 'toast ' + (type || 'info');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.add('hidden'), 3200);
}

// ---------------- 页面导航 ----------------
function openQuery(code) {
  $('#queryInput').value = code;
  const btn = document.querySelector('.nav-btn[data-page="query"]');
  if (btn) btn.click();
  setTimeout(() => doQuery(), 60);
}
document.querySelectorAll('.nav-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    $('#page-' + btn.dataset.page).classList.add('active');
    if (btn.dataset.page === 'watchlist') renderWatchlist();
    if (btn.dataset.page === 'trading') pollTradingStatus();
    if (btn.dataset.page === 'portfolio') renderPortfolio();
    if (btn.dataset.page === 'funds') renderFunds();
    if (btn.dataset.page === 'sector') renderSector();
    if (btn.dataset.page === 'realtime') renderRealtime();
    if (btn.dataset.page === 'crawl') renderCrawlList();
    if (btn.dataset.page === 'monitor') { monStatus(); startMonPoll(); }
    if (btn.dataset.page === 'storage') renderStorage();
    if (btn.dataset.page === 'analysis') { /* 懒加载 */ }
    if (btn.dataset.page === 'db') renderDb();
  });
});

// ---------------- 顶部大盘 ----------------
async function loadIndices() {
  try {
    const list = await api().market_indices();
    const box = $('#indices');
    if (!list || !list.length) { box.innerHTML = ''; return; }
    box.innerHTML = list.map(i => `
      <div class="indice">
        <span class="nm">${i.name}</span>
        <span class="vl ${pctClass(i.pct)}">${fmt(i.price)}</span>
        <span class="pct ${pctClass(i.pct)}">${signed(i.pct, 2)}%</span>
      </div>`).join('');
  } catch (e) { /* 忽略 */ }
}

// ---------------- 市场模式标签 ----------------
function marketModeText() {
  const now = new Date();
  const d = now.getDay();
  if (d === 0 || d === 6) return '📋 非交易日：今日全天分析总结（每60分钟刷新）';
  const mins = now.getHours() * 60 + now.getMinutes();
  const inMorning = mins >= 555 && mins <= 690;   // 9:15 - 11:30
  const inAfternoon = mins >= 780 && mins <= 900; // 13:00 - 15:00
  return inMorning || inAfternoon
    ? '📊 盘中：实时榜单（每5分钟自动刷新）'
    : '📋 已收盘：今日全天分析总结（每60分钟刷新）';
}

// ---------------- 推荐榜单 ----------------
function toggleAll(tableId, cb) {
  const table = document.getElementById(tableId);
  if (!table) return;
  table.querySelectorAll('tbody tr input.row-check').forEach(c => { c.checked = !!cb.checked; });
}

function updateSelectAll(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const cbs = [...table.querySelectorAll('tbody tr input.row-check')];
  const sel = table.querySelector('thead [data-selall]');
  if (sel) sel.checked = cbs.length > 0 && cbs.every(c => c.checked);
}

function getCheckedRows(tableId) {
  const table = document.getElementById(tableId);
  if (!table) return [];
  return [...table.querySelectorAll('tbody tr')]
    .filter(tr => !tr.classList.contains('empty'))
    .map(tr => ({
      code: tr.dataset.code || '',
      name: tr.dataset.name || '',
      checked: !!(tr.querySelector('input.row-check') || {}).checked
    }))
    .filter(r => r.checked && r.code);
}

function renderShort(rows) {
  window.rankData = window.rankData || {};
  window.rankData.short = rows;
  const tb = $('#shortTable tbody');
  if (!rows || !rows.length) { tb.innerHTML = '<tr class="empty"><td colspan="9">暂无数据</td></tr>'; return; }
  tb.innerHTML = rows.map((r, i) => {
    const r5 = r['5日涨幅'];
    return `
    <tr data-code="${esc(String(r['代码']))}" data-name="${esc(String(r['名称'] || ''))}">
      <td><input type="checkbox" class="row-check" onchange="updateSelectAll('shortTable')"></td>
      <td>${i + 1}</td><td>${r['代码']}</td><td>${r['名称']}</td>
      <td>${fmt(r['最新价'])}</td>
      <td class="${pctClass(r['涨跌幅'])}">${signed(r['涨跌幅'], 2)}%</td>
      <td class="${pctClass(r5)}">${r5 === null || r5 === undefined ? '-' : signed(r5, 2) + '%'}</td>
      <td><b>${fmt(r['短线分'])}</b></td>
      <td>
        <button class="btn-mini" onclick="openQuery('${r['代码']}')">查看</button>
        <button class="btn-mini" onclick="addOne('${r['代码']}','${r['名称']}',event)">加入自选</button>
      </td>
    </tr>`;
  }).join('');
  const sel = $('#shortSelAll'); if (sel) sel.checked = false;
}

function renderLong(rows) {
  window.rankData = window.rankData || {};
  window.rankData.long = rows;
  const tb = $('#longTable tbody');
  if (!rows || !rows.length) { tb.innerHTML = '<tr class="empty"><td colspan="9">暂无数据</td></tr>'; return; }
  tb.innerHTML = rows.map((r, i) => `
    <tr data-code="${esc(String(r['代码']))}" data-name="${esc(String(r['名称'] || ''))}">
      <td><input type="checkbox" class="row-check" onchange="updateSelectAll('longTable')"></td>
      <td>${i + 1}</td><td>${r['代码']}</td><td>${r['名称']}</td>
      <td>${fmt(r['现价'])}</td>
      <td class="${pctClass(r['今涨跌幅'])}">${r['今涨跌幅'] || '-'}</td>
      <td><b>${fmt(r['长期影响指数'])}</b></td>
      <td><span class="tag tag-${String(r['级别']).toLowerCase()}">${r['级别']}</span></td>
      <td>
        <button class="btn-mini" onclick="openQuery('${r['代码']}')">查看</button>
        <button class="btn-mini" onclick="addOne('${r['代码']}','${r['名称']}',event)">加入自选</button>
      </td>
    </tr>`).join('');
  const sel = $('#longSelAll'); if (sel) sel.checked = false;
}

async function addOne(code, name, ev) {
  const btn = ev && ev.target;
  if (btn) btn.disabled = true;
  const r = await api().watch_add(code, name);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  if (btn) btn.disabled = false;
}

let lastRankingRefreshAt = 0;
let rankingRunning = false;
async function rankingRefresh() {
  if (rankingRunning) return;
  rankingRunning = true;
  lastRankingRefreshAt = Date.now();
  const btn = $('#btnRankingRefresh');
  const wrap = $('#rankingProgress');
  const limit = parseInt($('#selRankLimit').value, 10) || 20;
  btn.disabled = true;
  wrap.classList.remove('hidden');
  $('#rankingBar').style.width = '2%';
  $('#rankingMsg').textContent = '启动分析...';
  let job;
  try {
    job = await api().ranking_start('both', limit);
  } catch (e) {
    showToast('启动失败: ' + e, 'err');
    btn.disabled = false;
    rankingRunning = false;
    return;
  }
  const id = job.id;
  const iv = setInterval(async () => {
    try {
      const st = await api().ranking_progress(id);
      $('#rankingBar').style.width = st.pct + '%';
      $('#rankingMsg').textContent = st.message + (st.running ? '…' : '');
      if (st.done) {
        clearInterval(iv);
        btn.disabled = false;
        rankingRunning = false;
        if (st.error) {
          showToast('刷新失败: ' + st.error, 'err');
        } else {
          const res = await api().ranking_result(id);
          renderShort(res.short);
          renderLong(res.long);
          showToast('✅ 榜单已刷新', 'ok');
          $('#marketMode').textContent = marketModeText();
        }
        setTimeout(() => wrap.classList.add('hidden'), 600);
      }
    } catch (e) { clearInterval(iv); btn.disabled = false; rankingRunning = false; }
  }, 600);
}

function isTradingTime() {
  const now = new Date();
  const d = now.getDay();
  if (d === 0 || d === 6) return false;
  const mins = now.getHours() * 60 + now.getMinutes();
  const inMorning = mins >= 555 && mins <= 690;   // 9:15 - 11:30
  const inAfternoon = mins >= 780 && mins <= 900; // 13:00 - 15:00
  return inMorning || inAfternoon;
}

// 自动刷新：盘中每5分钟、收盘后每60分钟（仅当用户至少手动刷新过一次榜单后生效）
function autoRefreshRanking() {
  if (!lastRankingRefreshAt) return;   // 用户还没用过榜单，不主动触发
  const now = Date.now();
  const gap = isTradingTime() ? 300000 : (marketModeText().indexOf('非交易日') >= 0 ? Infinity : 3600000);
  if (now - lastRankingRefreshAt >= gap) {
    rankingRefresh();
  }
}

async function addAllToWatchlist(kind) {
  const tableId = kind === 'short' ? 'shortTable' : 'longTable';
  const sel = getCheckedRows(tableId);
  if (!sel.length) { showToast('请先勾选要加入自选的股票', 'err'); return; }
  for (let i = 0; i < sel.length; i++) {
    await api().watch_add(sel[i].code, sel[i].name);
  }
  showToast('✅ 已加入自选股 ' + sel.length + ' 只', 'ok');
}

// 按金额推荐：从全市场挑买得起的活跃股，先尽量多买不同的股票（各1手），再给高分股补足
let lastAlloc = [];

async function allocateBudget() {
  const total = Number($('#rankBudget').value) || 0;
  if (total <= 0) { showToast('请填写买入总金额', 'err'); return; }
  const mode = $('#budgetMode').value || 'mix';
  const btn = $('#btnAllocate');
  btn.disabled = true;
  try {
    const r = await api().ranking_budget(total, 60, mode);
    if (!r.ok) { showToast('按金额推荐失败: ' + (r.msg || ''), 'err'); return; }
    const rows = r.rows || [];
    const tb = $('#allocTable tbody');
    lastAlloc = [];
    if (!rows.length) {
      tb.innerHTML = '<tr class="empty"><td colspan="10">没有找到买得起的非ST股票（A股最小1手=100股）</td></tr>';
      $('#allocSummary').textContent = `你的 ${money(total)} 元：最多可买 0 只`;
      $('#allocNote').textContent = '当前市场上最便宜的 1 手也要约 200~400 元，建议金额 ≥ 500 元再试。';
    } else {
      const items = rows.map(x => ({
        code: String(x['代码'] || '').trim(),
        name: x['名称'] || '',
        price: Number(x['现价']) || 0,
        pct: x['涨跌幅'] === undefined || x['涨跌幅'] === null ? null : Number(x['涨跌幅']),
        score: Number(x['活跃分']) || 0,
        cost1: (Number(x['1手成本']) || 0) || (Number(x['现价']) || 0) * 100
      })).filter(x => x.price > 0 && x.cost1 > 0);
      items.sort((a, b) => b.score - a.score);
      const byCost = [...items].sort((a, b) => a.cost1 - b.cost1);
      const capOf = total * 0.25;
      let remaining = total;
      const out = [];
      // 第一轮：便宜的先各买1手，最大化可买只数
      for (const x of byCost) {
        if (remaining <= 0) break;
        if (remaining < x.cost1) continue;
        out.push({ ...x, lots: 1, actual: x.cost1, pct: x.cost1 / total * 100 });
        remaining -= x.cost1;
      }
      // 第二轮：按活跃分从高到低，给已买入的补足（单只≤25%）
      const topUp = [...out].sort((a, b) => b.score - a.score);
      if (remaining >= 100) {
        for (const o of topUp) {
          if (remaining < 100) break;
          const extraByCap = Math.max(0, Math.floor((capOf - o.actual) / o.cost1));
          const extra = Math.min(extraByCap, Math.floor(remaining / o.cost1));
          if (extra >= 1) { o.lots += extra; o.actual += extra * o.cost1; o.pct = o.actual / total * 100; remaining -= extra * o.cost1; }
        }
      }
      // 第三轮：剩的钱还能再买1手（不同股）就继续加，最大化只数
      if (remaining >= 100) {
        for (const x of byCost) {
          if (remaining < 100) break;
          if (out.some(o => o.code === x.code)) continue;
          if (remaining < x.cost1) continue;
          out.push({ ...x, lots: 1, actual: x.cost1, pct: x.cost1 / total * 100 });
          remaining -= x.cost1;
        }
      }
      lastAlloc = out;
      if (!lastAlloc.length) {
        tb.innerHTML = '<tr class="empty"><td colspan="10">金额不够买任何 1 手</td></tr>';
        $('#allocSummary').textContent = `你的 ${money(total)} 元：最多可买 0 只`;
        const cheapest = Math.min(...items.map(x => x.cost1));
        $('#allocNote').textContent = `最便宜的 1 手也要约 ${money(cheapest)} 元，请加大金额。`;
      } else {
        tb.innerHTML = lastAlloc.map((x, i) => `
          <tr data-code="${esc(String(x.code))}" data-name="${esc(String(x.name || ''))}">
            <td><input type="checkbox" class="row-check" onchange="updateSelectAll('allocTable')"></td>
            <td>${i + 1}</td><td>${x.code}</td><td>${esc(x.name)}</td>
            <td>${fmt(x.price)}</td>
            <td class="${x.pct === null ? '' : pctClass(x.pct)}">${x.pct === null ? '-' : signed(x.pct, 2) + '%'}</td>
            <td>${fmt(x.score)}</td>
            <td>${money(x.actual)}</td><td><b>${x.lots} 手</b></td>
            <td>${fmt(x.pct, 1)}%</td>
          </tr>`).join('');
        const sel = $('#allocSelAll'); if (sel) sel.checked = false;
        const used = lastAlloc.reduce((s, x) => s + x.actual, 0);
        const styleName = mode === 'dip' ? '抄底·超跌' : (mode === 'hot' ? '追高·活跃' : '综合判断');
        $('#allocSummary').textContent =
          `你的 ${money(total)} 元（${styleName}）：最多可买 ${lastAlloc.length} 只股票，实际使用 ${money(used)} 元`;
        const styleDesc = mode === 'dip'
          ? '从全市场挑当日超跌（跌得越深分越高）、贴近当日低点、流动性适中的低价股'
          : (mode === 'hot'
            ? '从全市场按活跃度挑买得起的上涨股'
            : '综合权衡：超跌和温和上涨都给分，涨停/跌停降权防追高防接刀，量能适中、低价优先');
        $('#allocNote').textContent =
          `${styleDesc}（1手=100股），先尽量分散，再给高分股补足，单只≤${money(capOf)}（25%）。剩余 ${money(total - used)} 元留作可用资金。`;
      }
    }
    $('#allocResult').classList.remove('hidden');
  } catch (e) {
    showToast('按金额推荐失败: ' + e, 'err');
  } finally {
    btn.disabled = false;
  }
}

function rankImport() {
  const sel = getCheckedRows('allocTable');
  if (!sel.length) { showToast('请先在推荐结果里勾选要导入的股票', 'err'); return; }
  const total = Number($('#rankBudget').value) || 0;
  const codes = sel.map(x => x.code);
  $('#capital').value = total;
  $('#tradingPool').value = codes.join('\n');
  const p = autoTuneParams(codes.length);
  $('#maxSingle').value = p.single;
  $('#maxTotal').value = p.total;
  $('#stopLoss').value = p.stop;
  $('#takeProfit').value = p.take;
  $('#poolTips').textContent =
    `已导入 ${codes.length} 只，初始资金 ${money(total)} 元，自动调参：单只 ${p.single}%、总仓 ${p.total}%、止损 ${p.stop}%、止盈 ${p.take}%`;
  saveTradingConfig();
  showToast(`✅ 已导入交易：${codes.length} 只股票，初始资金 ${money(total)} 元`, 'ok');
  const btn = document.querySelector('.nav-btn[data-page="trading"]');
  if (btn) btn.click();
}

// 榜单勾选行 → 一键导入交易：只导入勾选的股票
function importRanking(kind) {
  const tableId = kind === 'short' ? 'shortTable' : 'longTable';
  const label = kind === 'short' ? '短线榜' : '长线榜';
  const sel = getCheckedRows(tableId);
  if (!sel.length) { showToast(`请在${label}勾选要导入的股票`, 'err'); return; }
  const codes = sel.map(x => x.code);
  $('#tradingPool').value = codes.join('\n');
  const p = autoTuneParams(codes.length);
  $('#maxSingle').value = p.single;
  $('#maxTotal').value = p.total;
  $('#stopLoss').value = p.stop;
  $('#takeProfit').value = p.take;
  $('#poolTips').textContent =
    `已导入${label} ${codes.length} 只，自动调参：单只 ${p.single}%、总仓 ${p.total}%、止损 ${p.stop}%、止盈 ${p.take}%（初始资金请到交易页确认）`;
  saveTradingConfig();
  showToast(`✅ 已导入${label} ${codes.length} 只股票到交易池`, 'ok');
  const btn = document.querySelector('.nav-btn[data-page="trading"]');
  if (btn) btn.click();
}

// 金额推荐结果 → 加入自选（只加入勾选的行）
async function allocAddToWatchlist() {
  const sel = getCheckedRows('allocTable');
  if (!sel.length) { showToast('请先勾选要加入自选的股票', 'err'); return; }
  for (let i = 0; i < sel.length; i++) {
    try { await api().watch_add(sel[i].code, sel[i].name); } catch (e) { /* 忽略单只失败 */ }
  }
  showToast(`✅ 已加入自选股 ${sel.length} 只`, 'ok');
}

// ---------------- 回测股票池导入 ----------------
function setBtCodes(items) {
  const codes = (items || []).map(i => {
    let c = i.code || i.stock || i[0] || '';
    c = String(c).replace(/^(sh|sz|bj)/i, '');
    return c.trim();
  }).filter(Boolean);
  const uniq = Array.from(new Set(codes));
  if (!uniq.length) { showToast('没有可导入的股票', 'err'); return; }
  $('#btCode').value = uniq.join(',');
  showToast(`已导入 ${uniq.length} 只到回测`, 'ok');
}

async function btImportWatch() {
  try { setBtCodes(await api().watch_list()); } catch (e) { showToast('导入自选失败: ' + e, 'err'); }
}

async function btImportPos() {
  try {
    const p = await api().portfolio_get();
    setBtCodes((p.positions || []).map(x => ({ code: x.code, name: x.name })));
  } catch (e) { showToast('导入持仓失败: ' + e, 'err'); }
}

function btImportAlloc() {
  const sel = getCheckedRows('allocTable');
  if (!sel.length) { showToast('请先在推荐结果里勾选要导入回测的股票', 'err'); return; }
  $('#btCode').value = sel.map(x => x.code).join(',');
  showToast(`已导入 ${sel.length} 只到回测`, 'ok');
}

// ---------------- 我的自选 ----------------
function renderWatchTable(items, quotes) {
  const tb = $('#watchTable tbody');
  const qmap = {};
  (quotes || []).forEach(q => { qmap[String(q['symbol'])] = q; });
  if (!items.length) { tb.innerHTML = '<tr class="empty"><td colspan="7">还没有自选股</td></tr>'; return; }
  tb.innerHTML = items.map(it => {
    const q = qmap[String(it.code)];
    const price = q ? fmt(q['price']) : '-';
    const pct = q ? q['change_percent'] : null;
    const amt = q ? q['change_amount'] : null;
    return `
      <tr>
        <td>${it.code}</td>
        <td>${q && q['name'] ? q['name'] : it.name}</td>
        <td>${price}</td>
        <td class="${pctClass(pct)}">${pct === null ? '-' : signed(pct, 2) + '%'}</td>
        <td class="${pctClass(amt)}">${amt === null ? '-' : signed(amt, 2)}</td>
        <td><button class="btn-mini" onclick="showWatchKline('${it.code}')">K线</button></td>
        <td><button class="btn-mini" onclick="openQuery('${it.code}')">分析</button></td>
        <td><button class="btn-mini" onclick="delWatch('${it.code}')">删除</button></td>
      </tr>`;
  }).join('');
}

async function showWatchKline(code) {
  const box = $('#watchKlineBox');
  box.innerHTML = '<p class="muted">正在加载 K 线...</p>';
  try {
    const r = await api().query_kline(code, 120);
    if (r.ok && r.kline && r.kline.length) {
      $('#watchKlineName').textContent = `${r.name || code}（${code}）`;
      renderKline(r.kline, '#watchKlineBox');
    } else {
      box.innerHTML = '<p class="muted">未获取到 K 线数据</p>';
    }
  } catch (e) {
    box.innerHTML = '<p class="muted">K 线加载失败</p>';
  }
}

let lastWatchKlineCode = '';
async function renderWatchlist() {
  const items = await api().watch_list();
  if (!items || !items.length) { renderWatchTable(items, []); return; }
  // 打开自选页即自动刷新行情，涨幅/涨跌额直接显示
  try {
    const r = await api().watch_refresh();
    renderWatchTable(items, r.rows || []);
  } catch (e) {
    renderWatchTable(items, []);
  }
  if (items[0].code !== lastWatchKlineCode) {
    lastWatchKlineCode = items[0].code;
    showWatchKline(items[0].code);
  }
}

async function watchRefresh() {
  const btn = $('#btnWatchRefresh');
  btn.disabled = true;
  const r = await api().watch_refresh();
  btn.disabled = false;
  const items = await api().watch_list();
  renderWatchTable(items, r.rows || []);
  if (r.rows && r.rows.length) showToast('✅ 行情已刷新', 'ok');
  else if (r.msg && r.msg !== 'ok') showToast(r.msg, 'err');
}

async function addWatch() {
  const code = prompt('请输入股票代码（6位）或名称：');
  if (!code) return;
  const r = await api().watch_add(code, '');
  showToast(r.msg, r.ok ? 'ok' : 'err');
  renderWatchlist();
}

async function delWatch(code) {
  const r = await api().watch_del(code);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  renderWatchlist();
}

// ---------------- 数据管理 ----------------
async function renderStorage() {
  try {
    const s = await api().storage_get();
    $('#storageSummary').innerHTML = `<p class="big">总占用 <b>${s.total_mb} MB</b></p>`;
    $('#storageCats').innerHTML = s.cats.map(c => `
      <div class="card" style="margin-top:12px">
        <div class="card-head"><h3>${c.label} <span class="muted">（${c.count} 个文件 / ${c.size_mb} MB）</span></h3></div>
        ${c.count ? `
        <div class="table-wrap" style="max-height:240px; overflow-y:auto">
          <table class="data-table">
            <thead><tr><th>文件名</th><th>大小</th><th>修改日期</th><th></th></tr></thead>
            <tbody>${c.files.map(f => `
              <tr>
                <td>${f.name}</td><td>${fmt(f.size_kb, 0)} KB</td><td>${f.mtime}</td>
                <td><button class="btn-mini danger" data-del="${esc(f.path)}">删除</button></td>
              </tr>`).join('')}
            </tbody>
          </table>
        </div>` : '<p class="muted">空</p>'}
      </div>`).join('');
    document.querySelectorAll('#storageCats [data-del]').forEach(b =>
      b.addEventListener('click', async () => {
        const r = await api().storage_delete(b.dataset.del);
        showToast(r.msg, r.ok ? 'ok' : 'err');
        if (r.ok) renderStorage();
      }));
  } catch (e) { $('#storageSummary').innerHTML = `<p class="err">加载失败：${e}</p>`; }
}

// ---------------- 走势分析 ----------------
let analysisPoll = null;
function pollAnalysis(jid) {
  if (analysisPoll) clearInterval(analysisPoll);
  analysisPoll = setInterval(async () => {
    const p = await api().analysis_progress(jid);
    $('#analysisProgress').classList.remove('hidden');
    $('#analysisBar').style.width = (p.pct || 0) + '%';
    $('#analysisMsg').textContent = p.message;
    if (p.done) {
      clearInterval(analysisPoll);
      analysisPoll = null;
      if (p.error) { $('#analysisMsg').innerHTML = `<span class="err">❌ ${p.error}</span>`; showToast('分析失败', 'err'); }
      else { $('#analysisMsg').textContent = '✅ 分析完成！点击「📄 打开分析报告」查看。'; showToast('分析完成', 'ok'); }
    }
  }, 2000);
}

async function analysisStart() {
  const r = await api().analysis_start();
  if (!r.ok) return showToast(r.msg || '启动失败', 'err');
  pollAnalysis(r.id);
}

// ---------------- 数据库管理 ----------------
async function renderDb() {
  try {
    const s = await api().db_status();
    const st = $('#dbStatus');
    if (!s.ok) { st.innerHTML = `<p class="err">❌ ${esc(s.msg)}</p>`; $('#dbTables').innerHTML = ''; return; }
    st.innerHTML = `<p class="big">✅ 已连接 <b>MySQL ${esc(s.version)}</b></p>
      <p class="muted">${esc(s.host)}:${s.port} · 数据库 ${esc(s.database)}</p>`;
    $('#dbTables').innerHTML = s.tables.map(t => `
      <tr>
        <td>${esc(t.table)}</td><td>${fmt(t.rows, 0)}</td>
        <td><button class="btn-mini" onclick="dbView('${esc(t.table)}')">查看</button></td>
        <td><button class="btn-mini danger" onclick="dbExport('${esc(t.table)}')">导出CSV</button></td>
      </tr>`).join('') || '<tr class="empty"><td colspan="4">无表</td></tr>';
    await fillDbCsvSelect();
  } catch (e) { $('#dbStatus').innerHTML = `<p class="err">加载失败：${e}</p>`; }
}

async function fillDbCsvSelect() {
  try {
    const l = await api().crawl_list();
    $('#dbCsvSelect').innerHTML = l.files.map(f => `<option>${esc(f.name)}</option>`).join('');
  } catch (e) { /* 忽略 */ }
}

async function dbView(table) {
  const r = await api().db_table_schema(table);
  if (!r.ok) return showToast(r.msg, 'err');
  $('#dbDetail').innerHTML = `
    <div class="card" style="margin-top:14px">
      <div class="card-head"><h3>📋 ${esc(table)} 结构（共 ${fmt(r.total, 0)} 行）</h3></div>
      <div class="table-wrap" style="max-height:200px; overflow-y:auto">
        <table class="data-table"><thead><tr><th>字段</th><th>类型</th><th>键</th><th>说明</th></tr></thead>
        <tbody>${r.columns.map(c => `<tr><td>${esc(c.field)}</td><td>${esc(c.type)}</td><td>${esc(c.key)}</td><td>${esc(c.comment)}</td></tr>`).join('')}</tbody></table>
      </div>
      <div class="card-head" style="margin-top:12px"><h3>数据预览（前 50 行）</h3></div>
      <div class="table-wrap" style="max-height:240px; overflow-y:auto">
        <table class="data-table">
          <thead><tr>${r.columns.map(c => `<th>${esc(c.field)}</th>`).join('')}</tr></thead>
          <tbody>${r.rows.map(row => `<tr>${r.columns.map(c => `<td>${esc(row[c.field])}</td>`).join('')}</tr>`).join('')}</tbody>
        </table>
      </div>
    </div>`;
}

async function dbExport(table) {
  const r = await api().db_export_csv(table);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok) fillDbCsvSelect();
}

async function dbImport() {
  const f = $('#dbCsvSelect').value;
  if (!f) return showToast('请先选择 CSV 文件', 'err');
  const r = await api().db_import_csv(f);
  $('#dbImportMsg').textContent = r.ok ? '✅ ' + r.msg : '❌ ' + r.msg;
  showToast(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok) renderDb();
}

let dbSyncPoll = null;
async function dbSync() {
  const r = await api().db_sync();
  if (!r.ok) return showToast(r.msg || '启动失败', 'err');
  $('#dbSyncBox').classList.remove('hidden');
  if (dbSyncPoll) clearInterval(dbSyncPoll);
  dbSyncPoll = setInterval(async () => {
    const p = await api().db_progress(r.id);
    $('#dbSyncBar').style.width = (p.pct || 0) + '%';
    $('#dbSyncMsg').textContent = p.message;
    $('#dbSyncLog').innerHTML = (p.logs || []).map(l => `<div class="err">${esc(l)}</div>`).join('');
    if (p.done) {
      clearInterval(dbSyncPoll);
      dbSyncPoll = null;
      $('#dbSyncMsg').textContent = p.error ? '❌ ' + p.error : (p.message + '（若因数据源超时失败，请稍后重试）');
    }
  }, 2000);
}

// ---------------- 智能查询 ----------------
let lastQueryText = '';
let lastKlineDays = 160;
async function doQuery() {
  const text = $('#queryInput').value.trim();
  if (!text) { showToast('请输入股票名称或代码', 'info'); return; }
  const btn = $('#btnQuery');
  btn.disabled = true;
  lastQueryText = text;
  try {
    const r = await api().query_stock(text);
    renderQuotes(r.quotes || []);
    renderAnalysis(r.analysis);
    if (!r.ok) showToast(r.msg, 'err');
    loadKline();
  } finally { btn.disabled = false; }
}

async function loadKline() {
  const box = $('#klineBox');
  if (!lastQueryText) return;
  $('#klineName').textContent = '';
  box.innerHTML = '<p class="muted">正在加载 K 线...</p>';
  try {
    const r = await api().query_kline(lastQueryText, lastKlineDays);
    if (r.ok && r.kline && r.kline.length) {
      $('#klineName').textContent = r.name || '';
      renderKline(r.kline);
    } else {
      box.innerHTML = '<p class="muted">未获取到 K 线数据</p>';
    }
  } catch (e) {
    box.innerHTML = '<p class="muted">K 线加载失败</p>';
  }
}

function renderKline(data, boxId) {
  const box = boxId ? document.querySelector(boxId) : $('#klineBox');
  if (!box) return;
  const W = 940, H = 350, PL = 46, PR = 16, PT = 14;
  const volH = 66, priceH = H - PT - volH - 26;
  const volTop = PT + priceH + 10;
  const n = data.length;
  const cw = (W - PL - PR) / n;
  const up = '#ef4444', down = '#22c55e';
  const maColors = { ma5: '#f5c451', ma10: '#7fb0ff', ma20: '#c084fc' };

  let minP = Infinity, maxP = -Infinity, maxV = 0;
  data.forEach(k => {
    minP = Math.min(minP, k.l, k.ma5, k.ma10, k.ma20);
    maxP = Math.max(maxP, k.h, k.ma5, k.ma10, k.ma20);
    maxV = Math.max(maxV, k.v || 0);
  });
  const pad = (maxP - minP) * 0.06 || 1;
  minP -= pad; maxP += pad;
  const pY = p => PT + (maxP - p) / (maxP - minP) * priceH;
  const vY = v => v === 0 ? volTop + volH : volTop + volH - (v / (maxV || 1)) * volH;

  let svg = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto">`;
  // 网格 + 价格刻度
  for (let i = 0; i <= 5; i++) {
    const g = minP + (maxP - minP) * i / 5;
    const y = pY(g);
    svg += `<line x1="${PL}" y1="${y}" x2="${W - PR}" y2="${y}" stroke="#1c2740" stroke-width="1"/>`;
    svg += `<text x="${PL - 6}" y="${y + 4}" fill="#5c6b8f" font-size="11" text-anchor="end">${g.toFixed(2)}</text>`;
  }
  // 日期刻度（首/中/尾）
  const idx = [0, Math.floor(n / 2), n - 1];
  idx.forEach(i => {
    const x = PL + cw * i + cw / 2;
    svg += `<text x="${x}" y="${H - 6}" fill="#5c6b8f" font-size="11" text-anchor="middle">${data[i].d.slice(5)}</text>`;
  });
  // 均线
  ['ma5', 'ma10', 'ma20'].forEach(ma => {
    let pts = data.map((k, i) => `${PL + cw * i + cw / 2},${pY(k[ma])}`).join(' ');
    svg += `<polyline points="${pts}" fill="none" stroke="${maColors[ma]}" stroke-width="1.4" opacity="0.9"/>`;
  });
  // K线
  data.forEach((k, i) => {
    const x = PL + cw * i + cw / 2;
    const color = k.c >= k.o ? up : down;
    const wickTop = pY(k.h), wickBot = pY(k.l);
    const bodyTop = pY(Math.max(k.o, k.c)), bodyBot = pY(Math.min(k.o, k.c));
    const bw = Math.max(2, cw * 0.62);
    svg += `<line x1="${x}" y1="${wickTop}" x2="${x}" y2="${wickBot}" stroke="${color}" stroke-width="1"/>`;
    svg += `<rect x="${x - bw / 2}" y="${bodyTop}" width="${bw}" height="${Math.max(1.2, bodyBot - bodyTop)}" fill="${color}" rx="0.5"/>`;
    // 成交量
    svg += `<rect x="${x - bw / 2}" y="${vY(k.v)}" width="${bw}" height="${Math.max(1, volTop + volH - vY(k.v))}" fill="${color}" opacity="0.45"/>`;
  });
  svg += '</svg>';
  box.innerHTML = svg;
}

function renderQuotes(rows) {
  const tb = $('#queryTable tbody');
  if (!rows.length) { tb.innerHTML = '<tr class="empty"><td colspan="8">未查到该标的行情</td></tr>'; return; }
  tb.innerHTML = rows.map(r => `
    <tr>
      <td>${r['symbol']}</td><td>${r['name']}</td>
      <td>${fmt(r['price'])}</td>
      <td class="${pctClass(r['change_percent'])}">${signed(r['change_percent'], 2)}%</td>
      <td>${fmt(r['open'])}</td><td>${fmt(r['high'])}</td><td>${fmt(r['low'])}</td>
      <td>${fmt(r['volume'], 0)}</td>
    </tr>`).join('');
}

function scoreBar(pct) {
  const v = Math.max(0, Math.min(100, Number(pct) || 0));
  return `<span class="score-bar"><i style="width:${v}%"></i></span>`;
}

function renderAnalysis(a) {
  const box = $('#analysisBox');
  if (!a) { box.innerHTML = '<p class="muted">查询后展示技术面 + 基本面 + AI 预测综合评分</p>'; return; }
  const lv = String(a.level).toLowerCase();
  box.innerHTML = `
    <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px">
      <div class="score-big" style="color:${a.total_score >= 80 ? '#f5c451' : a.total_score >= 65 ? '#7fb0ff' : '#8a97b5'}">${fmt(a.total_score)}</div>
      <div>
        <span class="tag tag-${lv}">级别 ${a.level}</span>
        <div class="muted" style="margin-top:4px">${a.verdict}</div>
      </div>
    </div>
    <div class="score-row"><span>技术面</span>${scoreBar(a.tech_score)}<b>${fmt(a.tech_score)}</b></div>
    <div class="score-row"><span>基本面</span>${scoreBar(a.fund_score)}<b>${fmt(a.fund_score)}</b></div>
    <div class="score-row"><span>AI 预测</span>${scoreBar(a.ai_score)}<b>${fmt(a.ai_score)}</b></div>
    <div class="card-head" style="margin-top:12px;border-top:1px dashed var(--line);padding-top:10px">
      <h3 style="font-size:14px">💎 估值评估</h3>
    </div>
    ${renderValuation(a.valuation)}
    <p class="muted" style="margin-top:8px">${a.ai_text || ''}${a.elapsed ? `（分析耗时 ${a.elapsed}s）` : ''}</p>`;
}

function renderValuation(v) {
  if (!v) return '<p class="muted">—</p>';
  const pe = v.pe, peg = v.peg;
  const verdictCls = !pe || (pe && pe < 30) ? 'up' : 'down';
  return `
    <div class="score-row"><span>市盈率 PE</span><b>${pe === null || pe === undefined ? '-' : fmt(pe) + ' 倍'}</b></div>
    <div class="score-row"><span>PEG</span><b>${peg === null || peg === undefined ? '-' : fmt(peg, 2)}</b></div>
    <p class="${verdictCls}" style="font-weight:600;margin-top:6px">${v.verdict || ''}</p>
    <ul class="val-detail">${(v.detail || []).map(d => `<li>${d}</li>`).join('')}</ul>`;
}

// ---------------- 我的持仓 / 资金管理 ----------------
function fmtN(v, d = 2) { return (v === null || v === undefined || isNaN(v)) ? '-' : Number(v).toFixed(d); }
function money(v) { return (v === null || v === undefined || isNaN(v)) ? '-' : Number(v).toLocaleString('zh-CN', { maximumFractionDigits: 2 }); }

async function renderPortfolio() {
  try {
    const p = await api().portfolio_get();
    if (!p.ok) { showToast(p.msg, 'err'); return; }
    $('#pfCash').value = p.cash;
    $('#pfSummary').innerHTML = `
      <div class="stat-card"><div class="lbl">总资产</div><div class="val">${money(p.total_value)}</div></div>
      <div class="stat-card"><div class="lbl">可用资金</div><div class="val">${money(p.cash)}</div></div>
      <div class="stat-card"><div class="lbl">持仓盈亏</div><div class="val ${p.total_profit >= 0 ? 'up' : 'down'}">${signed(p.total_profit, 2)} (${signed(p.total_profit_pct, 2)}%)</div></div>
      <div class="stat-card"><div class="lbl">持仓数</div><div class="val">${p.positions.length} 只</div></div>`;
    const tb = $('#pfTable');
    if (!p.positions.length) { tb.innerHTML = '<tr class="empty"><td colspan="8">暂无持仓</td></tr>'; }
    else {
      tb.innerHTML = p.positions.map(x => `
        <tr>
          <td>${x.code}</td><td>${x.name}</td><td>${x.volume}</td>
          <td>${fmtN(x.avg_price)}</td><td>${fmtN(x.current_price)}</td>
          <td>${money(x.current_value)}</td>
          <td class="${x.profit >= 0 ? 'up' : 'down'}">${signed(x.profit, 2)}</td>
          <td class="${x.profit >= 0 ? 'up' : 'down'}">${signed(x.profit_pct, 2)}%</td>
        </tr>`).join('');
    }
    const hb = $('#pfHistory');
    const recs = p.history || [];
    const fr = await api().fund_records_get();
    const lines = [];
    (fr.records || []).forEach(r => lines.push(`<div>${r.date} <b>${r.type}</b> ${money(r.amount)} 元 · 余额 ${money(r.balance)} ${r.note ? '· ' + r.note : ''}</div>`));
    lines.push('<div class="muted">—— 交易记录 ——</div>');
    recs.forEach(r => {
      const prof = r.action === 'sell' ? ` <span class="${(r.profit||0)>=0?'ok':'err'}">${signed(r.profit,2)}</span>` : '';
      lines.push(`<div>${r.date} <b>${r.action === 'buy' ? '买入' : '卖出'}</b> ${r.stock_name}(${r.stock_code}) ${r.volume}股 @ ${fmtN(r.price)} ${prof}</div>`);
    });
    hb.innerHTML = lines.join('') || '<p class="muted">暂无记录</p>';
  } catch (e) { showToast('加载持仓失败: ' + e, 'err'); }
}

async function pfAdd() {
  const code = $('#pfAddCode').value.trim();
  const name = $('#pfAddName').value.trim();
  const volume = $('#pfAddVol').value;
  const price = $('#pfAddPrice').value;
  if (!code) return showToast('请输入股票代码', 'err');
  const r = await api().portfolio_add(code, name || code, volume, price);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok) renderPortfolio();
}

async function pfSell() {
  const code = $('#pfSellCode').value.trim();
  const volume = $('#pfSellVol').value;
  const price = $('#pfSellPrice').value;
  if (!code) return showToast('请输入股票代码', 'err');
  const r = await api().portfolio_sell(code, volume, price);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok) renderPortfolio();
}

async function pfRefresh() {
  showToast('刷新持仓现价中...');
  const r = await api().portfolio_refresh_prices();
  showToast(r.msg, r.ok ? 'ok' : 'err');
  renderPortfolio();
}

async function pfSetCash() {
  const r = await api().portfolio_set_cash($('#pfCash').value);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  renderPortfolio();
}

async function frAdd() {
  const r = await api().fund_record_add($('#frType').value, $('#frAmount').value, $('#frNote').value);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok) renderPortfolio();
}

async function frClear() {
  const r = await api().fund_records_clear();
  showToast(r.msg, r.ok ? 'ok' : 'err');
  renderPortfolio();
}

// ---------------- 基金交易 ----------------
async function renderFunds() {
  try {
    const f = await api().fund_portfolio_get();
    const tb = $('#fundTable');
    if (!f.rows.length) { tb.innerHTML = '<tr class="empty"><td colspan="8">暂无基金持仓</td></tr>'; }
    else {
      tb.innerHTML = f.rows.map(x => `
        <tr>
          <td>${x.code}</td><td>${x.name}</td><td>${x.volume}</td>
          <td>${fmtN(x.avg_nav, 4)}</td><td>${fmtN(x.current_nav, 4)}</td>
          <td>${money(x.current_value)}</td>
          <td class="${x.profit >= 0 ? 'up' : 'down'}">${signed(x.profit, 2)}</td>
          <td><button class="btn ghost sm" onclick="fundSellPrompt('${x.code}')">卖出</button></td>
        </tr>`).join('');
    }
    const hb = $('#fundHistory');
    hb.innerHTML = (f.history || []).map(r => {
      const prof = r.action === 'sell' ? ` <span class="${(r.profit||0)>=0?'ok':'err'}">${signed(r.profit,2)}</span>` : '';
      return `<div>${r.date} <b>${r.action === 'buy' ? '买入' : '卖出'}</b> ${r.fund_name}(${r.fund_code}) ${r.volume}份 @ ${fmtN(r.nav, 4)} ${prof}</div>`;
    }).join('') || '<p class="muted">暂无记录</p>';
  } catch (e) { showToast('加载基金持仓失败: ' + e, 'err'); }
}

async function fundLookup() {
  const code = $('#fundCode').value.trim();
  if (!code) return showToast('请输入基金代码', 'err');
  showToast('查询中...');
  const r = await api().fund_lookup(code);
  if (!r.ok) { $('#fundInfo').innerHTML = '<span class="err">' + r.msg + '</span>'; return showToast(r.msg, 'err'); }
  $('#fundInfo').innerHTML = `<b>${r.name}</b>（${r.fund_type}）净值 ${r.nav}（${r.nav_date}）涨跌 ${signed(r.change, 2)}%`;
  $('#fundNav').value = r.nav;
  $('#fundCode').dataset.name = r.name;
}

async function fundBuy() {
  const code = $('#fundCode').value.trim();
  const name = $('#fundCode').dataset.name || code;
  const nav = $('#fundNav').value;
  const volume = $('#fundVol').value;
  if (!code) return showToast('请先查询基金代码', 'err');
  const r = await api().fund_buy(code, name, nav, volume);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok) renderFunds();
}

function fundSellPrompt(code) {
  const nav = prompt('卖出净值（元）：', '1.0');
  if (nav === null) return;
  const vol = prompt('卖出份额：', '100');
  if (vol === null) return;
  (async () => {
    const r = await api().fund_sell(code, nav, vol);
    showToast(r.msg, r.ok ? 'ok' : 'err');
    if (r.ok) renderFunds();
  })();
}

async function fundRefreshNav() {
  showToast('刷新基金净值中...');
  const r = await api().fund_refresh_nav();
  showToast(r.msg, r.ok ? 'ok' : 'err');
  renderFunds();
}

// ---------------- 热门板块 ----------------
async function renderSector() {
  const kind = $('#sectorKind').value;
  const tb = $('#sectorTable tbody');
  tb.innerHTML = '<tr class="empty"><td colspan="5">加载中...</td></tr>';
  try {
    const r = await api().sector_hot(kind, 20);
    if (!r.rows.length) { tb.innerHTML = '<tr class="empty"><td colspan="5">暂无数据' + (r.msg ? '：' + r.msg : '') + '</td></tr>'; return; }
    tb.innerHTML = r.rows.map((x, i) => `
      <tr style="cursor:pointer" onclick="loadSectorCons('${x.name}')">
        <td>${i + 1}</td><td>${x.name}</td>
        <td>${fmt(x.price)}</td>
        <td class="${pctClass(x.change_pct)}">${signed(x.change_pct, 2)}%</td>
        <td><span class="up">${x.up}</span> / <span class="down">${x.down}</span></td>
      </tr>`).join('');
  } catch (e) { tb.innerHTML = '<tr class="empty"><td colspan="5">加载失败: ' + e + '</td></tr>'; }
}

async function loadSectorCons(name) {
  const kind = $('#sectorKind').value;
  $('#sectorName').textContent = '正在加载【' + name + '】成分股...';
  const tb = $('#sectorConsTable tbody');
  tb.innerHTML = '<tr class="empty"><td colspan="6">加载中...</td></tr>';
  try {
    const r = await api().sector_constituents(kind, name);
    $('#sectorName').textContent = '【' + r.name + '】共 ' + r.rows.length + ' 只';
    if (!r.rows.length) { tb.innerHTML = '<tr class="empty"><td colspan="6">暂无数据' + (r.msg ? '：' + r.msg : '') + '</td></tr>'; return; }
    tb.innerHTML = r.rows.map(x => `
      <tr>
        <td>${x.code}</td><td>${x.name}</td>
        <td>${fmt(x.price)}</td>
        <td class="${pctClass(x.change_pct)}">${signed(x.change_pct, 2)}%</td>
        <td>${fmt(x.amount)}</td><td>${fmt(x.turnover)}</td>
      </tr>`).join('');
  } catch (e) { $('#sectorName').textContent = ''; tb.innerHTML = '<tr class="empty"><td colspan="6">加载失败: ' + e + '</td></tr>'; }
}

async function sectorSearch() {
  const kind = $('#sectorKind').value;
  const kw = $('#sectorSearch').value.trim();
  if (!kw) return showToast('请输入板块关键词', 'err');
  const r = await api().sector_search(kind, kw);
  if (!r.rows.length) { $('#sectorHit').innerHTML = '未找到匹配板块'; return; }
  $('#sectorHit').innerHTML = r.rows.slice(0, 10).map(x =>
    `<button class="btn ghost sm" onclick="loadSectorCons('${x.name}')">${x.name}</button>`
  ).join(' ');
}

// ---------------- 实时行情 ----------------
async function renderRealtime() {
  try {
    const o = await api().rt_overview();
    if (o.ok) {
      $('#rtOverview').innerHTML = `
        <div class="stat-row">
          <div class="stat-card"><div class="lbl">总数</div><div class="val">${o.total}</div></div>
          <div class="stat-card"><div class="lbl">上涨</div><div class="val up">${o.up}</div></div>
          <div class="stat-card"><div class="lbl">下跌</div><div class="val down">${o.down}</div></div>
          <div class="stat-card"><div class="lbl">涨停</div><div class="val up">${o.limit_up}</div></div>
          <div class="stat-card"><div class="lbl">跌停</div><div class="val down">${o.limit_down}</div></div>
          <div class="stat-card"><div class="lbl">成交额(亿)</div><div class="val">${fmt(o.turnover_yi)}</div></div>
        </div>
        <div class="muted" style="margin-top:6px">更新于 ${o.update_time}</div>`;
    } else {
      $('#rtOverview').innerHTML = '<span class="err">' + o.msg + '</span>';
    }
    const idx = await api().rt_indices();
    $('#rtIndices').innerHTML = (idx.rows || []).map(i => `
      <div class="stat-card"><div class="lbl">${i.name}</div>
        <div class="val">${fmt(i.price)}</div>
        <div class="${pctClass(i.pct)}">${signed(i.pct, 2)}%</div></div>`).join('') || '<p class="muted">暂无数据</p>';
  } catch (e) { $('#rtOverview').innerHTML = '<span class="err">' + e + '</span>'; }
}

async function rtQuery() {
  const codes = $('#rtCodes').value.trim();
  if (!codes) return showToast('请输入代码', 'err');
  const type = $('#rtType').value;
  const r = await api().rt_quotes(codes, type);
  const tb = $('#rtTable tbody');
  if (!r.rows || !r.rows.length) { tb.innerHTML = '<tr class="empty"><td colspan="5">暂无数据</td></tr>'; return; }
  tb.innerHTML = r.rows.map(x => `
    <tr>
      <td>${x.symbol || ''}</td><td>${x.name || ''}</td>
      <td>${fmt(x.price)}</td>
      <td class="${pctClass(x.change_percent)}">${signed(x.change_percent, 2)}%</td>
      <td>${fmt(x.amount)}</td>
    </tr>`).join('');
}

// ---------------- 数据抓取 ----------------
let crawlPoll = null;
function pollCrawl(jid) {
  if (crawlPoll) clearInterval(crawlPoll);
  crawlPoll = setInterval(async () => {
    const p = await api().crawl_progress(jid);
    $('#crawlProgress').classList.remove('hidden');
    $('#crawlBar').style.width = (p.pct || 0) + '%';
    $('#crawlMsg').textContent = p.message;
    if (p.done) {
      clearInterval(crawlPoll);
      crawlPoll = null;
      const ok = (p.results || []).filter(r => r.ok);
      const bad = (p.results || []).filter(r => !r.ok);
      $('#crawlResult').innerHTML = `完成：成功 ${ok.length} 只，失败 ${bad.length} 只。<br>` +
        bad.map(r => `❌ ${r.code}: ${r.msg}`).join('<br>');
      if (p.results && p.results.length) renderCrawlList();
    }
  }, 1500);
}

async function startCrawl() {
  const codes = $('#crawlCodes').value.trim();
  if (!codes) return showToast('请输入股票代码', 'err');
  const r = await api().crawl_history(codes, $('#crawlStart').value, $('#crawlEnd').value);
  if (!r.ok) return showToast(r.msg, 'err');
  $('#crawlResult').innerHTML = '';
  pollCrawl(r.id);
}

async function renderCrawlList() {
  try {
    const r = await api().crawl_list();
    $('#crawlDir').textContent = r.dir;
    const tb = $('#crawlTable tbody');
    if (!r.files.length) { tb.innerHTML = '<tr class="empty"><td colspan="3">暂无文件</td></tr>'; return; }
    tb.innerHTML = r.files.map(f => `
      <tr><td>${f.name}</td><td>${f.size_kb}</td>
        <td><button class="btn danger sm" onclick="delCrawl('${f.name}')">删除</button></td></tr>`).join('');
  } catch (e) { showToast('加载失败: ' + e, 'err'); }
}

async function delCrawl(name) {
  const r = await api().crawl_delete(name);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  renderCrawlList();
}

// ---------------- AI 回测 ----------------
async function loadBtModels() {
  try {
    const ms = await api().backtest_models();
    const opts = ms.map(m => `<option value="${m.id}">${m.id}. ${m.name}（${m.speed}）</option>`).join('');
    $('#btModel').innerHTML = opts;
    $('#monModel').innerHTML = opts;
  } catch (e) { /* 忽略 */ }
}

let btPoll = null;
function pollBt(jid) {
  if (btPoll) clearInterval(btPoll);
  btPoll = setInterval(async () => {
    const p = await api().backtest_progress(jid);
    $('#btProgress').classList.remove('hidden');
    $('#btBar').style.width = (p.pct || 0) + '%';
    $('#btMsg').textContent = p.message;
    if (p.done) {
      clearInterval(btPoll);
      btPoll = null;
      if (p.error) {
        $('#btResult').innerHTML = `<span class="err">❌ ${p.error}</span>`;
        showToast('回测失败', 'err');
      } else if (p.result) {
        const r = p.result;
        const cls = r.returns >= 0 ? 'up' : 'down';
        const perRows = (r.per_stock || []).map(x =>
          `<tr><td>${x.code}</td><td>${esc(x.name || '')}</td><td class="${x.buy_hold >= 0 ? 'up' : 'down'}">${signed(x.buy_hold, 2)}%</td></tr>`).join('');
        const skips = (r.capital_skipped || []).map(s =>
          `${s[0]}(1手约${money(s[1] * 100)})`).join('、');
        const capital = r.initial_cash || 500000;
        $('#btResult').innerHTML = `
          <div class="stat-row">
            <div class="stat-card"><div class="lbl">模型</div><div class="val" style="font-size:14px">${r.model_name}</div></div>
            <div class="stat-card"><div class="lbl">股票数</div><div class="val">${r.stock_count || 1}</div></div>
            <div class="stat-card"><div class="lbl">收益率</div><div class="val ${cls}">${signed(r.returns, 2)}%</div></div>
            <div class="stat-card"><div class="lbl">胜率</div><div class="val">${fmt(r.win_rate * 100, 1)}%</div></div>
            <div class="stat-card"><div class="lbl">交易次数</div><div class="val">${r.total_trades}</div></div>
            <div class="stat-card"><div class="lbl">买入持有</div><div class="val">${signed(r.buy_hold_return, 2)}%</div></div>
            <div class="stat-card"><div class="lbl">期末资产</div><div class="val">${money(r.final_value)}</div></div>
          </div>
          ${perRows ? `<div class="table-wrap" style="margin-top:10px;max-height:180px">
            <table class="data-table"><thead><tr><th>代码</th><th>名称</th><th>区间涨幅</th></tr></thead><tbody>${perRows}</tbody></table></div>` : ''}
          ${skips ? `<p class="err" style="margin-top:8px">⚠️ 资金不足未买入：${skips}（初始资金 ${money(capital)} 元不够 1 手）</p>` : ''}
          <p class="muted" style="margin-top:8px">组合回测：共享一个资金账户（初始 ${money(capital)} 元），多只股票按共同交易日同时交易。收益率=策略收益；买入持有=等权躺赢基准。</p>`;
      }
    }
  }, 2000);
}

async function btStart() {
  const code = $('#btCode').value.trim();
  if (!code) return showToast('请输入股票代码', 'err');
  $('#btResult').innerHTML = '回测运行中...';
  const cap = Number($('#btCapital').value) || 500000;
  const r = await api().backtest_start(code, $('#btStart').value, $('#btEnd').value, $('#btModel').value, cap);
  if (!r.ok) return showToast(r.msg, 'err');
  pollBt(r.id);
}

// ---------------- 盘中监控 ----------------
let monPoll = null;
function startMonPoll() {
  if (monPoll) return;
  monPoll = setInterval(monStatus, 3000);
}
async function monStart() {
  const codes = $('#monCodes').value.trim();
  if (!codes) return showToast('请输入股票代码', 'err');
  const r = await api().monitor_start(codes, $('#monModel').value, $('#monInterval').value);
  showToast(r.msg, r.ok ? 'ok' : 'err');
  if (r.ok) { startMonPoll(); monStatus(); }
}

async function monStop() {
  const r = await api().monitor_stop();
  showToast(r.msg, r.ok ? 'ok' : 'err');
  monStatus();
}

async function monStatus() {
  try {
    const st = await api().monitor_status();
    $('#monStatus').innerHTML = st.running
      ? `<p class="big up">🟢 监控运行中（${st.codes.length} 只，每 ${st.interval}s）</p>`
      : '<p class="muted">监控未启动</p>';
    const tb = $('#monTable tbody');
    if (!st.signals.length) { tb.innerHTML = '<tr class="empty"><td colspan="7">暂无信号</td></tr>'; }
    else {
      tb.innerHTML = st.signals.map(s => `
        <tr>
          <td>${s.code}</td><td>${fmt(s.price)}</td>
          <td class="${pctClass(s.change_pct)}">${signed(s.change_pct, 2)}%</td>
          <td>${s.rsi === null || s.rsi === undefined ? '-' : s.rsi}</td>
          <td>${s.macd === null || s.macd === undefined ? '-' : s.macd}</td>
          <td>${s.ai}</td><td>${s.action}</td>
        </tr>`).join('');
    }
    $('#monLog').innerHTML = (st.log || []).map(l =>
      `<div class="${l.indexOf('ERROR') >= 0 ? 'err' : ''}">${l}</div>`).join('') || '<p class="muted">暂无日志</p>';
    $('#monLog').scrollTop = $('#monLog').scrollHeight;
  } catch (e) { /* 忽略 */ }
}

// ---------------- 全自动交易 ----------------
function toggleTradingMode() {
  const mode = $('#tradingMode').value;
  const real = mode === 'easytrader';
  $('#fieldCapital').classList.toggle('hidden', real);
  $('#easytraderBox').classList.toggle('hidden', !real);
  $('#tradingGuide').classList.toggle('hidden', !real);
}

async function testConnect() {
  const btn = $('#btnTradingTest');
  btn.disabled = true;
  btn.textContent = '⏳ 检测中...';
  try {
    const r = await api().trading_test_connect(readTradingCfg());
    showToast(r.msg, r.ok ? 'ok' : 'err');
    if (r.exe_path) $('#exePath').value = r.exe_path;
  } catch (e) {
    showToast('检测失败: ' + e, 'err');
  } finally {
    btn.disabled = false;
    btn.textContent = '🔌 检测连接';
  }
}

async function detectExe() {
  try { $('#exePath').value = await api().detect_ths_exe(); } catch (e) { /* 忽略 */ }
}

function readTradingCfg() {
  const pool = $('#tradingPool').value
    .split(/[\n,，;；\s]+/)
    .map(s => s.trim())
    .filter(Boolean);
  return {
    mode: $('#tradingMode').value,
    capital: Number($('#capital').value) || 100000,
    broker: $('#broker').value,
    user: $('#user').value,
    password: $('#password').value,
    exe_path: $('#exePath').value,
    stocks: pool,
    max_single: Number($('#maxSingle').value) / 100 || 0.2,
    max_total: Number($('#maxTotal').value) / 100 || 0.8,
    stop_loss: Number($('#stopLoss').value) || 5,
    take_profit: Number($('#takeProfit').value) || 10,
    max_daily_trades: Number($('#maxDailyTrades').value) || 999999,
    // AI 混合策略
    ai_enabled: !!(($('#aiEnabled') && $('#aiEnabled').checked)),
    ai_api_key: ($('#aiApiKey').value || '').trim(),
    ai_api_url: ($('#aiApiUrl').value || 'https://api.openai.com/v1/chat/completions').trim(),
    ai_model: ($('#aiModel').value || 'gpt-4o-mini').trim(),
    // 仓位配置
    max_total_ratio: Number($('#maxTotalRatio').value) / 100 || 0.9,
    ai_min_lot: !!(($('#aiMinLot') && $('#aiMinLot').checked)),
  };
}

// 根据股票池数量自动算出较优的风控参数（单只/总仓位、止损止盈）
function autoTuneParams(n) {
  const N = Math.max(1, n || 1);
  // 单只上限：约均分 100/N，取整到5%，限制在 5%~30%
  const single = Math.max(5, Math.min(30, Math.round(100 / N / 5) * 5));
  // 总仓位：股票越多越能满仓分散，限制 30%~85%，且不超过 单只上限×数量
  const total = Math.max(30, Math.min(85, Math.round((35 + N * 4.5) / 5) * 5));
  const totalCap = Math.min(total, single * N);
  // 股票少时单票风险高，止损放宽、止盈提高；多票时用标准 5/10
  const wide = N < 8;
  return { single, total: totalCap, stop: wide ? 6 : 5, take: wide ? 12 : 10 };
}

async function importWatchToPool() {
  try {
    const items = await api().watch_list();
    const pairs = (items || []).map(i => {
      let c = (i.code || i.stock || i[0] || '');
      c = String(c).replace(/^(sh|sz|bj)/i, '');
      return { code: c.trim(), name: i.name || '' };
    }).filter(x => x.code);
    showPoolPick(pairs, '导入自选股');
  } catch (e) {
    showToast('导入自选股失败: ' + e, 'err');
  }
}

async function importPosToPool() {
  try {
    const p = await api().portfolio_get();
    const pairs = (p.positions || []).map(x => ({ code: x.code, name: x.name || '' }));
    showPoolPick(pairs, '导入持仓');
  } catch (e) {
    showToast('导入持仓失败: ' + e, 'err');
  }
}

async function importAllocToPool() {
  const sel = getCheckedRows('allocTable');
  if (!sel.length) { showToast('请先在推荐榜单「按金额推荐」结果里勾选股票', 'err'); return; }
  showPoolPick(sel, '导入金额推荐');
}

function showPoolPick(pairs, source) {
  const wrap = $('#poolPickWrap');
  if (!wrap) return;
  if (!pairs || !pairs.length) { showToast('没有可导入的股票', 'err'); return; }
  window.poolPickPairs = pairs;
  window.poolPickSource = source;
  wrap.classList.remove('hidden');
  renderPoolPick(pairs);
  wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// 渲染候选股票表格：带名称/现价/1手成本/可买手数，并标记买不起的
async function renderPoolPick(pairs) {
  const tb = $('#poolPickTable tbody');
  const sel = $('#poolSelAll'); if (sel) sel.checked = false;
  const cap = Number($('#capital').value) || 100000;
  const singlePct = (Number($('#maxSingle').value) || 20) / 100;
  const perStock = cap * singlePct;
  // 去掉重复代码
  const uniq = [];
  const seen = {};
  pairs.forEach(x => { const c = x.code; if (c && !seen[c]) { seen[c] = true; uniq.push(x); } });
  // 批量拉实时行情（名称/现价/涨跌幅）
  const quotes = {};
  try {
    const r = await api().rt_quotes(uniq.map(x => x.code).join(','), 'stock');
    (r.rows || []).forEach(q => { if (q && q.symbol) quotes[String(q.symbol).replace(/^(sh|sz|bj)/i, '')] = q; });
  } catch (e) { /* 行情失败则无现价 */ }
  let rows = uniq.map(x => {
    const q = quotes[x.code];
    const name = (q && q.name) || x.name || x.code;
    const price = Number(q && q.price) || Number(x.price) || 0;
    const pct = Number(q && q.change_percent);
    const cost1 = price > 0 ? price * 100 : (Number(x.cost1) || 0);
    const lots = cost1 > 0 ? Math.max(0, Math.min(Math.floor(cap / cost1), Math.floor(perStock / cost1))) : 0;
    return { code: x.code, name, price, pct: isNaN(pct) ? (x.pct === undefined || x.pct === null ? null : Number(x.pct)) : pct, cost1, lots, score: Number(x.score) || 0 };
  });
  rows = sortPoolRows(rows, $('#poolSortSel').value);
  const total = rows.length;
  const affordable = rows.filter(r => r.lots > 0).length;
  const notAfford = rows.filter(r => r.lots <= 0);
  if (!rows.length) {
    tb.innerHTML = '<tr class="empty"><td colspan="9">没有候选股票</td></tr>';
    $('#poolPickSummary').textContent = '没有候选股票';
    return;
  }
  tb.innerHTML = rows.map(r => {
    const bad = r.lots <= 0;
    const tip = bad ? '⚠️ 买不起1手' : `${r.lots} 手`;
    return `
    <tr data-code="${esc(String(r.code))}" data-name="${esc(String(r.name || ''))}" class="${bad ? 'row-dim' : ''}">
      <td><input type="checkbox" class="row-check" onchange="updateSelectAll('poolPickTable')"></td>
      <td>${r.code}</td><td>${esc(r.name)}</td>
      <td>${r.price > 0 ? fmt(r.price) : '-'}</td>
      <td class="${r.pct === null ? '' : pctClass(r.pct)}">${r.pct === null ? '-' : signed(r.pct, 2) + '%'}</td>
      <td>${r.cost1 > 0 ? fmt(r.cost1) : '-'}</td>
      <td class="${bad ? 'err' : ''}">${r.lots}</td>
      <td>${r.score ? '<b>' + fmt(r.score) + '</b>' : '—'}</td><td>${tip}</td>
    </tr>`;
  }).join('');
  const skipNote = notAfford.length
    ? `<span class="err">，其中 ${notAfford.length} 只买不起 1 手（初始资金 ${fmt(cap)} 元、单只上限 ${Math.round(singlePct * 100)}%）</span>` : '';
  $('#poolPickSummary').textContent =
    `候选 ${total} 只：${affordable} 只能买得起${skipNote}。点「✅ 加入选中」把勾选的写入交易池（自动去重+调参）。`;
}

function poolSortKey() {
  const v = $('#poolSortSel').value;
  const map = { score: r => r.score || 0, pct: r => (r.pct === null ? -999 : r.pct), cost: r => r.cost1, price: r => r.price };
  return map[v] || map.score;
}

function sortPoolRows(rows, key) {
  const fn = poolSortKey();
  return [...rows].sort((a, b) => {
    const x = fn(a), y = fn(b);
    if (key === 'score') return y - x; // 活跃分从高到低
    if (key === 'pct') return y - x;   // 涨幅从高到低
    return x - y;                       // 成本/现价从低到高
  });
}

function addCheckedToPool() {
  const sel = getCheckedRows('poolPickTable');
  if (!sel.length) { showToast('请先勾选要加入交易池的股票', 'err'); return; }
  // 合并到现有池：去重
  const cur = ($('#tradingPool').value || '').split(/[\n,，;；\s]+/).map(s => s.trim()).filter(Boolean);
  const pool = [...cur];
  const seen = {}; cur.forEach(c => { seen[c] = true; });
  sel.forEach(x => { if (!seen[x.code]) { pool.push(x.code); seen[x.code] = true; } });
  $('#tradingPool').value = pool.join('\n');
  const p = autoTuneParams(pool.length);
  $('#maxSingle').value = p.single;
  $('#maxTotal').value = p.total;
  $('#stopLoss').value = p.stop;
  $('#takeProfit').value = p.take;
  $('#poolTips').textContent =
    `已加入 ${sel.length} 只（共 ${pool.length} 只），自动调参：单只 ${p.single}%、总仓 ${p.total}%、止损 ${p.stop}%、止盈 ${p.take}%`;
  saveTradingConfig();
  showToast(`✅ 已加入 ${sel.length} 只到交易池（共 ${pool.length} 只）`, 'ok');
}

function closePoolPick() {
  const wrap = $('#poolPickWrap');
  if (wrap) wrap.classList.add('hidden');
}

async function smartPickStocks() {
  const btn = $('#btnSmartPick');
  btn.disabled = true;
  try {
    const cap = Number($('#capital').value) || 100000;
    if (cap <= 0) { showToast('请先填写初始资金', 'err'); return; }
    const singlePct = (Number($('#maxSingle').value) || 20) / 100;
    const perStock = cap * singlePct;
    // 多档预算分别尝试，确保返回足够多的候选
    let rows = [];
    const targets = [perStock, cap * 0.5, cap];
    for (const t of targets) {
      const r = await api().ranking_budget(t, 60, 'mix');
      if (r && r.ok && r.rows && r.rows.length) { rows = r.rows; break; }
    }
    if (!rows.length) { showToast('智能选股失败：未获取到候选股票', 'err'); return; }
    const pairs = rows.map(x => ({
      code: String(x['代码'] || '').trim(),
      name: x['名称'] || '',
      price: Number(x['现价']) || 0,
      pct: x['涨跌幅'] === undefined || x['涨跌幅'] === null ? null : Number(x['涨跌幅']),
      score: Number(x['活跃分']) || 0,
      cost1: (Number(x['1手成本']) || 0) || (Number(x['现价']) || 0) * 100,
    })).filter(x => x.code && x.price > 0);
    window.poolPickPairs = pairs;
    window.poolPickSource = '智能选股';
    const wrap = $('#poolPickWrap');
    wrap.classList.remove('hidden');
    const tb = $('#poolPickTable tbody');
    const sel = $('#poolSelAll'); if (sel) sel.checked = false;
    let out = pairs.map(r => {
      const lots = r.cost1 > 0 ? Math.max(0, Math.min(Math.floor(cap / r.cost1), Math.floor(perStock / r.cost1))) : 0;
      return { code: r.code, name: r.name, price: r.price, pct: r.pct, cost1: r.cost1, lots, score: r.score };
    });
    out = sortPoolRows(out, 'score');
    const affordable = out.filter(r => r.lots > 0).length;
    if (!out.length) {
      tb.innerHTML = '<tr class="empty"><td colspan="9">没有候选股票</td></tr>';
    } else {
      tb.innerHTML = out.map(r => {
        const bad = r.lots <= 0;
        const tip = bad ? '⚠️ 买不起1手' : `${r.lots} 手`;
        return `
        <tr data-code="${esc(String(r.code))}" data-name="${esc(String(r.name || ''))}" class="${bad ? 'row-dim' : ''}">
          <td><input type="checkbox" class="row-check" onchange="updateSelectAll('poolPickTable')"></td>
          <td>${r.code}</td><td>${esc(r.name)}</td>
          <td>${fmt(r.price)}</td>
          <td class="${r.pct === null ? '' : pctClass(r.pct)}">${r.pct === null ? '-' : signed(r.pct, 2) + '%'}</td>
          <td>${fmt(r.cost1)}</td>
          <td class="${bad ? 'err' : ''}">${r.lots}</td>
          <td><b>${fmt(r.score)}</b></td><td>${tip}</td>
        </tr>`;
      }).join('');
    }
    $('#poolPickSummary').textContent =
      `智能选股（按 ${fmt(cap)} 元、单只上限 ${Math.round(singlePct * 100)}%）从全市场挑出 ${out.length} 只，其中 ${affordable} 只能买得起。勾选后「✅ 加入选中」。`;
    wrap.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  } catch (e) {
    showToast('智能选股失败: ' + e, 'err');
  } finally {
    btn.disabled = false;
  }
}

function clearPool() {
  $('#tradingPool').value = '';
  $('#poolTips').textContent = '留空则使用默认股票池';
  const wrap = $('#poolPickWrap');
  if (wrap) wrap.classList.add('hidden');
  saveTradingConfig();
}

// 保存当前交易表单到后端（股票池+参数），重启后自动恢复
async function saveTradingConfig() {
  try { await api().trading_save_config(readTradingCfg()); } catch (e) { /* 忽略 */ }
}

// 启动时恢复上次的交易配置（股票池/参数/模式）
async function restoreTradingConfig() {
  try {
    const c = await api().trading_get_config();
    if (!c) return;
    if (c.mode && $('#tradingMode').value) $('#tradingMode').value = c.mode;
    if (c.capital) $('#capital').value = c.capital;
    if (c.broker) $('#broker').value = c.broker;
    if (c.user) $('#user').value = c.user;
    if (c.exe_path) $('#exePath').value = c.exe_path;
    if (c.max_single) $('#maxSingle').value = Math.round(c.max_single * 100);
    if (c.max_total) $('#maxTotal').value = Math.round(c.max_total * 100);
    if (c.stop_loss) $('#stopLoss').value = c.stop_loss;
    if (c.take_profit) $('#takeProfit').value = c.take_profit;
    if (c.max_daily_trades) $('#maxDailyTrades').value = c.max_daily_trades;
    if (Array.isArray(c.stocks) && c.stocks.length) {
      $('#tradingPool').value = c.stocks.join('\n');
      $('#poolTips').textContent = `已恢复上次股票池 ${c.stocks.length} 只`;
    }
    // AI 配置恢复
    if (c.ai_enabled !== undefined) $('#aiEnabled').checked = !!c.ai_enabled;
    if (c.ai_api_key) $('#aiApiKey').value = c.ai_api_key;
    if (c.ai_api_url) $('#aiApiUrl').value = c.ai_api_url;
    if (c.ai_model) $('#aiModel').value = c.ai_model;
    toggleAiConfig();
    toggleTradingMode();
  } catch (e) { /* 忽略 */ }
}

async function tradingStart() {
  const btn = $('#btnTradingStart');
  btn.disabled = true;
  try {
    const r = await api().trading_start(readTradingCfg());
    showToast(r.msg, r.ok ? 'ok' : 'err');
    saveTradingConfig();
  } finally {
    btn.disabled = false;
    pollTradingStatus();
  }
}

async function tradingStop() {
  const r = await api().trading_stop();
  showToast(r.msg, r.ok ? 'ok' : 'err');

  pollTradingStatus();
}

// -- AI 混合策略配置 --
function toggleAiConfig() {
  const en = $('#aiEnabled').checked;
  if ($('#aiConfigFields')) $('#aiConfigFields').classList.toggle('hidden', !en);
}

async function aiConfigSave() {
  const cfg = {
    ai_enabled: $('#aiEnabled').checked,
    ai_api_key: ($('#aiApiKey').value || '').trim(),
    ai_api_url: ($('#aiApiUrl').value || 'https://api.openai.com/v1/chat/completions').trim(),
    ai_model: ($('#aiModel').value || 'gpt-4o-mini').trim(),
  };
  const r = await api().ai_strategy_config_save(cfg);
  showToast(r.msg, r.ok ? 'ok' : 'err');
}

async function aiConfigLoad() {
  try {
    const r = await api().ai_strategy_config_get();
    if (!r.ok) { showToast(r.msg, 'err'); return; }
    $('#aiEnabled').checked = !!r.ai_enabled;
    $('#aiApiKey').value = r.ai_api_key || '';
    $('#aiApiUrl').value = r.ai_api_url || 'https://api.openai.com/v1/chat/completions';
    $('#aiModel').value = r.ai_model || 'gpt-4o-mini';
    toggleAiConfig();
    showToast('AI配置已加载', 'ok');
  } catch (e) { showToast('加载失败: ' + e, 'err'); }
}

async function pollAiStatus() {
  try {
    const r = await api().ai_strategy_status();
    const box = $('#aiStatusBox');
    const text = $('#aiStatusText');
    if (!box || !text) return;
    if (!r.ok) { box.classList.add('hidden'); return; }
    const s = r.status || {};
    box.classList.remove('hidden');
    const mode = s.signals_generated > 0
      ? (s.last_anomalies && Object.keys(s.last_anomalies).length > 0 ? 'AI异动分析中' : '决策树监测中')
      : '等待交易信号';
    text.textContent = mode + (s.ai_enabled ? ' | AI已启用' : ' | AI未启用');
  } catch (e) { /* ignore */ }
}
setInterval(pollAiStatus, 10000);


let tradingPollTimer = null;
async function pollTradingStatus() {
  try {
    const st = await api().trading_status();
    const box = $('#engineStatus');
    if (st.running) {
      box.innerHTML = `<p class="big up">🟢 运行中</p><p class="muted">状态详情：${JSON.stringify(st.engine || {})}</p>`;
    } else if (st.auto_restart) {
      box.innerHTML = `<p class="big warn">⏳ 引擎未运行（已设自动续跑）</p><p class="muted">服务器/本程序重启后会自动恢复交易，点击「停止」可取消续跑</p>`;
    } else {
      box.innerHTML = '<p class="muted">引擎未启动</p>';
    }
    const log = $('#tradingLog');
    log.innerHTML = (st.logs || []).map(l => {
      const cls = l.indexOf('[ERROR]') >= 0 ? 'err' : (l.indexOf('成功') >= 0 ? 'ok' : '');
      return `<div class="${cls}">${l}</div>`;
    }).join('') || '<p class="muted">暂无日志</p>';
    log.scrollTop = log.scrollHeight;
  } catch (e) { /* 忽略 */ }
  renderReturns();
}

// ---------------- 收益视图 ----------------
let lastReturnsCurve = '';
async function renderReturns() {
  try {
    const r = await api().trading_returns();
    if (!r || !r.ok) return;
    const cls = v => v >= 0 ? 'up' : 'down';
    $('#returnsStats').innerHTML = `
      <div class="stat-card"><div class="lbl">总资产</div><div class="val">${money(r.total_assets)}</div></div>
      <div class="stat-card"><div class="lbl">初始资金</div><div class="val">${money(r.initial_balance)}</div></div>
      <div class="stat-card"><div class="lbl">总收益</div><div class="val ${cls(r.total_profit)}">${signed(r.total_profit, 2)} (${signed(r.total_profit_pct, 2)}%)</div></div>
      <div class="stat-card"><div class="lbl">今日收益</div><div class="val ${cls(r.today_profit)}">${signed(r.today_profit, 2)}</div></div>
      <div class="stat-card"><div class="lbl">已实现盈亏</div><div class="val ${cls(r.realized)}">${signed(r.realized, 2)}</div></div>
      <div class="stat-card"><div class="lbl">浮动盈亏</div><div class="val ${cls(r.unrealized)}">${signed(r.unrealized, 2)}</div></div>
      <div class="stat-card"><div class="lbl">交易/卖出次数</div><div class="val">${r.trade_count} / ${r.sell_count}</div></div>
      <div class="stat-card"><div class="lbl">胜率</div><div class="val">${r.win_rate === null || r.win_rate === undefined ? '-' : fmtN(r.win_rate, 1) + '%'}</div></div>`;

    const curve = (r.equity_curve || []).map(p => ({ t: p.t, v: Number(p.v) || 0 }));
    if (curve.length) drawReturnsChart(curve, r.initial_balance);

    const byStock = r.by_stock || [];
    $('#returnsStocks').innerHTML = byStock.length
      ? `<div class="table-wrap" style="max-height:200px; overflow-y:auto">
          <table class="data-table"><thead><tr><th>代码</th><th>名称</th><th>卖出次数</th><th>已实现盈亏</th></tr></thead>
          <tbody>${byStock.map(s => `<tr>
            <td>${s.code}</td><td>${s.name}</td><td>${s.trades}</td>
            <td class="${s.realized >= 0 ? 'up' : 'down'}">${signed(s.realized, 2)}</td>
          </tr>`).join('')}</tbody></table></div>`
      : '<p class="muted">暂无已实现盈亏数据</p>';

    const trades = r.trades || [];
    $('#returnsTrades').innerHTML = trades.length
      ? `<div class="table-wrap" style="max-height:240px; overflow-y:auto">
          <table class="data-table"><thead><tr><th>时间</th><th>方向</th><th>代码</th><th>名称</th><th>价格</th><th>数量(手)</th><th>金额</th><th>已实现盈亏</th></tr></thead>
          <tbody>${trades.map(t => {
            const sideCls = t.side === 'SELL' ? 'down' : 'up';
            const profit = t.profit === undefined ? '' : `<td class="${t.profit >= 0 ? 'up' : 'down'}">${signed(t.profit, 2)}</td>`;
            return `<tr><td>${t.date}</td><td class="${sideCls}">${t.side === 'SELL' ? '卖出' : '买入'}</td><td>${t.stock_code}</td><td>${t.stock_name}</td><td>${fmtN(t.price)}</td><td>${t.volume}</td><td>${money(t.amount)}</td>${profit}</tr>`;
          }).join('')}</tbody></table></div>`
      : '<p class="muted">暂无交易记录</p>';
  } catch (e) { /* 忽略 */ }
}

function drawReturnsChart(curve, initialBalance) {
  const key = JSON.stringify(curve);
  if (key === lastReturnsCurve) return;
  lastReturnsCurve = key;
  const cv = $('#returnsChart');
  if (!cv) return;
  const ctx = cv.getContext('2d');
  const W = cv.parentElement.clientWidth || 900;
  const H = 220;
  const dpr = window.devicePixelRatio || 1;
  cv.width = W * dpr; cv.height = H * dpr;
  cv.style.width = W + 'px'; cv.style.height = H + 'px';
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, W, H);

  const padL = 70, padR = 16, padT = 16, padB = 28;
  const vs = curve.map(p => p.v);
  let mn = Math.min(...vs, initialBalance || 0);
  let mx = Math.max(...vs, initialBalance || 0);
  if (mn === mx) { mn -= 1; mx += 1; }
  const span = mx - mn;
  mn -= span * 0.08; mx += span * 0.08;
  const X = i => padL + (W - padL - padR) * (vs.length <= 1 ? 0.5 : i / (vs.length - 1));
  const Y = v => padT + (H - padT - padB) * (1 - (v - mn) / (mx - mn));

  ctx.strokeStyle = '#3b4358'; ctx.fillStyle = '#8b93a7'; ctx.font = '11px sans-serif'; ctx.lineWidth = 1;
  for (let g = 0; g <= 4; g++) {
    const v = mn + (mx - mn) * g / 4;
    const y = Y(v);
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(W - padR, y); ctx.stroke();
    ctx.textAlign = 'right'; ctx.fillText(v.toFixed(0), padL - 6, y + 4);
  }
  ctx.textAlign = 'center';
  const step = Math.max(1, Math.floor(curve.length / 8));
  for (let i = 0; i < curve.length; i += step) {
    ctx.fillStyle = '#8b93a7'; ctx.fillText(curve[i].t.slice(5, 16), X(i), H - 8);
  }
  const initY = Y(initialBalance || vs[0]);
  ctx.strokeStyle = '#5a6480'; ctx.setLineDash([5, 4]);
  ctx.beginPath(); ctx.moveTo(padL, initY); ctx.lineTo(W - padR, initY); ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = '#8b93a7'; ctx.textAlign = 'left'; ctx.fillText('初始资金 ' + Number(initialBalance).toLocaleString(), W - padR - 120, initY - 6);

  const grad = ctx.createLinearGradient(0, padT, 0, H - padB);
  grad.addColorStop(0, 'rgba(56,189,248,0.35)');
  grad.addColorStop(1, 'rgba(56,189,248,0.02)');
  ctx.beginPath();
  ctx.moveTo(X(0), Y(vs[0]));
  vs.forEach((v, i) => ctx.lineTo(X(i), Y(v)));
  ctx.lineTo(X(vs.length - 1), H - padB);
  ctx.lineTo(X(0), H - padB);
  ctx.closePath();
  ctx.fillStyle = grad; ctx.fill();

  ctx.beginPath();
  ctx.moveTo(X(0), Y(vs[0]));
  vs.forEach((v, i) => ctx.lineTo(X(i), Y(v)));
  ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 2; ctx.stroke();
}

// ---------------- 初始化 ----------------
let booted = false;
function boot() {
  if (booted) return;
  booted = true;
  $('#marketMode').textContent = marketModeText();
  on('#btnRankingRefresh', 'click', rankingRefresh);
  on('#btnAllocate', 'click', allocateBudget);
  on('#btnRankImport', 'click', rankImport);
  on('#btnAllocImport', 'click', rankImport);
  on('#btnAllocAdd', 'click', allocAddToWatchlist);
  on('#btnShortImport', 'click', () => importRanking('short'));
  on('#btnLongImport', 'click', () => importRanking('long'));
  on('#rankBudget', 'keydown', e => { if (e.key === 'Enter') allocateBudget(); });
  on('#btnShortAdd', 'click', () => addAllToWatchlist('short'));
  on('#btnLongAdd', 'click', () => addAllToWatchlist('long'));
  on('#btnWatchAdd', 'click', addWatch);
  on('#btnWatchRefresh', 'click', watchRefresh);
  on('#btnQuery', 'click', doQuery);
  on('#queryInput', 'keydown', e => { if (e.key === 'Enter') doQuery(); });
  on('#selKlineDays', 'change', e => {
    lastKlineDays = parseInt(e.target.value, 10) || 160;
    loadKline();
  });
  on('#btnTradingStart', 'click', tradingStart);
  on('#btnTradingStop', 'click', tradingStop);
  on('#btnReturnsRefresh', 'click', renderReturns);
  on('#btnTradingTest', 'click', testConnect);
  on('#tradingMode', 'change', toggleTradingMode);
  on('#btnImportWatch', 'click', importWatchToPool);
  on('#btnImportAlloc', 'click', importAllocToPool);
  on('#btnImportPos', 'click', importPosToPool);
  on('#btnSmartPick', 'click', smartPickStocks);
  on('#btnPoolAddChecked', 'click', addCheckedToPool);
  on('#btnPoolPickClose', 'click', closePoolPick);
  on('#poolSortSel', 'change', () => {
    if (window.poolPickPairs && window.poolPickPairs.length) renderPoolPick(window.poolPickPairs);
  });
  on('#btnClearPool', 'click', clearPool);
  on('#btnResetAccount', 'click', async () => {
    const r = await api().trading_reset_account();
    showToast(r.msg, r.ok ? 'ok' : 'err');
    if (r.ok) pollTradingStatus();
  });
  on('#btnPfRefresh', 'click', pfRefresh);
  on('#btnPfClear', 'click', async () => { await api().portfolio_clear(); renderPortfolio(); });
  on('#btnPfAdd', 'click', pfAdd);
  on('#btnPfSell', 'click', pfSell);
  on('#btnPfSetCash', 'click', pfSetCash);
  on('#btnFrAdd', 'click', frAdd);
  on('#btnFrClear', 'click', frClear);
  on('#btnFundLookup', 'click', fundLookup);
  on('#btnFundBuy', 'click', fundBuy);
  on('#btnFundNav', 'click', fundRefreshNav);
  on('#btnFundClear', 'click', async () => { await api().fund_clear(); renderFunds(); });
  on('#fundCode', 'keydown', e => { if (e.key === 'Enter') fundLookup(); });
  on('#btnSectorRefresh', 'click', renderSector);
  on('#btnSectorSearch', 'click', sectorSearch);
  on('#sectorSearch', 'keydown', e => { if (e.key === 'Enter') sectorSearch(); });
  on('#sectorKind', 'change', renderSector);
  on('#btnRtQuery', 'click', rtQuery);
  on('#btnRtRefresh', 'click', renderRealtime);
  on('#rtCodes', 'keydown', e => { if (e.key === 'Enter') rtQuery(); });
  on('#btnCrawl', 'click', startCrawl);
  on('#btnCrawlList', 'click', renderCrawlList);
  on('#btnBtStart', 'click', btStart);
  on('#btnBtImportWatch', 'click', btImportWatch);
  on('#btnBtImportPos', 'click', btImportPos);
  on('#btnBtImportAlloc', 'click', btImportAlloc);
  on('#btnMonStart', 'click', monStart);
  on('#btnMonStop', 'click', monStop);
  on('#btnRefreshStorage', 'click', renderStorage);
  on('#btnOpenData', 'click', async () => showToast((await api().storage_open_folder('data')).msg));
  on('#btnOpenAnalysis', 'click', async () => showToast((await api().storage_open_folder('analysis')).msg));
  on('#btnAnalysisStart', 'click', analysisStart);
  on('#btnOpenReport', 'click', async () => showToast((await api().analysis_open_report()).msg));
  on('#btnDbRefresh', 'click', renderDb);
  on('#btnDbImport', 'click', dbImport);
  on('#btnDbSync', 'click', dbSync);
  loadBtModels();
  on('#btnLegacy', 'click', async () => {
    const r = await api().open_legacy();
    showToast(r.msg, r.ok ? 'ok' : 'err');
  });
  toggleTradingMode();
  detectExe();
  restoreTradingConfig();
  if (window.pywebview) {
    loadIndices().then(() => {
      renderWatchlist().then(() => {
        document.title = 'READY-' + (document.querySelectorAll('.indice').length);
      });
    });
    setInterval(loadIndices, 60000);
    setInterval(autoRefreshRanking, 60000);
  } else {
    // HTTP 模式（浏览器/手机远程访问）
    loadIndices().then(() => renderWatchlist());
    setInterval(loadIndices, 60000);
    setInterval(autoRefreshRanking, 60000);
    showToast('远程模式已连接，交易引擎将持续运行', 'ok');
  }
  tradingPollTimer = setInterval(pollTradingStatus, 3000);
}

document.addEventListener('DOMContentLoaded', () => {
  if (window.pywebview && window.pywebview.api) {
    boot();
  } else {
    window.addEventListener('pywebviewready', boot);
    setTimeout(boot, 1800); // 兜底：桥接就绪稍慢时；HTTP 模式直接走这里
  }
});
