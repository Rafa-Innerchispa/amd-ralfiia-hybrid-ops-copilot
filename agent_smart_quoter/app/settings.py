from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    agent_port: int = 8221
    agent_auth: str = "quoter_bearer_token_change_me"
    smart_quoter_agent_auth: str = ""

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_intake_model: str = "qwen2.5:14b-instruct-q4_K_M"

    fireworks_api_base: str = "https://api.fireworks.ai/inference/v1"
    fireworks_model: str = "accounts/fireworks/models/gemma-2-9b-it"
    fireworks_api_key: str = ""

    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_db: str = "pcdoctor_swarm"
    public_base_url: str = "http://192.168.1.4:8221"


settings = AgentSettings()
if not settings.agent_auth or settings.agent_auth == "quoter_bearer_token_change_me":
    if settings.smart_quoter_agent_auth:
        settings.agent_auth = settings.smart_quoter_agent_auth
