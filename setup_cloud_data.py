"""Script para configurar dados iniciais no Cloud Run.

Nota: o endpoint de registro NÃO promove usuários a admin automaticamente.
Para acesso às rotas administrativas (ex.: CRUD de vídeos e criação/importação de palavras),
é necessário definir `users.is_admin = true` diretamente no banco.
"""
import requests
import json

BACKEND_URL = "https://idiomasbr-backend-975964890266.us-central1.run.app"

# 1. Criar usuario
print("Criando usuario...")
response = requests.post(
    f"{BACKEND_URL}/api/auth/register",
    json={
        "email": "admin@idiomasbr.com",
        "name": "Administrador",
        "password": "admin123"
    }
)

if response.status_code == 200:
    print("[OK] Usuario criado com sucesso!")
    user_data = response.json()
    print(f"   ID: {user_data['id']}")
    print(f"   Email: {user_data['email']}")
    print("   [!] Para acesso ADMIN, defina users.is_admin=true no banco.")
else:
    print(f"[ERRO] Erro ao criar usuario: {response.text}")
    if "already exists" not in response.text.lower():
        exit(1)

# 2. Fazer login para obter token
print("\nFazendo login...")
response = requests.post(
    f"{BACKEND_URL}/api/auth/login",
    data={
        "username": "admin@idiomasbr.com",
        "password": "admin123"
    }
)

if response.status_code == 200:
    token = response.json()["access_token"]
    print("[OK] Login realizado com sucesso!")
else:
    print(f"[ERRO] Erro ao fazer login: {response.text}")
    exit(1)

# 3. Verificar palavras existentes
print("\nVerificando palavras existentes...")
response = requests.get(
    f"{BACKEND_URL}/api/words",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code == 200:
    words_data = response.json()
    print(f"[OK] Banco de dados conectado!")
    print(f"   Palavras cadastradas: {words_data.get('total', 0)}")
else:
    print(f"[AVISO] {response.status_code} - {response.text}")

print("\n" + "="*60)
print("CONFIGURACAO CONCLUIDA!")
print("="*60)
print(f"\nAcesse o frontend: https://idiomasbr-frontend-975964890266.us-central1.run.app")
print(f"\nCredenciais de teste:")
print(f"  Email: admin@idiomasbr.com")
print(f"  Senha: admin123")
print("\n[!] IMPORTANTE: Troque esta senha em producao!")
print("[!] Para habilitar acesso ADMIN, marque users.is_admin=true no banco.")
print("="*60)
