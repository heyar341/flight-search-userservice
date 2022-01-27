from pydantic import BaseModel
from pydantic import EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    username: str
    email: EmailStr

    class Config:
        orm_mode = True

class NameUpdate(BaseModel):
    current_username: str
    new_username: str


class EmailUpdate(BaseModel):
    current_email: EmailStr
    new_email: EmailStr


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


class UserOut(BaseModel):
    username: str
    email: EmailStr

    class Config:
        orm_mode = True