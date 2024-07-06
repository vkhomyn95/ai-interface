from flask import Flask


def create_app():
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
        static_url_path="/",
    )

    from app.logger import logger

    from app.config.config import variables
    app.config.from_object(variables)

    from app.extensions import db, ma, storage
    db.init_app(app)
    ma.init_app(app)

    from app import models
    from app import schemas

    from app.routes import apis_bp, bases_bp
    app.register_blueprint(apis_bp)
    app.register_blueprint(bases_bp)

    with app.app_context():
        db.create_all()
        storage.insert_default_roles()
        storage.insert_default_user()

    return app
