from fastapi import APIRouter, Depends, HTTPException, Response, status
from typing import List, Optional
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.tracker import Tracker
from app.models.organization import Organization
from app.models.enums import RoleEnum
from app.schemas.tracker import TrackerCreate, TrackerOut
from app.core.tenant import apply_tenant_filter, get_tenant_scoped_entity, get_effective_organization_id

router = APIRouter()

@router.get("", response_model=List[TrackerOut], summary="List trackers scoped to tenant")
@router.get("/", response_model=List[TrackerOut], include_in_schema=False)
def list_trackers(
    organization_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Tracker)
    query = apply_tenant_filter(query, Tracker, current_user)
    
    # If Super Admin provides an organization_id filter query param
    if current_user.role == RoleEnum.SUPER_ADMIN and organization_id:
        query = query.filter(Tracker.organization_id == organization_id)
        
    return query.all()

@router.get("/{tracker_id}", response_model=TrackerOut, summary="Get tracker details by ID")
def get_tracker(
    tracker_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tracker = get_tenant_scoped_entity(db, Tracker, tracker_id, current_user)
    return tracker

@router.post("", response_model=TrackerOut, status_code=status.HTTP_201_CREATED, summary="Create a new tracker")
@router.post("/", response_model=TrackerOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
def create_tracker(
    tracker_in: TrackerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    effective_org_id = get_effective_organization_id(current_user, tracker_in.organization_id)
    
    # Verify target organization exists
    org = db.query(Organization).filter(Organization.id == effective_org_id).first()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
        
    tracker = Tracker(
        organization_id=effective_org_id,
        name=tracker_in.name,
        mqtt_topic=tracker_in.mqtt_topic
    )
    
    db.add(tracker)
    db.commit()
    db.refresh(tracker)
    
    return tracker

@router.delete("/{tracker_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a tracker")
def delete_tracker(
    tracker_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tracker = get_tenant_scoped_entity(db, Tracker, tracker_id, current_user)
    db.delete(tracker)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
