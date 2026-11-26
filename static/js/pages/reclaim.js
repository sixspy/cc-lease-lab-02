async function 刷新回收() {
  const rows = await 租约台.getJSON('/api/回收');
  const tb = document.getElementById('回收表');
  tb.innerHTML = '';
  for (const r of rows) {
    const tr = document.createElement('tr');
    let ops = '';
    if (r.状态 === '待回收') {
      ops =
        '<button class="按钮 琥珀" data-act="ok" data-id="' + 租约台.安全文本(r.回收号) + '">确认回收</button>' +
        '<button class="按钮 次" data-act="void" data-id="' + 租约台.安全文本(r.回收号) + '">作废</button>';
    }
    tr.innerHTML =
      '<td>' + 租约台.安全文本(r.回收号) + '</td>' +
      '<td>' + 租约台.安全文本(r.租约号) + '</td>' +
      '<td>' + 租约台.安全文本(r.原因) + '</td>' +
      '<td>' + 租约台.状态徽章(r.状态) + '</td>' +
      '<td>' + 租约台.安全文本(租约台.格式化时刻(r.入匣时)) + '</td>' +
      '<td class="工具条">' + ops + '</td>';
    tb.appendChild(tr);
  }
  tb.querySelectorAll('button').forEach((b) => {
    b.onclick = async () => {
      try {
        if (b.dataset.act === 'ok') {
          await 租约台.postJSON('/api/回收/确认', { 回收号: b.dataset.id });
        } else {
          await 租约台.postJSON('/api/回收/作废', { 回收号: b.dataset.id, 原因: '页面作废' });
        }
        await 刷新回收();
      } catch (e) {
        alert(e.message);
      }
    };
  });
}

document.getElementById('扫描钮').onclick = async () => {
  const out = await 租约台.postJSON('/api/回收/扫描逾期', {});
  document.getElementById('扫描结果').textContent =
    '处理 ' + (out.处理 ? out.处理.length : 0) + ' 条逾期租约';
  await 刷新回收();
};
document.getElementById('刷新钮').onclick = () => 刷新回收();

刷新回收();