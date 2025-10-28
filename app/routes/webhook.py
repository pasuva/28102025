from fastapi import APIRouter, Request, HTTPException
from sqlmodel import Session, select
from app.database import engine
from app.models import Ticket
from datetime import datetime
from app.services.logger import log_event

router = APIRouter()

@router.post("/webhook/adamo")
async def webhook_adamo(request: Request):
    data = await request.json()
    primary_key = data.get("primaryKey")
    state = data.get("baseTroubleTicketState")
    dialog = data.get("dialog")

    if not primary_key:
        raise HTTPException(status_code=400, detail="primaryKey es requerido")

    mirror_key = data.get("mirrorKey") or f"RED-{int(datetime.now().timestamp())}"

    with Session(engine) as session:
        stmt = select(Ticket).where(Ticket.primary_key == primary_key)
        existing = session.exec(stmt).first()

        if existing:
            existing.state = state or existing.state
            existing.dialog = dialog or existing.dialog
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            ticket = existing
        else:
            ticket = Ticket(
                primary_key=primary_key,
                mirror_key=mirror_key,
                state=state,
                dialog=dialog,
            )
            session.add(ticket)

        session.commit()
        session.refresh(ticket)

        # Después de guardar el ticket
    log_event(
        event_type="webhook_in",
        payload=data,
        ticket_pk=primary_key,
        direction="in",
        status="success"
    )

    return {"status": "ok", "mirrorKey": ticket.mirror_key}
