"""
Script para popular conquistas no banco de dados.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.gamification import Achievement, AchievementType

def create_achievements():
    """Cria as conquistas no banco de dados."""
    db = SessionLocal()

    try:
        # Verificar se já existem conquistas
        existing_count = db.query(Achievement).count()
        if existing_count > 0:
            print(f"⚠️  Já existem {existing_count} conquistas no banco de dados.")
            response = input("Deseja recriar todas? (s/n): ")
            if response.lower() != 's':
                print("Operação cancelada.")
                return

            # Deletar todas as conquistas existentes
            db.query(Achievement).delete()
            db.commit()
            print("✅ Conquistas antigas removidas.")

        achievements = [
            # Conquistas de Palavras
            {
                "name": "Primeiro Passo",
                "description": "Aprenda sua primeira palavra",
                "icon": "🎯",
                "type": AchievementType.WORDS,
                "requirement": 1,
                "xp_reward": 10
            },
            {
                "name": "Vocabulário Básico",
                "description": "Aprenda 50 palavras",
                "icon": "📚",
                "type": AchievementType.WORDS,
                "requirement": 50,
                "xp_reward": 50
            },
            {
                "name": "Aprendiz de Palavras",
                "description": "Aprenda 100 palavras",
                "icon": "📖",
                "type": AchievementType.WORDS,
                "requirement": 100,
                "xp_reward": 100
            },
            {
                "name": "Conhecedor de Palavras",
                "description": "Aprenda 250 palavras",
                "icon": "🎓",
                "type": AchievementType.WORDS,
                "requirement": 250,
                "xp_reward": 200
            },
            {
                "name": "Mestre do Vocabulário",
                "description": "Aprenda 500 palavras",
                "icon": "👑",
                "type": AchievementType.WORDS,
                "requirement": 500,
                "xp_reward": 500
            },
            {
                "name": "Poliglota",
                "description": "Aprenda 1000 palavras",
                "icon": "🌟",
                "type": AchievementType.WORDS,
                "requirement": 1000,
                "xp_reward": 1000
            },

            # Conquistas de Streak
            {
                "name": "Dedicação",
                "description": "Estude por 3 dias seguidos",
                "icon": "🔥",
                "type": AchievementType.STREAK,
                "requirement": 3,
                "xp_reward": 30
            },
            {
                "name": "Comprometido",
                "description": "Estude por 7 dias seguidos",
                "icon": "💪",
                "type": AchievementType.STREAK,
                "requirement": 7,
                "xp_reward": 70
            },
            {
                "name": "Persistente",
                "description": "Estude por 14 dias seguidos",
                "icon": "⚡",
                "type": AchievementType.STREAK,
                "requirement": 14,
                "xp_reward": 140
            },
            {
                "name": "Consistente",
                "description": "Estude por 30 dias seguidos",
                "icon": "🎯",
                "type": AchievementType.STREAK,
                "requirement": 30,
                "xp_reward": 300
            },
            {
                "name": "Imparável",
                "description": "Estude por 60 dias seguidos",
                "icon": "🚀",
                "type": AchievementType.STREAK,
                "requirement": 60,
                "xp_reward": 600
            },
            {
                "name": "Lenda do Streak",
                "description": "Estude por 100 dias seguidos",
                "icon": "🏆",
                "type": AchievementType.STREAK,
                "requirement": 100,
                "xp_reward": 1000
            },

            # Conquistas de Jogos
            {
                "name": "Jogador Iniciante",
                "description": "Jogue seu primeiro jogo",
                "icon": "🎮",
                "type": AchievementType.GAMES,
                "requirement": 1,
                "xp_reward": 10
            },
            {
                "name": "Gamer Casual",
                "description": "Jogue 10 jogos",
                "icon": "🕹️",
                "type": AchievementType.GAMES,
                "requirement": 10,
                "xp_reward": 50
            },
            {
                "name": "Gamer Dedicado",
                "description": "Jogue 50 jogos",
                "icon": "🎯",
                "type": AchievementType.GAMES,
                "requirement": 50,
                "xp_reward": 200
            },
            {
                "name": "Mestre dos Jogos",
                "description": "Jogue 100 jogos",
                "icon": "🏅",
                "type": AchievementType.GAMES,
                "requirement": 100,
                "xp_reward": 500
            },

            # Conquistas Perfeitas
            {
                "name": "Perfeição",
                "description": "Consiga uma pontuação perfeita em um quiz",
                "icon": "💯",
                "type": AchievementType.PERFECT,
                "requirement": 1,
                "xp_reward": 100
            },
            {
                "name": "Perfeccionista",
                "description": "Consiga 5 pontuações perfeitas",
                "icon": "⭐",
                "type": AchievementType.PERFECT,
                "requirement": 5,
                "xp_reward": 250
            },
            {
                "name": "Mestre da Perfeição",
                "description": "Consiga 10 pontuações perfeitas",
                "icon": "🌟",
                "type": AchievementType.PERFECT,
                "requirement": 10,
                "xp_reward": 500
            },

            # Conquistas de Velocidade
            {
                "name": "Relâmpago",
                "description": "Complete um jogo de memória em menos de 30 segundos",
                "icon": "⚡",
                "type": AchievementType.SPEED,
                "requirement": 30,
                "xp_reward": 150
            },
            {
                "name": "Velocista",
                "description": "Complete um jogo de memória em menos de 20 segundos",
                "icon": "🏃",
                "type": AchievementType.SPEED,
                "requirement": 20,
                "xp_reward": 250
            },

            # Conquistas de Nível
            {
                "name": "Iniciante",
                "description": "Alcance o nível 5",
                "icon": "🌱",
                "type": AchievementType.LEVEL,
                "requirement": 5,
                "xp_reward": 50
            },
            {
                "name": "Intermediário",
                "description": "Alcance o nível 10",
                "icon": "🌿",
                "type": AchievementType.LEVEL,
                "requirement": 10,
                "xp_reward": 100
            },
            {
                "name": "Avançado",
                "description": "Alcance o nível 20",
                "icon": "🌳",
                "type": AchievementType.LEVEL,
                "requirement": 20,
                "xp_reward": 300
            },
            {
                "name": "Expert",
                "description": "Alcance o nível 30",
                "icon": "🦅",
                "type": AchievementType.LEVEL,
                "requirement": 30,
                "xp_reward": 500
            },
            {
                "name": "Lendário",
                "description": "Alcance o nível 50",
                "icon": "👑",
                "type": AchievementType.LEVEL,
                "requirement": 50,
                "xp_reward": 1000
            },
        ]

        for achievement_data in achievements:
            achievement = Achievement(**achievement_data)
            db.add(achievement)

        db.commit()
        print(f"✅ {len(achievements)} conquistas criadas com sucesso!")

        # Exibir resumo
        print("\n📊 Resumo das conquistas:")
        for type in AchievementType:
            count = sum(1 for a in achievements if a["type"] == type)
            print(f"  {type.value}: {count} conquistas")

    except Exception as e:
        print(f"❌ Erro ao criar conquistas: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🎯 Criando conquistas...\n")
    create_achievements()
