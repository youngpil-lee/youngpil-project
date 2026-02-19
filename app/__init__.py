from flask import Flask
from .routes.kr_market import kr_bp
from .routes.common import common_bp

def create_app():
    app = Flask(__name__)
    
    # Register blueprints
    app.register_blueprint(kr_bp, url_prefix='/api/kr')
    app.register_blueprint(common_bp, url_prefix='/api/common')
    
    return app
