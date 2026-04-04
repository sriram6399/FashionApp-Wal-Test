import uvicorn

from fashion_backend.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "fashion_backend.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        reload_dirs=["fashion_backend"],
    )
