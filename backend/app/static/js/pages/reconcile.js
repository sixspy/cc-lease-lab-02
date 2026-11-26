function 口径卡(rep) {
  const box = document.getElementById('容量口径卡');
  if (!box || !rep) return;
  const cards = [
    ['旧容量影子占用合计', rep.旧容量影子占用合计],
    ['新容量内合法占用合计', rep.新容量内合法占用合计],
    ['池已占合计', rep.池已占合计],
    ['按租约计占用', rep.按租约计占用],
  ];
  box.innerHTML = cards
    .map(([k, v]) => `<div class="卡"><small>${k}</small><b>${租约台.安全文本(v)}</b></div>`)
    .join('');

  const tb = document.getElementById('超容表');
  const over = rep.容量超容池 || [];
  if (tb) {
    tb.innerHTML = over.length
      ? over.map((x) =>
          '<tr><td>' + 租约台.安全文本(x.池键) + '</td><td>' + 租约台.安全文本(x.容量) + '</td>' +
          '<td>' + 租约台.安全文本(x.已占) + '</td><td>' + 租约台.安全文本(x.新容量内合法占用) + '</td>' +
          '<td><span class="徽章 已回收">' + 租约台.安全文本(x.影子占用) + '</span></td></tr>').join('')
      : '<tr><td colspan="5">无超容影子占用（或尚未执行互证）</td></tr>';
  }
}

async function 刷新报告() {
  const rows = await 租约台.getJSON('/api/互证');
  const tb = document.getElementById('报告表');
  tb.innerHTML = '';
  for (const r of rows) {
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + 租约台.安全文本(r.报告号) + '</td>' +
      '<td>' + 租约台.安全文本(租约台.格式化时刻(r.时刻)) + '</td>' +
      '<td>' + 租约台.安全文本(r.结论) + '</td>' +
      '<td>' + (r.是否对齐 ? '对齐' : '有差异') + '</td>' +
      '<td>' + 租约台.安全文本(r.差异摘要) + '</td>';
    tb.appendChild(tr);
  }
}

async function 刷新留痕() {
  const rows = await 租约台.getJSON('/api/留痕');
  const tb = document.getElementById('留痕表');
  tb.innerHTML = '';
  for (const r of rows.slice(0, 30)) {
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + 租约台.安全文本(租约台.格式化时刻(r.时刻)) + '</td>' +
      '<td>' + 租约台.安全文本(r.操作) + '</td>' +
      '<td>' + 租约台.安全文本(r.租约号) + '</td>' +
      '<td>' + 租约台.安全文本(r.详情) + '</td>';
    tb.appendChild(tr);
  }
}

async function 刷新切流() {
  const tb = document.getElementById('切流表');
  if (!tb) return;
  const data = await 租约台.getJSON('/api/容量切流');
  tb.innerHTML = (data.账 || []).slice(0, 20).map((r) =>
    '<tr><td>' + 租约台.安全文本(r.指纹) + '</td><td>' + 租约台.安全文本(r.池键) + '</td>' +
    '<td>' + 租约台.安全文本(r.旧容量) + '→' + 租约台.安全文本(r.新容量) + '</td>' +
    '<td>' + 租约台.安全文本(r.收紧前已占) + '</td><td>' + 租约台.安全文本(r.可申领余量) + '</td>' +
    '<td>' + (r.是否收紧 ? '收紧' : '调整') + '</td>' +
    '<td>' + 租约台.安全文本(r.说明) + '</td></tr>').join('')
    || '<tr><td colspan="7">暂无切流记录</td></tr>';
}

async function 刷新裁决() {
  const tb = document.getElementById('裁决表');
  if (!tb) return;
  const data = await 租约台.getJSON('/api/容量裁决');
  tb.innerHTML = (data.账 || []).slice(0, 20).map((r) =>
    '<tr><td>' + 租约台.安全文本(租约台.格式化时刻(r.时刻)) + '</td>' +
    '<td>' + 租约台.安全文本(r.池键) + '</td>' +
    '<td><span class="徽章 ' + (r.结论 === '放行' ? '已续约' : '已回收') + '">' + r.结论 + '</span></td>' +
    '<td>' + 租约台.安全文本(r.原因码) + '</td>' +
    '<td>' + 租约台.安全文本(r.租约号) + '</td>' +
    '<td>容量' + 租约台.安全文本(r.读到容量) + ' / 已占' + 租约台.安全文本(r.读到已占) + '</td></tr>').join('')
    || '<tr><td colspan="6">暂无裁决</td></tr>';
}

document.getElementById('跑互证').onclick = async () => {
  const rep = await 租约台.postJSON('/api/互证/跑', {});
  document.getElementById('互证详情').textContent = JSON.stringify(rep, null, 2);
  口径卡(rep);
  await Promise.all([刷新报告(), 刷新留痕(), 刷新切流(), 刷新裁决()]);
};

刷新报告();
刷新留痕();
刷新切流();
刷新裁决();
