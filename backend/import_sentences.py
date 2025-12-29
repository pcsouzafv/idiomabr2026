"""
Script para popular o banco de dados com frases de exemplo
"""
import sys
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, '.')

from app.models.sentence import Sentence
from app.core.config import get_settings

# Frases de exemplo organizadas por nível
SAMPLE_SENTENCES = [
    # A1 - Iniciante
    {
        "english": "Hello, my name is John.",
        "portuguese": "Olá, meu nome é John.",
        "level": "A1",
        "category": "greetings",
        "difficulty_score": 1.0,
        "grammar_points": json.dumps(["present simple", "verb to be"]),
        "vocabulary_used": json.dumps(["hello", "name"])
    },
    {
        "english": "I am 25 years old.",
        "portuguese": "Eu tenho 25 anos.",
        "level": "A1",
        "category": "personal_info",
        "difficulty_score": 1.5,
        "grammar_points": json.dumps(["verb to be", "numbers"]),
        "vocabulary_used": json.dumps(["age", "years"])
    },
    {
        "english": "She lives in São Paulo.",
        "portuguese": "Ela mora em São Paulo.",
        "level": "A1",
        "category": "daily_life",
        "difficulty_score": 2.0,
        "grammar_points": json.dumps(["present simple", "third person -s"]),
        "vocabulary_used": json.dumps(["live", "city"])
    },

    # A2 - Básico
    {
        "english": "I usually wake up at 7 o'clock in the morning.",
        "portuguese": "Eu normalmente acordo às 7 horas da manhã.",
        "level": "A2",
        "category": "daily_routine",
        "difficulty_score": 3.0,
        "grammar_points": json.dumps(["present simple", "frequency adverbs", "time expressions"]),
        "vocabulary_used": json.dumps(["wake up", "morning", "usually"])
    },
    {
        "english": "We are going to the beach this weekend.",
        "portuguese": "Nós vamos à praia este fim de semana.",
        "level": "A2",
        "category": "plans",
        "difficulty_score": 3.5,
        "grammar_points": json.dumps(["present continuous for future", "prepositions of place"]),
        "vocabulary_used": json.dumps(["beach", "weekend", "going"])
    },

    # B1 - Intermediário
    {
        "english": "If I had more time, I would learn to play the guitar.",
        "portuguese": "Se eu tivesse mais tempo, eu aprenderia a tocar violão.",
        "level": "B1",
        "category": "hypothetical",
        "difficulty_score": 5.0,
        "grammar_points": json.dumps(["second conditional", "past simple in if-clause", "would + infinitive"]),
        "vocabulary_used": json.dumps(["time", "learn", "guitar"])
    },
    {
        "english": "I have been studying English for three years.",
        "portuguese": "Eu estudo inglês há três anos.",
        "level": "B1",
        "category": "experience",
        "difficulty_score": 5.5,
        "grammar_points": json.dumps(["present perfect continuous", "duration with for"]),
        "vocabulary_used": json.dumps(["study", "years"])
    },
    {
        "english": "She told me that she was feeling tired yesterday.",
        "portuguese": "Ela me disse que estava se sentindo cansada ontem.",
        "level": "B1",
        "category": "reported_speech",
        "difficulty_score": 6.0,
        "grammar_points": json.dumps(["reported speech", "past continuous", "backshifting"]),
        "vocabulary_used": json.dumps(["told", "feeling", "tired"])
    },

    # B2 - Intermediário-Avançado
    {
        "english": "Despite having studied hard, he didn't pass the exam.",
        "portuguese": "Apesar de ter estudado muito, ele não passou no exame.",
        "level": "B2",
        "category": "contrast",
        "difficulty_score": 7.0,
        "grammar_points": json.dumps(["despite + gerund", "perfect aspect", "negative past simple"]),
        "vocabulary_used": json.dumps(["despite", "studied", "pass", "exam"])
    },
    {
        "english": "By the time we arrive, they will have already left.",
        "portuguese": "Quando chegarmos, eles já terão partido.",
        "level": "B2",
        "category": "time_sequences",
        "difficulty_score": 7.5,
        "grammar_points": json.dumps(["future perfect", "time clauses with 'by the time'"]),
        "vocabulary_used": json.dumps(["arrive", "already", "left"])
    },

    # C1 - Avançado
    {
        "english": "Had I known about the traffic, I would have taken a different route.",
        "portuguese": "Se eu soubesse sobre o trânsito, eu teria pegado uma rota diferente.",
        "level": "C1",
        "category": "regret",
        "difficulty_score": 8.5,
        "grammar_points": json.dumps(["third conditional", "inversion in conditionals", "past perfect"]),
        "vocabulary_used": json.dumps(["traffic", "route", "taken"])
    },
    {
        "english": "Not only did she finish the project on time, but she also exceeded expectations.",
        "portuguese": "Ela não apenas terminou o projeto no prazo, mas também superou as expectativas.",
        "level": "C1",
        "category": "emphasis",
        "difficulty_score": 9.0,
        "grammar_points": json.dumps(["inversion after negative adverbials", "not only...but also"]),
        "vocabulary_used": json.dumps(["finish", "project", "exceed", "expectations"])
    },

    # C2 - Proficiente
    {
        "english": "Notwithstanding the numerous obstacles, the team managed to deliver exceptional results.",
        "portuguese": "Apesar dos inúmeros obstáculos, a equipe conseguiu entregar resultados excepcionais.",
        "level": "C2",
        "category": "formal",
        "difficulty_score": 9.5,
        "grammar_points": json.dumps(["formal connectors", "complex sentence structure"]),
        "vocabulary_used": json.dumps(["notwithstanding", "obstacles", "exceptional"])
    },
]


def populate_sentences():
    """Popula o banco de dados com frases de exemplo"""

    settings = get_settings()
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Verificar se já existem frases
        existing = db.query(Sentence).count()
        if existing > 0:
            print(f"⚠️  Já existem {existing} frases no banco.")
            response = input("Deseja adicionar mais frases? (s/n): ")
            if response.lower() != 's':
                print("Operação cancelada.")
                return

        # Inserir frases
        count = 0
        for sentence_data in SAMPLE_SENTENCES:
            sentence = Sentence(**sentence_data)
            db.add(sentence)
            count += 1

        db.commit()
        print(f"✅ {count} frases adicionadas com sucesso!")

        # Mostrar estatísticas
        for level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
            count = db.query(Sentence).filter(Sentence.level == level).count()
            print(f"   {level}: {count} frases")

    except Exception as e:
        print(f"❌ Erro ao popular banco: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("🔄 Populando banco de dados com frases de exemplo...")
    populate_sentences()
