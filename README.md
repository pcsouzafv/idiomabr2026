# IdiomasBR - Plataforma de Aprendizado de Inglês

Aplicação web para aprendizado de inglês com flashcards e repetição espaçada (spaced repetition).

## 🚀 Funcionalidades

- ✅ **Flashcards Inteligentes** - Sistema de repetição espaçada (SM-2)
- ✅ **5.000+ Palavras** - Vocabulário de alta frequência com IPA e tradução
- ✅ **Pronúncia** - Transcrição fonética (IPA) + Text-to-Speech
- ✅ **Gamificação** - Streaks diários, metas e progresso
- ✅ **Estudo Bidirecional** - Inglês→Português e Português→Inglês

## 📁 Estrutura do Projeto

```
idiomasbr2026/
├── backend/           # API FastAPI + PostgreSQL
│   ├── app/
│   │   ├── core/      # Configurações, DB, segurança
│   │   ├── models/    # Modelos SQLAlchemy
│   │   ├── routes/    # Endpoints da API
│   │   └── schemas/   # Schemas Pydantic
│   ├── import_words.py
│   └── requirements.txt
│
└── frontend/          # Next.js + Tailwind CSS
    ├── src/
    │   ├── app/       # Páginas (App Router)
    │   ├── lib/       # API client
    │   └── store/     # Zustand state
    └── package.json
```

## 🛠️ Setup - Backend

### 1. Criar ambiente virtual

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Configurar banco de dados

Crie um arquivo `.env` baseado no `.env.example`:

```bash
cp .env.example .env
```

Edite o `.env` com suas configurações:

```env
DATABASE_URL=postgresql://usuario:senha@localhost:5432/idiomasbr
SECRET_KEY=sua-chave-secreta-muito-segura
```

### 4. Criar banco de dados PostgreSQL

```sql
CREATE DATABASE idiomasbr;
```

### 5. Importar palavras

```bash
# Criar algumas palavras de exemplo
python import_words.py

# OU importar de um CSV
python import_words.py caminho/para/palavras.csv
```

O CSV deve ter as colunas: `english`, `ipa`, `portuguese`

Opcional: gerar um CSV de vocabulário a partir de um PDF/transcrições (extrai apenas tokens, não salva trechos do conteúdo):

```bash
python backend/scripts/ingest_course_material.py --pdf "C:/Users/.../curso.pdf" --out "backend/data/curso_vocab.csv" --translate
python backend/import_words.py backend/data/curso_vocab.csv
```

### 6. Iniciar servidor

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em: http://localhost:8000
Documentação: http://localhost:8000/docs

## 🎨 Setup - Frontend

### 1. Instalar dependências

```bash
cd frontend
npm install
```

### 2. Configurar variáveis de ambiente

Crie um arquivo `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Iniciar servidor de desenvolvimento

```bash
npm run dev
```

O frontend estará disponível em: http://localhost:3000

## 📱 Endpoints da API

### Autenticação
- `POST /api/auth/register` - Criar conta
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Dados do usuário

### Palavras
- `GET /api/words` - Listar palavras (com busca e filtros)
- `GET /api/words/{id}` - Detalhes da palavra
- `POST /api/words/bulk` - Importar palavras em lote

### Estudo
- `GET /api/study/session` - Obter sessão de estudo
- `POST /api/study/review` - Registrar revisão
- `GET /api/study/stats` - Estatísticas de progresso
- `GET /api/study/history` - Histórico de estudo

## 🧠 Algoritmo de Repetição Espaçada

O app usa uma versão simplificada do algoritmo SM-2:

| Dificuldade | Próxima Revisão |
|-------------|-----------------|
| **Difícil** | 4 horas depois  |
| **Médio**   | 1 dia depois    |
| **Fácil**   | 3+ dias depois  |

A cada revisão bem-sucedida, o intervalo aumenta progressivamente.

## 🐳 Docker

### Pré-requisitos
- Docker Desktop instalado
- Docker Compose

### Iniciar com Docker (Produção)

```bash
# Windows
docker-start.bat

# Ou manualmente
docker-compose up --build -d
```

### Iniciar com Docker (Desenvolvimento)

```bash
# Windows - Com hot-reload
docker-dev.bat

# Ou manualmente
docker-compose -f docker-compose.dev.yml up --build
```

### Parar containers

```bash
# Windows
docker-stop.bat

# Ou manualmente
docker-compose down
```

### URLs após iniciar

- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **PostgreSQL:** localhost:5432

## ☁️ Deploy na GCP

Para atualização/deploy no Google Cloud (Cloud Run + Cloud SQL), veja: [GCP_DEPLOY_GUIDE.md](GCP_DEPLOY_GUIDE.md)

### Variáveis de ambiente Docker

Copie `.env.docker` para `.env` e ajuste conforme necessário:

```bash
copy .env.docker .env
```

## 🔧 Tecnologias

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- JWT (autenticação)

### Frontend
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Zustand (estado)
- Framer Motion (animações)

## 🔐 Sistema de Administração

O projeto inclui um **painel completo de administração** para gerenciar o banco de dados:

### Funcionalidades Admin
- ✅ **Dashboard com estatísticas** em tempo real
- ✅ **CRUD completo** de palavras, sentenças, vídeos e usuários
- ✅ **Importação em massa** via CSV (com templates)
- ✅ **Filtros e busca** avançada
- ✅ **Controle de permissões** (admin vs usuário comum)

### Acesso Rápido

```bash
# 1. Criar conta no sistema (http://localhost:3000/register)

# 2. Promover usuário a admin
cd backend
python make_admin.py seu-email@example.com

# 3. Acessar painel
# http://localhost:3000/admin
```

### Documentação Completa
- **[QUICK_START_ADMIN.md](QUICK_START_ADMIN.md)** - Início rápido (5 minutos)
- **[ADMIN_GUIDE.md](ADMIN_GUIDE.md)** - Guia completo do sistema admin
- **Template CSV de exemplo:** `template_palavras_exemplo.csv`

### Importar Dados

```bash
# Via interface web (recomendado)
1. Acesse /admin/words
2. Baixe o template CSV
3. Edite com suas palavras
4. Importe o arquivo

# Via API
curl -X POST http://localhost:8000/api/admin/words/bulk \
  -H "Authorization: Bearer SEU_TOKEN" \
  -F "file=@palavras.csv"
```

## 📊 Próximos Passos

- [x] Sistema de Administração completo
- [x] Importação em massa de dados
- [ ] App Mobile (React Native)
- [ ] Áudio real das palavras
- [ ] Exercícios de escrita
- [ ] Sistema de níveis
- [ ] Ranking entre usuários
- [ ] Temas personalizados

## 📄 Licença

MIT - Livre para uso pessoal e comercial.
