import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'guardiantext-secret-2024'
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'guardiantext.db')
    HOST = '0.0.0.0'   # Allows other PCs on same network to connect
    PORT = 5000
    DEBUG = True
    TOXICITY_THRESHOLD = 0.01  # 0.0 - 1.0, messages above this are flagged
    BLOCK_THRESHOLD = 0.70     # Messages above this are auto-blocked
