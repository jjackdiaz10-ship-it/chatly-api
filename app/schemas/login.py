from pydantic import BaseModel

class UserLoginSchema(BaseModel):
    id: int
    email: str
    role: str


class LoginResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: UserLoginSchema