async function 填池下拉(sel) {
  const rows = await 租约台.getJSON('/api/资源池');
  sel.innerHTML = '';
  for (const r of rows) {
    if (!r.启用) continue;
    const o = document.createElement('option');
    o.value = r.池键;
    o.textContent = r.名称 + ' (' + r.池键 + ')';
    sel.appendChild(o);
  }
}

async function 刷新租约() {
  const st = document.getElementById('状态筛').value;
  const url = st ? '/api/租约?状态=' + encodeURIComponent(st) : '/api/租约';
  const rows = await 租约台.getJSON(url);
  const tb = document.getElementById('租约表');
  tb.innerHTML = '';
  for (const r of rows) {
    const tr = document.createElement('tr');
    const act = r.状态 === '待生效'
      ? '<button class="按钮" data-id="' + 租约台.安全文本(r.租约号) + '">激活</button>'
      : '';
    tr.innerHTML =
      '<td>' + 租约台.安全文本(r.租约号) + '</td>' +
      '<td>' + 租约台.安全文本(r.租户) + '</td>' +
      '<td>' + 租约台.安全文本(r.池键) + '</td>' +
      '<td>' + 租约台.状态徽章(r.状态) + '</td>' +
      '<td>' + 租约台.安全文本(租约台.格式化时刻(r.到期时刻)) + '</td>' +
      '<td>' + act + '</td>';
    tb.appendChild(tr);
  }
  tb.querySelectorAll('button').forEach((b) => {
    b.onclick = async () => {
      await 租约台.postJSON('/api/租约/激活', { 租约号: b.dataset.id });
      await 刷新租约();
    };
  });
}

document.getElementById('申领钮').onclick = async () => {
  const msg = document.getElementById('申领消息');
  try {
    const row = await 租约台.postJSON('/api/租约/申领', {
      池键: document.getElementById('申领池').value,
      租户: document.getElementById('申领租户').value,
      租期分钟: Number(document.getElementById('申领分钟').value),
      立即生效: document.getElementById('申领立即').value === '1',
    });
    msg.textContent = '已申领 ' + row.租约号 + ' 状态 ' + row.状态;
    await 刷新租约();
  } catch (e) {
    msg.textContent = e.message;
  }
};

document.getElementById('刷新钮').onclick = () => 刷新租约();
document.getElementById('状态筛').onchange = () => 刷新租约();

填池下拉(document.getElementById('申领池'));
刷新租约();