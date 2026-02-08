#!/usr/bin/env python3
"""Script para criar usuário admin"""
from app.core.database import SessionLocal
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    db = SessionLocal()

    # Verificar se já existe admin
    admin = db.query(User).filter(User.email == "admin@idiomasbr.com").first()
    if admin:
        print("✓ Admin já existe!")
        print(f"  Email: admin@idiomasbr.com")
        print(f"  Senha: admin123")
        return

    # Criar novo admin
    hashed_password = pwd_context.hash("admin123")

    new_admin = User(
        email="admin@idiomasbr.com",
        name="Administrador",
        hashed_password=hashed_password,
        is_active=True,
        is_admin=True,
        daily_goal=20,
        current_streak=0
    )

    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)

    print("✓ Admin criado com sucesso!")
    print(f"  Email: admin@idiomasbr.com")
    print(f"  Senha: admin123")
    print(f"  ID: {new_admin.id}")

    db.close()

if __name__ == "__main__":
    create_admin()
