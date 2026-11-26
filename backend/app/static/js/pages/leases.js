let 池映射 = {};

function 当前池() {
  const sel = document.getElementById('申领池');
  return sel && 池映射[sel.value] ? 池映射[sel.value] : null;
}

function 渲染容量提示() {
  const box = document.getElementById('容量提示');
  if (!box) return;
  const r = 当前池();
  if (!r) {
    box.textContent = '';
    return;
  }
  const 余量 = r.可申领余量 != null ? Number(r.可申领余量) : Math.max(0, r.容量 - r.已占);
  const 影子 = r.影子占用 != null ? Number(r.影子占用) : Math.max(0, r.已占 - r.容量);
  let html = `现行容量 <b>${r.容量}</b> · 已占 <b>${r.已占}</b> · 可申领余量 <b>${余量}</b>` +
    ` · 指纹 #${Number(r.容量指纹 || 0)}`;
  if (影子 > 0) {
    html += `<br><span class="徽章 已回收">容量已收紧至 ${r.容量}</span> ` +
      `<span>${影子} 格旧容量影子占用为收紧前既占，保留不动；新申领按新容量拦截，当前余量 0。</span>`;
  } else if (Number(r.容量指纹 || 0) > 0) {
    html += `<br><span class="徽章 已续约">容量已收紧/调整</span> <span>申领以现行容量 ${r.容量} 为准。</span>`;
  }
  box.innerHTML = html;
}

async function 填池下拉(sel) {
  const rows = await 租约台.getJSON('/api/资源池');
  池映射 = {};
  sel.innerHTML = '';
  for (const r of rows) {
    池映射[r.池键] = r;
    if (!r.启用) continue;
    const o = document.createElement('option');
    o.value = r.池键;
    const 余量 = r.可申领余量 != null ? r.可申领余量 : Math.max(0, r.容量 - r.已占);
    o.textContent = `${r.名称} (${r.池键}) 容量${r.容量}/已占${r.已占}/余量${余量}`;
    sel.appendChild(o);
  }
  sel.onchange = 渲染容量提示;
  渲染容量提示();
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

async function 刷新裁决() {
  const tb = document.getElementById('裁决表');
  if (!tb) return;
  let data;
  try {
    data = await 租约台.getJSON('/api/容量裁决');
  } catch (e) {
    return;
  }
  const rows = (data.账 || []).slice(0, 12);
  tb.innerHTML = rows.map((r) =>
    '<tr>' +
    '<td>' + 租约台.安全文本(租约台.格式化时刻(r.时刻)) + '</td>' +
    '<td><span class="徽章 ' + (r.结论 === '放行' ? '已续约' : '已回收') + '">' + r.结论 + '</span></td>' +
    '<td>' + 租约台.安全文本(r.原因码) + '</td>' +
    '<td>' + 租约台.安全文本(r.租约号) + '</td>' +
    '<td>' + 租约台.安全文本(r.池键) + '</td>' +
    '<td>容量' + 租约台.安全文本(r.读到容量) + ' / 已占' + 租约台.安全文本(r.读到已占) + ' / 余量' + 租约台.安全文本(r.可申领余量) + '</td>' +
    '</tr>').join('') || '<tr><td colspan="6">暂无容量裁决</td></tr>';
}

document.getElementById('申领钮').onclick = async () => {
  const msg = document.getElementById('申领消息');
  msg.classList.remove('好消息', '坏消息');
  const pool = 当前池();
  try {
    const body = {
      池键: document.getElementById('申领池').value,
      租户: document.getElementById('申领租户').value,
      租期分钟: Number(document.getElementById('申领分钟').value),
      立即生效: document.getElementById('申领立即').value === '1',
    };
    if (pool) body.容量指纹 = Number(pool.容量指纹 || 0); // 读集合指纹，旧指纹拒回刷
    const row = await 租约台.postJSON('/api/租约/申领', body);
    msg.classList.add('好消息');
    msg.textContent = '已申领 ' + row.租约号 + '，状态 ' + row.状态 + '（按现行新容量裁决放行，已双写两轨）';
    await Promise.all([刷新租约(), 填池下拉(document.getElementById('申领池')), 刷新裁决()]);
  } catch (e) {
    msg.classList.add('坏消息');
    const v = e.data && e.data.容量裁决;
    msg.textContent = e.message + (v ? `｜裁决=${v.结论}/${v.原因码}（读到容量${v.读到容量}、已占${v.读到已占}、余量${v.可申领余量}）` : '');
    // 被拒后刷新池余量与裁决轨，避免页面还停在旧容量读集合上。
    await Promise.all([填池下拉(document.getElementById('申领池')), 刷新裁决()]);
  }
};

document.getElementById('刷新钮').onclick = () => Promise.all([刷新租约(), 填池下拉(document.getElementById('申领池')), 刷新裁决()]);
document.getElementById('状态筛').onchange = () => 刷新租约();

填池下拉(document.getElementById('申领池'));
刷新租约();
刷新裁决();
