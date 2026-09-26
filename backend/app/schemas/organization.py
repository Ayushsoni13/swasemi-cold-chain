from pydantic import BaseModel, ConfigDict
from datetime import datetime

class OrganizationCreate(BaseModel):
    id: str
    name: str

class OrganizationOut(BaseModel):
    id: str
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
