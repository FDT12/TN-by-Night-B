# backend/app.py
from flask import Flask
from flask_smorest import Api
from flask_cors import CORS
import os
from dotenv import load_dotenv

from models import db
from routes.events import blp as events_blp
from routes.heatmap import blp as heatmap_blp

def create_app():
    # Load environment variables
    load_dotenv()
    
    # Create Flask app
    app = Flask(__name__)
    
    # Configuration
    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["API_TITLE"] = "Tunisia Nightlife API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    
    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///nightlife.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Initialize extensions
    db.init_app(app)
    api = Api(app)
    CORS(app)  # Enable CORS for frontend
    
    # Security extensions
    from flask_jwt_extended import JWTManager
    from flask_bcrypt import Bcrypt
    
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-this")
    jwt = JWTManager(app)
    bcrypt = Bcrypt(app)
    
    # Store bcrypt in app context or importable location if needed, 
    # but usually we just import Bcrypt and init it with app.
    # To make it accessible in blueprints without circular imports, 
    # we can attach it to app or use a shared extensions file.
    # For simplicity here, we'll keep it local or pass it.
    # Better yet, let's create a small extensions.py if needed, 
    # but for now let's just make sure auth blueprint can run.
    
    # Register blueprints (API routes)
    from routes.auth import blp as auth_blp
    api.register_blueprint(events_blp)
    api.register_blueprint(heatmap_blp)
    api.register_blueprint(auth_blp)
    
    # Create tables
    with app.app_context():
        db.create_all()
        print("✅ Database tables created")
    
    # Basic route
    @app.route('/')
    def home():
        return {
            "message": "Tunisia Nightlife API",
            "version": "1.0",
            "endpoints": {
                "events": "/api/events",
                "heatmap": "/api/heatmap",
                "docs": "/swagger-ui"
            }
        }
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)