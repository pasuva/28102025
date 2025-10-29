from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database import engine
from app.models import User, Ticket
from passlib.context import CryptContext
import os
from datetime import datetime
from typing import List, Optional

# Importamos ambos flujos
from app.services.ftth_flow import request_additional_info as ftth_request_info, \
    propose_resolution as ftth_propose_resolution, \
    send_report as ftth_send_report

from app.services.ftth_masive_flow import request_additional_info as massive_request_info, \
    propose_resolution as massive_propose_resolution, \
    send_report as massive_send_report

# 🔹 Nuevo flujo: Trabajos programados
from app.services.workflows_flow import request_additional_info as wf_request_info, \
    propose_resolution as wf_propose_resolution, \
    send_report as wf_send_report

router = APIRouter(prefix="/web", tags=["Web"])
templates = Jinja2Templates(directory="app/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Sesión simple (no JWT)
SESSION_USER = None

# ---------- LOGIN / LOGOUT ----------

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login", response_class=HTMLResponse)
def login_action(request: Request, email: str = Form(...), password: str = Form(...)):
    global SESSION_USER
    with Session(engine) as session:
        user = session.exec(select(User).where(User.email == email)).first()
        if not user or not pwd_context.verify(password, user.password_hash):
            return templates.TemplateResponse("login.html", {"request": request, "error": "Credenciales inválidas"})
        SESSION_USER = user
    return RedirectResponse("/web/dashboard", status_code=302)

@router.get("/logout")
def logout():
    global SESSION_USER
    SESSION_USER = None
    return RedirectResponse("/web/login", status_code=302)


# ---------- DASHBOARD / LISTADO ----------

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    with Session(engine) as session:
        tickets = session.exec(select(Ticket).order_by(Ticket.created_at.desc())).all()
        stats = {
            "total": len(tickets),
            "abierto": sum(1 for t in tickets if t.state == "abierto"),
            "proceso": sum(1 for t in tickets if t.state == "proceso"),
            "cerrado": sum(1 for t in tickets if t.state == "cerrado"),
        }
        new_tickets_count = sum(1 for t in tickets if t.state == "abierto")
        latest_tickets = tickets[:5]
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "current_user": SESSION_USER,
        "stats": stats,
        "latest_tickets": latest_tickets,
        "new_tickets_count": new_tickets_count
    })

@router.get("/tickets", response_class=HTMLResponse)
def list_tickets(request: Request):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    with Session(engine) as session:
        tickets = session.exec(select(Ticket).order_by(Ticket.created_at.desc())).all()
    return templates.TemplateResponse("tickets.html", {"request": request, "tickets": tickets, "current_user": SESSION_USER})

@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: int):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
    return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": ticket, "current_user": SESSION_USER})

# ---------- SUBIDA DE ARCHIVO ----------

@router.post("/tickets/{ticket_id}/upload", response_class=HTMLResponse)
async def upload_file(request: Request, ticket_id: int, file: UploadFile = File(...)):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    contents = await file.read()
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, file.filename)
    with open(filepath, "wb") as f:
        f.write(contents)
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
    message = f"Archivo '{file.filename}' subido correctamente."
    return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": ticket, "current_user": SESSION_USER, "message": message})

# ---------- UTILIDADES PARA FLUJO DINÁMICO ----------

def get_ticket_flow(ticket: Ticket):
    """Devuelve las funciones del flujo según el tipo de ticket."""
    tipo = getattr(ticket, "ticket_type", None)

    if tipo == "ftth_masivo":
        return massive_request_info, massive_propose_resolution, massive_send_report
    elif tipo == "trabajos_programados":
        return wf_request_info, wf_propose_resolution, wf_send_report
    # Por defecto: ftth_cliente
    return ftth_request_info, ftth_propose_resolution, ftth_send_report

# ---------- ENDPOINTS DE ACCIÓN ----------

@router.post("/tickets/{ticket_id}/request_info", response_class=HTMLResponse)
async def web_request_info(request: Request, ticket_id: int, dialog: str = Form(...), attachments: Optional[List[UploadFile]] = File(None)):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": None, "message": "Ticket no encontrado"})

    request_func, _, _ = get_ticket_flow(ticket)
    result = request_func(ticket, dialog, attachments)
    return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": ticket, "current_user": SESSION_USER, "message": str(result)})


@router.post("/tickets/{ticket_id}/propose_resolution", response_class=HTMLResponse)
async def web_propose_resolution(
        request: Request,
        ticket_id: int,
        date_restore_service: str = Form(...),
        raw_resolution: str = Form(...),
        dialog: Optional[str] = Form(None),
        certification: Optional[str] = Form(None),
        department: Optional[str] = Form(None),
        raw_real_tipification: Optional[str] = Form(None),
        attachments: Optional[List[UploadFile]] = File(None)
):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": None, "message": "Ticket no encontrado"})

    _, propose_func, _ = get_ticket_flow(ticket)
    date_obj = datetime.fromisoformat(date_restore_service)
    result = propose_func(ticket, date_obj, raw_resolution, dialog, attachments, certification, department, raw_real_tipification)
    return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": ticket, "current_user": SESSION_USER, "message": str(result)})


@router.post("/tickets/{ticket_id}/send_report", response_class=HTMLResponse)
async def web_send_report(request: Request, ticket_id: int, dialog: str = Form(...), attachments: Optional[List[UploadFile]] = File(None)):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": None, "message": "Ticket no encontrado"})

    _, _, send_func = get_ticket_flow(ticket)
    result = send_func(ticket, dialog, attachments)
    return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": ticket, "current_user": SESSION_USER, "message": str(result)})



