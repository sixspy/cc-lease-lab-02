(function () {
  const 链接 = [
    ['/', '租约总览', 'index'],
    ['/资源池.html', '资源池', 'pools'],
    ['/租约台.html', '租约台', 'leases'],
    ['/续约心跳.html', '续约心跳', 'heartbeat'],
    ['/回收匣.html', '回收匣', 'reclaim'],
    ['/租账互证.html', '租账互证', 'reconcile'],
    ['/租账规.html', '租账规', 'rules'],
  ];
  const path = location.pathname.replace(/\/$/, '') || '/';
  const page = document.body.dataset.page || '';
  const nav = document.getElementById('侧栏导航');
  if (!nav) return;
  for (const [href, label, key] of 链接) {
    const a = document.createElement('a');
    a.href = href;
    a.textContent = label;
    const hit = href === path || (href !== '/' && path.endsWith(href)) || page === key;
    if (hit) a.classList.add('亮');
    nav.appendChild(a);
  }
  const out = document.getElementById('退出钮');
  if (out) {
    out.onclick = () =>
      fetch('/api/登出', { method: 'POST', credentials: 'same-origin' }).then(() => {
        location.href = '/login';
      });
  }
})();