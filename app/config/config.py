import os


class Variables:
    """ This class is responsible for saving and
        loading variables from the system environment.

        Initiated at the entry point
    """

    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "secret"
    )

    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "mysql://root:root@127.0.0.1/amd"
    )

    USER_DEFAULT_PASSWORD: str = os.getenv(
        "USER_DEFAULT_PASSWORD",
        "password"
    )

    APP_HOST: str = os.getenv(
        "APP_HOST",
        "127.0.0.1"
    )

    APP_PORT: str = os.getenv(
        "APP_PORT",
        "5000"
    )

    license_server_access_token: str = os.getenv(
        "LICENSE_SERVER_ACCESS_TOKEN",
        "TOKEN"
    )

    # Directory for storing audio recognition wav files
    audio_dir: str = os.getenv(
        "AUDIO_DIR",
        "/stor/data/audio/"
    )
    # Directory for storing server logs
    logger_dir: str = os.getenv(
        "LOGGER_DIR",
        "/stor/data/logs/interface"
    )
    # Default audio recognition interval
    audio_interval: float = float(os.getenv(
        "DEFAULT_MAX_AUDIO_INTERVAL",
        2.0
    ))
    # Default audio recognition interval
    max_predictions: int = int(os.getenv(
        "DEFAULT_MAX_PREDICTIONS",
        2
    ))
    # Default recognition prediction criteria
    prediction_criteria: str = os.getenv(
        "DEFAULT_PREDICTION_CRITERIA",
        '{"1_interval_1": "True", "1_interval_2": "True", "1_result_3": "True",'
        ' "2_interval_1": "True", "2_interval_2": "False", "2_result_3": "True",'
        ' "3_interval_1": "False", "3_interval_2": "True", "3_result_3": "True",'
        ' "4_interval_1": "False", "4_interval_2": "False", "4_result_3": "False"}'
    )
    # Default audio sample rate
    audio_sample_rate: int = int(os.getenv(
        "DEFAULT_AUDIO_RATE",
        8000
    ))

    # Database connection properties
    database_user: str = os.getenv("DATABASE_USER", "root")
    database_password: str = os.getenv("DATABASE_PASSWORD", "root")
    database_host: str = os.getenv("DATABASE_HOST", "127.0.0.1")
    database_port: int = int(os.getenv("DATABASE_PORT", 3306))
    database_name: str = os.getenv("DATABASE_NAME", "amd")


variables = Variables()