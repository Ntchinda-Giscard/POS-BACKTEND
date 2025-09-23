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
            print(self._valider_donnees_entree(donnees_vente))
            
            # 2. Construction des critères de recherche
            criteres = self._construire_criteres(donnees_vente)
            print(f"Critères construits: {criteres}")

            # 3. Recherche des règles applicables
            regles = self._rechercher_regles_applicables(criteres)
            print(f"Règles trouvées: {regles}")
            # 4. Application de la première règle valide
            code_taxe = self._appliquer_premiere_regle_valide(
                regles, donnees_vente
            )
            print(f"Code taxe déterminé: {code_taxe}")
            
            # 5. Récupération des détails du code taxe
            if code_taxe:
                details_taxe = self._recuperer_details_taxe(code_taxe)
                print(f"Détails du code taxe: {details_taxe}")
                return {
                    'code_taxe': code_taxe,
                    'taux': details_taxe[0] if details_taxe else 0.0,
                    # 'compte_comptable': details_taxe.get('compte', ''),
                    # 'exonere': details_taxe.get('exonere', False)
                }
            else:
                raise Exception("Aucun code taxe trouvé pour ces critères")
                
        except Exception as e:
            return {'erreur': str(e)}
    
    def _valider_donnees_entree(self, donnees):
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
            print(f"Vérification de la règle: {regle}")
            # Vérification des critères additionnels
            # if self._valider_criteres_additionnels(regle, donnees_contexte):
                
                # Retourne le code taxe de la première règle valide
            return regle[39] or regle[39].strip()  # Supposant que le code taxe est à l'index 39
        
        return None
    
    def _valider_criteres_additionnels(self, regle, contexte):
        """
        Validation des critères supplémentaires incluant TAXLINK
        """
        # Vérification de la cohérence législation/groupe
        if not self._verifier_coherence_legislation_groupe(regle):
            return False
        
        # Vérification des critères TAXLINK
        if not self._valider_criteres_taxlink(regle, contexte):
            return False
        
        # Vérification des critères métier spécifiques
        if not self._valider_criteres_metier(regle, contexte):
            return False
        
        return True
    
    def _valider_criteres_taxlink(self, regle, contexte):
        """
        Validation des critères complémentaires de la table TAXLINK
        """
        # Récupération des critères TAXLINK pour cette règle
        criteres_taxlink = self._recuperer_criteres_taxlink(regle['COD_0'])
        
        if not criteres_taxlink:
            return True  # Pas de critères supplémentaires
        
        # Validation de chaque critère TAXLINK
        for critere in criteres_taxlink:
            if not self._evaluer_critere_taxlink(critere, contexte):
                return False
        
        return True
    
    def _recuperer_criteres_taxlink(self, code_determination):
        """
        Récupération des critères TAXLINK pour un code de détermination donné
        """
        query = """
        SELECT * FROM TAXLINK 
        WHERE CLE_0 = :code_determination
        ORDER BY LIGNE
        """
        
        return self.db.execute(query, {'code_determination': code_determination}).fetchall()
    
    def _evaluer_critere_taxlink(self, critere, contexte):
        """
        Évaluation d'un critère TAXLINK individuel
        """
        champ = critere.get('CHAMP')
        operateur = critere.get('OPERATEUR', '=')
        valeur_attendue = critere.get('VALEUR')
        valeur_contexte = contexte.get(champ)
        
        if not champ or valeur_attendue is None:
            return True
        
        # Évaluation selon l'opérateur
        if operateur == '=':
            return valeur_contexte == valeur_attendue
        elif operateur == '!=':
            return valeur_contexte != valeur_attendue
        elif operateur == '>':
            return valeur_contexte and valeur_contexte > valeur_attendue
        elif operateur == '<':
            return valeur_contexte and valeur_contexte < valeur_attendue
        elif operateur == '>=':
            return valeur_contexte and valeur_contexte >= valeur_attendue
        elif operateur == '<=':
            return valeur_contexte and valeur_contexte <= valeur_attendue
        elif operateur == 'LIKE':
            return valeur_contexte and valeur_attendue in valeur_contexte
        elif operateur == 'IN':
            liste_valeurs = valeur_attendue.split(',')
            return valeur_contexte in liste_valeurs
        
        return True
    
    def _verifier_coherence_legislation_groupe(self, regle: Dict):
        """
        Vérification de la cohérence entre législation et groupe de sociétés
        """
        # Si pas de groupe défini, pas de contrôle nécessaire
        if not regle['GRP_0']:
            return True
        
        # Si pas de législation définie, pas de contrôle nécessaire
        if not regle['LEG_0']:
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
        WHERE VACBPR_0 = :regime_tiers 
        AND VACITM_0 = :niveau_article 
        AND ENAFLG_0 = 2
        """
        
        params = {
            'regime_tiers': criteres['VACBPR_0'],
            'niveau_article': criteres['VACITM_0']
        }
        
        # Ajout des critères optionnels selon priorité
        if criteres.get('LEG_0'):
            query += " AND LEG_0 = :legislation"
            params['legislation'] = criteres['LEG_0']
        
        # if criteres.get('GRP_0'):
        #     query += " AND GRP_0 = :groupe"
        #     params['groupe'] = criteres['GRP_0']
        
        query += " ORDER BY COD_0"  # Ordre d'application
        
        return self.db.execute(query, params).fetchall()
    
    def _recuperer_details_taxe(self, code_taxe):
        """
        Récupération des détails depuis TABVAT
        """
        query = """
        SELECT
        VATRAT_0
        FROM
        TABRATVAT
        WHERE
        VAT_0 = :code_taxe
        ORDER BY
        STRDAT_0 DESC
        """

        print(f"Exécution de la requête pour récupérer les détails du code taxe avec code_taxe={code_taxe}")
        
        
        return self.db.execute(query, {'code_taxe': code_taxe}).fetchone()

# Utilisation
# sqlite_conn = sqlite3.connect("sagex3_seed.db")
# cursor = sqlite_conn.cursor()
# determinateur = DeterminationTaxe(cursor)
# resultat = determinateur.determiner_code_taxe({
#     'regime_taxe_tiers': 'FRA',
#     'niveau_taxe_article': 'NOR',
#     'legislation': 'FRA',
#     'groupe_societe': 'FR01'
# })

# print(f"Code taxe: {resultat['code_taxe']}")
# print(f"Taux: {resultat['taux']}%")