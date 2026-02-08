# Deploy na VPS Oracle (Docker Compose + Caddy no host)

Este guia descreve o deploy atual do IdiomasBR na VPS da Oracle:
- Ubuntu na VPS Oracle
- Docker Compose para postgres, redis, backend (FastAPI) e frontend (Next.js)
- Caddy rodando no host (systemd) com HTTPS automatico
- Dominio raiz (idiomasbr.com) e www apontando para o IP da VPS
- API servida no mesmo dominio via /api

## Visao geral da rota
- https://idiomasbr.com           -> frontend (Next.js)
- https://idiomasbr.com/api/*     -> backend (FastAPI)

Isso evita subdominios (api/app). Se voce decidir criar subdominios no futuro,
ajuste NEXT_PUBLIC_API_URL e o Caddyfile.

## 1) DNS (ja configurado)
No provedor do dominio, criar registros A:
- idiomasbr.com -> IP da VPS
- www           -> IP da VPS

## 2) Preparar a VPS (Ubuntu)

```bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# (opcional) Caddy via systemd
# sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
# curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo tee /etc/apt/trusted.gpg.d/caddy-stable.asc
# curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
# sudo apt-get update -y
# sudo apt-get install -y caddy
```

Logout/login para aplicar o grupo docker.

## 3) Clonar o projeto

```bash
git clone https://github.com/pcsouzafv/idiomabr2026.git
cd idiomabr2026
```

## 4) Configurar .env

```bash
cp .env.example .env
nano .env
```

Minimo obrigatorio:
- POSTGRES_PASSWORD (senha forte)
- SECRET_KEY (string longa e aleatoria)
- NEXT_PUBLIC_API_URL=https://idiomasbr.com

Observacao importante:
- NEXT_PUBLIC_API_URL e embutido no build do Next.js.
- Se voce mudar esse valor, precisa rebuildar o frontend.

## 5) Garantir que o compose usa NEXT_PUBLIC_API_URL
No docker-compose.yml, o frontend deve usar a variavel:

```yaml
frontend:
  build:
    args:
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-https://idiomasbr.com}
  environment:
    NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-https://idiomasbr.com}
```

## 6) Caddy no host (systemd)
Arquivo: /etc/caddy/Caddyfile

```caddyfile
{
  email admin@idiomasbr.com
}

idiomasbr.com, www.idiomasbr.com {
  handle /api/* {
    reverse_proxy 127.0.0.1:8000
  }
  handle {
    reverse_proxy 127.0.0.1:3000
  }
}
```

Aplicar:

```bash
sudo systemctl reload caddy
```

## 7) Subir os containers

```bash
docker compose up -d --build
```

Conferir:

```bash
docker compose ps
```

## 8) Validacao rapida

```bash
# frontend (200)
curl -I http://127.0.0.1:3000

# backend (200/404 ja indica que respondeu)
curl -I http://127.0.0.1:8000
```

No navegador:
- https://idiomasbr.com
- login deve chamar https://idiomasbr.com/api/auth/login

## 9) Procedimento correto de atualizacao (deploy)

```bash
cd ~/idiomabr2026

# atualizar codigo
git pull

# revisar .env (evitar duplicados)
grep NEXT_PUBLIC_API_URL .env

# rebuild (use o que mudou)
# se alterou frontend ou NEXT_PUBLIC_API_URL:
docker compose build --no-cache frontend

# se alterou backend:
docker compose build backend

# subir

docker compose up -d

# se mudou Caddyfile:
sudo systemctl reload caddy
```

Checklist pos-deploy:
- docker compose ps
- docker compose logs --tail 50 frontend
- docker compose logs --tail 50 backend
- sudo journalctl -u caddy -n 50 --no-pager

## 10) Problemas comuns (lembrete rapido)
- Browser chama http://localhost:8000
  -> NEXT_PUBLIC_API_URL errado; rebuild do frontend.
- ERR_NAME_NOT_RESOLVED para api.idiomasbr.com
  -> subdominio nao existe; usar /api no dominio raiz ou criar DNS.
- 502 no site
  -> Caddy apontando para backend:8000 (nome de container). Use 127.0.0.1.
- 404 em /api/auth/login
  -> Caddy usando handle_path e removendo /api. Use handle /api/*.
