"""Realistic 'what the LLM heard' cases, with the contact the user really meant."""

from voxmail.domain.recipient_search import RecipientHint as H

# (description, hint, expected email)
CASES: list[tuple[str, H, str]] = [
    # Homonyms in the same company
    (
        "first name + company, 2 Jacques at Mecalux",
        H(heard_names=["Jacques"], company="Mecalux"),
        "jacques.mauger@mecalux.fr",
    ),
    (
        "full name, homonym at the same company",
        H(heard_names=["Jacques Bertin"]),
        "j.bertin@mecalux.fr",
    ),
    ("full name, other homonym", H(heard_names=["Jacques Mauger"]), "jacques.mauger@mecalux.fr"),
    # Close first names
    ("Jacky", H(heard_names=["Jacky"]), "jacky.moreau@orange.fr"),
    (
        "Jack with its full name",
        H(heard_names=["Jack Wilson"]),
        "jack.wilson@wilson-consulting.co.uk",
    ),
    (
        "Jack or Jacques hypotheses + company",
        H(heard_names=["Jack", "Jacques"], company="Wilson Consulting"),
        "jack.wilson@wilson-consulting.co.uk",
    ),
    ("Jacky Moreau", H(heard_names=["Jacky Moreau"]), "jacky.moreau@orange.fr"),
    # Badly transcribed names
    ("Mojé + company", H(heard_names=["Mojé"], company="Mecalux"), "jacques.mauger@mecalux.fr"),
    ("Jacques Maugé", H(heard_names=["Jacques Maugé"]), "jacques.mauger@mecalux.fr"),
    ("Jacques Mojé", H(heard_names=["Jacques Mojé"]), "jacques.mauger@mecalux.fr"),
    ("Lucie Mojé", H(heard_names=["Lucie Mojé"]), "lucie.mauge@gmail.com"),
    ("Dupond", H(heard_names=["Dupond"]), "jean.dupont@btp-dupont.fr"),
    ("Jean Dupond", H(heard_names=["Jean Dupond"]), "jean.dupont@btp-dupont.fr"),
    ("Hélène Lefebvre", H(heard_names=["Hélène Lefebvre"]), "helene.lefevre@mairie-lyon.fr"),
    ("Nadia Adad", H(heard_names=["Nadia Adad"]), "nadia.haddad@orange.fr"),
    ("Tomas Petit", H(heard_names=["Tomas Petit"]), "thomas.petit@petit-elec.fr"),
    ("Isabelle Moro", H(heard_names=["Isabelle Moro"]), "i.moreau@banque-populaire.fr"),
    ("Kévin Novak", H(heard_names=["Kévin Novak"]), "k.nowak@nowak-peinture.fr"),
    ("Yannick Legall", H(heard_names=["Yannick Legall"]), "yannick.legall@legall-elec.bzh"),
    ("Pierre Lorain", H(heard_names=["Pierre Lorain"]), "pierre.lorrain@gmail.com"),
    (
        "Christophe Faure + trade",
        H(heard_names=["Christophe Faure"], other_clues="le maçon"),
        "c.faure@faure-maconnerie.fr",
    ),
    ("Rachid Amrany", H(heard_names=["Rachid Amrany"]), "r.amrani@amrani-transports.fr"),
    ("Mohamed Bensalah", H(heard_names=["Mohamed Bensalah"]), "m.bensalah@sbs-renovation.fr"),
    (
        "Sébastien Dubois without accent",
        H(heard_names=["Sebastien Dubois"]),
        "s.dubois@dubois-bois.fr",
    ),
    # Accents and hyphens
    (
        "Jacques-Édouard Lefebvre",
        H(heard_names=["Jacques Edouard Lefebvre"]),
        "je.lefebvre@notaires-lefebvre.fr",
    ),
    (
        "Jacques-Édouard alone",
        H(heard_names=["Jacques-Édouard"]),
        "je.lefebvre@notaires-lefebvre.fr",
    ),
    (
        "Anne Sophie Da Silva",
        H(heard_names=["Anne Sophie Da Silva"]),
        "annesophie.dasilva@gmail.com",
    ),
    ("Dasilva in one word", H(heard_names=["Dasilva"]), "annesophie.dasilva@gmail.com"),
    ("Emilie Roux", H(heard_names=["Emilie Roux"]), "emilie.roux@mairie-villeurbanne.fr"),
    # Last name only
    ("Rousseau", H(heard_names=["Rousseau"]), "marc.rousseau@rousseau-materiaux.fr"),
    ("Garnier", H(heard_names=["Garnier"]), "s.garnier@comptable-garnier.fr"),
    ("Nguyen", H(heard_names=["Nguyen"]), "minh.nguyen@nguyen-carrelage.fr"),
    ("Girardot", H(heard_names=["Girardot"]), "stephanie.girardot@wanadoo.fr"),
    ("Leroy", H(heard_names=["Leroy"]), "contact@maconnerie-leroy.fr"),
    # First name only
    ("Jean (most frequent Jean)", H(heard_names=["Jean"]), "jean.dupont@btp-dupont.fr"),
    ("Karim (pro address used more)", H(heard_names=["Karim"]), "karim@benali-plomberie.fr"),
    ("Stéphanie", H(heard_names=["Stéphanie"]), "stephanie.girardot@wanadoo.fr"),
    ("Lucas", H(heard_names=["Lucas"]), "lucas.bernard@gmail.com"),
    ("Minh", H(heard_names=["Minh"]), "minh.nguyen@nguyen-carrelage.fr"),
    # Company or clue only
    (
        "the guy from Mecalux",
        H(company="Mecalux", other_clues="le gars de chez Mecalux"),
        "jacques.mauger@mecalux.fr",
    ),
    ("my accountant", H(other_clues="mon comptable"), "s.garnier@comptable-garnier.fr"),
    ("Point P supplier", H(company="Point P"), "p.laurent@pointp.fr"),
    (
        "the roofer",
        H(heard_names=["Stéphane"], other_clues="le couvreur de Girard Toiture"),
        "s.girard@girard-toiture.fr",
    ),
    (
        "my banker Isabelle",
        H(heard_names=["Isabelle"], other_clues="ma banquière à la Banque Populaire"),
        "i.moreau@banque-populaire.fr",
    ),
    (
        "Karim the plumber",
        H(heard_names=["Karim"], other_clues="le plombier"),
        "karim@benali-plomberie.fr",
    ),
]

# Hints that match nobody in the address book.
NO_MATCH: list[tuple[str, H]] = [
    ("unknown full name", H(heard_names=["Zébulon Kowalski"])),
    ("unknown English name", H(heard_names=["Bartholomew Fitzgerald"])),
    ("unknown company only", H(company="Airbus")),
    ("unknown first name only", H(heard_names=["Gaspard"])),
]
