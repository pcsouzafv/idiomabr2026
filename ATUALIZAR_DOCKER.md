# ⚡ Guia Rápido - Atualizar Docker

## 🎯 Um Comando Só

```bash
.\docker-rebuild.bat
```

Isso vai fazer **tudo automaticamente**:
- ✅ Parar containers
- ✅ Rebuild das imagens
- ✅ Iniciar containers
- ✅ Aplicar migrações
- ✅ Pronto para usar!

---

## 📝 Passo a Passo Manual

Se preferir fazer manualmente:

### 1. Parar containers
```bash
docker-compose down
```

### 2. Rebuild
```bash
docker-compose build --no-cache
```

### 3. Iniciar
```bash
docker-compose up -d
```

### 4. Aguardar (15 segundos)
```bash
timeout /t 15
```

### 5. Aplicar migração
```bash
docker cp backend\migrations\add_word_details.sql idiomasbr-postgres:/tmp/
docker-compose exec postgres psql -U idiomasbr -d idiomasbr -f /tmp/add_word_details.sql
```

---

## ✅ Verificar se Funcionou

### Ver containers rodando
```bash
docker-compose ps
```

**Deve mostrar 3 containers "Up":**
- idiomasbr-postgres
- idiomasbr-backend
- idiomasbr-frontend

### Testar acesso
- Frontend: http://localhost:3000
- Backend: http://localhost:8000/docs

---

## 🔄 O que Mudou

### Arquivos Modificados:
- ✅ `docker-compose.yml` - Adicionado volume de cache
- ✅ `requirements.txt` - Biblioteca `requests` (já tinha)

### Arquivos Novos:
- ✅ `backend/services/dictionary_api.py`
- ✅ `backend/enrich_words.py`
- ✅ `backend/enrich_words_api.py`
- ✅ `backend/migrations/add_word_details.sql`
- ✅ `docker-rebuild.bat`

### Banco de Dados:
- ✅ 8 novos campos na tabela `words`

---

## 🚀 Próximo Passo

Após atualizar o Docker, enriqueça as palavras:

```bash
# Opção 1: Rápido (5 segundos)
.\enrich-words.bat

# Opção 2: Completo (25 minutos)
.\enrich-words-api.bat
```

---

## 🐛 Problemas?

### Container não inicia
```bash
docker-compose logs backend --tail 20
```

### Porta ocupada
Edite `docker-compose.yml` e mude:
```yaml
ports:
  - "8001:8000"  # Backend
  - "3001:3000"  # Frontend
```

### Banco não conecta
```bash
docker-compose restart postgres
timeout /t 10
docker-compose restart backend
```

---

**Mais detalhes**: Veja `DOCKER_UPDATE_GUIDE.md`
