import os
import sys
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 프로젝트 루트를 경로에 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

logger.info(f"BASE_DIR: {BASE_DIR}")
logger.info(f"sys.path: {sys.path}")

try:
    from flask_app import app
    # Vercel은 'app' 객체를 요구함
    handler = app
    logger.info("Successfully imported app from flask_app")
except Exception as e:
    logger.error(f"Failed to import app: {e}")
    import traceback
    logger.error(traceback.format_exc())
    raise e
