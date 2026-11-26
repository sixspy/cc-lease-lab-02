# cc-lease-lab · 资源租约台

应用开发 / 全栈实验基线：**资源池 → 租约申领 → 心跳续约 → 逾期回收 → 租账互证**。

## 技术栈

- 后端：FastAPI + uvicorn（Python 3.12）
- 前端：多页 HTML + 原生 JS，左侧栏导航（冷石板 + 琥珀强调色）
- 存储：SQLite
- 端口：**8600**

## 主链

1. **资源池**：登记池、调容量、启用/禁用，占用随申领变化。
2. **租约台**：从启用池申领租约（待生效/生效中），可激活待生效条目。
3. **续约心跳**：对生效租约发心跳，成功则延长到期并记续约次数。
4. **回收匣**：逾期扫描入匣，确认后释放池占用并标记租约已回收。
5. **租账互证**：核对池已占合计与未回收租约数，写入互证报告。

## 登录

- 地址：`http://127.0.0.1:8600/login`
- 账号：`admin` / 密码：`123456`

## 本地运行

```bash
docker compose up -d --build
```

冒烟（在 `claude-workspace/scripts` 下）：

```bash
python _smoke_lab_access.py --dir ..\cc-lease-lab
```

厚度：

```bash
python _baseline_thickness.py cc-lease-lab
```

## 测试

```bash
cd backend && pip install -r requirements.txt && pytest
```