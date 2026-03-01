import os
from flask import Flask
from flask_cors import CORS
from config import config
from extensions import db, login_manager, mail


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config.get(config_name, config["default"]))

    CORS(app)
    db.init_app(app)
    mail.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to access that page."
    login_manager.login_message_category = "error"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

    with app.app_context():
        from routes.main import main_bp
        from routes.leads import leads_bp
        from routes.chat import chat_bp
        from routes.auth import auth_bp

        app.register_blueprint(main_bp)
        app.register_blueprint(leads_bp, url_prefix="/api")
        app.register_blueprint(chat_bp, url_prefix="/api")
        app.register_blueprint(auth_bp)

        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
