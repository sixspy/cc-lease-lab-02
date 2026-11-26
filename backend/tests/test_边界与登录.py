import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["数据目录"] = _tmp
os.environ["会话密钥"] = "test-lease-key"

import pytest
from fastapi.testclient import TestClient

from app import seed
from app.factory import create_app


@pytest.fixture()
def client():
    seed.初始化库()
    return TestClient(create_app())


def test_未登录拒api(client):
    r = client.get("/api/概览")
    assert r.status_code == 401


def test_登录与会话(client):
    r = client.post("/api/登录", json={"账号": "admin", "密码": "123456"})
    assert r.status_code == 200
    assert r.json().get("ok")
    r2 = client.get("/api/概览")
    assert r2.status_code == 200


def test_登录页文案(client):
    r = client.get("/login")
    assert r.status_code == 200
    body = r.text
    assert "登录" in body
    assert "密码" in body


def test_错误密码(client):
    r = client.post("/api/登录", json={"账号": "admin", "密码": "wrong"})
    assert r.status_code == 401