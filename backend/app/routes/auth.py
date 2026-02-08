from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    create_password_reset_token,
    verify_password_reset_token
)
from app.core.config import get_settings
from app.services.email_service import send_email
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


@router.post("/register", response_model=UserResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Registrar novo usuário"""
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
    
    # Criar usuário
    user = User(
        email=user_data.email,
        phone_number=phone_number,
        name=user_data.name,
        hashed_password=get_password_hash(user_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login com email e senha"""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    settings = get_settings()
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


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
def forgot_password(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    """Solicitar redefinicao de senha"""
    settings = get_settings()
    user = db.query(User).filter(User.email == payload.email).first()

    # Sempre retorna a mesma mensagem para evitar enumeracao de usuarios
    default_message = "Se o email estiver cadastrado, enviaremos um link para redefinir a senha."

    if not user:
        return {"message": default_message}

    reset_token = create_password_reset_token(user.id)
    base_url = settings.frontend_base_url.rstrip("/")
    reset_url = f"{base_url}/reset-password?token={reset_token}"

    if settings.smtp_host and settings.smtp_from:
        subject = "Redefinicao de senha - IdiomasBR"
        text_body = f"Use este link para redefinir sua senha: {reset_url}"
        html_body = (
            "<p>Voce solicitou a redefinicao de senha.</p>"
            f"<p><a href=\"{reset_url}\">Clique aqui para redefinir a senha</a></p>"
            "<p>Se voce nao solicitou, ignore este email.</p>"
        )
        send_email(user.email, subject, html_body, text_body)
        return {"message": default_message}

    if settings.environment.lower() != "production":
        return {"message": "Reset gerado (ambiente de desenvolvimento).", "reset_url": reset_url}

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Recuperacao de senha nao configurada",
    )


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
