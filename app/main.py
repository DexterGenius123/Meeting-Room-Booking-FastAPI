from contextlib import asynccontextmanager
from datetime import date, datetime, time
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .database import Base, engine, get_db
from .models import Booking, Room
from .schemas import BookingCreate, BookingRead, DashboardRead, RoomCreate, RoomRead


def seed_rooms(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(Room)):
        return
    db.add_all([
        Room(name="Алатау", capacity=8, floor=3, equipment="TV, HDMI, доска"),
        Room(name="Каспий", capacity=12, floor=3, equipment="Проектор, камера, доска"),
        Room(name="Орбита", capacity=4, floor=4, equipment="Монитор, HDMI"),
        Room(name="Самал", capacity=20, floor=4, equipment="Проектор, камера, микрофоны"),
    ])
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_rooms(db)
    yield


app = FastAPI(title="Meeting Room Booking API", version="1.0.0", lifespan=lifespan)
static_dir = Path(__file__).resolve().parent.parent / "web"


@app.get("/api/health")
def health_check():
    return {"status": "ok"}


@app.get("/api/rooms", response_model=list[RoomRead])
def list_rooms(db: Session = Depends(get_db)):
    return db.scalars(select(Room).where(Room.is_active.is_(True)).order_by(Room.floor, Room.name)).all()


@app.post("/api/rooms", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Room).where(func.lower(Room.name) == payload.name.lower())):
        raise HTTPException(status_code=409, detail="Переговорная с таким названием уже существует")
    room = Room(**payload.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@app.get("/api/bookings", response_model=list[BookingRead])
def list_bookings(
    booking_date: date | None = None,
    room_id: int | None = None,
    db: Session = Depends(get_db),
):
    statement = select(Booking).options(joinedload(Booking.room)).where(Booking.status == "active")
    if booking_date:
        start = datetime.combine(booking_date, time.min)
        end = datetime.combine(booking_date, time.max)
        statement = statement.where(Booking.start_at <= end, Booking.end_at >= start)
    if room_id:
        statement = statement.where(Booking.room_id == room_id)
    return db.scalars(statement.order_by(Booking.start_at)).unique().all()


@app.post("/api/bookings", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
def create_booking(payload: BookingCreate, db: Session = Depends(get_db)):
    room = db.get(Room, payload.room_id)
    if not room or not room.is_active:
        raise HTTPException(status_code=404, detail="Переговорная не найдена")
    if payload.attendees > room.capacity:
        raise HTTPException(status_code=422, detail=f"Вместимость комнаты — {room.capacity} человек")

    conflict = db.scalar(
        select(Booking).where(
            Booking.room_id == payload.room_id,
            Booking.status == "active",
            Booking.start_at < payload.end_at,
            Booking.end_at > payload.start_at,
        )
    )
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Слот пересекается с бронью «{conflict.title}» ({conflict.start_at:%H:%M}–{conflict.end_at:%H:%M})",
        )

    booking = Booking(**payload.model_dump())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return db.scalar(select(Booking).options(joinedload(Booking.room)).where(Booking.id == booking.id))


@app.patch("/api/bookings/{booking_id}/cancel", response_model=BookingRead)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.scalar(select(Booking).options(joinedload(Booking.room)).where(Booking.id == booking_id))
    if not booking:
        raise HTTPException(status_code=404, detail="Бронь не найдена")
    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail="Бронь уже отменена")
    booking.status = "cancelled"
    db.commit()
    db.refresh(booking)
    return booking


@app.get("/api/dashboard", response_model=DashboardRead)
def dashboard(db: Session = Depends(get_db)):
    today_start = datetime.combine(date.today(), time.min)
    tomorrow_start = datetime.combine(date.today(), time.max)
    today_bookings = db.scalars(
        select(Booking).where(Booking.status == "active", Booking.start_at <= tomorrow_start, Booking.end_at >= today_start)
    ).all()
    hours = sum((min(b.end_at, tomorrow_start) - max(b.start_at, today_start)).total_seconds() / 3600 for b in today_bookings)
    upcoming = db.scalars(
        select(Booking).options(joinedload(Booking.room)).where(Booking.status == "active", Booking.end_at >= datetime.now()).order_by(Booking.start_at).limit(5)
    ).unique().all()
    return DashboardRead(
        rooms_total=db.scalar(select(func.count()).select_from(Room).where(Room.is_active.is_(True))) or 0,
        active_bookings_today=len(today_bookings),
        occupancy_hours_today=round(hours, 1),
        next_bookings=upcoming,
    )


# Mount must be registered after API routes; otherwise it would catch /api/* too.
app.mount("/", StaticFiles(directory=static_dir, html=True), name="web")
