import os
from typing import Optional

from fastapi import FastAPI, HTTPException

from .classifier import get_classifier
from .models import Category, Priority, Status, StatusUpdate, Ticket, TicketCreate
from .storage import TicketRepository


def create_app(repo: Optional[TicketRepository] = None, classifier=None) -> FastAPI:
    """Application factory so tests can inject an in-memory repo and a fake classifier."""
    repo = repo or TicketRepository(os.getenv("TICKETS_DB", "tickets.db"))
    classifier = classifier or get_classifier()
    app = FastAPI(title="Ticket Triage API", version="1.0.0")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/tickets", response_model=Ticket, status_code=201)
    def create_ticket(payload: TicketCreate):
        classification = classifier.classify(payload.title, payload.body)
        return repo.create(payload.title, payload.body, classification)

    @app.get("/tickets", response_model=list[Ticket])
    def list_tickets(
        category: Optional[Category] = None,
        priority: Optional[Priority] = None,
        status: Optional[Status] = None,
    ):
        return repo.list(category=category, priority=priority, status=status)

    @app.get("/tickets/{ticket_id}", response_model=Ticket)
    def get_ticket(ticket_id: int):
        ticket = repo.get(ticket_id)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return ticket

    @app.patch("/tickets/{ticket_id}/status", response_model=Ticket)
    def update_status(ticket_id: int, payload: StatusUpdate):
        ticket = repo.update_status(ticket_id, payload.status)
        if ticket is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return ticket

    @app.get("/stats")
    def stats():
        return repo.stats()

    return app


app = create_app()
