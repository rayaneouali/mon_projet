"""Réveil : ouvre l'app comme un vrai visiteur et clique sur le bouton de réveil si elle dort.

Une simple requête HTTP ne suffit pas : la page « endormie » de Streamlit Cloud attend un
clic sur « Yes, get this app back up! ». On utilise donc un vrai navigateur (Playwright).

Utilisation (GitHub Actions le lance en semaine) :
    uv run --no-project --with playwright==1.63.0 python scripts/reveil.py https://…streamlit.app
"""

import re
import sys

from playwright.sync_api import sync_playwright

BOUTON_REVEIL = re.compile(r"get this app back up", re.IGNORECASE)
ATTENTE_CHARGEMENT_MS = 10_000
ATTENTE_REDEMARRAGE_MS = 60_000


def reveiller(url: str) -> str:
    """Ouvre l'URL ; clique sur le bouton de réveil s'il est là. Renvoie un résumé."""
    with sync_playwright() as p:
        navigateur = p.chromium.launch()
        page = navigateur.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        page.wait_for_timeout(ATTENTE_CHARGEMENT_MS)
        bouton = page.get_by_role("button", name=BOUTON_REVEIL)
        if bouton.count() == 0:
            resume = "L'app était déjà réveillée : rien à faire."
        else:
            bouton.first.click()
            page.wait_for_timeout(ATTENTE_REDEMARRAGE_MS)  # le temps qu'elle redémarre
            resume = "L'app dormait : bouton de réveil cliqué, elle redémarre."
        navigateur.close()
    return resume


def main() -> None:
    """Lit l'URL passée en argument et affiche le résultat."""
    if len(sys.argv) != 2:
        raise SystemExit("Usage : python scripts/reveil.py <adresse de l'app>")
    print(reveiller(sys.argv[1]))  # script en ligne de commande : on affiche le résultat


if __name__ == "__main__":
    main()
