#!/bin/bash
# Script para atualizar e reconstruir as imagens Docker do IdiomasBR

set -euo pipefail

echo "🐳 ATUALIZAÇÃO DAS IMAGENS DOCKER - IdiomasBR"
echo "=============================================="
echo ""

# Seleciona o comando do Compose (prefere v2: "docker compose" / fallback v1: "docker-compose")
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD=(docker-compose)
else
    echo "❌ ERRO: Não foi encontrado 'docker compose' nem 'docker-compose'."
    echo "   Instale/atualize o Docker e tente novamente."
    exit 1
fi

# Verifica se Docker está rodando
if ! docker info > /dev/null 2>&1; then
    echo "❌ ERRO: Docker não está rodando!"
    echo "   Inicie o Docker Desktop e tente novamente."
    exit 1
fi

echo "✅ Docker está rodando"
echo ""

# Menu de opções
echo "Escolha uma opção:"
echo "1. Atualizar TUDO (Backend + Frontend + DB)"
echo "2. Atualizar apenas Backend"
echo "3. Atualizar apenas Frontend"
echo "4. Reconstruir sem cache (completo)"
echo "5. Ver logs dos containers"
echo ""
read -p "Digite o número da opção: " opcao

case $opcao in
    1)
        echo ""
        echo "🔄 Atualizando todos os serviços..."
        echo "=================================="
        
        # Para os containers
        echo "⏹️  Parando containers..."
        "${COMPOSE_CMD[@]}" down

        echo "⬇️  Baixando imagens (services com image: ...)..."
        "${COMPOSE_CMD[@]}" pull
        
        # Reconstrói as imagens
        echo "🔨 Reconstruindo imagens..."
        "${COMPOSE_CMD[@]}" build --pull
        
        # Inicia os serviços
        echo "🚀 Iniciando serviços..."
        "${COMPOSE_CMD[@]}" up -d
        
        echo ""
        echo "✅ Todos os serviços foram atualizados!"
        ;;
        
    2)
        echo ""
        echo "🔄 Atualizando Backend..."
        echo "========================"
        
        # Para apenas o backend
        echo "⏹️  Parando backend..."
        "${COMPOSE_CMD[@]}" stop backend
        
        # Reconstrói o backend
        echo "🔨 Reconstruindo backend..."
        "${COMPOSE_CMD[@]}" build --pull backend
        
        # Inicia o backend
        echo "🚀 Iniciando backend..."
        "${COMPOSE_CMD[@]}" up -d backend
        
        echo ""
        echo "✅ Backend atualizado!"
        ;;
        
    3)
        echo ""
        echo "🔄 Atualizando Frontend..."
        echo "========================="
        
        # Para apenas o frontend
        echo "⏹️  Parando frontend..."
        "${COMPOSE_CMD[@]}" stop frontend
        
        # Reconstrói o frontend
        echo "🔨 Reconstruindo frontend..."
        "${COMPOSE_CMD[@]}" build --pull frontend
        
        # Inicia o frontend
        echo "🚀 Iniciando frontend..."
        "${COMPOSE_CMD[@]}" up -d frontend
        
        echo ""
        echo "✅ Frontend atualizado!"
        ;;
        
    4)
        echo ""
        echo "🔄 Reconstrução completa (sem cache)..."
        echo "======================================="
        
        # Para tudo
        echo "⏹️  Parando containers..."
        "${COMPOSE_CMD[@]}" down
        
        # Remove imagens antigas
        echo "🗑️  Removendo containers antigos..."
        "${COMPOSE_CMD[@]}" rm -f

        echo "⬇️  Baixando imagens (services com image: ...)..."
        "${COMPOSE_CMD[@]}" pull
        
        # Reconstrói sem cache
        echo "🔨 Reconstruindo tudo sem cache..."
        "${COMPOSE_CMD[@]}" build --no-cache --pull
        
        # Inicia os serviços
        echo "🚀 Iniciando serviços..."
        "${COMPOSE_CMD[@]}" up -d
        
        echo ""
        echo "✅ Reconstrução completa finalizada!"
        ;;
        
    5)
        echo ""
        echo "📋 Logs dos containers"
        echo "====================="
        echo ""
        echo "Pressione Ctrl+C para sair"
        echo ""
        "${COMPOSE_CMD[@]}" logs -f
        ;;
        
    *)
        echo ""
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac

echo ""
echo "📊 Status dos containers:"
echo "========================"
"${COMPOSE_CMD[@]}" ps

echo ""
echo "🌐 URLs:"
echo "Frontend: http://localhost:3000"
echo "Backend:  http://localhost:8000"
echo "Docs API: http://localhost:8000/docs"
echo ""
echo "✅ Atualização concluída!"
echo ""
echo "💡 Dica: Para ver os logs em tempo real, execute:"
if [ "${COMPOSE_CMD[*]}" = "docker compose" ]; then
    echo "   docker compose logs -f"
else
    echo "   docker-compose logs -f"
fi
