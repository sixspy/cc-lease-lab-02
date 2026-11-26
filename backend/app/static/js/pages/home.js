(async function renderHome() {
  const c = await 租约台.getJSON('/api/仓情');
  document.getElementById('主链说明').textContent = c.主链 + ' · ' + c.技术;
  await 租约台.刷新概览指标('指标');
  const rows = await 租约台.getJSON('/api/租约');
  const tb = document.getElementById('租约表');
  tb.innerHTML = '';
  for (const r of rows.slice(0, 12)) {
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + 租约台.安全文本(r.租约号) + '</td>' +
      '<td>' + 租约台.安全文本(r.池键) + '</td>' +
      '<td>' + 租约台.安全文本(r.租户) + '</td>' +
      '<td>' + 租约台.状态徽章(r.状态) + '</td>' +
      '<td>' + 租约台.安全文本(租约台.格式化时刻(r.到期时刻)) + '</td>';
    tb.appendChild(tr);
  }
  const 台账 = await 租约台.getJSON('/api/台账/租户');
  if (台账.length) {
    const tip = document.createElement('p');
    tip.className = '说明';
    tip.textContent = '活跃租户前三：' + 台账.slice(0, 3).map((t) => t.租户 + '(' + t.活跃数 + ')').join('、');
    document.querySelector('.页头').appendChild(tip);
  }
  document.getElementById('互证钮').onclick = async () => {
    const rep = await 租约台.postJSON('/api/互证/跑', {});
    document.getElementById('互证出').textContent = JSON.stringify(rep, null, 2);
    await 租约台.刷新概览指标('指标');
  };
})();