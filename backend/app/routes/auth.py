from datetime import datetime, timedelta, timezone
import logging
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    create_password_reset_token,
    verify_password_reset_token,
    create_email_verification_token,
    verify_email_verification_token,
)
from app.core.config import get_settings
from app.services.email_service import (
    is_smtp_configured,
    send_password_reset_email,
    send_email_verification_email,
)
from app.services.anti_abuse import (
    get_client_ip,
    enforce_rate_limit,
    enforce_register_captcha,
)
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    Token,
    PasswordChange,
    PasswordResetRequest,
    PasswordResetConfirm,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse)
def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
    """Registrar novo usuário"""
    settings = get_settings()
    require_email_verification = bool(getattr(settings, "auth_require_email_verification", True))
    client_ip = get_client_ip(request)

    enforce_rate_limit(
        scope="auth-register-ip",
        identifier=client_ip,
        limit=settings.auth_register_limit_per_ip,
        window_seconds=settings.auth_register_window_seconds,
    )
    enforce_rate_limit(
        scope="auth-register-email",
        identifier=str(user_data.email).lower(),
        limit=settings.auth_register_limit_per_email,
        window_seconds=settings.auth_register_window_seconds,
    )

    # Verificar se email já existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já registrado"
        )
    phone_number = user_data.phone_number.strip()
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telefone é obrigatório"
        )
    existing_phone = db.query(User).filter(User.phone_number == phone_number).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telefone já registrado"
        )

    if require_email_verification and not is_smtp_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cadastro indisponivel: confirmacao de email nao configurada",
        )

    enforce_register_captcha(
        captcha_token=user_data.captcha_token,
        client_ip=client_ip,
    )
    
    # Criar usuário
    user = User(
        email=user_data.email,
        phone_number=phone_number,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password),
        email_verified_at=None if require_email_verification else datetime.now(timezone.utc),
    )
    db.add(user)

    if require_email_verification:
        db.flush()
        if user.id is None:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Falha ao criar conta",
            )
        verify_token = create_email_verification_token(user.id)
        verify_url = f"{settings.frontend_base_url.rstrip('/')}/verify-email?token={verify_token}"
        try:
            send_email_verification_email(user.email, verify_url)
        except Exception:
            db.rollback()
            logger.exception("Falha ao enviar email de confirmacao para %s", user.email)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nao foi possivel enviar o email de confirmacao. Tente novamente em instantes.",
            )

    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login com email e senha"""
    settings = get_settings()
    client_ip = get_client_ip(request)
    login_identifier = (form_data.username or "").strip().lower() or "-"

    enforce_rate_limit(
        scope="auth-login-ip",
        identifier=client_ip,
        limit=settings.auth_login_limit_per_ip,
        window_seconds=settings.auth_login_window_seconds,
    )
    enforce_rate_limit(
        scope="auth-login-email",
        identifier=login_identifier,
        limit=settings.auth_login_limit_per_email,
        window_seconds=settings.auth_login_window_seconds,
    )

    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if bool(getattr(settings, "auth_require_email_verification", True)) and not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email nao verificado. Confirme seu email para entrar.",
        )

    if not bool(getattr(user, "is_active", True)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Conta inativa. Contate o suporte.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Confirmar email a partir de um token"""
    user_id = verify_email_verification_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token invalido ou expirado",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

    if user.email_verified:
        return {"message": "Email ja confirmado. Voce ja pode fazer login."}

    user.email_verified_at = datetime.now(timezone.utc)
    db.commit()
    return {"message": "Email confirmado com sucesso. Voce ja pode fazer login."}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Obter dados do usuário atual"""
    return current_user


@router.put("/me", response_model=UserResponse)
def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Atualizar dados do usuário"""
    if user_data.name:
        current_user.name = user_data.name  # type: ignore[assignment]
    if user_data.daily_goal is not None:
        current_user.daily_goal = user_data.daily_goal  # type: ignore[assignment]
    if user_data.phone_number:
        phone_number = user_data.phone_number.strip()
        if not phone_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone inválido")
        existing_phone = (
            db.query(User)
            .filter(User.phone_number == phone_number, User.id != current_user.id)
            .first()
        )
        if existing_phone:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Telefone já registrado")
        current_user.phone_number = phone_number  # type: ignore[assignment]

    db.commit()
    db.refresh(current_user)

    return current_user


@router.post("/change-password")
def change_password(
    payload: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Alterar senha do usuario logado"""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")

    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ter pelo menos 6 caracteres",
        )

    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha nao pode ser igual a senha atual",
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Senha atualizada com sucesso"}


@router.post("/forgot-password")
def forgot_password(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Solicitar redefinicao de senha"""
    settings = get_settings()
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        scope="auth-forgot-ip",
        identifier=client_ip,
        limit=settings.auth_forgot_limit_per_ip,
        window_seconds=settings.auth_forgot_window_seconds,
    )

    user = db.query(User).filter(User.email == payload.email).first()

    # Sempre retorna a mesma mensagem para evitar enumeracao de usuarios
    default_message = "Se o email estiver cadastrado, enviaremos um link para redefinir a senha."

    if not user:
        return {"message": default_message}

    reset_token = create_password_reset_token(user.id)
    base_url = settings.frontend_base_url.rstrip("/")
    reset_url = f"{base_url}/reset-password?token={reset_token}"

    if is_smtp_configured():
        try:
            send_password_reset_email(user.email, reset_url)
            return {"message": default_message}
        except Exception:
            logger.exception("Falha ao enviar email de redefinicao para %s", user.email)
            if settings.environment.lower() != "production":
                return {
                    "message": "Falha no envio de email (dev). Use o link abaixo.",
                    "reset_url": reset_url,
                }
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Nao foi possivel enviar o email de redefinicao agora. Tente novamente em instantes.",
            )

    if settings.environment.lower() != "production":
        return {"message": "Reset gerado (ambiente de desenvolvimento).", "reset_url": reset_url}

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Recuperacao de senha nao configurada",
    )


@router.post("/resend-verification")
def resend_verification_email(request: Request, payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Reenviar email de confirmacao"""
    settings = get_settings()
    require_email_verification = bool(getattr(settings, "auth_require_email_verification", True))
    client_ip = get_client_ip(request)
    enforce_rate_limit(
        scope="auth-resend-ip",
        identifier=client_ip,
        limit=settings.auth_resend_limit_per_ip,
        window_seconds=settings.auth_resend_window_seconds,
    )
    enforce_rate_limit(
        scope="auth-resend-email",
        identifier=str(payload.email).lower(),
        limit=settings.auth_resend_limit_per_email,
        window_seconds=settings.auth_resend_window_seconds,
    )

    default_message = "Se o email estiver pendente de confirmacao, enviaremos um novo link."

    if not require_email_verification:
        return {"message": "Confirmacao de email desativada neste ambiente."}

    user = db.query(User).filter(User.email == payload.email).first()
    if not user or user.email_verified:
        return {"message": default_message}

    if not is_smtp_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Confirmacao de email nao configurada",
        )

    verify_token = create_email_verification_token(user.id)
    verify_url = f"{settings.frontend_base_url.rstrip('/')}/verify-email?token={verify_token}"
    try:
        send_email_verification_email(user.email, verify_url)
    except Exception:
        logger.exception("Falha ao reenviar email de confirmacao para %s", user.email)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nao foi possivel reenviar o email de confirmacao agora. Tente novamente em instantes.",
        )

    return {"message": default_message}


@router.post("/reset-password")
def reset_password(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Redefinir senha a partir de um token"""
    if len(payload.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A nova senha deve ter pelo menos 6 caracteres",
        )

    user_id = verify_password_reset_token(payload.token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token invalido ou expirado")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario nao encontrado")

    user.hashed_password = get_password_hash(payload.new_password)
    db.commit()
    return {"message": "Senha redefinida com sucesso"}
