from flask import Flask, send_from_directory
from .routes.kr_market import kr_bp
from .routes.common import common_bp
import os

def create_app():
    # frontend 폴더를 static 및 template 경로로 설정
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    
    @app.route('/')
    def index():
        return send_from_directory(frontend_dir, 'dashboard.html')

    @app.route('/<path:path>')
    def serve_static(path):
        return send_from_directory(frontend_dir, path)

    # Register blueprints
    app.register_blueprint(kr_bp, url_prefix='/api/kr')
    app.register_blueprint(common_bp, url_prefix='/api/common')
    
    return app
