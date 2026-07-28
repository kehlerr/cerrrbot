from app.types import CerrrBotSettings


class InfrastructureSettings(CerrrBotSettings):

    # MongoDB settings
    mongo_db_host: str = "localhost"
    mongo_db_port: int = 27017
    mongo_db_name: str = "cerrrbot_mongo"

    # Redis settings
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 1

    # Celery settings
    celery_broker_db: int = 0
    celery_backend_db: int = 1

    @property
    def redis_client_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_broker(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.celery_broker_db}"

    @property
    def celery_backend(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.celery_backend_db}"


infrastructure_settings = InfrastructureSettings()
