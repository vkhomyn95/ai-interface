#!/bin/bash
docker rm -f ai-interface
docker build -t vk/ai-interface .
docker run -d --restart always --net=host -v /stor:/stor -v /etc/localtime:/etc/localtime:ro \
        --log-opt max-size=500m --log-opt max-file=5 \
        -e APP_HOST='0.0.0.0' \
        -e APP_PORT='5000' \
        -e AUDIO_DIR='/stor/data/audio/' \
        -e LOGGER_DIR='/stor/data/logs/interface/' \
        -e DEFAULT_MAX_AUDIO_INTERVAL='2.0' \
        -e DEFAULT_AUDIO_RATE=8000 \
        -e DEFAULT_AUDIO_SILENCE_EXCLUDE_INTERVAL=0.4 \
        -e SQLALCHEMY_DATABASE_URI='mysql://root:root@127.0.0.1/amd' \
        -e USER_DEFAULT_PASSWORD='Erhf]yf12' \
        -e LICENSE_SERVER_ACCESS_TOKEN='272C8DCC83zBxxBDBB7y@DCyBzyCB7Bx' \
        -e PYTHONUNBUFFERED=0 \
        --name ai-interface vk/ai-interface
