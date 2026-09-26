from typing import Type, TypeVar, Optional
from sqlalchemy.orm import Query, Session
from fastapi import HTTPException, status
from app.models.user import User
from app.models.enums import RoleEnum

ModelType = TypeVar("ModelType")

def apply_tenant_filter(query: Query, model: Type[ModelType], user: User) -> Query:
    """
    Applies tenant isolation to a SQLAlchemy query.
    - Super Admin: Returns unmodified query.
    - Normal User: Filters by model.organization_id == user.organization_id.
    """
    if user.role == RoleEnum.SUPER_ADMIN:
        return query
    
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no organization assigned"
        )
        
    return query.filter(model.organization_id == user.organization_id)

def get_tenant_scoped_entity(
    db: Session,
    model: Type[ModelType],
    entity_id: str,
    user: User
) -> ModelType:
    """
    Fetches an entity by ID enforcing tenant isolation.
    Returns 404 Not Found if entity does not exist or belongs to another tenant
    to prevent leaking resource existence across organizations.
    """
    query = db.query(model).filter(model.id == entity_id)
    query = apply_tenant_filter(query, model, user)
    entity = query.first()
    
    if not entity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{model.__name__} not found"
        )
        
    return entity

def get_effective_organization_id(
    user: User,
    requested_org_id: Optional[str] = None
) -> str:
    """
    Determines the organization ID for resource creation.
    - Normal User: ALWAYS uses user.organization_id from JWT (ignores request body).
    - Super Admin: Uses requested_org_id if provided.
    """
    if user.role != RoleEnum.SUPER_ADMIN:
        if not user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has no organization assigned"
            )
        return user.organization_id
    
    if requested_org_id:
        return requested_org_id
        
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="organization_id is required for Super Admin when creating resources"
    )
