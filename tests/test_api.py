import pytest
from fastapi.testclient import TestClient

from app.classifier import RuleBasedClassifier
from app.main import create_app
from app.storage import TicketRepository


@pytest.fixture
def client():
    app = create_app(repo=TicketRepository(":memory:"), classifier=RuleBasedClassifier())
    return TestClient(app)


def make_ticket(client, title="App crashes", body="I get an error on start"):
    return client.post("/tickets", json={"title": title, "body": body})


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_ticket_is_classified_and_open(client):
    response = make_ticket(client)
    assert response.status_code == 201
    data = response.json()
    assert data["category"] == "bug"
    assert data["priority"] == "high"
    assert data["status"] == "open"


def test_create_ticket_rejects_short_title(client):
    response = client.post("/tickets", json={"title": "x", "body": "valid body"})
    assert response.status_code == 422


def test_get_ticket_and_404(client):
    ticket_id = make_ticket(client).json()["id"]
    assert client.get(f"/tickets/{ticket_id}").status_code == 200
    assert client.get("/tickets/9999").status_code == 404


def test_filter_by_category(client):
    make_ticket(client)
    make_ticket(client, "Refund", "I was charged twice for my subscription")
    response = client.get("/tickets", params={"category": "billing"})
    assert [t["category"] for t in response.json()] == ["billing"]


def test_invalid_filter_value_is_rejected(client):
    assert client.get("/tickets", params={"status": "nonsense"}).status_code == 422


def test_update_status(client):
    ticket_id = make_ticket(client).json()["id"]
    response = client.patch(f"/tickets/{ticket_id}/status", json={"status": "resolved"})
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    assert client.patch("/tickets/9999/status", json={"status": "resolved"}).status_code == 404


def test_stats_counts(client):
    make_ticket(client)
    make_ticket(client, "Refund", "I was charged twice for my subscription")
    stats = client.get("/stats").json()
    assert stats["total"] == 2
    assert stats["by_category"]["bug"] == 1
    assert stats["by_category"]["billing"] == 1
    assert stats["by_status"]["open"] == 2
