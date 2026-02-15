from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SupportContactRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    subject: str = Field(min_length=5, max_length=140)
    message: str = Field(min_length=10, max_length=5000)
    category: Optional[str] = Field(default=None, max_length=60)
    context_url: Optional[str] = Field(default=None, max_length=300)


class SupportAdminEmailRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    to_email: EmailStr
    subject: str = Field(min_length=5, max_length=140)
    message: str = Field(min_length=10, max_length=5000)
    reply_to: Optional[EmailStr] = None
