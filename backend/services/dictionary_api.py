"""Serviço de integração com APIs de dicionário para enriquecimento automático.

Foco
- Enriquecer palavras (headwords em inglês) com definição, classe gramatical,
  IPA, sinônimos/antônimos e exemplos.

APIs
- Free Dictionary API: https://api.dictionaryapi.dev
- Datamuse: https://api.datamuse.com

Robustez
- Reutiliza conexão via requests.Session
- Cache em memória por execução (evita reconsulta repetida)
- Retentativas com backoff em 429/5xx (reduz falhas por rate limit)
"""

from __future__ import annotations

import json
import random
import time
from typing import Dict, List, Optional

import requests


class DictionaryAPI:
    """Classe principal para buscar dados de dicionários online."""

    def __init__(
        self,
        *,
        timeout_s: float = 6.0,
        max_retries: int = 4,
        backoff_base_s: float = 0.6,
        backoff_max_s: float = 8.0,
    ):
        self.free_dict_url = "https://api.dictionaryapi.dev/api/v2/entries/en/"
        self.datamuse_url = "https://api.datamuse.com/words"
        self.cache: dict[str, dict] = {}

        self._timeout_s = float(timeout_s)
        self._max_retries = int(max_retries)
        self._backoff_base_s = float(backoff_base_s)
        self._backoff_max_s = float(backoff_max_s)

        # Keep-alive + connection pooling
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": "idiomasbr2026/word-enrichment (requests)",
                "Accept": "application/json",
            }
        )

    def _sleep_backoff(self, attempt: int, retry_after_s: Optional[float] = None) -> None:
        if retry_after_s is not None and retry_after_s > 0:
            time.sleep(min(retry_after_s, self._backoff_max_s))
            return

        # Exponential backoff with jitter
        exp = min(self._backoff_max_s, self._backoff_base_s * (2 ** max(0, attempt - 1)))
        jitter = random.uniform(0, min(0.25, exp))
        time.sleep(min(self._backoff_max_s, exp + jitter))

    def _get_json(self, url: str, *, params: Optional[dict] = None) -> Optional[object]:
        """GET com retries/backoff para erros transitórios."""
        last_exc: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                resp = self._session.get(url, params=params, timeout=self._timeout_s)

                if resp.status_code == 200:
                    return resp.json()

                # Not found: não adianta retry
                if resp.status_code == 404:
                    return None

                # Rate limit / transient server failures
                if resp.status_code in (429, 500, 502, 503, 504):
                    retry_after_hdr = resp.headers.get("Retry-After")
                    retry_after_s: Optional[float] = None
                    if retry_after_hdr:
                        try:
                            retry_after_s = float(retry_after_hdr)
                        except ValueError:
                            retry_after_s = None

                    if attempt < self._max_retries:
                        self._sleep_backoff(attempt, retry_after_s=retry_after_s)
                        continue
                    return None

                # Outros 4xx: não retry
                return None
            except Exception as e:
                last_exc = e
                if attempt < self._max_retries:
                    self._sleep_backoff(attempt)
                    continue
                break

        if last_exc is not None:
            print(f"⚠️  Erro ao buscar URL: {url} ({last_exc})")
        return None

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
        - audio_url: URL de áudio (pronúncia), quando disponível
        """
        if not word:
            return None

        headword = word.strip().lower()
        if not headword:
            return None

        # Verificar cache
        if headword in self.cache:
            return self.cache[headword]

        payload = self._get_json(f"{self.free_dict_url}{headword}")
        if not payload:
            return None

        try:
            data = payload[0]  # Primeira entrada
        except Exception:
            return None

        result = self._parse_free_dict_response(data)

        # Salvar em cache
        self.cache[headword] = result
        return result

    def _parse_free_dict_response(self, data: Dict) -> Dict:
        """Parser para Free Dictionary API."""
        result = {
            "word_type": None,
            "definition_en": None,
            "synonyms": None,
            "antonyms": None,
            "example_sentences": [],
            "ipa": None,
            "audio_url": None,
        }

        # IPA (pronúncia) + áudio
        if "phonetics" in data and len(data["phonetics"]) > 0:
            for phonetic in data["phonetics"]:
                if "text" in phonetic and phonetic["text"]:
                    result["ipa"] = phonetic["text"].strip("/")
                    break

            for phonetic in data["phonetics"]:
                audio = phonetic.get("audio") if isinstance(phonetic, dict) else None
                if isinstance(audio, str) and audio.strip():
                    result["audio_url"] = audio.strip()
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
        headword = (word or "").strip().lower()
        if not headword:
            return []

        payload = self._get_json(self.datamuse_url, params={"rel_syn": headword, "max": 10})
        if not payload or not isinstance(payload, list):
            return []

        out: list[str] = []
        for item in payload[:5]:
            w = item.get("word") if isinstance(item, dict) else None
            if isinstance(w, str) and w:
                out.append(w)
        return out

    def get_collocations_datamuse(self, word: str) -> List[str]:
        """
        Busca colocações comuns usando Datamuse API.
        """
        headword = (word or "").strip().lower()
        if not headword:
            return []

        payload = self._get_json(self.datamuse_url, params={"lc": headword, "max": 10})
        if not payload or not isinstance(payload, list):
            return []

        out: list[str] = []
        for item in payload[:6]:
            w = item.get("word") if isinstance(item, dict) else None
            if isinstance(w, str) and w:
                out.append(w)
        return out


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
    # Reusa a mesma instância para aproveitar cache e conexão.
    api = _DEFAULT_API

    # Buscar dados principais (Free Dictionary)
    word_data = api.get_word_data(word)

    # Se não houver no dicionário principal, ainda tentamos extrair algo do Datamuse
    # (sinônimos/colocações). Isso ajuda a reduzir cadastros parcialmente vazios.
    if not word_data:
        synonyms = api.get_synonyms_datamuse(word)
        collocations = api.get_collocations_datamuse(word)

        if not synonyms and not collocations:
            return None

        return {
            "word_type": None,
            "definition_en": None,
            "synonyms": ", ".join(synonyms) if synonyms else None,
            "antonyms": None,
            "example_sentences": [],
            "ipa": None,
            "audio_url": None,
            "collocations": collocations or None,
        }

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


# Instância singleton por processo para cache + pooling de conexões
_DEFAULT_API = DictionaryAPI()


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
