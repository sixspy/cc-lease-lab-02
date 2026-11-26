import os

import uvicorn

from app.factory import create_app, 端口

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("端口", 端口))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)