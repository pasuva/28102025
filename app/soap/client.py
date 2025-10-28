from zeep import Client, Settings
from zeep.transports import Transport
from requests import Session
from requests.auth import HTTPBasicAuth
import os
from app.services.logger import log_event

# Cargar endpoints desde .env
WSDL_PRE = os.getenv("ADAMO_WSDL_PRE", "https://34.78.49.138:8081/ticket-gateway/ws/troubleTicketWSPort.wsdl")
WSDL_PRO = os.getenv("ADAMO_WSDL_PRO", "https://34.78.244.159:8081/ticket-gateway/ws/troubleTicketWSPort.wsdl")

# Si Adamo requiere autenticación básica o certificado:
ADAMO_USER = os.getenv("ADAMO_USER")
ADAMO_PASS = os.getenv("ADAMO_PASS")

def get_client(env: str = "PRE"):
    """Devuelve un cliente Zeep configurado para el entorno dado."""
    wsdl = WSDL_PRE if env == "PRE" else WSDL_PRO

    session = Session()
    if ADAMO_USER and ADAMO_PASS:
        session.auth = HTTPBasicAuth(ADAMO_USER, ADAMO_PASS)

    transport = Transport(session=session, timeout=10)
    settings = Settings(strict=False, xml_huge_tree=True)

    client = Client(wsdl=wsdl, transport=transport, settings=settings)
    return client

def set_trouble_ticket_by_value(payload: dict, env: str = "PRE"):
    """
    Invoca el método SOAP 'setTroubleTicketByValue'.
    En modo local (sin acceso a Adamo), simula una respuesta.
    """
    simulate_offline = os.getenv("ADAMO_SIMULATE", "true").lower() == "true"

    log_event(
        event_type="soap_out",
        payload=payload,
        ticket_pk=payload.get("primaryKey"),
        direction="out",
        status="pending"
    )

    if simulate_offline:
        print("[SOAP MOCK] Simulación local activada.")

        return {
            "status": "mock",
            "echo_payload": payload,
            "message": "Simulación local de envío a Adamo (sin conexión real)"
        }
        log_event(
            event_type="soap_out",
            payload=result,
            ticket_pk=payload.get("primaryKey"),
            direction="out",
            status="success"
        )
        return result

    try:
        client = get_client(env)
        response = client.service.setTroubleTicketByValue(**payload)
        log_event("soap_out", response, payload.get("primaryKey"), direction="out", status="success")
        return response
    except Exception as e:
        print(f"[SOAP ERROR] {e}")
        log_event("soap_out", str(e), payload.get("primaryKey"), direction="out", status="error")
        return {"error": str(e)}

