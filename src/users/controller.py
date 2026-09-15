from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.session import get_db
from .model import ChangePinRequest, LoginRequest, UserResponse
from .service import change_pin, get_user, list_users, login

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserResponse])
def read_users(db: Session = Depends(get_db)):
    """Active Sage X3 users (AUTILIS) that can sign in at the till."""
    return list_users(db)


@router.post("/login", response_model=UserResponse)
def user_login(request: LoginRequest, db: Session = Depends(get_db)):
    try:
        return login(db, request.user_code, request.pin)
    except ValueError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(e))


@router.post("/pin")
def user_change_pin(request: ChangePinRequest, db: Session = Depends(get_db)):
    try:
        change_pin(db, request.user_code, request.old_pin, request.new_pin)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"status": "ok"}


@router.get("/{user_code}", response_model=UserResponse)
def read_user(user_code: str, db: Session = Depends(get_db)):
    user = get_user(db, user_code)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur inconnu")
    return user
