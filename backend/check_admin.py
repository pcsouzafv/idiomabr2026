#!/usr/bin/env python3
"""
Script para verificar se um usuário é admin

Uso:
    python check_admin.py usuario@email.com
"""

import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User
from app.core.config import get_settings

settings = get_settings()


def check_admin(email: str):
    """Verifica se um usuário é admin e mostra detalhes"""

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

        print(f"\n📋 Detalhes do Usuário:\n")
        print(f"  ID: {user.id}")
        print(f"  Nome: {user.name}")
        print(f"  Email: {user.email}")
        print(f"  Ativo: {'✅ Sim' if user.is_active else '❌ Não'}")
        print(f"  Admin: {'✅ SIM' if user.is_admin else '❌ NÃO'}")
        print(f"  Meta Diária: {user.daily_goal} palavras")
        print(f"  Streak Atual: {user.current_streak} dias")
        print(f"  Criado em: {user.created_at}")
        print()

        if user.is_admin:
            print("✅ Este usuário TEM permissões de administrador")
            print("\n💡 Próximos passos:")
            print("   1. Faça LOGOUT no navegador")
            print("   2. Faça LOGIN novamente")
            print("   3. Acesse http://localhost:3000/admin")
        else:
            print("❌ Este usuário NÃO TEM permissões de administrador")
            print("\n💡 Para promover a admin, execute:")
            print(f"   python make_admin.py {email}")

        return True

    except Exception as e:
        print(f"❌ Erro ao verificar usuário: {e}")
        return False
    finally:
        db.close()


def list_all_users():
    """Lista todos os usuários do sistema"""

    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        users = db.query(User).all()

        if not users:
            print("ℹ️  Nenhum usuário encontrado no sistema")
            return

        print(f"\n📋 Todos os Usuários ({len(users)}):\n")
        for user in users:
            admin_badge = "👑 ADMIN" if user.is_admin else "👤"
            active_badge = "✅" if user.is_active else "❌"
            print(f"  {admin_badge} {active_badge} {user.name} ({user.email})")
            print(f"     ID: {user.id} | Streak: {user.current_streak} dias")
            print()

    except Exception as e:
        print(f"❌ Erro ao listar usuários: {e}")
    finally:
        db.close()


def main():
    if len(sys.argv) < 2:
        print("📚 Uso:")
        print("  python check_admin.py <email>       - Verificar se usuário é admin")
        print("  python check_admin.py --list        - Listar todos os usuários")
        print()
        print("Exemplos:")
        print("  python check_admin.py usuario@example.com")
        print("  python check_admin.py --list")
        sys.exit(1)

    command = sys.argv[1]

    if command == "--list":
        list_all_users()
    else:
        # Assume que é um email
        email = command
        check_admin(email)


if __name__ == "__main__":
    main()
