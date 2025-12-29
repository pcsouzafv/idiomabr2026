# 📚 IdiomasBR - Documentação Técnica Completa

> **Última atualização:** 11 de Dezembro de 2025  
> **Status:** ✅ Funcional em Docker

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Estrutura de Pastas](#estrutura-de-pastas)
4. [Backend (FastAPI)](#backend-fastapi)
5. [Frontend (Next.js)](#frontend-nextjs)
6. [Banco de Dados](#banco-de-dados)
7. [Docker](#docker)
8. [API Endpoints](#api-endpoints)
9. [Algoritmo de Repetição Espaçada](#algoritmo-de-repetição-espaçada)
10. [Comandos Úteis](#comandos-úteis)

---

## 🎯 Visão Geral

**IdiomasBR** é uma plataforma de aprendizado de inglês com:

- ✅ **Flashcards interativos** com animação de flip
- ✅ **Repetição espaçada (Spaced Repetition)** - Algoritmo SM-2
- ✅ **5.000+ palavras** com transcrição fonética (IPA)
- ✅ **Text-to-Speech** para pronúncia
- ✅ **Sistema de streaks** e metas diárias
- ✅ **Autenticação JWT** completa
- ✅ **Containerização Docker** pronta para deploy

---

## 🏗️ Arquitetura

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Frontend      │────▶│   Backend       │────▶│   PostgreSQL    │
│   Next.js 14    │     │   FastAPI       │     │   Database      │
│   Port: 3000    │     │   Port: 8000    │     │   Port: 5433    │
│                 │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## 📁 Estrutura de Pastas

```
idiomasbr2026/
├── backend/                    # API FastAPI
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py       # Configurações (Pydantic Settings)
│   │   │   ├── database.py     # Conexão SQLAlchemy
│   │   │   └── security.py     # JWT + Bcrypt
│   │   ├── models/
│   │   │   ├── user.py         # Modelo User
│   │   │   ├── word.py         # Modelo Word
│   │   │   ├── review.py       # Modelo Review
│   │   │   └── progress.py     # Modelo UserProgress
│   │   ├── routes/
│   │   │   ├── auth.py         # Endpoints de autenticação
│   │   │   ├── words.py        # Endpoints de palavras
│   │   │   └── study.py        # Endpoints de estudo
│   │   ├── schemas/            # Schemas Pydantic
│   │   └── main.py             # App principal
│   ├── import_words.py         # Script de importação
│   ├── requirements.txt        # Dependências Python
│   ├── Dockerfile              # Docker produção
│   ├── Dockerfile.dev          # Docker desenvolvimento
│   └── .dockerignore
│
├── frontend/                   # App Next.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx        # Landing page
│   │   │   ├── login/page.tsx  # Página de login
│   │   │   ├── register/page.tsx # Página de registro
│   │   │   ├── dashboard/page.tsx # Dashboard principal
│   │   │   ├── study/page.tsx  # Flashcards de estudo
│   │   │   ├── words/page.tsx  # Explorador de vocabulário
│   │   │   ├── layout.tsx      # Layout raiz
│   │   │   └── globals.css     # Estilos globais
│   │   ├── lib/
│   │   │   └── api.ts          # Cliente Axios
│   │   └── store/
│   │       └── authStore.ts    # Estado Zustand
│   ├── package.json
│   ├── tailwind.config.js
│   ├── next.config.js
│   ├── Dockerfile              # Docker produção
│   ├── Dockerfile.dev          # Docker desenvolvimento
│   └── .dockerignore
│
├── docker-compose.yml          # Produção
├── docker-compose.dev.yml      # Desenvolvimento
├── .env.docker                 # Variáveis de ambiente
├── docker-start.bat            # Script Windows - iniciar
├── docker-dev.bat              # Script Windows - dev
├── docker-stop.bat             # Script Windows - parar
├── docker-import-words.bat     # Script Windows - importar palavras
└── README.md
```

---

## ⚙️ Backend (FastAPI)

### Tecnologias
| Tecnologia | Versão | Uso |
|------------|--------|-----|
| Python | 3.11 | Runtime |
| FastAPI | 0.104.1 | Framework API |
| SQLAlchemy | 2.0.23 | ORM |
| Pydantic | 2.5.2 | Validação |
| python-jose | 3.3.0 | JWT |
| passlib | 1.7.4 | Hashing |
| bcrypt | 4.0.1 | Password hashing |
| psycopg2-binary | 2.9.9 | PostgreSQL driver |
| uvicorn | 0.24.0 | ASGI Server |

### Arquivo: `backend/app/core/config.py`
```python
# Configurações usando Pydantic Settings
class Settings(BaseSettings):
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 dias
```

### Arquivo: `backend/app/core/security.py`
```python
# Funções de segurança
- verify_password(plain, hashed) -> bool
- get_password_hash(password) -> str
- create_access_token(data, expires) -> str
- get_current_user(token, db) -> User
```

### Arquivo: `backend/app/main.py`
```python
# App principal com CORS configurado
origins = [
    "http://localhost:3000",
    "http://frontend:3000",
    "http://127.0.0.1:3000",
]
```

---

## 🎨 Frontend (Next.js)

### Tecnologias
| Tecnologia | Versão | Uso |
|------------|--------|-----|
| Next.js | 14.0.4 | Framework React |
| React | 18 | UI Library |
| TypeScript | 5 | Tipagem |
| Tailwind CSS | 3.3 | Estilos |
| Zustand | 4.4.7 | State Management |
| Framer Motion | 10.17 | Animações |
| Axios | 1.6.2 | HTTP Client |
| Lucide React | 0.303.0 | Ícones |
| react-hot-toast | 2.4.1 | Notificações |

### Páginas Implementadas

| Rota | Arquivo | Descrição |
|------|---------|-----------|
| `/` | `page.tsx` | Landing page com hero e features |
| `/login` | `login/page.tsx` | Formulário de login |
| `/register` | `register/page.tsx` | Formulário de registro |
| `/dashboard` | `dashboard/page.tsx` | Dashboard com stats e progresso |
| `/study` | `study/page.tsx` | Flashcards com flip animation |
| `/words` | `words/page.tsx` | Explorador de vocabulário |

### Arquivo: `frontend/src/lib/api.ts`
```typescript
// Cliente Axios com interceptors
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL
});

// Interceptor adiciona token automaticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// APIs exportadas
export const authApi = { login, register, getMe }
export const wordsApi = { getWords, getWord }
export const studyApi = { getSession, submitReview, getStats }
```

### Arquivo: `frontend/src/store/authStore.ts`
```typescript
// Estado global com Zustand
interface AuthState {
  user: User | null;
  token: string | null;
  stats: Stats | null;
  isLoading: boolean;
  login: (email, password) => Promise<void>;
  register: (name, email, password) => Promise<void>;
  logout: () => void;
  fetchUser: () => Promise<void>;
  fetchStats: () => Promise<void>;
}
```

---

## 🗄️ Banco de Dados

### Modelos SQLAlchemy

#### User (`backend/app/models/user.py`)
```python
class User(Base):
    id: int (PK)
    email: str (unique)
    name: str
    hashed_password: str
    is_active: bool = True
    created_at: datetime
    daily_goal: int = 20
    current_streak: int = 0
    longest_streak: int = 0
    last_study_date: date | None
```

#### Word (`backend/app/models/word.py`)
```python
class Word(Base):
    id: int (PK)
    english: str (unique)
    ipa: str              # Transcrição fonética
    portuguese: str
    level: str            # A1, A2, B1, B2, C1, C2
    tags: str | None      # JSON array
    example_sentence: str | None
    created_at: datetime
```

#### Review (`backend/app/models/review.py`)
```python
class Review(Base):
    id: int (PK)
    user_id: int (FK -> users)
    word_id: int (FK -> words)
    quality: int          # 1-5 (dificuldade)
    reviewed_at: datetime
```

#### UserProgress (`backend/app/models/progress.py`)
```python
class UserProgress(Base):
    id: int (PK)
    user_id: int (FK -> users)
    word_id: int (FK -> words)
    ease_factor: float = 2.5
    interval: int = 0     # dias
    repetitions: int = 0
    next_review: datetime
    last_review: datetime | None
```

### Diagrama ER

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│    users     │       │   reviews    │       │    words     │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ id (PK)      │──┐    │ id (PK)      │    ┌──│ id (PK)      │
│ email        │  │    │ user_id (FK) │────┘  │ english      │
│ name         │  └───▶│ word_id (FK) │───────│ ipa          │
│ password     │       │ quality      │       │ portuguese   │
│ daily_goal   │       │ reviewed_at  │       │ level        │
│ streak       │       └──────────────┘       │ tags         │
└──────────────┘                              └──────────────┘
        │
        │              ┌──────────────┐
        │              │user_progress │
        │              ├──────────────┤
        └─────────────▶│ id (PK)      │
                       │ user_id (FK) │
                       │ word_id (FK) │───────▶ words
                       │ ease_factor  │
                       │ interval     │
                       │ next_review  │
                       └──────────────┘
```

---

## 🐳 Docker

### Containers

| Container | Imagem | Porta | Descrição |
|-----------|--------|-------|-----------|
| idiomasbr-postgres | postgres:15-alpine | 5433:5432 | Banco de dados |
| idiomasbr-backend | python:3.11-slim | 8000:8000 | API FastAPI |
| idiomasbr-frontend | node:20-alpine | 3000:3000 | App Next.js |

### Arquivo: `docker-compose.yml`
```yaml
services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: idiomasbr
      POSTGRES_PASSWORD: idiomasbr123
      POSTGRES_DB: idiomasbr
    ports:
      - "5433:5432"  # Porta externa 5433
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U idiomasbr"]

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://idiomasbr:idiomasbr123@postgres:5432/idiomasbr
      SECRET_KEY: sua-chave-secreta
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

### Variáveis de Ambiente (`.env.docker`)
```env
# PostgreSQL
POSTGRES_USER=idiomasbr
POSTGRES_PASSWORD=idiomasbr123
POSTGRES_DB=idiomasbr

# Backend
SECRET_KEY=sua-chave-secreta-muito-segura
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🔌 API Endpoints

### Autenticação (`/api/auth`)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| POST | `/api/auth/register` | Criar conta | ❌ |
| POST | `/api/auth/login` | Login (retorna token) | ❌ |
| GET | `/api/auth/me` | Dados do usuário logado | ✅ |

#### POST /api/auth/register
```json
// Request
{
  "name": "João Silva",
  "email": "joao@email.com",
  "password": "senha123"
}

// Response 201
{
  "id": 1,
  "name": "João Silva",
  "email": "joao@email.com",
  "is_active": true,
  "created_at": "2025-12-11T10:00:00Z"
}
```

#### POST /api/auth/login
```json
// Request (form-data)
username=joao@email.com
password=senha123

// Response 200
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Palavras (`/api/words`)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| GET | `/api/words` | Listar palavras | ✅ |
| GET | `/api/words/{id}` | Detalhes da palavra | ✅ |
| POST | `/api/words/bulk` | Importar em lote | ✅ |

#### GET /api/words
```
Query params:
- search: string (busca em inglês/português)
- level: string (A1, A2, B1, B2, C1, C2)
- skip: int (paginação)
- limit: int (default: 50)
```

### Estudo (`/api/study`)

| Método | Endpoint | Descrição | Auth |
|--------|----------|-----------|------|
| GET | `/api/study/session` | Obter sessão de estudo | ✅ |
| POST | `/api/study/review` | Registrar revisão | ✅ |
| GET | `/api/study/stats` | Estatísticas | ✅ |

#### GET /api/study/session
```json
// Response
{
  "cards": [
    {
      "id": 1,
      "english": "hello",
      "ipa": "/həˈloʊ/",
      "portuguese": "olá",
      "level": "A1",
      "is_review": false
    }
  ],
  "total": 20,
  "new_count": 10,
  "review_count": 10
}
```

#### POST /api/study/review
```json
// Request
{
  "word_id": 1,
  "quality": 3  // 1=hard, 3=medium, 5=easy
}

// Response
{
  "next_review": "2025-12-14T10:00:00Z",
  "interval": 3,
  "ease_factor": 2.6
}
```

#### GET /api/study/stats
```json
// Response
{
  "total_words": 5000,
  "words_learned": 150,
  "words_to_review": 25,
  "current_streak": 7,
  "daily_goal": 20,
  "today_reviewed": 15
}
```

---

## 🧠 Algoritmo de Repetição Espaçada

Baseado no **SM-2 (SuperMemo 2)**, simplificado:

### Intervalos por Dificuldade

| Resposta | Quality | Próxima Revisão |
|----------|---------|-----------------|
| **Difícil** | 1 | 4 horas |
| **Médio** | 3 | 1 dia × ease_factor |
| **Fácil** | 5 | 3 dias × ease_factor |

### Fórmula do Ease Factor
```python
new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
# Mínimo: 1.3
```

### Implementação (`backend/app/routes/study.py`)
```python
def calculate_next_review(quality: int, progress: UserProgress):
    if quality < 3:  # Difícil
        interval = 0.17  # 4 horas
        ease_factor = max(1.3, progress.ease_factor - 0.2)
    elif quality == 3:  # Médio
        interval = max(1, progress.interval * progress.ease_factor)
    else:  # Fácil
        interval = max(3, progress.interval * progress.ease_factor * 1.3)
    
    next_review = datetime.now() + timedelta(days=interval)
    return next_review, interval, ease_factor
```

---

## 💻 Comandos Úteis

### Docker

```powershell
# Iniciar em produção
.\docker-start.bat
# ou
docker-compose up -d

# Iniciar em desenvolvimento (hot-reload)
.\docker-dev.bat
# ou
docker-compose -f docker-compose.dev.yml up

# Parar containers
.\docker-stop.bat
# ou
docker-compose down

# Ver logs
docker-compose logs -f
docker-compose logs backend --tail 50

# Importar palavras
docker-compose exec backend python import_words.py

# Importar de CSV
docker-compose exec backend python import_words.py /app/palavras.csv

# Acessar banco de dados
docker exec -it idiomasbr-postgres psql -U idiomasbr -d idiomasbr
```

### Desenvolvimento Local (sem Docker)

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## 🌐 URLs de Acesso

| Serviço | URL | Descrição |
|---------|-----|-----------|
| Frontend | http://localhost:3000 | Aplicação web |
| Backend API | http://localhost:8000 | API REST |
| API Docs (Swagger) | http://localhost:8000/docs | Documentação interativa |
| API Docs (ReDoc) | http://localhost:8000/redoc | Documentação alternativa |
| PostgreSQL | localhost:5433 | Banco de dados |

---

## ✅ Status dos Recursos

### Funcionando ✅
- [x] Registro de usuário
- [x] Login com JWT
- [x] Dashboard com estatísticas
- [x] Flashcards com flip animation
- [x] Sistema de dificuldade (fácil/médio/difícil)
- [x] Algoritmo de repetição espaçada
- [x] Explorador de vocabulário
- [x] Busca e filtro de palavras
- [x] Importação de palavras (CSV)
- [x] Docker completo (prod + dev)
- [x] Text-to-Speech (browser API)
- [x] Streak tracking

### Pendente 📋
- [ ] Áudio gravado das palavras
- [ ] App Mobile (React Native)
- [ ] Exercícios de escrita
- [ ] Sistema de níveis/XP
- [ ] Ranking entre usuários
- [ ] Temas personalizados (dark mode)
- [ ] PWA (Progressive Web App)
- [ ] Exportação de progresso

---

## 🔧 Troubleshooting

### Erro: "port is already allocated"
```powershell
# Porta 5432 em uso (PostgreSQL local)
# Solução: usar porta 5433 (já configurado)
```

### Erro: "bcrypt/passlib incompatibility"
```powershell
# Solução: usar bcrypt==4.0.1 (já corrigido)
pip install bcrypt==4.0.1
```

### Erro: "CORS blocked"
```python
# Verificar origins em backend/app/main.py
allow_origins=[
    "http://localhost:3000",
    "http://frontend:3000",
]
```

### Erro: "npm ci failed"
```dockerfile
# Usar npm install se não houver package-lock.json
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
```

---

**Desenvolvido com ❤️ para aprender inglês de forma eficiente!**
