const 租约台 = {
  async getJSON(url) {
    const r = await fetch(url, { credentials: 'same-origin' });
    if (r.status === 401) {
      location.href = '/login';
      throw new Error('未登录');
    }
    return r.json();
  },
  async postJSON(url, body) {
    const r = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify(body || {}),
    });
    const data = await r.json();
    if (r.status === 401) location.href = '/login';
    if (!r.ok) throw new Error(data.错误 || '请求失败');
    return data;
  },
  安全文本(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  },
  状态徽章(状态) {
    const cls = String(状态 || '').replace(/\s/g, '');
    return `<span class="徽章 ${租约台.安全文本(cls)}">${租约台.安全文本(状态)}</span>`;
  },
  占用比(已占, 容量) {
    const cap = Number(容量) || 1;
    const used = Number(已占) || 0;
    const pct = Math.min(100, Math.round((used / cap) * 100));
    return { pct, label: `${used}/${cap} (${pct}%)` };
  },
  格式化时刻(t) {
    if (!t) return '—';
    const d = new Date(t);
    if (Number.isNaN(d.getTime())) return t;
    return d.toLocaleString('zh-CN', { hour12: false });
  },
  async 刷新概览指标(containerId) {
    const o = await 租约台.getJSON('/api/概览');
    const box = document.getElementById(containerId);
    if (!box) return;
    box.innerHTML = '';
    const keys = ['资源池数', '启用池', '租约总数', '生效中', '待生效', '回收匣待处置', '心跳条数'];
    for (const k of keys) {
      if (o[k] == null) continue;
      const d = document.createElement('div');
      d.className = '卡';
      d.innerHTML = `<small>${租约台.安全文本(k)}</small><b>${租约台.安全文本(o[k])}</b>`;
      box.appendChild(d);
    }
  },
};

window.租约台 = 租约台;