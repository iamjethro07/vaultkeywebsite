import os
from flask import Flask, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from db import init_db

load_dotenv()

def create_app():
    app = Flask(__name__)

    # Config
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vaultkey-secret')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'vaultkey-jwt')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 2592000

    # Extensions
    CORS(app, supports_credentials=True)
    JWTManager(app)
    init_db(app)

    # Blueprints
    from routes.auth import auth_bp
    from routes.vault import vault_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(vault_bp, url_prefix='/api/vault')

    # ✅ API test route
    @app.route('/api')
    def api_status():
        return {'status': 'VaultKey API running'}, 200

    # ✅ Serve frontend (main website)
    @app.route('/')
    @app.route('/index.html')
    def serve_frontend():
        return send_from_directory(
            os.path.join(os.getcwd(), '../frontend'),
            'index.html'
        )

    # ✅ Serve all static files (CSS, JS, images)
    @app.route('/<path:path>')
    def serve_static(path):
        return send_from_directory(
            os.path.join(os.getcwd(), '../frontend'),
            path
        )

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)