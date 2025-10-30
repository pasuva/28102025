from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.database import engine
from app.models import Log
from app.auth.dependencies import get_current_user

router = APIRouter(prefix="/logs", tags=["Logs"])
templates = Jinja2Templates(directory="app/templates")

@router.get("/", dependencies=[Depends(get_current_user)])
def list_logs(request: Request, limit: int = 50, offset: int = 0):
    with Session(engine) as session:
        logs = session.exec(
            select(Log)
            .order_by(Log.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    return templates.TemplateResponse(
        "logs.html",
        {"request": request, "logs": logs, "limit": limit, "offset": offset}
    )

