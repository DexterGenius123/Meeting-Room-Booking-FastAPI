import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def booking_payload(room_id, start="2026-10-21T10:00:00", end="2026-10-21T11:00:00"):
    return {"room_id": room_id, "title": "Планирование", "organizer": "Данияр", "attendees": 3, "start_at": start, "end_at": end}


def test_creates_booking(client):
    room_id = client.get("/api/rooms").json()[0]["id"]
    response = client.post("/api/bookings", json=booking_payload(room_id))
    assert response.status_code == 201
    assert response.json()["status"] == "active"


def test_rejects_overlapping_booking(client):
    room_id = client.get("/api/rooms").json()[0]["id"]
    client.post("/api/bookings", json=booking_payload(room_id))
    response = client.post("/api/bookings", json=booking_payload(room_id, "2026-10-21T10:30:00", "2026-10-21T11:30:00"))
    assert response.status_code == 409
    assert "пересекается" in response.json()["detail"]


def test_cancelled_booking_does_not_block_slot(client):
    room_id = client.get("/api/rooms").json()[0]["id"]
    first = client.post("/api/bookings", json=booking_payload(room_id)).json()
    assert client.patch(f"/api/bookings/{first['id']}/cancel").status_code == 200
    assert client.post("/api/bookings", json=booking_payload(room_id)).status_code == 201


def test_rejects_when_attendees_exceed_capacity(client):
    room = client.get("/api/rooms").json()[0]
    payload = booking_payload(room["id"])
    payload["attendees"] = room["capacity"] + 1
    assert client.post("/api/bookings", json=payload).status_code == 422
