let 规缓存 = {};

async function 加载规() {
  规缓存 = await 租约台.getJSON('/api/租账规');
  const box = document.getElementById('规表单');
  box.innerHTML = '<h2>当前规约</h2>';
  for (const [k, v] of Object.entries(规缓存)) {
    const wrap = document.createElement('div');
    wrap.className = '表单行';
    wrap.innerHTML =
      '<div class="项"><label>' + 租约台.安全文本(k) + '</label>' +
      '<input data-key="' + 租约台.安全文本(k) + '" value="' + 租约台.安全文本(v) + '"/></div>';
    box.appendChild(wrap);
  }
}

document.getElementById('保存规').onclick = async () => {
  const msg = document.getElementById('规消息');
  const body = {};
  document.querySelectorAll('#规表单 input[data-key]').forEach((inp) => {
    body[inp.dataset.key] = inp.value;
  });
  try {
    await 租约台.postJSON('/api/租账规', body);
    msg.textContent = '已保存';
    await 加载规();
  } catch (e) {
    msg.textContent = e.message;
  }
};

加载规();