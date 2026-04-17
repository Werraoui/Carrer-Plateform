from pydantic import BaseModel, EmailStr
from typing import Optional
 
 
# ── Création d'un compte ──────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    level: Optional[str] = "débutant"  # débutant | intermédiaire | avancé
 
 
# ── Login ─────────────────────────────────────────────────────────
class UserLogin(BaseModel):
    email: EmailStr
    password: str
 
 
# ── Réponse renvoyée au frontend (sans password) ──────────────────
class UserResponse(BaseModel):
    id: int
    name: str
    email: EmailStr
    level: Optional[str]
 
    model_config = {"from_attributes": True}
 
 
# ── Token JWT renvoyé après login/register ────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
 
 
# ── Payload décodé depuis le token JWT ───────────────────────────
class TokenData(BaseModel):
    user_id: Optional[int] = None
    email: Optional[str] = None