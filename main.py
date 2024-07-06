from app import create_app

app = create_app()

app.run(debug=True, host=app.config.get("APP_HOST", "0.0.0.0"), port=app.config.get("APP_PORT", "5000"))
