# app/services/workflows_flow.py
from datetime import datetime
from sqlmodel import Session
from app.database import engine
from app.models import Ticket
from app.soap.client import set_trouble_ticket_by_value

def request_additional_info(ticket: Ticket, dialog: str, attachments=None):
    payload = {
        "baseTroubleTicketState": "OPENACTIVE",
        "primaryKey": ticket.primary_key,
        "mirrorKey": ticket.mirror_key,
        "dialog": dialog,
        "clearancePerson": "ibiocom",
        "attachments": attachments or None
    }
    result = set_trouble_ticket_by_value(payload, env="PRE")
    return f"Solicitud de información enviada correctamente: {result}"

def propose_resolution(ticket: Ticket, date_restore_service: datetime, raw_resolution: str,
                       dialog: str = None, attachments=None, certification=None,
                       department=None, raw_real_tipification=None):
    payload = {
        "baseTroubleTicketState": "OPENACTIVE",
        "primaryKey": ticket.primary_key,
        "mirrorKey": ticket.mirror_key,
        "certification": certification,
        "department": department,
        "rawRealTipification": raw_real_tipification,
        "dateRestoreService": date_restore_service.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "rawResolution": raw_resolution,
        "dialog": dialog,
        "clearancePerson": "ibiocom",
        "attachments": attachments or None
    }
    result = set_trouble_ticket_by_value(payload, env="PRE")
    return f"Propuesta de resolución enviada correctamente: {result}"

def send_report(ticket: Ticket, dialog: str, attachments=None):
    payload = {
        "primaryKey": ticket.primary_key,
        "mirrorKey": ticket.mirror_key,
        "dialog": dialog,
        "clearancePerson": "ibiocom",
        "attachments": attachments or None
    }
    result = set_trouble_ticket_by_value(payload, env="PRE")
    return f"Reporte enviado correctamente: {result}"
