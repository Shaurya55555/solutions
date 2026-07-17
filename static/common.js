const API = '';

/**
 * Injects the shared sidebar navigation into the page.
 */
function initNav(activePage) {
  const sidebar = document.getElementById('sidebar');
  if (!sidebar) return;

  const pages = [
    { id: 'home',          href: '/',                  icon: '🏠', label: 'Home',            badge: '' },
    { id: 'events',        href: '/ui/events',         icon: '📨', label: 'Ingest Events',   badge: 'POST' },
    { id: 'transactions',  href: '/ui/transactions',   icon: '💳', label: 'Transactions',    badge: 'GET' },
    { id: 'transaction',   href: '/ui/transaction',    icon: '🔍', label: 'Lookup Txn',      badge: 'GET' },
    { id: 'summary',       href: '/ui/summary',        icon: '📊', label: 'Summary',         badge: 'GET' },
    { id: 'discrepancies', href: '/ui/discrepancies',  icon: '⚠️', label: 'Discrepancies',   badge: 'GET' },
  ];

  let html = `
    <a href="/" class="sidebar-logo"><span class="icon">🍓</span><span>StrawberryPay</span></a>
    <ul class="sidebar-nav">
  `;

  pages.forEach(p => {
    const cls = p.id === activePage ? ' active' : '';
    const badgeCls = p.badge === 'POST' ? 'post' : 'get';
    const badgeHtml = p.badge ? `<span class="sidebar-badge ${badgeCls}">${p.badge}</span>` : '';
    html += `<li><a href="${p.href}" class="${cls}"><span class="nav-icon">${p.icon}</span><span>${p.label}</span>${badgeHtml}</a></li>`;
  });

  html += `</ul><div class="sidebar-footer">StrawberryPay API v1.0</div>`;
  sidebar.innerHTML = html;
}
