from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: Literal["student", "landlord"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class OnboardingRequest(BaseModel):
    university_id: int | None = None
    budget_min: int | None = None
    budget_max: int | None = None
    sleep_schedule: Literal["early_bird", "night_owl", "flexible"] | None = None
    study_habits: Literal["quiet", "moderate", "flexible"] | None = None
    cleanliness: Literal["high", "medium", "low"] | None = None
    guests: Literal["never", "rarely", "sometimes", "often"] | None = None
    language: Literal["arabic", "french", "english", "mixed"] | None = None
    priorities: list[str] = []


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str


class StudentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    university_id: int | None
    budget_min: int | None
    budget_max: int | None
    sleep_schedule: str | None
    study_habits: str | None
    cleanliness: str | None
    guests: str | None
    language: str | None
    priorities: list


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class UserMeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role: str
    profile: StudentProfileOut | dict | None = None
