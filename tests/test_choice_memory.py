from voxmail.contacts.memory import InMemoryChoiceMemory


def test_counts_are_normalized_and_summed():
    memory = InMemoryChoiceMemory()
    memory.record("Jean", "jmartin@gmail.com")
    memory.record("jean", "jmartin@gmail.com")
    memory.record("Jean Martin", "jmartin@gmail.com")
    memory.record("Jean", "jean.dupont@btp-dupont.fr")
    assert memory.counts_for(["JEAN"]) == {"jmartin@gmail.com": 2, "jean.dupont@btp-dupont.fr": 1}
    assert memory.counts_for(["Jean", "Jean Martin"])["jmartin@gmail.com"] == 3
    assert memory.counts_for(["Paul"]) == {}
