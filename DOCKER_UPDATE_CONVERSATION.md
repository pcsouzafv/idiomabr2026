# 🔄 Guia de Atualização Docker

## ✅ O Que Foi Atualizado

### 1. Dashboard (/dashboard)
- ✅ **Novo Card:** Módulo de Conversação com IA adicionado
- 🎨 **Estilo:** Gradiente roxo-violeta (violet-500 to purple-600)
- 🎯 **Localização:** Entre "Estudar Frases com IA" e "Desafio Diário"
- 🔗 **Link:** `/conversation`

### 2. Docker Compose (docker-compose.yml)
- ✅ **Backend:** Variáveis ElevenLabs já configuradas
  - `ELEVENLABS_API_KEY`
  - `ELEVENLABS_VOICE_ID`
- ✅ **Frontend:** Build configurado
- ✅ **Networks:** Comunicação entre serviços OK

### 3. Scripts de Atualização
- ✅ **update-docker.sh** (Linux/Mac)
- ✅ **update-docker.bat** (Windows)

## 🚀 Como Atualizar a Imagem Docker

### Opção 1: Script Automático (Recomendado)

**Windows:**
```bash
.\update-docker.bat
```

**Linux/Mac:**
```bash
chmod +x update-docker.sh
./update-docker.sh
```

Escolha a opção:
1. **Atualizar TUDO** - Recomendado para novas features
2. **Apenas Backend** - Se só mudou código Python
3. **Apenas Frontend** - Se só mudou código React
4. **Rebuild completo** - Se estiver com problemas
5. **Ver logs** - Para debug

### Opção 2: Manual

#### Atualizar Tudo
```bash
docker compose down
docker compose pull
docker compose build --pull
docker compose up -d
```

#### Apenas Backend
```bash
docker compose stop backend
docker compose build --pull backend
docker compose up -d backend
```

#### Apenas Frontend
```bash
docker compose stop frontend
docker compose build --pull frontend
docker compose up -d frontend
```

#### Rebuild Completo (limpa cache)
```bash
docker compose down
docker compose pull
docker compose build --no-cache --pull
docker compose up -d
```

## 📋 Verificar Status

```bash
# Ver containers rodando
docker compose ps

# Ver logs
docker compose logs -f

# Ver logs de um serviço específico
docker compose logs -f backend
docker compose logs -f frontend
```

## 🔍 Verificar Funcionalidades

### 1. Dashboard
✅ Acessar: http://localhost:3000/dashboard
✅ Verificar card "Conversação com IA 🎙️"
✅ Clicar no card e acessar `/conversation`

### 2. Módulo de Conversação
✅ Acessar: http://localhost:3000/conversation
✅ Testar iniciar conversação
✅ Testar enviar mensagem
✅ Verificar resposta com áudio

### 3. Backend
✅ API Docs: http://localhost:8000/docs
✅ Verificar endpoints `/api/conversation/*`
✅ Testar endpoint `/api/conversation/voices`

## 🐛 Troubleshooting

### Erro: "Container já existe"
```bash
docker compose down
docker compose up -d
```

### Erro: "Porta já em uso"
```bash
# Verificar processos usando as portas
netstat -ano | findstr :3000
netstat -ano | findstr :8000

# Parar containers conflitantes
docker stop $(docker ps -aq)
```

### Erro: "Imagem não atualiza"
```bash
# Forçar rebuild sem cache
docker compose pull
docker compose build --no-cache --pull
docker compose up -d --force-recreate
```

### Erro: "ElevenLabs API não funciona"
1. Verificar `.env` tem `ELEVENLABS_API_KEY`
2. Rebuild backend:
```bash
docker compose stop backend
docker compose build --pull backend
docker compose up -d backend
```

### Erro: "Frontend não mostra novo card"
1. Limpar cache do navegador (Ctrl+Shift+Delete)
2. Rebuild frontend:
```bash
docker compose stop frontend
docker compose build --no-cache --pull frontend
docker compose up -d frontend
```

## 📊 Monitoramento

### Ver Uso de Recursos
```bash
docker stats
```

### Ver Logs em Tempo Real
```bash
# Todos os serviços
docker compose logs -f

# Apenas backend
docker compose logs -f backend

# Apenas frontend
docker compose logs -f frontend

# Últimas 100 linhas
docker compose logs --tail=100
```

### Verificar Saúde dos Containers
```bash
docker compose ps
```

Saída esperada:
```
NAME                    STATUS
idiomasbr-backend       Up (healthy)
idiomasbr-frontend      Up
idiomasbr-postgres      Up (healthy)
idiomasbr-ollama        Up (healthy)
```

## 🔐 Variáveis de Ambiente

Certifique-se que o `.env` contém:

```env
# ElevenLabs (Conversação com IA)
ELEVENLABS_API_KEY=sk_b02c22ac329da0be5814c207bbe6a1b76d3b0f827da68aad
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# OpenAI (IA para respostas)
OPENAI_API_KEY=sk-proj-...

# OU DeepSeek
DEEPSEEK_API_KEY=sk-...
```

## 🚀 Deploy em Produção

### Google Cloud Platform (GCP)
```bash
# Build e push para Container Registry
docker-compose build
docker tag idiomasbr-backend gcr.io/seu-projeto/idiomasbr-backend
docker tag idiomasbr-frontend gcr.io/seu-projeto/idiomasbr-frontend
docker push gcr.io/seu-projeto/idiomasbr-backend
docker push gcr.io/seu-projeto/idiomasbr-frontend
```

### Docker Hub
```bash
# Login
docker login

# Tag e push
docker tag idiomasbr-backend seu-usuario/idiomasbr-backend:latest
docker tag idiomasbr-frontend seu-usuario/idiomasbr-frontend:latest
docker push seu-usuario/idiomasbr-backend:latest
docker push seu-usuario/idiomasbr-frontend:latest
```

## 📝 Checklist de Atualização

- [ ] Código atualizado no Git
- [ ] `.env` configurado corretamente
- [ ] Docker está rodando
- [ ] Executar script de atualização
- [ ] Verificar containers rodando (`docker-compose ps`)
- [ ] Acessar dashboard e verificar novo card
- [ ] Testar módulo de conversação
- [ ] Verificar logs sem erros
- [ ] Testar API endpoints
- [ ] Backup do banco de dados (se necessário)

## 🎯 Próximos Passos

1. **Testar localmente** com Docker
2. **Verificar todas as funcionalidades**
3. **Fazer backup do banco** antes de deploy
4. **Deploy em staging** (opcional)
5. **Deploy em produção**
6. **Monitorar logs** após deploy

## 📚 Comandos Úteis

```bash
# Reiniciar tudo
docker-compose restart

# Parar tudo
docker-compose stop

# Remover tudo (⚠️ CUIDADO: remove volumes)
docker-compose down -v

# Limpar containers parados
docker container prune

# Limpar imagens não usadas
docker image prune

# Limpar tudo (⚠️ CUIDADO)
docker system prune -a
```

---

**Status:** ✅ Docker atualizado e pronto para deploy
**Última atualização:** 09/01/2026
**Módulo adicionado:** Conversação com IA (ElevenLabs + OpenAI/DeepSeek)
