from datetime import timedelta
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from routes.auth import bp as auth_bp
from routes.transactions import bp as tx_bp
from routes.imports import bp as imports_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.secret_key = Config.SECRET_KEY
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",  
        SESSION_COOKIE_SECURE=False,  
        PERMANENT_SESSION_LIFETIME=timedelta(days=7)
    )

    cors_allowed = Config.CORS_ORIGINS or ["http://localhost:5173", "http://127.0.0.1:5173"]
    CORS(app,
         resources={r"/api/*": {"origins": cors_allowed}},
         supports_credentials=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tx_bp)
    app.register_blueprint(imports_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"ok": True})

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
