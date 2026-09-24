from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Net-Neutral AI"

    database_url: str = ""

    num_clients: int = 3
    num_rounds: int = 3
    local_epochs: int = 1

    learning_rate: float = 1e-3
    batch_size: int = 32

    heartbeat_interval: int = 10
    client_timeout: int = 30

    class Config:
        env_file = ".env"


settings = Settings()