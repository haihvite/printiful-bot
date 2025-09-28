import uvicorn
from app import app   # import app FastAPI đã định nghĩa trong app.py

if __name__ == "__main__":
    # chạy server với host 0.0.0.0 để có thể truy cập từ ngoài máy
    uvicorn.run(
        "app:app",         # module:object
        host="0.0.0.0",    # cho phép truy cập từ IP khác
        port=8000,         # đổi nếu cần
        reload=True        # auto reload khi code thay đổi (dev mode)
    )
