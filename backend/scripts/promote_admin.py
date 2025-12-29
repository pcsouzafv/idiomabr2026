"""Promove (ou remove) permissão de admin de um usuário.

Uso (no host ou no container backend, com DATABASE_URL configurada):

  python backend/scripts/promote_admin.py --email "voce@dominio.com" --grant
  python backend/scripts/promote_admin.py --email "voce@dominio.com" --revoke

Este script existe porque o sistema NÃO expõe endpoint público para promover admins.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user import User


def main() -> int:
    parser = argparse.ArgumentParser(description="Promover/remover admin de um usuário")
    parser.add_argument("--email", required=True, help="Email do usuário a alterar")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--grant", action="store_true", help="Define is_admin=true")
    group.add_argument("--revoke", action="store_true", help="Define is_admin=false")

    args = parser.parse_args()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == args.email).first()
        if not user:
            print(f"[ERRO] Usuário não encontrado: {args.email}")
            return 2

        new_value = bool(args.grant)
        user.is_admin = new_value  # type: ignore[assignment]
        db.commit()
        db.refresh(user)

        status = "ADMIN" if user.is_admin else "NÃO-ADMIN"
        print(f"[OK] {user.email} agora é {status} (id={user.id}).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
