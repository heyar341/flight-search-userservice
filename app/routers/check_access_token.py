from fastapi import status, HTTPException, Request

from app.access_token import verify_access_token


class CheckAccessToken(object):
    async def __call__(self, request: Request) -> str | None:
        access_token: str = request.cookies.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="ログインしていません。")
        token_data, error = verify_access_token(access_token)
        if error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=error)
        return token_data
