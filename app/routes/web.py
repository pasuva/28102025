from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database import engine
from app.models import User, Ticket
from passlib.context import CryptContext
import os, base64

router = APIRouter(prefix="/web", tags=["Web"])
templates = Jinja2Templates(directory="app/templates")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Sesión simple (no JWT para interfaz interna)
SESSION_USER = None

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
    return RedirectResponse("/web/tickets", status_code=302)

@router.get("/logout")
def logout():
    global SESSION_USER
    SESSION_USER = None
    return RedirectResponse("/web/login", status_code=302)

@router.get("/tickets", response_class=HTMLResponse)
def list_tickets(request: Request):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    with Session(engine) as session:
        tickets = session.exec(select(Ticket).order_by(Ticket.created_at.desc())).all()
    return templates.TemplateResponse("tickets.html", {"request": request, "tickets": tickets})

@router.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def ticket_detail(request: Request, ticket_id: int):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
    return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": ticket})

@router.post("/tickets/{ticket_id}/upload", response_class=HTMLResponse)
async def upload_file(request: Request, ticket_id: int, file: UploadFile = File(...)):
    if not SESSION_USER:
        return RedirectResponse("/web/login")
    contents = await file.read()
    encoded = base64.b64encode(contents).decode("utf-8")
    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, file.filename)
    with open(filepath, "wb") as f:
        f.write(contents)
    with Session(engine) as session:
        ticket = session.get(Ticket, ticket_id)
    message = f"Archivo '{file.filename}' subido correctamente."
    return templates.TemplateResponse("ticket_detail.html", {"request": request, "ticket": ticket, "message": message})
