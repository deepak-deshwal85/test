from __future__ import annotations

import logging

import uvicorn

from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
