from fastapi import status, Depends, HTTPException, APIRouter
from logging import getLogger
from sqlalchemy.orm import Session

from app.schemas import JWTData, UserOut
import app.models as models
from app.database import get_db
from app.routers.check_access_token import CheckAccessToken

router = APIRouter(prefix="/show")
logger = getLogger("uvicorn")

oauth2 = CheckAccessToken()


@router.get("/user_data", status_code=status.HTTP_200_OK,
            response_model=UserOut)
def get_user(token_data: JWTData = Depends(oauth2),
             db: Session = Depends(get_db)) -> UserOut or HTTPException:
    print(token_data)
    user = db.query(models.User.username, models.User.email).filter(
        models.User.id == token_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ユーザー情報が取得できませんでした。")
    return user
