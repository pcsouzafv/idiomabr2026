"""
Script para analisar a distribuição de palavras por nível via API.
"""
import requests
import sys
import io

# Configurar encoding UTF-8 para saída
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "http://localhost:8000"

def analyze_words_by_level():
    """Analisa e exibe a distribuição de palavras por nível via API."""

    try:
        print("\n" + "="*60)
        print("ANALISE DE PALAVRAS POR NIVEL")
        print("="*60)

        # Buscar níveis disponíveis
        levels_response = requests.get(f"{API_URL}/api/words/levels/list")
        if levels_response.status_code != 200:
            print(f"Erro ao buscar niveis: {levels_response.status_code}")
            return

        levels = sorted(levels_response.json())
        print(f"\nNiveis encontrados: {', '.join(levels)}")

        # Analisar cada nível
        level_stats = {}
        total_words = 0

        for level in levels:
            response = requests.get(
                f"{API_URL}/api/words",
                params={"level": level, "per_page": 1}
            )
            if response.status_code == 200:
                data = response.json()
                count = data.get("total", 0)
                level_stats[level] = count
                total_words += count

        print(f"\nTotal de palavras no banco: {total_words}")

        # Exibir tabela
        print(f"\n{'Nivel':<10} {'Quantidade':<15} {'Porcentagem':<15} {'Barra'}")
        print("-"*60)

        # Ordenar níveis na ordem correta (A1, A2, B1, B2, C1, C2)
        level_order = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
        sorted_levels = [l for l in level_order if l in level_stats]

        for level in sorted_levels:
            count = level_stats[level]
            percentage = (count / total_words * 100) if total_words > 0 else 0
            bar = '#' * int(percentage / 2)  # Escala de 0-50 caracteres
            print(f"{level:<10} {count:<15} {percentage:>6.2f}%        {bar}")

        # Buscar amostras de cada nível
        print(f"\n{'='*60}")
        print("AMOSTRAS DE PALAVRAS POR NIVEL (5 primeiras de cada)")
        print("="*60)

        for level in sorted_levels:
            response = requests.get(
                f"{API_URL}/api/words",
                params={"level": level, "per_page": 5, "page": 1}
            )
            if response.status_code == 200:
                data = response.json()
                words = data.get("words", [])

                print(f"\n[Nivel {level}] - {level_stats[level]} palavras total:")
                for word in words:
                    ipa_str = f"/{word.get('ipa')}/" if word.get('ipa') else ""
                    english = word.get('english', '')
                    portuguese = word.get('portuguese', '')
                    print(f"  - {english:<20} {ipa_str:<15} -> {portuguese}")

        # Estatísticas gerais
        print(f"\n{'='*60}")
        print("RESUMO")
        print("="*60)

        # Buscar algumas palavras para verificar completude dos dados
        response = requests.get(f"{API_URL}/api/words", params={"per_page": 100})
        if response.status_code == 200:
            data = response.json()
            words = data.get("words", [])

            words_with_ipa = sum(1 for w in words if w.get('ipa'))
            words_with_examples = sum(1 for w in words if w.get('example_en'))
            words_with_tags = sum(1 for w in words if w.get('tags'))

            sample_size = len(words)
            print(f"\nAmostra analisada: {sample_size} palavras")
            print(f"Palavras com IPA: {words_with_ipa} ({words_with_ipa/sample_size*100:.1f}%)")
            print(f"Palavras com exemplos: {words_with_examples} ({words_with_examples/sample_size*100:.1f}%)")
            print(f"Palavras com tags: {words_with_tags} ({words_with_tags/sample_size*100:.1f}%)")

        print(f"\n{'='*60}\n")

    except requests.exceptions.ConnectionError:
        print("\nErro: Nao foi possivel conectar a API.")
        print("Certifique-se de que o backend esta rodando em http://localhost:8000")
        sys.exit(1)
    except Exception as e:
        print(f"\nErro ao analisar dados: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    analyze_words_by_level()
