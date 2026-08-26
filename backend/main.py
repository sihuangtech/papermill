"""ASGI 入口。"""

import os

from dotenv import load_dotenv

from backend.api.webapp import create_app

load_dotenv()

app = create_app(enable_durable=True)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ["BACKEND_PORT"]))
