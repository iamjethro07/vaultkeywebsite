import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from db import init_db

load_dotenv()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY']               = os.getenv('SECRET_KEY', 'vaultkey-secret')
    app.config['JWT_SECRET_KEY']           = os.getenv('JWT_SECRET_KEY', 'vaultkey-jwt')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 3600
    app.config['JWT_REFRESH_TOKEN_EXPIRES']= 2592000

    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)
    init_db(app)

    from routes.auth  import auth_bp
    from routes.vault import vault_bp
    app.register_blueprint(auth_bp,  url_prefix='/api/auth')
    app.register_blueprint(vault_bp, url_prefix='/api/vault')

    @app.route('/api')
    def index():
        return {'status': 'VaultKey API running'}, 200

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)