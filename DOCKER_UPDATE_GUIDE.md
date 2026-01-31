# 🐳 Guia de Atualização do Docker

## 📦 O que foi atualizado

### 1. **docker-compose.yml**
- ✅ Adicionado volume `backend_cache` para cache de APIs
- ✅ Mapeamento do cache em `/app/.cache`

### 2. **requirements.txt**
- ✅ `requests==2.32.3` - Já incluída (para APIs)

### 3. **Novos Scripts**
- ✅ `backend/services/dictionary_api.py` - Integração com APIs
- ✅ `backend/enrich_words.py` - Enriquecimento local
- ✅ `backend/enrich_words_api.py` - Enriquecimento via API
- ✅ `backend/migrations/add_word_details.sql` - Migração SQL

---

## 🚀 Como Atualizar

### Opção 1: Script Automático (Recomendado)

```bash
.\docker-rebuild.bat
```

Este script:
1. Para containers
2. Faz rebuild das imagens
3. Inicia containers novos
4. Aplica migrações
5. Pronto para usar!

### Opção 2: Manual

```bash
# 1. Parar containers
docker compose down

# 2. Baixar imagens (services com image: ...)
docker compose pull

# 3. Rebuild (força rebuild sem cache e atualiza base images)
docker compose build --no-cache --pull

# 4. Iniciar novamente
docker compose up -d

# 4. Aguardar banco inicializar
timeout /t 15

# 5. Aplicar migrações
docker cp backend\migrations\add_word_details.sql idiomasbr-postgres:/tmp/
docker compose exec postgres psql -U idiomasbr -d idiomasbr -f /tmp/add_word_details.sql
```

---

## ✅ Verificação

### Containers rodando
```bash
docker compose ps
```

**Deve mostrar:**
```
NAME                    STATUS
idiomasbr-postgres      Up (healthy)
idiomasbr-backend       Up
idiomasbr-frontend      Up
```

### Backend funcionando
```bash
curl http://localhost:8000/docs
```

### Banco de dados com novos campos
```bash
docker compose exec postgres psql -U idiomasbr -d idiomasbr -c "\d words"
```

**Deve listar os novos campos:**
- word_type
- definition_en
- definition_pt
- synonyms
- antonyms
- example_sentences
- usage_notes
- collocations

---

## 🔧 Troubleshooting

### Erro: "port is already allocated"

**Solução 1: Parar tudo**
```bash
docker-compose down
docker ps -a  # Ver todos containers
docker stop $(docker ps -aq)  # Parar todos
```

**Solução 2: Mudar portas** (editar `docker-compose.yml`)
```yaml
ports:
  - "8001:8000"  # Backend na porta 8001
  - "3001:3000"  # Frontend na porta 3001
```

### Erro: "network not found"

```bash
docker network create idiomasbr-network
docker-compose up -d
```

### Erro: "volume not found"

```bash
docker volume create idiomasbr_backend_cache
docker volume create idiomasbr_postgres_data
docker-compose up -d
```

### Build muito lento

**Limpar cache do Docker:**
```bash
docker system prune -a
docker-compose build --no-cache
```

### Container não inicia

**Ver logs:**
```bash
docker-compose logs backend --tail 50
docker-compose logs postgres --tail 50
docker-compose logs frontend --tail 50
```

---

## 📊 Volumes Criados

| Volume | Descrição | Localização |
|--------|-----------|-------------|
| `postgres_data` | Dados do PostgreSQL | `/var/lib/postgresql/data` |
| `backend_cache` | Cache de APIs | `/app/.cache` |

### Ver volumes
```bash
docker volume ls
```

### Inspecionar volume
```bash
docker volume inspect idiomasbr_backend_cache
docker volume inspect idiomasbr_postgres_data
```

### Backup do banco
```bash
# Exportar
docker compose exec postgres pg_dump -U idiomasbr idiomasbr > backup.sql

# Importar
docker compose exec -T postgres psql -U idiomasbr -d idiomasbr < backup.sql
```

---

## 🔄 Comandos Úteis

### Ver logs em tempo real
```bash
docker compose logs -f
docker compose logs -f backend
docker compose logs -f postgres
```

### Reiniciar apenas um serviço
```bash
docker compose restart backend
docker compose restart postgres
docker compose restart frontend
```

### Entrar no container
```bash
# Backend
docker compose exec backend bash

# PostgreSQL
docker compose exec postgres psql -U idiomasbr -d idiomasbr

# Frontend
docker compose exec frontend sh
```

### Ver uso de recursos
```bash
docker stats
```

### Limpar tudo (CUIDADO!)
```bash
# Remove containers, networks, volumes
docker compose down -v

# Remove imagens também
docker compose down -v --rmi all
```

---

## 🎯 Após Atualização

### 1. Testar Backend
```bash
curl http://localhost:8000/docs
```

### 2. Testar Frontend
Abrir http://localhost:3000

### 3. Enriquecer Palavras

**Opção A: Dados Locais (rápido)**
```bash
.\enrich-words.bat
```

**Opção B: APIs (completo)**
```bash
.\enrich-words-api.bat
```

### 4. Verificar Dados
```bash
docker-compose exec postgres psql -U idiomasbr -d idiomasbr

# No psql:
SELECT COUNT(*) FROM words WHERE definition_en IS NOT NULL;
\q
```

---

## 📈 Performance

### Antes vs Depois

| Aspecto | Antes | Depois |
|---------|-------|--------|
| Tamanho imagem backend | ~500MB | ~500MB |
| Tempo de build | ~2 min | ~2 min |
| Volumes | 1 | 2 |
| Cache de API | ❌ | ✅ |

### Otimizações Aplicadas

1. **Cache persistente**: APIs não precisam refazer requests
2. **Volume mapeado**: `/app` permite hot reload em dev
3. **Health check**: Backend só inicia após DB estar pronto

---

## 🆕 Novidades no Docker

### Variáveis de Ambiente

Novas variáveis (opcional):

```bash
# .env
POSTGRES_USER=idiomasbr
POSTGRES_PASSWORD=idiomasbr123
POSTGRES_DB=idiomasbr
SECRET_KEY=sua-chave-secreta
```

### Networks

Todos os containers na mesma network:
```
idiomasbr-network (bridge)
```

### Healthcheck

PostgreSQL tem healthcheck:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U idiomasbr"]
  interval: 10s
  timeout: 5s
  retries: 5
```

---

## 📝 Checklist de Atualização

- [ ] Backup do banco de dados (opcional mas recomendado)
- [ ] Executar `docker-rebuild.bat`
- [ ] Verificar containers rodando (`docker-compose ps`)
- [ ] Testar backend (http://localhost:8000/docs)
- [ ] Testar frontend (http://localhost:3000)
- [ ] Verificar novos campos no banco
- [ ] Executar enriquecimento de palavras
- [ ] Testar flashcards com novos dados

---

## 🎓 Próximos Passos

1. ✅ Docker atualizado
2. ⏭️ Executar `.\enrich-words-api.bat`
3. ⏭️ Testar a aplicação
4. ⏭️ Deploy para produção (se aplicável)

---

## 📞 Suporte

### Logs completos
```bash
docker-compose logs > docker-logs.txt
```

### Status do sistema
```bash
docker-compose ps
docker volume ls
docker network ls
docker images
```

### Reiniciar do zero (última opção)
```bash
# CUIDADO: Apaga TODOS os dados!
docker-compose down -v
docker system prune -a -f
docker-compose up -d --build
```

---

**Atualização concluída! 🎉**

Execute agora: `.\docker-rebuild.bat`
