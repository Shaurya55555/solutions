const API = '';

// ── State ──
let currentSkip = 0;
const PAGE_SIZE = 20;
let filters = {};

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  checkHealth();
  setupTabs();
  setupFilters();
  loadTransactions();
});

// ── Health ──
async function checkHealth() {
  const badge = document.getElementById('health-badge');
  try {
    const res = await fetch(`${API}/health`);
    const data = await res.json();
    badge.textContent = data.status === 'ok' ? '● Healthy' : '● Down';
    badge.className = data.status === 'ok' ? 'health-badge' : 'health-badge error';
  } catch {
    badge.textContent = '● Offline';
    badge.className = 'health-badge error';
  }
}

// ── Tabs ──
function setupTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById(btn.dataset.tab).classList.add('active');

      if (btn.dataset.tab === 'tab-summary') loadSummary();
      if (btn.dataset.tab === 'tab-discrepancies') loadDiscrepancies();
    });
  });
}

// ── Filters ──
function setupFilters() {
  document.getElementById('filter-form').addEventListener('submit', e => {
    e.preventDefault();
    currentSkip = 0;
    filters = {
      merchant_id: document.getElementById('f-merchant').value.trim(),
      status: document.getElementById('f-status').value,
      start_date: document.getElementById('f-start').value,
      end_date: document.getElementById('f-end').value,
    };
    loadTransactions();
  });

  document.getElementById('clear-filters').addEventListener('click', () => {
    document.getElementById('filter-form').reset();
    filters = {};
    currentSkip = 0;
    loadTransactions();
  });
}

// ── Transactions ──
async function loadTransactions() {
  const tbody = document.getElementById('txn-tbody');
  tbody.innerHTML = '<tr><td colspan="6" class="loading">Loading…</td></tr>';

  const params = new URLSearchParams();
  params.set('skip', currentSkip);
  params.set('limit', PAGE_SIZE);
  if (filters.merchant_id) params.set('merchant_id', filters.merchant_id);
  if (filters.status) params.set('status', filters.status);
  if (filters.start_date) params.set('start_date', filters.start_date + 'T00:00:00');
  if (filters.end_date) params.set('end_date', filters.end_date + 'T23:59:59');

  try {
    const res = await fetch(`${API}/transactions?${params}`);
    const data = await res.json();

    if (!data.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No transactions found</td></tr>';
      updatePagination(0);
      return;
    }

    tbody.innerHTML = data.map(t => `
      <tr onclick="openDetail('${t.id}')">
        <td title="${t.id}">${t.id.slice(0, 12)}…</td>
        <td>${t.merchant_id}</td>
        <td>₹${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td>${t.currency}</td>
        <td><span class="badge ${t.status}">${t.status.replace('payment_', '')}</span></td>
        <td>${new Date(t.updated_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}</td>
      </tr>
    `).join('');

    updatePagination(data.length);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="6" class="empty-state">Error loading transactions</td></tr>`;
  }
}

function updatePagination(count) {
  document.getElementById('page-info').textContent = `Showing ${currentSkip + 1}–${currentSkip + count}`;
  document.getElementById('prev-btn').disabled = currentSkip === 0;
  document.getElementById('next-btn').disabled = count < PAGE_SIZE;
}

function changePage(dir) {
  currentSkip += dir * PAGE_SIZE;
  if (currentSkip < 0) currentSkip = 0;
  loadTransactions();
}

// ── Transaction Detail ──
async function openDetail(id) {
  const overlay = document.getElementById('modal-overlay');
  const body = document.getElementById('modal-body');
  body.innerHTML = '<div class="loading">Loading…</div>';
  overlay.classList.add('open');

  try {
    const res = await fetch(`${API}/transactions/${id}`);
    const t = await res.json();

    let html = `
      <div class="detail-row"><span class="key">Transaction ID</span><span class="val">${t.id}</span></div>
      <div class="detail-row"><span class="key">Merchant</span><span class="val">${t.merchant ? t.merchant.name : t.merchant_id}</span></div>
      <div class="detail-row"><span class="key">Amount</span><span class="val">₹${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</span></div>
      <div class="detail-row"><span class="key">Currency</span><span class="val">${t.currency}</span></div>
      <div class="detail-row"><span class="key">Status</span><span class="val"><span class="badge ${t.status}">${t.status.replace('payment_', '')}</span></span></div>
      <div class="detail-row"><span class="key">Created</span><span class="val">${new Date(t.created_at).toLocaleString()}</span></div>
      <div class="detail-row"><span class="key">Updated</span><span class="val">${new Date(t.updated_at).toLocaleString()}</span></div>
    `;

    if (t.events && t.events.length) {
      html += '<h4>Event History</h4>';
      html += '<table><thead><tr><th>Type</th><th>Timestamp</th></tr></thead><tbody>';
      t.events.forEach(e => {
        html += `<tr><td><span class="badge ${e.event_type}">${e.event_type.replace('payment_', '')}</span></td><td>${new Date(e.timestamp).toLocaleString()}</td></tr>`;
      });
      html += '</tbody></table>';
    }

    body.innerHTML = html;
  } catch {
    body.innerHTML = '<div class="empty-state">Failed to load details</div>';
  }
}

function closeModal() {
  document.getElementById('modal-overlay').classList.remove('open');
}

document.getElementById('modal-overlay').addEventListener('click', e => {
  if (e.target === e.currentTarget) closeModal();
});

// ── Reconciliation Summary ──
async function loadSummary() {
  const container = document.getElementById('summary-content');
  container.innerHTML = '<div class="loading">Loading…</div>';

  try {
    const res = await fetch(`${API}/reconciliation/summary`);
    const data = await res.json();

    if (!data.length) {
      container.innerHTML = '<div class="empty-state">No summary data</div>';
      return;
    }

    // Aggregate stats
    let totalTxns = 0, totalAmt = 0;
    const statusCounts = {};
    data.forEach(r => {
      totalTxns += r.total_transactions;
      totalAmt += r.total_amount;
      statusCounts[r.status] = (statusCounts[r.status] || 0) + r.total_transactions;
    });

    let html = '<div class="stats-row">';
    html += `<div class="stat-card"><div class="label">Total Transactions</div><div class="value">${totalTxns.toLocaleString()}</div></div>`;
    html += `<div class="stat-card"><div class="label">Total Amount</div><div class="value">₹${totalAmt.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div></div>`;
    for (const [status, count] of Object.entries(statusCounts)) {
      html += `<div class="stat-card"><div class="label">${status.replace('payment_', '')}</div><div class="value">${count.toLocaleString()}</div></div>`;
    }
    html += '</div>';

    // Table
    html += '<div class="card"><h2>Breakdown by Date & Merchant</h2>';
    html += '<table><thead><tr><th>Date</th><th>Merchant</th><th>Status</th><th>Count</th><th>Amount</th></tr></thead><tbody>';
    data.slice(0, 100).forEach(r => {
      html += `<tr>
        <td>${r.date}</td>
        <td>${r.merchant_id}</td>
        <td><span class="badge ${r.status}">${r.status.replace('payment_', '')}</span></td>
        <td>${r.total_transactions}</td>
        <td>₹${r.total_amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
      </tr>`;
    });
    html += '</tbody></table></div>';

    container.innerHTML = html;
  } catch {
    container.innerHTML = '<div class="empty-state">Error loading summary</div>';
  }
}

// ── Discrepancies ──
async function loadDiscrepancies() {
  const container = document.getElementById('discrepancy-content');
  container.innerHTML = '<div class="loading">Loading…</div>';

  try {
    const res = await fetch(`${API}/reconciliation/discrepancies`);
    const data = await res.json();

    let html = '';

    // Failed but settled
    html += '<div class="discrepancy-section"><h3><span class="dot red"></span> Settled with Prior Failure</h3>';
    if (data.failed_but_settled.length) {
      html += renderDiscrepancyTable(data.failed_but_settled);
    } else {
      html += '<div class="empty-state">None found ✓</div>';
    }
    html += '</div>';

    // Stuck
    html += '<div class="discrepancy-section"><h3><span class="dot orange"></span> Stuck Transactions (>48h)</h3>';
    if (data.stuck_transactions.length) {
      html += renderDiscrepancyTable(data.stuck_transactions);
    } else {
      html += '<div class="empty-state">None found ✓</div>';
    }
    html += '</div>';

    // Conflicting
    html += '<div class="discrepancy-section"><h3><span class="dot blue"></span> Conflicting State Transitions</h3>';
    if (data.conflicting_transitions.length) {
      html += renderDiscrepancyTable(data.conflicting_transitions);
    } else {
      html += '<div class="empty-state">None found ✓</div>';
    }
    html += '</div>';

    container.innerHTML = html;
  } catch {
    container.innerHTML = '<div class="empty-state">Error loading discrepancies</div>';
  }
}

function renderDiscrepancyTable(items) {
  let html = '<table><thead><tr><th>Transaction ID</th><th>Merchant</th><th>Amount</th><th>Status</th></tr></thead><tbody>';
  items.forEach(t => {
    html += `<tr onclick="openDetail('${t.id}')">
      <td title="${t.id}">${t.id.slice(0, 12)}…</td>
      <td>${t.merchant_id}</td>
      <td>₹${t.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
      <td><span class="badge ${t.status}">${t.status.replace('payment_', '')}</span></td>
    </tr>`;
  });
  html += '</tbody></table>';
  return html;
}
