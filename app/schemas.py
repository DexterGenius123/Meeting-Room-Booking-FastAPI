from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RoomCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    capacity: int = Field(gt=0, le=100)
    floor: int = Field(ge=1, le=100)
    equipment: str = Field(default="", max_length=500)


class RoomRead(RoomCreate):
    id: int
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    room_id: int
    title: str = Field(min_length=2, max_length=150)
    organizer: str = Field(min_length=2, max_length=100)
    start_at: datetime
    end_at: datetime
    attendees: int = Field(gt=0, le=100)

    @field_validator("start_at", "end_at")
    @classmethod
    def must_be_naive_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is not None:
            return value.replace(tzinfo=None)
        return value

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_at <= self.start_at:
            raise ValueError("Время окончания должно быть позже времени начала")
        if (self.end_at - self.start_at).total_seconds() > 8 * 3600:
            raise ValueError("Одна бронь не может длиться более 8 часов")
        return self


class BookingRead(BookingCreate):
    id: int
    status: str
    room: RoomRead
    model_config = ConfigDict(from_attributes=True)


class DashboardRead(BaseModel):
    rooms_total: int
    active_bookings_today: int
    occupancy_hours_today: float
    next_bookings: list[BookingRead]
