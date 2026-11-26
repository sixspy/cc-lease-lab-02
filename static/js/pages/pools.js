async function 刷新池表() {
  const rows = await 租约台.getJSON('/api/资源池');
  const tb = document.getElementById('池表');
  tb.innerHTML = '';
  for (const r of rows) {
    const ratio = 租约台.占用比(r.已占, r.容量);
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + 租约台.安全文本(r.池键) + '</td>' +
      '<td>' + 租约台.安全文本(r.名称) + '</td>' +
      '<td><span>' + 租约台.安全文本(ratio.label) + '</span><div class="进度条"><i style="width:' + ratio.pct + '%"></i></div></td>' +
      '<td>' + (r.启用 ? '启用' : '禁用') + '</td>' +
      '<td class="工具条">' +
      '<button class="按钮" data-act="toggle" data-key="' + 租约台.安全文本(r.池键) + '" data-on="' + (r.启用 ? '0' : '1') + '">' + (r.启用 ? '禁用' : '启用') + '</button>' +
      '<button class="按钮 次" data-act="cap" data-key="' + 租约台.安全文本(r.池键) + '">+容量</button>' +
      '</td>';
    tb.appendChild(tr);
  }
  tb.querySelectorAll('button').forEach((btn) => {
    btn.onclick = async () => {
      const key = btn.dataset.key;
      try {
        if (btn.dataset.act === 'toggle') {
          await 租约台.postJSON('/api/资源池/启用', { 池键: key, 启用: btn.dataset.on === '1' });
        } else {
          const row = rows.find((x) => x.池键 === key);
          const n = prompt('新容量', String((Number(row.容量) || 0) + 10));
          if (n) await 租约台.postJSON('/api/资源池/容量', { 池键: key, 容量: Number(n) });
        }
        await 刷新池表();
      } catch (e) {
        alert(e.message);
      }
    };
  });
}

document.getElementById('登记钮').onclick = async () => {
  const msg = document.getElementById('登记消息');
  try {
    await 租约台.postJSON('/api/资源池', {
      池键: document.getElementById('新池键').value,
      名称: document.getElementById('新名称').value,
      容量: Number(document.getElementById('新容量').value),
    });
    msg.textContent = '登记成功';
    await 刷新池表();
  } catch (e) {
    msg.textContent = e.message;
  }
};

刷新池表();