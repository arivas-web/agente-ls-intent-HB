"""Casado de filas de Venzo con empresas de HubSpot: CIF > dominio > nombre normalizado.
Las coincidencias dudosas NO se asumen: van al informe de revisión."""
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

GENERIC_DOMAINS = {"gmail.com", "hotmail.com", "hotmail.es", "outlook.com", "outlook.es", "yahoo.com", "yahoo.es",
                   "icloud.com", "live.com", "telefonica.net", "movistar.es"}
LEGAL = r"\b(s ?l ?u?|s ?a ?u?|s ?l ?l|s ?c|s ?coop|ltda|sociedad limitada|sociedad anonima|s r l|slp)\b"


def _ascii(t):
    return unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode().lower()


def norm_cif(v):
    v = re.sub(r"[^A-Z0-9]", "", (v or "").upper())
    if v.startswith("ES") and len(v) == 11:
        v = v[2:]
    return v if len(v) >= 8 else ""


def norm_domain(v):
    v = _ascii(v).strip()
    if "@" in v:
        v = v.split("@")[-1]
    v = re.sub(r"^https?://", "", v)
    v = re.sub(r"^www\.", "", v).split("/")[0].split("?")[0].strip()
    return "" if (not v or "." not in v or v in GENERIC_DOMAINS) else v


def norm_name(v):
    t = _ascii(v)
    t = re.sub(r"[.,]", "", t)
    t = re.sub(LEGAL, " ", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


class Matcher:
    def __init__(self, companies, fuzzy_threshold=0.8):
        """companies: [{'hs_id','cif','domain','name'}]"""
        self.fuzzy = fuzzy_threshold
        self.by_cif, self.by_dom, self.by_name = defaultdict(set), defaultdict(set), defaultdict(set)
        self.names = {}
        for c in companies:
            k = norm_cif(c.get("cif"))
            if k:
                self.by_cif[k].add(c["hs_id"])
            d = norm_domain(c.get("domain"))
            if d:
                self.by_dom[d].add(c["hs_id"])
            n = norm_name(c.get("name"))
            if n:
                self.by_name[n].add(c["hs_id"])
                self.names[c["hs_id"]] = n

    def match(self, row):
        """row: {'cif','domain' (o email/web),'name'}. Devuelve dict(hs_id, method, confidence, review, candidates)."""
        found = {}
        for method, idx, key, conf in (("cif", self.by_cif, norm_cif(row.get("cif")), 1.0),
                                       ("dominio", self.by_dom, norm_domain(row.get("domain")), 0.9),
                                       ("nombre", self.by_name, norm_name(row.get("name")), 0.7)):
            if key and key in idx:
                found[method] = (idx[key], conf)
        # Revisión: ambigüedad (varios candidatos) o conflicto entre métodos.
        for method in ("cif", "dominio", "nombre"):
            if method in found:
                ids, conf = found[method]
                others = {i for m, (s, _) in found.items() if m != method for i in s}
                if len(ids) > 1:
                    return self._review(found, f"{method}_ambiguo")
                if others and not (ids & others):
                    return self._review(found, "conflicto_entre_metodos")
                return {"hs_id": next(iter(ids)), "method": method, "confidence": conf, "review": False,
                        "candidates": []}
        # Sin coincidencia exacta: similitud de nombre -> siempre a revisión.
        n = norm_name(row.get("name"))
        if n:
            scored = sorted(((SequenceMatcher(None, n, v).ratio(), k) for k, v in self.names.items()), reverse=True)[:3]
            cands = [{"hs_id": k, "similarity": round(s, 2)} for s, k in scored if s >= self.fuzzy]
            if cands:
                return {"hs_id": None, "method": "nombre_similar", "confidence": cands[0]["similarity"] * 0.7,
                        "review": True, "candidates": cands}
        return {"hs_id": None, "method": "ninguno", "confidence": 0.0, "review": False, "candidates": []}

    @staticmethod
    def _review(found, why):
        cands = sorted({i for s, _ in found.values() for i in s})
        return {"hs_id": None, "method": why, "confidence": 0.0, "review": True,
                "candidates": [{"hs_id": i} for i in cands]}
