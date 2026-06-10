"""Pydantic request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class SectorRead(BaseModel):
    sector_id: str
    crop_type: str
    area_hectares: float
    soil_moisture_pct: float
    soil_temp_c: float
    valve_open: bool
    last_updated: datetime


class TractorRead(BaseModel):
    tractor_id: str
    latitude: float
    longitude: float
    fuel_pct: float
    status: str
    last_updated: datetime


class IrrigationExecutionRead(BaseModel):
    execution_id: int
    sector_id: str
    triggered_by: str
    yield_health: float
    water_volume_l: float
    duration_seconds: int
    trace_id: str | None
    executed_at: datetime


class IrrigationExecutionCreate(BaseModel):
    sector_id: str
    triggered_by: str = Field(..., description="who/what triggered: 'manual', 'forecast', 'synthetic'")
    yield_health: float = Field(..., ge=0.0, le=100.0)
    water_volume_l: float = Field(..., ge=0.0)
    duration_seconds: int = Field(..., ge=1)
    trace_id: str | None = None
    # Synthetic edge-case payload: any value here forces a 500 in core-engine.
    emergency_override: str | None = None
