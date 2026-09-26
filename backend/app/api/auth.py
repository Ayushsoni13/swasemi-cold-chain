from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_super_admin
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.models.user import User
from app.core.security import verify_password, create_access_token

router = APIRouter()

@router.post("/login", response_model=TokenResponse, summary="User login to obtain JWT token")
def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
        organization_id=user.organization_id
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )

@router.get("/me", response_model=UserOut, summary="Get current logged in user details")
def get_me(
    current_user: User = Depends(get_current_user)
):
    return current_user

@router.get("/admin-only", summary="Test endpoint for Super Admin authorization")
def test_admin_only(
    admin_user: User = Depends(require_super_admin)
):
    return {"message": "Welcome Super Admin", "user_id": admin_user.id}
