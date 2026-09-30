"""A small phonetic key for FRENCH names: two names that sound alike get the same key.

Soundex or Metaphone are designed for English ("Mauger" and "Mojé" do not match).
These rules follow French pronunciation: "au"/"eau" -> o, "ge" -> je, final "er"/"é"
-> e, silent final consonants, nasal sounds (an/en, in/ain, on)...
"""

import re
import unicodedata

# (pattern, replacement), applied in this order to one lowercase word without accents.
# Capital letters are internal markers for nasal sounds: A = an/en, I = in/ain, O = on.
_RULES: list[tuple[str, str]] = [
    (r"w", "v"),
    (r"ph", "f"),
    (r"sch|sh", "ch"),
    (r"ch", "x"),
    (r"qu|q", "k"),
    (r"ck", "k"),
    (r"c(?=[eiy])", "s"),
    (r"c", "k"),
    (r"gu(?=[eiy])", "g"),
    (r"ge(?=[aou])", "j"),
    (r"g(?=[eiy])", "j"),
    (r"gn", "n"),
    (r"tion", "sion"),
    (r"h", ""),
    (r"eau|au", "o"),
    (r"oi", "va"),
    (r"(ain|ein|in|im|yn|ym|un)(?![aeiouy])", "I"),
    (r"(an|am|en|em)(?![aeiouy])", "A"),
    (r"(on|om)(?![aeiouy])", "O"),
    (r"ou", "u"),
    (r"ai|ei", "e"),
    (r"(er|ez|et)$", "e"),
    (r"y", "i"),
    (r"z", "s"),
    (r"([a-zA-Z])\1+", r"\1"),  # double letters sound single
    (r"[tdsxp]+$", ""),  # silent final consonants
    (r"(?<=.)e$", ""),  # silent final e
]


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _word_key(word: str) -> str:
    # The only two rules that need accents, applied before removing them.
    word = re.sub(r"é$", "er", word)  # final "é" sounds like final "er"
    word = _strip_accents(word.replace("ç", "s"))
    for pattern, replacement in _RULES:
        word = re.sub(pattern, replacement, word)
    return word


def phonetic_key(text: str) -> str:
    """'Jacques Mauger' -> 'jak moje'. Words are keyed one by one."""
    words = re.findall(r"[a-zà-öø-ÿ]+", text.lower())
    return " ".join(_word_key(word) for word in words)
