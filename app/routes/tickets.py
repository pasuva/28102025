from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import Session, select
from app.database import engine
from app.models import Ticket
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get("/")
def list_tickets(limit: int = 50, offset: int = 0):
    """
    Devuelve la lista de tickets almacenados localmente (espejo de Adamo).
    """
    with Session(engine) as session:
        tickets = session.exec(select(Ticket).offset(offset).limit(limit)).all()
        return tickets


@router.get("/{ticket_id}")
def get_ticket(ticket_id: int):
    """
    Devuelve el detalle de un ticket concreto.
    """
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return ticket

@router.get("/", dependencies=[Depends(get_current_user)])
def list_tickets(limit: int = 50, offset: int = 0):
    with Session(engine) as session:
        tickets = session.exec(select(Ticket).offset(offset).limit(limit)).all()
        return tickets


@router.get("/{ticket_id}", dependencies=[Depends(get_current_user)])
def get_ticket(ticket_id: int):
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket no encontrado")
        return ticket

def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return user