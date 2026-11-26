let 池行缓存 = [];

function 容量标记(r) {
  const 余量 = Number(r.可申领余量 != null ? r.可申领余量 : Math.max(0, (r.容量 || 0) - (r.已占 || 0)));
  const 影子 = Number(r.影子占用 != null ? r.影子占用 : Math.max(0, (r.已占 || 0) - (r.容量 || 0)));
  let html = `<span class="容量余量">可申领余量 <b>${余量}</b></span>`;
  if (影子 > 0) {
    html += ` <span class="徽章 已回收" title="收紧前既占、超过新容量的部分，租约保留但不是新容量内合法占用">旧容量影子 ${影子}</span>`;
  }
  if (Number(r.容量指纹 || 0) > 0) {
    html += ` <span class="徽章 已续约" title="容量切流指纹">#${Number(r.容量指纹)}</span>`;
  }
  return html;
}

async function 刷新池表() {
  const rows = await 租约台.getJSON('/api/资源池');
  池行缓存 = rows;
  const tb = document.getElementById('池表');
  tb.innerHTML = '';
  for (const r of rows) {
    const ratio = 租约台.占用比(r.已占, r.容量);
    const tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + 租约台.安全文本(r.池键) + '</td>' +
      '<td>' + 租约台.安全文本(r.名称) + '</td>' +
      '<td><span>' + 租约台.安全文本(ratio.label) + '</span>' +
        '<div class="进度条"><i style="width:' + ratio.pct + '%"></i></div>' +
        '<div class="容量标记行">' + 容量标记(r) + '</div></td>' +
      '<td>' + (r.启用 ? '启用' : '禁用') + '</td>' +
      '<td class="工具条">' +
        '<button class="按钮 次" data-act="detail" data-key="' + 租约台.安全文本(r.池键) + '">详情</button>' +
        '<button class="按钮" data-act="toggle" data-key="' + 租约台.安全文本(r.池键) + '" data-on="' + (r.启用 ? '0' : '1') + '">' + (r.启用 ? '禁用' : '启用') + '</button>' +
        '<button class="按钮 次" data-act="cap" data-key="' + 租约台.安全文本(r.池键) + '">改容量</button>' +
      '</td>';
    tb.appendChild(tr);
  }
  tb.querySelectorAll('button').forEach((btn) => {
    btn.onclick = async () => {
      const key = btn.dataset.key;
      const msg = document.getElementById('容量消息');
      if (msg) msg.textContent = '';
      try {
        if (btn.dataset.act === 'detail') {
          await 打开详情(key);
          return;
        }
        if (btn.dataset.act === 'toggle') {
          await 租约台.postJSON('/api/资源池/启用', { 池键: key, 启用: btn.dataset.on === '1' });
        } else {
          const row = 池行缓存.find((x) => x.池键 === key);
          const n = prompt('新额定容量（收紧到 60 后，既有租约保留，新申领按新容量拦）', String(Number(row.容量) || 0));
          if (n == null || n === '') return;
          const saved = await 租约台.postJSON('/api/资源池/容量', { 池键: key, 容量: Number(n) });
          if (msg) {
            const 影子 = Number(saved.影子占用 || 0);
            msg.textContent =
              `已保存：${key} 容量=${saved.容量}，已占=${saved.已占}，当场重算可申领余量=${saved.可申领余量}` +
              (影子 > 0 ? `；容量已收紧，旧容量影子占用 ${影子} 格保留不挤掉，新申领按 ${saved.容量} 拦截。` : '；容量成败已双写两轨。');
            msg.classList.add('好消息');
          }
          await 打开详情(key);
        }
        await 刷新池表();
      } catch (e) {
        if (msg) {
          msg.classList.remove('好消息');
          msg.textContent = '容量保存失败：' + e.message;
        } else {
          alert(e.message);
        }
      }
    };
  });
}

async function 打开详情(key) {
  const 卷 = document.getElementById('详情卷');
  卷.hidden = false;
  document.getElementById('详情标题').textContent = key;
  const [实况, 规, 切流, 裁决] = await Promise.all([
    租约台.getJSON('/api/容量实况?池键=' + encodeURIComponent(key)),
    租约台.getJSON('/api/租账规'),
    租约台.getJSON('/api/容量切流?池键=' + encodeURIComponent(key)),
    租约台.getJSON('/api/容量裁决?池键=' + encodeURIComponent(key)),
  ]);

  const cards = [
    ['额定容量', 实况.容量],
    ['当前已占', 实况.已占],
    ['可申领余量', 实况.可申领余量],
    ['新容量内合法占用', 实况.新容量内合法占用],
    ['旧容量影子占用', 实况.影子占用],
    ['容量指纹', '#' + (实况.容量指纹 || 0)],
  ];
  document.getElementById('详情卡').innerHTML = cards
    .map(([k, v]) => `<div class="卡"><small>${k}</small><b>${租约台.安全文本(v)}</b></div>`)
    .join('');

  const 策略键 = ['允许超额申领', '默认租期分钟', '心跳宽限分钟', '回收策略'];
  document.getElementById('详情策略').innerHTML =
    '<h3>设置策略（租账规）</h3><table><tbody>' +
    策略键.map((k) =>
      '<tr><th>' + 租约台.安全文本(k) + '</th><td>' +
      租约台.安全文本(规[k] == null ? '（未设置）' : 规[k]) + '</td></tr>').join('') +
    '<tr><th>口径</th><td>' + 租约台.安全文本(实况.容量口径 || '收紧后只拦新申领，已生效租约不动') + '</td></tr>' +
    '</tbody></table>';

  const ct = document.getElementById('详情切流表');
  ct.innerHTML = (切流.账 || []).map((r) =>
    '<tr><td>' + 租约台.安全文本(r.指纹) + '</td><td>' + 租约台.安全文本(r.旧容量) + '→' + 租约台.安全文本(r.新容量) + '</td>' +
    '<td>' + 租约台.安全文本(r.收紧前已占) + '</td><td>' + 租约台.安全文本(r.可申领余量) + '</td>' +
    '<td>' + (r.是否收紧 ? '收紧' : '调整') + '</td><td>' + 租约台.安全文本(r.说明) + '</td>' +
    '<td>' + 租约台.格式化时刻(r.时刻) + '</td></tr>').join('')
    || '<tr><td colspan="7">暂无切流记录</td></tr>';

  const vt = document.getElementById('详情裁决表');
  vt.innerHTML = (裁决.账 || []).slice(0, 20).map((r) =>
    '<tr><td>' + 租约台.格式化时刻(r.时刻) + '</td>' +
    '<td><span class="徽章 ' + (r.结论 === '放行' ? '已续约' : '已回收') + '">' + r.结论 + '</span></td>' +
    '<td>' + 租约台.安全文本(r.原因码) + '</td>' +
    '<td>' + 租约台.安全文本(r.租约号) + '</td>' +
    '<td>容量' + 租约台.安全文本(r.读到容量) + ' / 已占' + 租约台.安全文本(r.读到已占) + '</td></tr>').join('')
    || '<tr><td colspan="5">暂无裁决</td></tr>';

  卷.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

document.getElementById('登记钮').onclick = async () => {
  const msg = document.getElementById('登记消息');
  msg.classList.remove('好消息');
  try {
    await 租约台.postJSON('/api/资源池', {
      池键: document.getElementById('新池键').value,
      名称: document.getElementById('新名称').value,
      容量: Number(document.getElementById('新容量').value),
    });
    msg.textContent = '登记成功';
    msg.classList.add('好消息');
    await 刷新池表();
  } catch (e) {
    msg.textContent = e.message;
  }
};

刷新池表();
