# Deploy em VPS (barato) — Docker Compose + Caddy

Este guia roda o IdiomasBR em **1 VPS** com **HTTPS automático** via Caddy.

## Domínios (recomendado)

- Frontend: `app.idiomasbr.com`
- Backend: `api.idiomasbr.com`

> Se quiser usar o domínio raiz (`idiomasbr.com`) também dá, mas subdomínios deixam tudo mais simples.

---

## 1) DNS

Crie registros **A** apontando para o IP da VPS:

- `app.idiomasbr.com` → `IP_DA_VPS`
- `api.idiomasbr.com` → `IP_DA_VPS`

---

## 2) Preparar a VPS

Exemplo para Ubuntu:

```bash
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl git

# Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER

# Docker Compose plugin (normalmente já vem)
docker compose version
```

Reinicie a sessão (logout/login) para aplicar o grupo `docker`.

---

## 3) Clonar o projeto

```bash
git clone https://github.com/pcsouzafv/idiomabr2026.git
cd idiomabr2026
```

---

## 4) Configurar variáveis de ambiente

Crie um `.env` (no servidor) baseado em `.env.example`:

```bash
cp .env.example .env
nano .env
```

Obrigatório ajustar:

- `POSTGRES_PASSWORD` (senha forte)
- `SECRET_KEY` (string longa e aleatória)

Para o deploy por subdomínios, deixe:

- `NEXT_PUBLIC_API_URL=https://api.idiomasbr.com`

---

## 5) Subir em produção

O compose de produção usa [docker-compose.prod.yml](docker-compose.prod.yml) e Caddy com [Caddyfile](Caddyfile).

```bash
docker compose --env-file .env -f docker-compose.prod.yml up -d --build
```

Verificar status:

```bash
docker compose -f docker-compose.prod.yml ps
```

---

## 6) Backup do Postgres

Script pronto em [scripts/backup_postgres.sh](scripts/backup_postgres.sh):

```bash
chmod +x scripts/backup_postgres.sh
./scripts/backup_postgres.sh
```

Para rodar diariamente via cron (exemplo 03:30):

```bash
crontab -e
```

Adicionar:

```cron
30 3 * * * cd /caminho/idiomabr2026 && ./scripts/backup_postgres.sh >> backups/backup.log 2>&1
```

---

## 7) Atualizar (deploy de nova versão)

```bash
cd idiomabr2026
git pull

docker compose --env-file .env -f docker-compose.prod.yml up -d --build
```

---

## Observação sobre Ollama

O deploy de VPS **não sobe o Ollama** por padrão (para reduzir custo/RAM/CPU). Se você quiser usar IA:

- Use `OPENAI_API_KEY` e/ou `DEEPSEEK_API_KEY` no `.env`.
