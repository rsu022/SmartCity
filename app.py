import os
import sys
from flask import Flask, send_from_directory
from config import Config
from flask_cors import CORS
from models.db import db, migrate
from routes.detection_routes import detection_bp, detect_ml_bp
from controller.auth.auth_controller import auth_bp

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(detection_bp, url_prefix="/api/detections")          
    app.register_blueprint(detect_ml_bp, url_prefix="/detection")  
    app.register_blueprint(auth_bp)

    @app.route("/")
    def index():
        return "Backend is running"

    @app.route("/storage/<path:filename>")
    def storage(filename):
        """Serve files from the configured STORAGE_FOLDER.

        Expects that image_path / detected_image_path are stored relative
        to STORAGE_FOLDER, e.g. 'pothole/original/file.jpg'.
        """
        return send_from_directory(app.config["STORAGE_FOLDER"], filename)

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)