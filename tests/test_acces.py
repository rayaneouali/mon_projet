"""Tests du contrôle d'accès par code."""

from services import acces

CHEFS, ADMIN = "123456", "654321"


def test_code_chefs_et_code_admin() -> None:
    """Le bon code donne le bon rôle ; espaces autour ignorés."""
    assert acces.verifier_code("123456", CHEFS, ADMIN) == acces.ROLE_CHEFS
    assert acces.verifier_code(" 654321 ", CHEFS, ADMIN) == acces.ROLE_ADMIN


def test_mauvais_code_ou_code_vide_refuse() -> None:
    """Un faux code ou un code vide ne donne aucun accès."""
    assert acces.verifier_code("000000", CHEFS, ADMIN) is None
    assert acces.verifier_code("", CHEFS, ADMIN) is None


def test_codes_non_configures_aucun_acces() -> None:
    """Si les codes ne sont pas définis, personne n'entre (même avec un code vide)."""
    assert acces.verifier_code("", "", "") is None
    assert acces.verifier_code("123456", "", "") is None


def test_chefs_n_ont_pas_acces_a_l_admin() -> None:
    """Code chefs : Saisie/Semaine/Samedis mais pas Admin ; code admin : tout."""
    assert acces.autorise(acces.ROLE_CHEFS, acces.ROLE_CHEFS)
    assert not acces.autorise(acces.ROLE_CHEFS, acces.ROLE_ADMIN)
    assert acces.autorise(acces.ROLE_ADMIN, acces.ROLE_CHEFS)
    assert acces.autorise(acces.ROLE_ADMIN, acces.ROLE_ADMIN)
    assert not acces.autorise(None, acces.ROLE_CHEFS)


def test_jeton_de_l_adresse() -> None:
    """Le jeton redonne le bon rôle, ne contient pas le code, et meurt si le code change."""
    jeton = acces.fabriquer_jeton(acces.ROLE_CHEFS, CHEFS)
    assert CHEFS not in jeton
    assert acces.role_depuis_jeton(jeton, CHEFS, ADMIN) == acces.ROLE_CHEFS
    assert acces.role_depuis_jeton(jeton, "999999", ADMIN) is None
    assert acces.role_depuis_jeton("n-importe-quoi", CHEFS, ADMIN) is None
