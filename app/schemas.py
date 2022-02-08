from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class Token(BaseModel):
    token: str
    action: str


class UserCreateReq(BaseModel):
    user_data: UserCreate
    token_data: Token

    class Config:
        orm_mode = True


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


class JWTData(BaseModel):
    user_id: str
