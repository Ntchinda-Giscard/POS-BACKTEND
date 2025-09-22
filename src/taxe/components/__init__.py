

import sqlite3
from typing import Dict


class DeterminationTaxe:
    
    def __init__(self, connection_db):
        self.db = connection_db
    
    def determiner_code_taxe(self, donnees_vente):
        """
        Méthode principale de détermination du code taxe
        """
        try:
            # 1. Validation des données d'entrée
            self._valider_donnees_entree(donnees_vente)
            
            # 2. Construction des critères de recherche
            criteres = self._construire_criteres(donnees_vente)
            
            # 3. Recherche des règles applicables
            regles = self._rechercher_regles_applicables(criteres)
            
            # 4. Application de la première règle valide
            code_taxe = self._appliquer_premiere_regle_valide(
                regles, donnees_vente
            )
            
            # 5. Récupération des détails du code taxe
            if code_taxe:
                details_taxe = self._recuperer_details_taxe(code_taxe)
                return {
                    'code_taxe': code_taxe,
                    'taux': details_taxe.get('taux', 0),
                    'compte_comptable': details_taxe.get('compte', ''),
                    'exonere': details_taxe.get('exonere', False)
                }
            else:
                raise Exception("Aucun code taxe trouvé pour ces critères")
                
        except Exception as e:
            return {'erreur': str(e)}
    
    def _valider_donnees_entree(self, donnees: Dict):
        """
        Validation des données d'entrée obligatoires
        """
        champs_obligatoires = ['regime_taxe_tiers', 'niveau_taxe_article']
        
        for champ in champs_obligatoires:
            if champ not in donnees or not donnees[champ]:
                raise ValueError(f"Le champ {champ} est obligatoire")
        
        # Validation du format des codes
        if len(donnees['regime_taxe_tiers']) > 10:
            raise ValueError("Le régime de taxe tiers ne peut dépasser 10 caractères")
        
        if len(donnees['niveau_taxe_article']) > 10:
            raise ValueError("Le niveau de taxe article ne peut dépasser 10 caractères")
    
    def _construire_criteres(self, donnees):
        """
        Construction des critères de recherche pour TABVAC
        """
        criteres = {
            'VACBPR_0': donnees['regime_taxe_tiers'],
            'VACITM_0': donnees['niveau_taxe_article'],
            'ENAFLG_0': 2  # Seulement les règles actives
        }
        
        # Ajout des critères optionnels
        if donnees.get('legislation'):
            criteres['LEG_0'] = donnees['legislation']
        
        if donnees.get('groupe_societe'):
            criteres['GRP_0'] = donnees['groupe_societe']
        
        if donnees.get('type_taxe'):
            criteres['VATTYP_0'] = donnees['type_taxe']
        
        return criteres
    
    def _appliquer_premiere_regle_valide(self, regles, donnees_contexte):
        """
        Application de la première règle valide selon l'ordre de priorité
        """
        if not regles:
            return None
        
        for regle in regles:
            # Vérification des critères additionnels
            if self._valider_criteres_additionnels(regle, donnees_contexte):
                # Retourne le code taxe de la première règle valide
                return regle.get('CODE_TAXE') or regle.get('CODTAXE')
        
        return None
    
    def _valider_criteres_additionnels(self, regle, contexte):
        """
        Validation des critères supplémentaires
        """
        # Vérification de la cohérence législation/groupe
        if not self._verifier_coherence_legislation_groupe(regle):
            return False
        
        # Vérification des critères métier spécifiques
        if not self._valider_criteres_metier(regle, contexte):
            return False
        
        return True
    
    def _verifier_coherence_legislation_groupe(self, regle):
        """
        Vérification de la cohérence entre législation et groupe de sociétés
        """
        # Si pas de groupe défini, pas de contrôle nécessaire
        if not regle.get('GRP_0'):
            return True
        
        # Si pas de législation définie, pas de contrôle nécessaire
        if not regle.get('LEG_0'):
            return True
        
        # Ici, on devrait vérifier que le groupe contient au moins
        # une société avec la même législation
        # Pour simplifier, on retourne True (à implémenter selon vos besoins)
        return True
    
    def _valider_criteres_metier(self, regle, contexte):
        """
        Validation des critères métier spécifiques
        """
        # Ici, vous pouvez ajouter des validations métier spécifiques
        # comme la vérification de dates de validité, critères additionnels, etc.
        
        # Pour l'exemple, on retourne True
        return True
    
    def _rechercher_regles_applicables(self, criteres):
        """
        Recherche dans TABVAC selon l'ordre de priorité
        """
        query = """
        SELECT * FROM TABVAC 
        WHERE VACBPR = :regime_tiers 
        AND VACITM = :niveau_article 
        AND ENAFLG = 1
        """
        
        params = {
            'regime_tiers': criteres['VACBPR'],
            'niveau_article': criteres['VACITM']
        }
        
        # Ajout des critères optionnels selon priorité
        if criteres.get('LEG'):
            query += " AND LEG = :legislation"
            params['legislation'] = criteres['LEG']
        
        if criteres.get('GRP'):
            query += " AND GRP = :groupe"
            params['groupe'] = criteres['GRP']
        
        query += " ORDER BY COD"  # Ordre d'application
        
        return self.db.execute(query, params).fetchall()
    
    def _recuperer_details_taxe(self, code_taxe):
        """
        Récupération des détails depuis TABVAT
        """
        query = """
        SELECT * FROM TABVAT 
        WHERE CODE = :code_taxe
        """
        
        return self.db.execute(query, {'code_taxe': code_taxe}).fetchone()



sqlite_conn = sqlite3.connect("sagex3_seed.db")
cursor = sqlite_conn.cursor()
# Utilisation
determinateur = DeterminationTaxe(cursor)
resultat = determinateur.determiner_code_taxe({
    'regime_taxe_tiers': 'FRA',
    'niveau_taxe_article': 'NOR',
    'legislation': 'FRA',
    'groupe_societe': 'FR01'
})





print(f"Code taxe: {resultat['code_taxe']}")
print(f"Taux: {resultat['taux']}%")