import pytest

from voxmail.domain.phonetic import phonetic_key


@pytest.mark.parametrize(
    "names",
    [
        ("Mauger", "Maugé", "Mojé"),
        ("Jacques", "Jack"),
        ("Dupont", "Dupond"),
        ("Faure", "Fort"),
        ("Haddad", "Adad"),
        ("Thomas", "Tomas"),
        ("Nowak", "Novak"),
        ("Rousseau", "Rousso"),
        ("Moreau", "Moro"),
    ],
)
def test_names_that_sound_alike_have_the_same_key(names):
    keys = {phonetic_key(name) for name in names}
    assert len(keys) == 1, keys


@pytest.mark.parametrize(
    ("a", "b"),
    [("Martin", "Marton"), ("Laurent", "Lorrain"), ("Jacques", "Jacky"), ("Moreau", "Mauger")],
)
def test_names_that_sound_different_have_different_keys(a, b):
    assert phonetic_key(a) != phonetic_key(b)


def test_each_word_is_keyed_and_accents_are_handled():
    assert phonetic_key("Jacques-Édouard Mauger") == "jak eduar moj"
    assert phonetic_key("François") == phonetic_key("Fransoi")
