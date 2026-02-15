import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, require_admin
from app.models.user import User
from app.schemas.support import SupportAdminEmailRequest, SupportContactRequest
from app.services.email_service import (
    is_smtp_configured,
    send_support_acknowledgement,
    send_support_email_to_student,
    send_support_message_to_team,
)

router = APIRouter(prefix="/api/support", tags=["Support"])
logger = logging.getLogger(__name__)


@router.post("/contact")
def contact_support(
    payload: SupportContactRequest,
    current_user: User = Depends(get_current_user),
):
    if not is_smtp_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Canal de suporte por email nao configurado",
        )

    try:
        send_support_message_to_team(
            student_name=current_user.name,
            student_email=current_user.email,
            student_phone=current_user.phone_number,
            subject=payload.subject,
            message=payload.message,
            category=payload.category,
            context_url=payload.context_url,
        )
        send_support_acknowledgement(
            student_email=current_user.email,
            student_name=current_user.name,
            subject=payload.subject,
        )
    except Exception:
        logger.exception("Falha ao enviar mensagem de suporte do usuario %s", current_user.email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Nao foi possivel enviar sua mensagem agora. Tente novamente em alguns minutos.",
        )

    return {"message": "Mensagem enviada ao suporte com sucesso."}


@router.post("/send")
def send_support_to_student(
    payload: SupportAdminEmailRequest,
    current_user: User = Depends(require_admin),
):
    if not is_smtp_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Canal de suporte por email nao configurado",
        )

    try:
        send_support_email_to_student(
            to_email=str(payload.to_email),
            subject=payload.subject,
            message=payload.message,
            sent_by=current_user.email,
            reply_to=str(payload.reply_to) if payload.reply_to else None,
        )
    except Exception:
        logger.exception("Falha ao enviar email de suporte para %s", payload.to_email)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Nao foi possivel enviar o email para o aluno neste momento.",
        )

    return {"message": "Email enviado ao aluno com sucesso."}
