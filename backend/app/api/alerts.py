from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.alert import Alert
from app.models.enums import RoleEnum
from app.schemas.alert import AlertOut
from app.core.tenant import apply_tenant_filter

router = APIRouter()

@router.get("", response_model=List[AlertOut], summary="List tenant-scoped temperature and system alerts")
@router.get("/", response_model=List[AlertOut], include_in_schema=False)
def list_alerts(
    shipment_id: Optional[str] = None,
    tracker_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Alert)
    query = apply_tenant_filter(query, Alert, current_user)

    if current_user.role == RoleEnum.SUPER_ADMIN and organization_id:
        query = query.filter(Alert.organization_id == organization_id)

    if shipment_id:
        query = query.filter(Alert.shipment_id == shipment_id)

    if tracker_id:
        query = query.filter(Alert.tracker_id == tracker_id)

    return query.order_by(Alert.created_at.desc()).all()
