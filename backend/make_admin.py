#!/usr/bin/env python3
"""
Script para promover um usuário a administrador

Uso:
    python make_admin.py usuario@email.com
"""

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.config import get_settings

settings = get_settings()


def make_admin(email: str):
    """Promove um usuário a administrador"""

    # Criar engine
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Buscar usuário
        user = db.query(User).filter(User.email == email).first()

        if not user:
            print(f"❌ Erro: Usuário com email '{email}' não encontrado")
            return False

        # Verificar se já é admin
        if user.is_admin:
            print(f"ℹ️  O usuário '{user.name}' ({email}) já é administrador")
            return True

        # Promover a admin
        user.is_admin = True
        db.commit()

        print(f"✅ Sucesso! O usuário '{user.name}' ({email}) agora é administrador")
        return True

    except Exception as e:
        print(f"❌ Erro ao promover usuário: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def list_admins():
    """Lista todos os administradores"""

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        admins = db.query(User).filter(User.is_admin == True).all()

        if not admins:
            print("ℹ️  Nenhum administrador encontrado")
            return

        print(f"\n📋 Administradores do sistema ({len(admins)}):\n")
        for admin in admins:
            print(f"  • {admin.name} ({admin.email})")
            print(f"    ID: {admin.id} | Ativo: {'Sim' if admin.is_active else 'Não'}")
            print()

    except Exception as e:
        print(f"❌ Erro ao listar administradores: {e}")
    finally:
        db.close()


def revoke_admin(email: str):
    """Remove privilégios de administrador de um usuário"""

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            print(f"❌ Erro: Usuário com email '{email}' não encontrado")
            return False

        if not user.is_admin:
            print(f"ℹ️  O usuário '{user.name}' ({email}) não é administrador")
            return True

        user.is_admin = False
        db.commit()

        print(f"✅ Privilégios de administrador removidos de '{user.name}' ({email})")
        return True

    except Exception as e:
        print(f"❌ Erro ao revogar admin: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("📚 Uso:")
        print("  python make_admin.py <email>          - Promover usuário a admin")
        print("  python make_admin.py --list           - Listar todos os admins")
        print("  python make_admin.py --revoke <email> - Revogar privilégios de admin")
        print()
        print("Exemplos:")
        print("  python make_admin.py usuario@example.com")
        print("  python make_admin.py --list")
        print("  python make_admin.py --revoke usuario@example.com")
        sys.exit(1)

    command = sys.argv[1]

    if command == "--list":
        list_admins()
    elif command == "--revoke":
        if len(sys.argv) < 3:
            print("❌ Erro: Especifique o email do usuário")
            sys.exit(1)
        email = sys.argv[2]
        revoke_admin(email)
    else:
        # Assume que é um email para promover
        email = command
        make_admin(email)


if __name__ == "__main__":
    main()
