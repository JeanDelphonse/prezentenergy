import os
from flask import Flask
from flask_cors import CORS
from config import config
from extensions import db


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config["default"]))

    CORS(app)
    db.init_app(app)

    with app.app_context():
        from routes.main import main_bp
        from routes.leads import leads_bp
        from routes.chat import chat_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(leads_bp, url_prefix="/api")
        app.register_blueprint(chat_bp, url_prefix="/api")

        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
