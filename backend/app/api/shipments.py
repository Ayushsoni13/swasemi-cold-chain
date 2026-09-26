import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Response, status
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.tracker import Tracker
from app.models.shipment import Shipment
from app.models.telemetry import TelemetryReading
from app.models.enums import RoleEnum, ShipmentStatusEnum
from app.schemas.shipment import ShipmentStartRequest, ShipmentOut
from app.schemas.telemetry import TelemetryReadingOut
from app.core.tenant import apply_tenant_filter, get_tenant_scoped_entity, get_effective_organization_id

router = APIRouter()

@router.get("", response_model=List[ShipmentOut], summary="List shipments scoped to tenant")
@router.get("/", response_model=List[ShipmentOut], include_in_schema=False)
def list_shipments(
    organization_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Shipment)
    query = apply_tenant_filter(query, Shipment, current_user)
    
    if current_user.role == RoleEnum.SUPER_ADMIN and organization_id:
        query = query.filter(Shipment.organization_id == organization_id)
        
    return query.all()

@router.get("/{shipment_id}", response_model=ShipmentOut, summary="Get shipment details by ID")
def get_shipment(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shipment = get_tenant_scoped_entity(db, Shipment, shipment_id, current_user)
    return shipment

@router.get("/{shipment_id}/telemetry", response_model=List[TelemetryReadingOut], summary="Get historical telemetry for a shipment")
def get_shipment_telemetry(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shipment = get_tenant_scoped_entity(db, Shipment, shipment_id, current_user)
    
    telemetry_readings = db.query(TelemetryReading).filter(
        TelemetryReading.shipment_id == shipment.id
    ).order_by(TelemetryReading.timestamp.asc()).all()
    
    return telemetry_readings

@router.get("/{shipment_id}/export", summary="Export historical shipment telemetry as CSV")
def export_shipment_csv(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Enforce tenant isolation (returns 404 for cross-tenant access)
    shipment = get_tenant_scoped_entity(db, Shipment, shipment_id, current_user)
    
    readings = db.query(TelemetryReading).filter(
        TelemetryReading.shipment_id == shipment.id
    ).order_by(TelemetryReading.timestamp.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV Header
    writer.writerow([
        "timestamp",
        "tracker_id",
        "latitude",
        "longitude",
        "temperature",
        "humidity",
        "battery_level",
        "door_open"
    ])
    
    for r in readings:
        ts_str = r.timestamp.isoformat() if hasattr(r.timestamp, 'isoformat') else str(r.timestamp)
        writer.writerow([
            ts_str,
            r.tracker_id,
            r.latitude,
            r.longitude,
            r.temperature,
            r.humidity if r.humidity is not None else "",
            r.battery_level if r.battery_level is not None else "",
            r.door_open
        ])
        
    csv_content = output.getvalue()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=shipment_{shipment_id}_telemetry.csv"
        }
    )

@router.post("/start", response_model=ShipmentOut, status_code=status.HTTP_201_CREATED, summary="Start a new shipment")
def start_shipment(
    shipment_in: ShipmentStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tracker = get_tenant_scoped_entity(db, Tracker, shipment_in.tracker_id, current_user)
    effective_org_id = get_effective_organization_id(current_user, shipment_in.organization_id or tracker.organization_id)
    
    if tracker.organization_id != effective_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracker organization mismatch"
        )


    active_shipment = db.query(Shipment).filter(
        Shipment.tracker_id == tracker.id,
        Shipment.status == ShipmentStatusEnum.IN_TRANSIT.value
    ).first()
    
    if active_shipment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tracker already has an active shipment in progress"
        )
        
    new_shipment = Shipment(
        organization_id=effective_org_id,
        tracker_id=tracker.id,
        status=ShipmentStatusEnum.IN_TRANSIT.value,
        started_at=datetime.now(timezone.utc),
        allowed_min_temp=shipment_in.allowed_min_temp,
        allowed_max_temp=shipment_in.allowed_max_temp,
        grace_period_readings=shipment_in.grace_period_readings,
        consecutive_breach_count=0,
        breach_active=False,
        origin_lat=shipment_in.origin_lat,
        origin_lng=shipment_in.origin_lng,
        target_lat=shipment_in.target_lat,
        target_lng=shipment_in.target_lng,
        route_name=shipment_in.route_name,
    )
    
    db.add(new_shipment)
    db.commit()
    db.refresh(new_shipment)
    
    return new_shipment

@router.post("/{shipment_id}/end", response_model=ShipmentOut, summary="End an active shipment")
def end_shipment(
    shipment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    shipment = get_tenant_scoped_entity(db, Shipment, shipment_id, current_user)
    
    if shipment.status != ShipmentStatusEnum.IN_TRANSIT.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shipment is not active or has already ended"
        )
        
    shipment.status = ShipmentStatusEnum.DELIVERED.value
    shipment.ended_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(shipment)
    
    return shipment
