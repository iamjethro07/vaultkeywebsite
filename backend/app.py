import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from db import init_db

load_dotenv()

def create_app():
    app = Flask(__name__)

    # ---------------- CONFIG ---------------- #
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'vaultkey-secret')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'vaultkey-jwt')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = 2592000

    # ---------------- CORS FIX ---------------- #
    frontend_urls = os.getenv(
        'FRONTEND_URL',
        'http://localhost:3000,https://vaultkeywebsite.vercel.app'
    ).split(',')

    frontend_urls = [url.strip() for url in frontend_urls]

    CORS(
        app,
        resources={r"/api/*": {"origins": frontend_urls}},
        supports_credentials=True
    )

    # ---------------- INIT ---------------- #
    JWTManager(app)
    init_db(app)

    # ---------------- ROUTES ---------------- #
    from routes.auth import auth_bp
    from routes.vault import vault_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(vault_bp, url_prefix='/api/vault')

    # ---------------- TEST ROUTE ---------------- #
    @app.route('/api')
    def api_status():
        return {'status': 'VaultKey API running'}, 200

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)