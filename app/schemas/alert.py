from typing import Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID

class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    greenhouse_id: UUID
    sensor_id: Optional[int] = None
    severity: str
    status: str
    title: str
    message: str
    trigger_value: Optional[float] = None
    threshold_value: Optional[float] = None
    created_at: datetime

class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: Optional[str] = None
    due_date: datetime
    status: str
    recurrence_interval_days: int
