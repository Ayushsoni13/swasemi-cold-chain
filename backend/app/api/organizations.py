from fastapi import APIRouter, Depends, HTTPException, Response, status
from typing import List
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_super_admin
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationOut

router = APIRouter()

@router.get("", response_model=List[OrganizationOut], summary="List all organizations (Super Admin only)")
@router.get("/", response_model=List[OrganizationOut], include_in_schema=False)
def list_organizations(
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    return db.query(Organization).all()

@router.post("", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED, summary="Create a new organization (Super Admin only)")
@router.post("/", response_model=OrganizationOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_organization(
    org_in: OrganizationCreate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    existing = db.query(Organization).filter(Organization.id == org_in.id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with ID '{org_in.id}' already exists"
        )
        
    org = Organization(
        id=org_in.id,
        name=org_in.name
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org

@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete an organization (Super Admin only)")
def delete_organization(
    org_id: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_id}' not found"
        )
    db.delete(org)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
