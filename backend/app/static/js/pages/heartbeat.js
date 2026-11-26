async function 填租约下拉() {
  const rows = await 租约台.getJSON('/api/租约');
  const sel = document.getElementById('心跳租约');
  sel.innerHTML = '';
  for (const r of rows) {
    if (!['生效中', '已续约'].includes(r.状态)) continue;
    const o = document.createElement('option');
    o.value = r.租约号;
    o.textContent = r.租约号 + ' · ' + r.状态;
    sel.appendChild(o);
  }
}

async function 刷新心跳() {
  const rows = await 租约台.getJSON('/api/心跳');
  const tb = document.getElementById('心跳表');
  tb.innerHTML = '';
  for (const r of rows.slice(0, 40)) {
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + 租约台.安全文本(r.心跳号) + '</td>' +
      '<td>' + 租约台.安全文本(r.租约号) + '</td>' +
      '<td>' + 租约台.安全文本(租约台.格式化时刻(r.时刻)) + '</td>' +
      '<td>' + 租约台.安全文本(r.结果) + '</td>' +
      '<td>' + 租约台.安全文本(r.延迟毫秒) + '</td>';
    tb.appendChild(tr);
  }
}

async function 发(失败) {
  const msg = document.getElementById('心跳消息');
  try {
    const rep = await 租约台.postJSON('/api/心跳', {
      租约号: document.getElementById('心跳租约').value,
      延长分钟: Number(document.getElementById('延长分').value),
      模拟失败: 失败,
    });
    msg.textContent = '结果 ' + rep.结果 + (rep.新到期时刻 ? ' 新到期 ' + 租约台.格式化时刻(rep.新到期时刻) : '');
    await 刷新心跳();
    await 填租约下拉();
  } catch (e) {
    msg.textContent = e.message;
  }
}

document.getElementById('心跳钮').onclick = () => 发(false);
document.getElementById('失败钮').onclick = () => 发(true);

填租约下拉();
刷新心跳();