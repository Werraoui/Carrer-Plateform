import json

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/career_guidance"

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    ML_SERVICE_URL: str = "http://localhost:8001"

    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gemini-2.5-flash-lite"
    LLM_FALLBACK_MODELS: str = "gemini-2.5-flash-lite,gemini-2.0-flash,gemini-2.5-flash"
    LLM_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"

    # CORS — sur Render: une URL ou plusieurs séparées par des virgules
    # Ex: https://carrer-plateform.onrender.com
    ALLOWED_ORIGINS: str = (
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://localhost:8080,"
        "http://127.0.0.1:8080"
    )

    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE_MB: int = 10

    @field_validator("LLM_API_KEY", mode="before")
    @classmethod
    def clean_llm_api_key(cls, v: object) -> str:
        if v is None:
            return ""
        s = str(v).strip()
        if "#" in s:
            s = s.split("#", 1)[0].strip()
        return s

    @property
    def cors_origins(self) -> list[str]:
        raw = (self.ALLOWED_ORIGINS or "").strip()
        if not raw:
            return ["*"]
        if raw == "*":
            return ["*"]
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x).strip() for x in parsed if str(x).strip()]
            except json.JSONDecodeError:
                pass
        return [part.strip() for part in raw.split(",") if part.strip()]

    @property
    def llm_model_candidates(self) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        primary = (self.LLM_MODEL or "").strip()
        if primary:
            out.append(primary)
            seen.add(primary)
        for part in (self.LLM_FALLBACK_MODELS or "").split(","):
            m = part.strip()
            if m and m not in seen:
                out.append(m)
                seen.add(m)
        return out or ["gemini-2.5-flash-lite"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
