"""Listes de référence (équipes, gars, dossiers) et petites aides pour les afficher."""

from dataclasses import dataclass
from typing import Any

from db import connexion, requetes


@dataclass
class References:
    """Les trois listes de base, actifs ET inactifs (pour retrouver les noms dans l'historique)."""

    equipes: list[dict[str, Any]]
    gars: list[dict[str, Any]]
    dossiers: list[dict[str, Any]]

    def gars_actifs(self) -> list[dict[str, Any]]:
        """Les gars encore en activité."""
        return [g for g in self.gars if g["actif"]]

    def gars_actifs_de(self, equipe_id: int) -> list[dict[str, Any]]:
        """Les gars actifs d'une équipe."""
        return [g for g in self.gars_actifs() if g["equipe_id"] == equipe_id]

    def dossiers_actifs(self) -> list[dict[str, Any]]:
        """Les dossiers encore ouverts."""
        return [d for d in self.dossiers if d["actif"]]

    def nom_equipe(self, equipe_id: int) -> str:
        """Nom d'une équipe à partir de son id."""
        return next((e["nom"] for e in self.equipes if e["id"] == equipe_id), "?")

    def chef_equipe(self, equipe_id: int) -> str:
        """Chef d'une équipe à partir de son id."""
        return next((e["chef"] for e in self.equipes if e["id"] == equipe_id), "")

    def un_gars(self, gars_id: int) -> dict[str, Any]:
        """La fiche d'un gars à partir de son id."""
        return next(g for g in self.gars if g["id"] == gars_id)

    def libelle_dossier(self, dossier_id: int | None) -> str:
        """« D-2026-001 · Client · Lieu », ou « Aucun dossier »."""
        if not dossier_id:  # None ou 0
            return "Aucun dossier"
        dossier = next((d for d in self.dossiers if d["id"] == dossier_id), None)
        if dossier is None:
            return "?"
        morceaux = [dossier["code"], dossier["client"], dossier["lieu"]]
        return " · ".join(m for m in morceaux if m)


def charger_references() -> References:
    """Lit les équipes, les gars et les dossiers dans la base (une seule connexion)."""
    with connexion.ouvrir_connexion() as conn:
        return References(
            equipes=requetes.lister_equipes(conn),
            gars=requetes.lister_gars(conn),
            dossiers=requetes.lister_dossiers(conn),
        )
