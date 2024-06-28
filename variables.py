import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Variables:
    """ This class is responsible for saving and
        loading variables from the system environment.

        Initiated at the entry point
    """

    app_host: str = os.getenv(
        "APP_HOST",
        "127.0.0.1"
    )
    app_port: str = os.getenv(
        "APP_PORT",
        "5000"
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
    # Directory for storing server logs

    secret_key: str = os.getenv(
        "SECRET_KEY",
        "secret"
    )

    # Database connection properties
    database_user: str = os.getenv("DATABASE_USER", "root")
    database_password: str = os.getenv("DATABASE_PASSWORD", "root")
    database_host: str = os.getenv("DATABASE_HOST", "127.0.0.1")
    database_port: int = int(os.getenv("DATABASE_PORT", 3306))
    database_name: str = os.getenv("DATABASE_NAME", "amd")

    # License server

    license_server_access_token: str = os.getenv(
        "LICENSE_SERVER_ACCESS_TOKEN",
        "TOKEN"
    )
