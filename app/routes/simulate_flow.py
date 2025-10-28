from fastapi import APIRouter
from app.services.ticket_flow import handle_incoming_ticket, propose_resolution

router = APIRouter(prefix="/simulate", tags=["Simulation"])

@router.post("/adamo-to-ibiocom")
def simulate_adamo_to_ibiocom():
    """
    Simula que Adamo nos envía un ticket nuevo vía webhook.
    """
    fake_ticket = {
        "primaryKey": "IB-LOCAL-001",
        "baseTroubleTicketState": "OPENACTIVE",
        "dialog": "Incidencia simulada enviada por Adamo (modo local)"
    }

    ticket = handle_incoming_ticket(fake_ticket)
    return {"status": "received", "ticket": ticket}


@router.post("/ibiocom-to-adamo")
def simulate_ibiocom_to_adamo():
    """
    Simula que Ibiocom propone una resolución y la envía a Adamo vía SOAP.
    """
    # Reutilizamos el ticket anterior
    from app.database import engine
    from sqlmodel import Session, select
    from app.models import Ticket

    with Session(engine) as session:
        ticket = session.exec(select(Ticket).order_by(Ticket.id.desc())).first()
        if not ticket:
            return {"error": "No hay tickets en la base de datos para enviar"}

    response = propose_resolution(ticket)
    return {"status": "sent", "soap_response": response}
