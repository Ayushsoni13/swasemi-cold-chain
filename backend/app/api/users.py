from fastapi import APIRouter, Depends, HTTPException, Response, status
from typing import List
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_super_admin
from app.models.user import User
from app.models.organization import Organization
from app.models.enums import RoleEnum
from app.schemas.user import UserCreate
from app.schemas.auth import UserOut
from app.core.security import get_password_hash

router = APIRouter()

@router.get("", response_model=List[UserOut], summary="List all users (Super Admin only)")
@router.get("/", response_model=List[UserOut], include_in_schema=False)
def list_users(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    return db.query(User).all()

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED, summary="Create / provision a new user (Super Admin only)")
@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_user(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{user_in.email}' already exists"
        )
        
    if user_in.role == RoleEnum.USER:
        if not user_in.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="organization_id is required when creating a Normal User"
            )
        org = db.query(Organization).filter(Organization.id == user_in.organization_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization '{user_in.organization_id}' not found"
            )
            
    new_user = User(
        email=user_in.email,
        password_hash=get_password_hash(user_in.password),
        role=user_in.role,
        organization_id=user_in.organization_id if user_in.role == RoleEnum.USER else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a user (Super Admin only)")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    if user_id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own active Super Admin account"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found"
        )
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
