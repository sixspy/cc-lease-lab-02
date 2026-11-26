from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app import seed
from app.services import 会话, 互证, 回收, 台账, 夹具, 租约, 续约, 说明, 资源

_STATIC = Path(__file__).resolve().parent / "static"
端口 = int(os.environ.get("端口", "8600"))


def _未登录():
    return JSONResponse({"错误": "未登录"}, status_code=401)


def create_app() -> FastAPI:
    app = FastAPI(title="资源租约台", docs_url=None, redoc_url=None)
    app.mount("/assets", StaticFiles(directory=str(_STATIC)), name="assets")

    @app.middleware("http")
    async def auth_gate(request: Request, call_next):
        path = request.url.path
        if path.startswith("/api/") and path not in ("/api/登录",):
            user = 会话.从请求取用户(request.cookies)
            if not user:
                return _未登录()
        return await call_next(request)

    @app.on_event("startup")
    def on_start():
        seed.初始化库()

    @app.get("/login")
    def 登录页():
        return FileResponse(_STATIC / "login.html", media_type="text/html; charset=utf-8")

    @app.get("/")
    def 首页():
        return FileResponse(_STATIC / "index.html", media_type="text/html; charset=utf-8")

    @app.get("/styles.css")
    def css():
        return FileResponse(_STATIC / "styles.css", media_type="text/css")

    @app.get("/common.js")
    def common_js():
        return FileResponse(_STATIC / "common.js", media_type="application/javascript")

    @app.get("/sidebar.js")
    def sidebar_js():
        return FileResponse(_STATIC / "sidebar.js", media_type="application/javascript")

    @app.get("/js/pages/{name}")
    def page_js(name: str):
        p = _STATIC / "js" / "pages" / name
        if p.is_file():
            return FileResponse(p, media_type="application/javascript")
        return JSONResponse({"错误": "无此脚本"}, status_code=404)

    @app.post("/api/登录")
    async def api_登录(request: Request):
        body = await request.json()
        账号 = str(body.get("账号") or body.get("user") or "")
        密码 = str(body.get("密码") or body.get("password") or "")
        if not 会话.校验登录(账号, 密码):
            return JSONResponse({"ok": False, "错误": "账号或密码不对"}, status_code=401)
        token = 会话.签发令牌(账号)
        resp = JSONResponse({"ok": True, "用户": 账号})
        resp.set_cookie(会话.COOKIE, token, httponly=True, max_age=86400 * 7, samesite="lax")
        return resp

    @app.post("/api/登出")
    def api_登出():
        resp = JSONResponse({"ok": True})
        resp.delete_cookie(会话.COOKIE)
        return resp

    @app.get("/api/概览")
    def api_概览():
        return 说明.概览()

    @app.get("/api/仓情")
    def api_仓情():
        return 说明.仓情()

    @app.get("/api/租账规")
    def api_租账规_get():
        return 说明.租账规()

    @app.post("/api/租账规")
    async def api_租账规_post(request: Request):
        body = await request.json()
        try:
            return 说明.改租账规(body)
        except ValueError as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.get("/api/资源池")
    def api_资源池():
        return 说明.资源池列表()

    @app.post("/api/资源池")
    async def api_资源池登记(request: Request):
        body = await request.json()
        try:
            return 资源.登记(body)
        except ValueError as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.post("/api/资源池/容量")
    async def api_资源池容量(request: Request):
        body = await request.json()
        try:
            return 资源.改容量(body["池键"], body["容量"])
        except (KeyError, ValueError) as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.post("/api/资源池/启用")
    async def api_资源池启用(request: Request):
        body = await request.json()
        try:
            return 资源.改启用(body["池键"], bool(body.get("启用")))
        except (KeyError, ValueError) as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.get("/api/租约")
    def api_租约列表(状态: str | None = None):
        return 说明.租约列表(状态)

    @app.get("/api/租约/{租约号}")
    def api_租约一条(租约号: str):
        row = 说明.租约一条(租约号)
        if not row:
            return JSONResponse({"错误": "无此租约"}, status_code=404)
        return row

    @app.post("/api/租约/申领")
    async def api_租约申领(request: Request):
        body = await request.json()
        try:
            return 租约.申领(body)
        except ValueError as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.post("/api/租约/激活")
    async def api_租约激活(request: Request):
        body = await request.json()
        try:
            return 租约.激活(body["租约号"])
        except (KeyError, ValueError) as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.get("/api/心跳")
    def api_心跳(租约号: str | None = None):
        return 说明.心跳列表(租约号)

    @app.post("/api/心跳")
    async def api_心跳发(request: Request):
        body = await request.json()
        try:
            return 续约.发心跳(body)
        except ValueError as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.post("/api/心跳/批量")
    async def api_心跳批量(request: Request):
        body = await request.json()
        ids = body.get("租约号列表") or []
        return 续约.批量心跳([str(x) for x in ids])

    @app.get("/api/回收")
    def api_回收():
        return 说明.回收列表()

    @app.post("/api/回收/入匣")
    async def api_回收入匣(request: Request):
        body = await request.json()
        try:
            return 回收.入匣(body)
        except ValueError as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.post("/api/回收/确认")
    async def api_回收确认(request: Request):
        body = await request.json()
        try:
            return 回收.确认回收(body["回收号"])
        except (KeyError, ValueError) as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.post("/api/回收/作废")
    async def api_回收作废(request: Request):
        body = await request.json()
        try:
            return 回收.作废(body["回收号"], body.get("原因", "误回收"))
        except (KeyError, ValueError) as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.post("/api/回收/扫描逾期")
    def api_回收扫描():
        return {"处理": 回收.扫描并入匣()}

    @app.get("/api/互证")
    def api_互证列表():
        return 说明.互证列表()

    @app.post("/api/互证/跑")
    def api_互证跑():
        return 互证.跑一次()

    @app.get("/api/留痕")
    def api_留痕():
        return 说明.留痕列表()

    @app.get("/api/台账/池")
    def api_台账池(池键: str | None = None):
        return 台账.租约台账(池键)

    @app.get("/api/台账/租户")
    def api_台账租户():
        return 台账.租户汇总()

    @app.get("/api/夹具")
    def api_夹具():
        return 夹具.列表()

    @app.post("/api/夹具申领/{name}")
    def api_夹具申领(name: str):
        try:
            out = 夹具.批量申领(name)
            return {"申领": out}
        except FileNotFoundError:
            return JSONResponse({"错误": name}, status_code=404)
        except ValueError as e:
            return JSONResponse({"错误": str(e)}, status_code=400)

    @app.get("/api/空桩")
    def api_空桩():
        root = Path(__file__).resolve().parent / "modules"
        out = []
        if root.is_dir():
            for p in sorted(root.iterdir()):
                if p.is_dir() and (p / "__init__.py").is_file():
                    out.append(p.name)
        return {"空桩": out, "条数": len(out)}

    @app.get("/{page_name}")
    def 多页(page_name: str):
        if page_name.startswith("api"):
            return RedirectResponse("/")
        target = _STATIC / page_name
        if target.is_file():
            mt = "text/html; charset=utf-8" if target.suffix == ".html" else None
            return FileResponse(target, media_type=mt)
        return RedirectResponse("/")

    return app