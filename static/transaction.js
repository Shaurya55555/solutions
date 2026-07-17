document.addEventListener('DOMContentLoaded', () => {
  initNav('transaction');

  const params = new URLSearchParams(window.location.search);
  const idFromUrl = params.get('id');
  if (idFromUrl) {
    document.getElementById('txn-id-input').value = idFromUrl;
    lookupTransaction(idFromUrl);
  }

  document.getElementById('lookup-btn').addEventListener('click', () => {
    const id = document.getElementById('txn-id-input').value.trim();
    if (id) lookupTransaction(id);
  });

  document.getElementById('txn-id-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      const id = e.target.value.trim();
      if (id) lookupTransaction(id);
    }
  });
});

async function lookupTransaction(id) {
  const area = document.getElementById('detail-area');
  area.innerHTML = '<div class="loading">Loading…</div>';

  try {
    const res = await fetch(`${API}/transactions/${encodeURIComponent(id)}`);
    const data = await res.json();

    document.getElementById('res-status').textContent = res.status;
    document.getElementById('res-status').className = 'status-code ' + (res.ok ? 'ok' : 'error');
    document.getElementById('res-body').textContent = JSON.stringify(data, null, 2);
    document.getElementById('response-box').classList.add('show');

    if (!res.ok) {
      area.innerHTML = '<div class="card"><div class="empty-state">Transaction not found</div></div>';
      return;
    }

    const merchantDisplay = data.merchant ? data.merchant.name + ' (' + data.merchant.id + ')' : data.merchant_id;
    let html = '<div class="card"><h2>Transaction Details</h2>';
    html += row('Transaction ID', '<span class="mono">' + data.id + '</span>');
    html += row('Merchant', merchantDisplay);
    html += row('Amount', '₹' + data.amount.toLocaleString('en-IN', { minimumFractionDigits: 2 }));
    html += row('Currency', data.currency);
    html += row('Status', '<span class="badge ' + data.status + '">' + data.status.replace('payment_', '') + '</span>');
    html += row('Created', new Date(data.created_at).toLocaleString());
    html += row('Updated', new Date(data.updated_at).toLocaleString());
    html += '</div>';

    if (data.events && data.events.length) {
      html += '<div class="card"><h2>Event History</h2><table><thead><tr><th>Event ID</th><th>Type</th><th>Timestamp</th></tr></thead><tbody>';
      data.events.forEach(e => {
        html += '<tr><td class="mono">' + e.id + '</td>';
        html += '<td><span class="badge ' + e.event_type + '">' + e.event_type.replace('payment_', '') + '</span></td>';
        html += '<td>' + new Date(e.timestamp).toLocaleString() + '</td></tr>';
      });
      html += '</tbody></table></div>';
    }

    area.innerHTML = html;
  } catch (err) {
    area.innerHTML = '<div class="card"><div class="empty-state">Error: ' + err.message + '</div></div>';
  }
}

function row(key, val) {
  return '<div class="detail-row"><span class="key">' + key + '</span><span class="val">' + val + '</span></div>';
}
