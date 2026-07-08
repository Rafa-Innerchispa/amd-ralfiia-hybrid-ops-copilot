from pydantic_settings import BaseSettings, SettingsConfigDict


class WatchdogSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_port: int = 8222
    agent_auth: str = "watchdog_bearer_token_change_me"
    watchdog_agent_auth: str = ""

    ollama_base_url: str = "http://127.0.0.1:11434"
    # No usar OLLAMA_MODEL del .env (formato LiteLLM ollama_chat/...) — modelo Ollama nativo
    watchdog_ollama_model: str = "qwen2.5:7b"
    public_base_url: str = "http://192.168.1.4:8222"


settings = WatchdogSettings()
if settings.watchdog_agent_auth:
    settings.agent_auth = settings.watchdog_agent_auth
