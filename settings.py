from pydantic import BaseSettings


class Settings(BaseSettings):
    DB: str
    username: str
    password: str
    host: str
    port: str
    virtual_host: str
    MS_SQL_SERVER: str
    MS_SQL_USERNAME: str
    MS_SQL_PASSWORD: str
    MS_SQL_DATABASE: str

    class Config:
        env_file = './.env'


settings = Settings()