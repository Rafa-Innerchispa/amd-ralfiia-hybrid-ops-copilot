"""Settings — root gateway."""

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(__file__), "../../.env"),
        extra="ignore"
    )

    root_gateway_host: str = "0.0.0.0"
    root_gateway_port: int = 8220
    public_base_url: str = "http://192.168.1.4:8220"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_amd_url: str = "http://192.168.1.5:11434"
    ollama_primary_url: str = "http://192.168.1.4:11434"
    ollama_model: str = "ollama_chat/llama3.1:latest"
    ollama_intake_model: str = "qwen2.5:7b"

    vllm_model: str = "hosted_vllm/meta-llama/Llama-3.1-8B-Instruct"
    openai_api_base: str = "http://localhost:8088/v1"

    fireworks_api_base: str = "https://api.fireworks.ai/inference/v1"
    fireworks_base_url: str = "https://api.fireworks.ai/inference/v1"  # alias harness AMD
    fireworks_model: str = "accounts/fireworks/models/gemma-4-31b-it"
    fireworks_api_key: str = ""

    amd_cloud_api_token: str = ""
    amd_cloud_api_base: str = "https://api.digitalocean.com/v2"
    amd_inference_base_url: str = ""
    amd_inference_api_key: str = "not-required"
    amd_inference_token: str = ""
    amd_inference_model: str = "Qwen/Qwen2.5-1.5B-Instruct"

    harness_input_path: str = "/input/tasks.json"
    harness_output_path: str = "/output/results.json"

    smart_quoter_agent_auth: str = "quoter_bearer_token_change_me"
    smart_quoter_agent_url: str = "http://127.0.0.1:8221"
    watchdog_agent_auth: str = "watchdog_bearer_token_change_me"
    watchdog_agent_url: str = "http://127.0.0.1:8222"

    pizza_seller_agent_auth: str = ""
    pizza_seller_agent_url: str = ""
    burger_seller_agent_auth: str = ""
    burger_seller_agent_url: str = ""

    mongo_uri: str = "mongodb://127.0.0.1:27017"
    mongo_db: str = "pcdoctor_swarm"

    mcp_ralfia_url: str = "http://127.0.0.1:8102"
    mcp_ralfia_token: str = ""

    smart_quoter_url: str = "http://127.0.0.1:2026"
    smart_portal_url: str = "http://192.168.1.4:2002"
    public_ngrok_base: str = "https://sworn-profusely-alongside.ngrok-free.dev"
    public_amd_ops_path: str = "/amd-ops"
    public_amd_api_path: str = "/amd-ops-api"


def _apply_local_profile(s: Settings) -> None:
    """Bare-metal: .env may contain Docker hostnames — rewrite for local uvicorn."""
    if os.getenv("AMD_OPS_DOCKER") == "1" or os.path.exists("/.dockerenv"):
        return
    s.ollama_base_url = s.ollama_base_url.replace("host.docker.internal", "127.0.0.1")
    s.mongo_uri = s.mongo_uri.replace("host.docker.internal", "127.0.0.1")
    s.smart_quoter_url = s.smart_quoter_url.replace("host.docker.internal", "127.0.0.1")
    s.mcp_ralfia_url = s.mcp_ralfia_url.replace("host.docker.internal", "127.0.0.1")
    if "agent-smart-quoter" in s.smart_quoter_agent_url:
        s.smart_quoter_agent_url = "http://127.0.0.1:8221"
    if "agent-watchdog" in s.watchdog_agent_url:
        s.watchdog_agent_url = "http://127.0.0.1:8222"


settings = Settings()
_apply_local_profile(settings)

# Tutorial alias resolution
if not settings.pizza_seller_agent_url:
    settings.pizza_seller_agent_url = settings.smart_quoter_agent_url
if not settings.pizza_seller_agent_auth:
    settings.pizza_seller_agent_auth = settings.smart_quoter_agent_auth
if not settings.burger_seller_agent_url:
    settings.burger_seller_agent_url = settings.watchdog_agent_url
if not settings.burger_seller_agent_auth:
    settings.burger_seller_agent_auth = settings.watchdog_agent_auth
