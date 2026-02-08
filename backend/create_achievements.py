"""
Script para criar conquistas iniciais no banco de dados.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.models.gamification import Achievement

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Lista de conquistas
ACHIEVEMENTS = [
    # Palavras aprendidas
    {"name": "Primeiro Passo", "description": "Aprenda sua primeira palavra", "icon": "🌱", "type": "words", "requirement": 1, "xp_reward": 10},
    {"name": "Vocabulário Básico", "description": "Aprenda 50 palavras", "icon": "📚", "type": "words", "requirement": 50, "xp_reward": 50},
    {"name": "Estudante Dedicado", "description": "Aprenda 100 palavras", "icon": "📖", "type": "words", "requirement": 100, "xp_reward": 100},
    {"name": "Poliglota Iniciante", "description": "Aprenda 250 palavras", "icon": "🎓", "type": "words", "requirement": 250, "xp_reward": 200},
    {"name": "Mestre do Vocabulário", "description": "Aprenda 500 palavras", "icon": "👑", "type": "words", "requirement": 500, "xp_reward": 500},
    {"name": "Enciclopédia Viva", "description": "Aprenda 1000 palavras", "icon": "🏆", "type": "words", "requirement": 1000, "xp_reward": 1000},
    {"name": "Lenda do Idioma", "description": "Aprenda 2500 palavras", "icon": "⭐", "type": "words", "requirement": 2500, "xp_reward": 2500},
    
    # Streaks
    {"name": "Constância", "description": "Mantenha 3 dias de estudo seguidos", "icon": "🔥", "type": "streak", "requirement": 3, "xp_reward": 30},
    {"name": "Uma Semana Forte", "description": "Mantenha 7 dias de estudo seguidos", "icon": "💪", "type": "streak", "requirement": 7, "xp_reward": 70},
    {"name": "Duas Semanas", "description": "Mantenha 14 dias de estudo seguidos", "icon": "⚡", "type": "streak", "requirement": 14, "xp_reward": 150},
    {"name": "Um Mês Inabalável", "description": "Mantenha 30 dias de estudo seguidos", "icon": "🌟", "type": "streak", "requirement": 30, "xp_reward": 300},
    {"name": "Dedicação Total", "description": "Mantenha 100 dias de estudo seguidos", "icon": "💎", "type": "streak", "requirement": 100, "xp_reward": 1000},
    
    # Jogos
    {"name": "Jogador Casual", "description": "Jogue 5 jogos", "icon": "🎮", "type": "games", "requirement": 5, "xp_reward": 25},
    {"name": "Gamer", "description": "Jogue 25 jogos", "icon": "🕹️", "type": "games", "requirement": 25, "xp_reward": 100},
    {"name": "Pro Player", "description": "Jogue 100 jogos", "icon": "🏅", "type": "games", "requirement": 100, "xp_reward": 300},
    {"name": "Lenda dos Jogos", "description": "Jogue 500 jogos", "icon": "🎖️", "type": "games", "requirement": 500, "xp_reward": 1000},
    
    # Níveis
    {"name": "Nível 5", "description": "Alcance o nível 5", "icon": "📈", "type": "level", "requirement": 5, "xp_reward": 50},
    {"name": "Nível 10", "description": "Alcance o nível 10", "icon": "📊", "type": "level", "requirement": 10, "xp_reward": 100},
    {"name": "Nível 25", "description": "Alcance o nível 25", "icon": "🚀", "type": "level", "requirement": 25, "xp_reward": 250},
    {"name": "Nível 50", "description": "Alcance o nível 50", "icon": "🌠", "type": "level", "requirement": 50, "xp_reward": 500},
    {"name": "Nível 100", "description": "Alcance o nível 100", "icon": "👼", "type": "level", "requirement": 100, "xp_reward": 1000},
]


def create_achievements():
    """Cria conquistas no banco de dados."""
    db = SessionLocal()
    
    try:
        # Verificar se já existem conquistas
        existing = db.query(Achievement).count()
        if existing > 0:
            print(f"Já existem {existing} conquistas. Pulando criação.")
            return
        
        for ach_data in ACHIEVEMENTS:
            achievement = Achievement(**ach_data)
            db.add(achievement)
        
        db.commit()
        print(f"✅ Criadas {len(ACHIEVEMENTS)} conquistas!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_achievements()
