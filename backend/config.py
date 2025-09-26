import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY   = os.getenv("SECRET_KEY", "dev-key-change-me")
    MONGODB_URI  = os.getenv("MONGODB_URI", "")
    MONGODB_DB   = os.getenv("MONGODB_DB", "typeface_finance")
    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    UPLOAD_DIR = "./uploads"        
    MAX_CONTENT_LENGTH = 15 * 1024 * 1024  
    ALLOWED_EXTS = {"png","jpg","jpeg","webp","pdf"}

