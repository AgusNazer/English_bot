import os

bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = 2  # Ajustado para instancias de recursos bajos
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 120