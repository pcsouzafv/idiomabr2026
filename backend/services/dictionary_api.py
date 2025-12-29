"""
Serviço de integração com APIs de dicionário para enriquecimento automático.

APIs Suportadas:
1. Free Dictionary API - Gratuita, sem limite
2. WordsAPI (RapidAPI) - 2500 req/dia grátis
3. Datamuse API - Sinônimos e associações
"""

import requests
import json
from typing import Dict, List, Optional
from time import sleep


class DictionaryAPI:
    """Classe principal para buscar dados de dicionários online."""

    def __init__(self):
        self.free_dict_url = "https://api.dictionaryapi.dev/api/v2/entries/en/"
        self.datamuse_url = "https://api.datamuse.com/words"
        self.cache = {}

    def get_word_data(self, word: str) -> Optional[Dict]:
        """
        Busca dados completos de uma palavra usando Free Dictionary API.

        Retorna:
        - word_type: tipo gramatical
        - definition_en: definição em inglês
        - synonyms: sinônimos
        - antonyms: antônimos
        - example_sentences: exemplos
        - ipa: pronúncia IPA
        """
        # Verificar cache
        if word in self.cache:
            return self.cache[word]

        try:
            response = requests.get(
                f"{self.free_dict_url}{word}",
                timeout=5
            )

            if response.status_code != 200:
                return None

            data = response.json()[0]  # Primeira entrada
            result = self._parse_free_dict_response(data)

            # Salvar em cache
            self.cache[word] = result
            return result

        except Exception as e:
            print(f"⚠️  Erro ao buscar '{word}': {e}")
            return None

    def _parse_free_dict_response(self, data: Dict) -> Dict:
        """Parser para Free Dictionary API."""
        result = {
            "word_type": None,
            "definition_en": None,
            "synonyms": None,
            "antonyms": None,
            "example_sentences": [],
            "ipa": None
        }

        # IPA (pronúncia)
        if "phonetics" in data and len(data["phonetics"]) > 0:
            for phonetic in data["phonetics"]:
                if "text" in phonetic and phonetic["text"]:
                    result["ipa"] = phonetic["text"].strip("/")
                    break

        # Significados
        if "meanings" in data:
            all_synonyms = set()
            all_antonyms = set()
            examples = []

            for meaning in data["meanings"]:
                # Tipo da palavra (primeiro encontrado)
                if not result["word_type"] and "partOfSpeech" in meaning:
                    result["word_type"] = self._normalize_word_type(
                        meaning["partOfSpeech"]
                    )

                # Definições e exemplos
                if "definitions" in meaning:
                    for i, definition in enumerate(meaning["definitions"][:3]):
                        # Primeira definição como principal
                        if not result["definition_en"] and "definition" in definition:
                            result["definition_en"] = definition["definition"]

                        # Exemplos
                        if "example" in definition:
                            examples.append({
                                "en": definition["example"],
                                "pt": ""  # Será traduzido depois
                            })

                        # Sinônimos e antônimos
                        if "synonyms" in definition:
                            all_synonyms.update(definition["synonyms"][:5])
                        if "antonyms" in definition:
                            all_antonyms.update(definition["antonyms"][:5])

            # Consolidar sinônimos e antônimos
            if all_synonyms:
                result["synonyms"] = ", ".join(list(all_synonyms)[:5])
            if all_antonyms:
                result["antonyms"] = ", ".join(list(all_antonyms)[:5])

            # Consolidar exemplos
            if examples:
                result["example_sentences"] = examples[:3]

        return result

    def _normalize_word_type(self, pos: str) -> str:
        """Normaliza o tipo de palavra."""
        pos_map = {
            "noun": "noun",
            "verb": "verb",
            "adjective": "adjective",
            "adverb": "adverb",
            "pronoun": "pronoun",
            "preposition": "preposition",
            "conjunction": "conjunction",
            "interjection": "interjection",
        }
        return pos_map.get(pos.lower(), pos.lower())

    def get_synonyms_datamuse(self, word: str) -> List[str]:
        """
        Busca sinônimos usando Datamuse API.
        Útil como fallback ou complemento.
        """
        try:
            response = requests.get(
                self.datamuse_url,
                params={"rel_syn": word, "max": 10},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                return [item["word"] for item in data[:5]]

        except Exception as e:
            print(f"⚠️  Erro Datamuse para '{word}': {e}")

        return []

    def get_collocations_datamuse(self, word: str) -> List[str]:
        """
        Busca colocações comuns usando Datamuse API.
        """
        try:
            response = requests.get(
                self.datamuse_url,
                params={"lc": word, "max": 10},
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                return [item["word"] for item in data[:6]]

        except Exception as e:
            print(f"⚠️  Erro collocations para '{word}': {e}")

        return []


# Tradutor simples usando dicionário local
class SimpleTranslator:
    """Tradutor básico para exemplos."""

    def __init__(self):
        # Palavras comuns já traduzidas
        self.translations = {
            "I": "Eu",
            "you": "você",
            "he": "ele",
            "she": "ela",
            "it": "isso",
            "we": "nós",
            "they": "eles/elas",
            "am": "sou/estou",
            "is": "é/está",
            "are": "são/estão",
            "was": "era/estava",
            "were": "eram/estavam",
            "have": "tenho/temos",
            "has": "tem",
            "had": "tinha/tínhamos",
            "a": "um/uma",
            "the": "o/a",
            "and": "e",
            "but": "mas",
            "or": "ou",
            "not": "não",
            "today": "hoje",
            "yesterday": "ontem",
            "tomorrow": "amanhã",
        }

    def translate_simple(self, text: str) -> str:
        """Tradução palavra por palavra (limitada)."""
        words = text.split()
        translated = []

        for word in words:
            clean_word = word.strip(".,!?").lower()
            if clean_word in self.translations:
                translated.append(self.translations[clean_word])
            else:
                translated.append(f"[{word}]")

        return " ".join(translated)


# Função principal de uso
def enrich_word_from_api(word: str) -> Optional[Dict]:
    """
    Enriquece uma palavra usando APIs externas.

    Uso:
    >>> data = enrich_word_from_api("happy")
    >>> print(data["definition_en"])
    >>> print(data["synonyms"])
    """
    api = DictionaryAPI()

    # Buscar dados principais
    word_data = api.get_word_data(word)

    if not word_data:
        return None

    # Complementar com sinônimos (se necessário)
    if not word_data.get("synonyms"):
        synonyms = api.get_synonyms_datamuse(word)
        if synonyms:
            word_data["synonyms"] = ", ".join(synonyms)

    # Buscar colocações
    collocations = api.get_collocations_datamuse(word)
    if collocations:
        word_data["collocations"] = collocations

    return word_data


# Teste
if __name__ == "__main__":
    # Teste com algumas palavras
    test_words = ["happy", "learn", "time", "good", "run"]

    print("🧪 Testando APIs de Dicionário...\n")

    for word in test_words:
        print(f"📖 Palavra: {word}")
        data = enrich_word_from_api(word)

        if data:
            print(f"   Tipo: {data.get('word_type', 'N/A')}")
            print(f"   IPA: {data.get('ipa', 'N/A')}")
            print(f"   Definição: {data.get('definition_en', 'N/A')[:60]}...")
            print(f"   Sinônimos: {data.get('synonyms', 'N/A')}")
            print(f"   Exemplos: {len(data.get('example_sentences', []))}")
            print(f"   Colocações: {len(data.get('collocations', []))}")
        else:
            print(f"   ❌ Não encontrado")

        print()
        sleep(0.5)  # Rate limiting
