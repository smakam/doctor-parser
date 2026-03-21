from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    # No JWT secret needed — Supabase uses asymmetric RS256; public key is
    # fetched automatically from {supabase_url}/auth/v1/.well-known/jwks.json

    google_vision_api_key: str
    openai_api_key: str

    imagekit_public_key: str
    imagekit_private_key: str
    imagekit_url_endpoint: str

    mappls_api_key: str = ""  # kept for backwards compat, no longer used

    pii_encryption_key: str  # Fernet key — generate with: Fernet.generate_key().decode()

    secret_key: str
    environment: str = "development"
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    model_config = {"env_file": ".env"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
