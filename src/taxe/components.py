"""
Sage X3 tax determination (fonction GESVAC / table TABVAC).

A rule row in TABVAC is keyed by legislation (LEG_0), company group (GRP_0, blank = any),
BP tax rule (VACBPR_0 = régime de taxe du tiers) and item tax level (VACITM_0 = niveau de
taxe de l'article). Up to five extra criteria (FLD_n / OPE_n / VALS_n) refine the match —
in the ARE dataset the criterion is SATISS (state of the issuing site, e.g. "AE-DU").
The winning rule gives the tax code VAT_0; the rate comes from TABRATVAT (effective
start date STRDAT_0, optionally per company CPY_0) with TABVAT.VATRAT_0 as fallback.
"""
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

ACTIVE = "2"      # X3 local menu 1: 1 = No, 2 = Yes
OPE_EQUAL = "2"   # operator "=" in TABVAC.OPE_n (1 = none)
OPE_DIFF = "3"    # operator "<>"


def _s(value: Any) -> str:
    return (value or "").strip() if isinstance(value, str) else ("" if value is None else str(value).strip())


def _dec(value: Any) -> Decimal:
    try:
        return Decimal(_s(value) or "0")
    except InvalidOperation:
        return Decimal(0)


class DeterminationTaxe:
    """Resolves the tax code and rate for (régime tiers, niveau article) on a given site."""

    def __init__(self, cursor):
        self.cursor = cursor
        self._site_cache: Dict[str, Dict[str, str]] = {}

    # ---- context -------------------------------------------------------

    def site_context(self, site: Optional[str]) -> Dict[str, str]:
        """Legislation, company, group and issuing state for a sales site (FACILITY → COMPANY / BPADDRESS)."""
        key = _s(site)
        if key in self._site_cache:
            return self._site_cache[key]

        if key:
            row = self.cursor.execute(
                "SELECT FCY_0, LEGCPY_0, LEG_0, BPAADD_0 FROM FACILITY WHERE FCY_0 = ?", (key,)
            ).fetchone()
        else:
            row = self.cursor.execute("SELECT FCY_0, LEGCPY_0, LEG_0, BPAADD_0 FROM FACILITY LIMIT 1").fetchone()

        ctx = {"site": key, "company": "", "legislation": "", "group": "", "state": ""}
        if row:
            ctx["site"] = _s(row[0])
            ctx["company"] = _s(row[1])
            ctx["legislation"] = _s(row[2])
            cpy = self.cursor.execute(
                "SELECT LEG_0, GRUCOD_0 FROM COMPANY WHERE CPY_0 = ?", (ctx["company"],)
            ).fetchone()
            if cpy:
                ctx["legislation"] = _s(cpy[0]) or ctx["legislation"]
                ctx["group"] = _s(cpy[1])
            addr = self.cursor.execute(
                "SELECT SAT_0 FROM BPADDRESS WHERE BPANUM_0 = ? AND BPAADD_0 = ?", (ctx["site"], _s(row[3]))
            ).fetchone()
            if addr:
                ctx["state"] = _s(addr[0])
        self._site_cache[key] = ctx
        return ctx

    # ---- rule matching ---------------------------------------------------

    def _rules(self, legislation: str, regime: str, niveau: str) -> List[Dict[str, Any]]:
        rows = self.cursor.execute(
            """
            SELECT COD_0, GRP_0, VACBPR_0, VACITM_0, VAT_0, VATTYP_0, ENAFLG_0,
                   FLD_0, OPE_0, VALS_0, FLD_1, OPE_1, VALS_1, FLD_2, OPE_2, VALS_2,
                   FLD_3, OPE_3, VALS_3, FLD_4, OPE_4, VALS_4
            FROM TABVAC
            WHERE LEG_0 = ? AND VACBPR_0 = ? AND VACITM_0 = ?
            ORDER BY COD_0
            """,
            (legislation, regime, niveau),
        ).fetchall()
        rules = []
        for r in rows:
            criteria = []
            for i in range(5):
                fld, ope, val = _s(r[7 + 3 * i]), _s(r[8 + 3 * i]), _s(r[9 + 3 * i])
                if fld and ope not in ("", "0", "1"):
                    criteria.append({"field": fld, "op": ope, "value": val})
            rules.append({
                "code": _s(r[0]), "group": _s(r[1]), "regime": _s(r[2]), "niveau": _s(r[3]),
                "vat": _s(r[4]), "type": _s(r[5]), "active": _s(r[6]) == ACTIVE, "criteria": criteria,
            })
        return rules

    @staticmethod
    def _criteria_match(rule: Dict[str, Any], ctx: Dict[str, str]) -> Optional[bool]:
        """True/False when every criterion can be evaluated; None when a criterion is unknown."""
        known = {"SATISS": ctx.get("state", ""), "SALFCY": ctx.get("site", ""), "CPY": ctx.get("company", "")}
        result = True
        for crit in rule["criteria"]:
            if crit["field"] not in known:
                return None
            actual = known[crit["field"]]
            if crit["op"] == OPE_EQUAL:
                result = result and actual == crit["value"]
            elif crit["op"] == OPE_DIFF:
                result = result and actual != crit["value"]
            else:
                return None
        return result

    def _pick(self, rules: List[Dict[str, Any]], ctx: Dict[str, str]):
        """Most specific applicable rule: group match > criteria match > no criteria."""
        candidates = [r for r in rules if r["group"] in ("", ctx.get("group", ""))]
        matched = [r for r in candidates if r["criteria"] and self._criteria_match(r, ctx) is True]
        if matched:
            return matched[0], None
        plain = [r for r in candidates if not r["criteria"]]
        if plain:
            return plain[0], None
        undecided = [r for r in candidates if r["criteria"] and self._criteria_match(r, ctx) is None]
        if undecided:
            return undecided[0], f"critère {undecided[0]['criteria'][0]['field']} non évaluable, règle {undecided[0]['code']} appliquée"
        return None, None

    def determiner_code_taxe(self, criteres: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        criteres: regime_taxe_tiers, niveau_taxe_article, legislation (optional, derived from site),
                  site (optional), groupe_societe (optional), date (optional, ISO)
        """
        regime = _s(criteres.get("regime_taxe_tiers"))
        niveau = _s(criteres.get("niveau_taxe_article"))
        ctx = self.site_context(criteres.get("site"))
        legislation = _s(criteres.get("legislation")) or ctx["legislation"]
        if criteres.get("groupe_societe"):
            ctx = {**ctx, "group": _s(criteres["groupe_societe"])}
        if not (regime and niveau and legislation):
            return None

        rules = self._rules(legislation, regime, niveau)
        active = [r for r in rules if r["active"]]
        warning = None

        rule, warning = self._pick(active, ctx)
        if rule is None and rules:
            # X3 would refuse the line; the till keeps selling and flags it.
            rule, _ = self._pick(rules, ctx)
            if rule:
                warning = f"règle {rule['code']} inactive dans X3, appliquée par défaut"
        if rule is None:
            return None

        details = self._recuperer_details_taxe(rule["vat"], ctx["company"], criteres.get("date"))
        return {
            "code_taxe": rule["vat"],
            "regle": rule["code"],
            "legislation": legislation,
            "taux": details["taux"],
            "compte_comptable": details["compte_comptable"],
            "exonere": details["exonere"],
            "description": details["description"],
            "warning": warning,
        }

    # ---- rate lookup ---------------------------------------------------------

    def _recuperer_details_taxe(self, vat: str, company: str, date: Optional[str]) -> Dict[str, Any]:
        at = _s(date)[:10] if date else datetime.now().strftime("%Y-%m-%d")
        rate_row = self.cursor.execute(
            """
            SELECT VATRAT_0, VATEXEFLG_0, CPY_0 FROM TABRATVAT
            WHERE VAT_0 = ? AND (CPY_0 = ? OR TRIM(CPY_0) = '') AND substr(STRDAT_0, 1, 10) <= ?
            ORDER BY CASE WHEN CPY_0 = ? THEN 0 ELSE 1 END, STRDAT_0 DESC
            LIMIT 1
            """,
            (vat, company, at, company),
        ).fetchone()
        vat_row = self.cursor.execute(
            "SELECT VATRAT_0, ACCCOD_0, VATDES_0, LANDESSHO_0 FROM TABVAT WHERE VAT_0 = ?", (vat,)
        ).fetchone()

        if rate_row:
            taux = _dec(rate_row[0])
            exonere = _s(rate_row[1]) == ACTIVE or taux == 0
        elif vat_row:
            taux = _dec(vat_row[0])
            exonere = taux == 0
        else:
            taux, exonere = Decimal(0), True

        description = ""
        if vat_row:
            description = _s(vat_row[2])
            if not description and "~" in _s(vat_row[3]):      # LANDESSHO_0 = "LAN~long~short"
                parts = _s(vat_row[3]).split("~")
                description = parts[1] if len(parts) > 1 else parts[0]
        return {
            "taux": float(taux),
            "compte_comptable": _s(vat_row[1]) if vat_row else None,
            "exonere": exonere,
            "description": description or None,
        }
