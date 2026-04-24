from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    # LLM 配置
    llm_api_key: str
    llm_base_url: str
    llm_model_name: str = "your_model_name"
    
    # MySQL 数据库配置
    db_host: str = "localhost"
    db_user: str = "root"
    db_password: str = ""
    db_database: str = "stock_chat_room"
    db_port: int = 3306
    
    # 服务配置
    server_host: str = "0.0.0.0"
    server_port: int = 8083
    debug: bool = True
    
    # MCP 服务器配置
    mcp_server_url: str = "http://localhost:8084"
    
    @property
    def database_url(self) -> str:
        return f"mysql+mysqlconnector://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_database}"

settings = Settings()
