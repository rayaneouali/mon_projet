"""Tests des règles de dates (semaine du lundi, affichage français, samedis)."""

from datetime import date

from services import dates


def test_lundi_de_la_semaine() -> None:
    """La semaine commence le lundi, y compris quand on part d'un dimanche."""
    assert dates.lundi_de(date(2026, 11, 9)) == date(2026, 11, 9)  # lundi
    assert dates.lundi_de(date(2026, 11, 14)) == date(2026, 11, 9)  # samedi
    assert dates.lundi_de(date(2026, 11, 15)) == date(2026, 11, 9)  # dimanche


def test_format_francais() -> None:
    """Les dates s'affichent « lun. 9 nov. »."""
    assert dates.formater(date(2026, 11, 9)) == "lun. 9 nov."
    assert dates.formater(date(2026, 8, 1)) == "sam. 1 août"


def test_jours_de_la_semaine_sans_et_avec_dimanche() -> None:
    """Lundi → samedi par défaut, lundi → dimanche sur demande."""
    assert len(dates.jours_de_la_semaine(date(2026, 11, 9))) == 6
    assert dates.jours_de_la_semaine(date(2026, 11, 9), avec_dimanche=True)[-1] == date(
        2026, 11, 15
    )


def test_jour_ouvre() -> None:
    """Du lundi au vendredi seulement."""
    assert dates.est_jour_ouvre(date(2026, 11, 13))  # vendredi
    assert not dates.est_jour_ouvre(date(2026, 11, 14))  # samedi


def test_huit_prochains_samedis() -> None:
    """8 samedis à venir ; si on est samedi, celui du jour est inclus."""
    samedis = dates.prochains_samedis(date(2026, 11, 10))
    assert len(samedis) == 8
    assert samedis[0] == date(2026, 11, 14)
    assert all(dates.est_samedi(s) for s in samedis)
    assert dates.prochains_samedis(date(2026, 11, 14))[0] == date(2026, 11, 14)
