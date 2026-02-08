"""
Utilitário para gerar exemplos de frases em contexto
"""
import requests
from typing import Optional, Tuple

FREE_DICT_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

def get_example_from_api(word: str) -> Optional[Tuple[str, str]]:
    """
    Busca exemplo real de frase da API do dicionário
    Returns: (example_en, definition) ou None
    """
    try:
        url = FREE_DICT_API.format(word=word)
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                for entry in data[0].get('meanings', []):
                    for definition in entry.get('definitions', []):
                        example = definition.get('example')
                        if example and len(example) > 10:
                            return (example, definition.get('definition', ''))
        return None
    except Exception:
        return None

def translate_text(text: str) -> Optional[str]:
    """
    Traduz texto usando MyMemory API
    """
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {'q': text, 'langpair': 'en|pt-br'}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        if data.get('responseStatus') == 200:
            translation = data['responseData']['translatedText']
            if translation and translation.lower() != text.lower():
                return translation
        return None
    except Exception:
        return None

def detect_word_type(word: str) -> str:
    """
    Detecta tipo de palavra baseado em padrões morfológicos
    """
    word_lower = word.lower()

    # Verbos
    verb_endings = ['ing', 'ed', 'ate', 'ize', 'ify']
    if any(word_lower.endswith(e) for e in verb_endings):
        return 'verb'

    # Adjetivos
    adj_endings = ['ful', 'less', 'ous', 'ive', 'able', 'ible', 'al', 'ic']
    if any(word_lower.endswith(e) for e in adj_endings):
        return 'adjective'

    # Advérbios
    if word_lower.endswith('ly'):
        return 'adverb'

    # Substantivos
    noun_endings = ['tion', 'ness', 'ment', 'ity', 'er', 'or', 'ism', 'ist']
    if any(word_lower.endswith(e) for e in noun_endings):
        return 'noun'

    return 'noun'  # Padrão

def generate_smart_example(word: str, word_type: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Gera exemplo inteligente baseado no tipo de palavra
    Returns: (example_en, example_pt)
    """
    if not word_type:
        word_type = detect_word_type(word)

    templates = {
        'verb': [
            f"I {word} every day.",
            f"She usually {word}s in the morning.",
            f"They will {word} tomorrow.",
            f"We should {word} more often.",
        ],
        'noun': [
            f"The {word} is very important.",
            f"I saw a beautiful {word} yesterday.",
            f"This {word} is amazing!",
            f"She bought a new {word}.",
        ],
        'adjective': [
            f"She is very {word}.",
            f"The weather is {word} today.",
            f"It looks {word} from here.",
            f"This book is quite {word}.",
        ],
        'adverb': [
            f"He speaks {word}.",
            f"She smiled {word}.",
            f"They work {word}.",
        ],
    }

    template_list = templates.get(word_type, templates['noun'])
    example_en = template_list[0]
    example_pt = translate_text(example_en)

    return (example_en, example_pt)

def generate_example(word: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Gera ou busca exemplo para uma palavra
    Returns: (example_en, example_pt)
    """
    # Tenta buscar exemplo real primeiro
    result = get_example_from_api(word)

    if result:
        example_en, _ = result
        example_pt = translate_text(example_en)
        if example_pt:
            return (example_en, example_pt)

    # Fallback: gera exemplo inteligente
    return generate_smart_example(word)
