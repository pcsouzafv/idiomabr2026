from __future__ import annotations

from typing import Optional


def sanitize_unmatched_brackets(value: Optional[str]) -> Optional[str]:
    """Remove colchetes órfãos em texto.

    Mantém anotações válidas do tipo "... [nota]" (quando há '[' e ']'), mas
    remove '[' quando não existe ']' e remove ']' quando não existe '['.

    Isso evita exibição de textos malformados como "uaie]" ou "algo [sem fechar".
    """

    if value is None:
        return None

    text = value.strip()
    if not text:
        return text

    has_open = "[" in text
    has_close = "]" in text

    if has_open and not has_close:
        return text.replace("[", "").strip()

    if has_close and not has_open:
        return text.replace("]", "").strip()

    return text
