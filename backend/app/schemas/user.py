from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# User Schemas
class UserCreate(BaseModel):
    email: EmailStr
    phone_number: str
    name: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    phone_number: Optional[str] = None
    name: str
    is_active: bool
    is_admin: bool = False
    daily_goal: int
    current_streak: int
    last_study_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = None
    daily_goal: Optional[int] = None
    phone_number: Optional[str] = None


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[int] = None
