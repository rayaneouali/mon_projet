import pytest

from voxmail.domain.contacts import Contact, company_from_email, is_email, normalize


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hélène", "helene"),
        ("  JEAN   Dupont ", "jean dupont"),
        ("Jacques-Édouard", "jacques edouard"),
        ("N'Diaye", "ndiaye"),
        ("jean.dupont", "jean dupont"),
    ],
)
def test_normalize(raw, expected):
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    ("email", "company"),
    [
        ("j.bertin@mecalux.fr", "mecalux"),
        ("jean@btp-dupont.fr", "btp dupont"),
        ("someone@gmail.com", None),
        ("someone@orange.fr", None),
    ],
)
def test_company_from_email(email, company):
    assert company_from_email(email) == company


def test_contact_names():
    contact = Contact(email="a@mecalux.fr", first_name="Jacques", last_name="Mauger")
    assert contact.full_name == "Jacques Mauger"
    assert contact.effective_company == "mecalux"
    assert Contact(email="compta@x.fr").display_name == "compta@x.fr"


def test_is_email():
    assert is_email("jean.dupont@gmail.com")
    assert not is_email("jean dupont")
