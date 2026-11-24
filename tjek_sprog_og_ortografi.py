#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sprog- og ortografikontrol i værtsløkken — tre lag.

Lag 1, forbudte mønstre i prosa (kun prosa-artefakter: .adoc .md .json .py .txt;
kildekode er engelsk/ascii efter sprog-reglen og er en tvangne undtagelse):
  - ascii-udvanding af dansk (aa/ae/oe i stedet for å/æ/o),
  - engelske fagord (merge/draft/commit/branch/backend/token, persistence,
    resume, review, process, know-how) uden for backticks,
  - stedord (jeg/du/dig/mig) uden for backticks.

Backticks (`...`) og tekniske sammensatninger (QVariantList-properties,
host-loop) fratrakkes. Regeltekster og historiske logposter, der citerer
forbudte ord, tillades (linjer med: regel, ortografi, terminologi, stedord,
eskalering, historisk, lukket, aa/ae/oe). Kontrollen selv undtages.

Lag 2, stavetjek mod ordliste: hvis en dansk ordliste findes (--ordliste
<sti> eller /usr/share/dict/da*), tjekkes hver prosa-token mod den; ellers
bruges den indbyggede liste over kendte fejl (KENDTE_FEJL).

Lag 3, bindestregsbrug: dansk skrives sammenhængende (uden bindestreg);
bindestreg tillades ved låneord/forkortelser og tekniske termer (git-, mål-,
ascii-, test-, host-loop, know-how, read-only, end-to-end m.fl.). Danske
enkeltord, der ikke må splittes med bindestreg, står i KENDTE_BINDESTREG_FEJL
(f.eks. genoptagelses-regel -> genoptagelsesregel).

Exit 0 hvis rent, ellers exit 1 med alle fund (fil:linje: hvad).
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SELV = os.path.basename(__file__)

BACKTICK = re.compile(r"`[^`]*`")
TEKNISK_SAMMENSAT = re.compile(r"\b[A-Za-z][A-Za-z0-9_]*(?:-[A-Za-z0-9_-]+)+\b")
IDENTIFIKATOR = re.compile(r"\b[A-Za-zÆØÅæøå][A-Za-zÆØÅæøå0-9]*_[A-Za-z0-9_]*\b")
KLASSE_SUFFIKSER = ("model", "client", "lager", "reader", "framereader",
                    "protocol", "proces", "dialog", "visning", "side")
KLASSE_NAVN = re.compile(
    r"\b[A-Za-zÆØÅæøå]*(?:%s)\b" % "|".join(KLASSE_SUFFIKSER), re.IGNORECASE)
TOKEN = re.compile(r"[A-Za-zÆØÅæøå][A-Za-zÆØÅæøå\-']*")
ASCII_UDVANDING = re.compile(
    r"\b[a-zæøå]*(?:aa|ae)[a-zæøå]*\b|\b[a-zæøå]*oe(?!r\b)[a-zæøå]*\b")
ENGELSK_FAGORD = re.compile(
    r"\b(?:merges?|merged|drafts?|commits?|branches?|backend|tokens?|persistence|"
    r"resume|reviews?|process|knowhow|know-how)\b",
    re.IGNORECASE,
)
STEDORD = re.compile(r"\b(?:jeg|du|dig|mig)\b", re.IGNORECASE)

TILLADTE_LINJER = ("stedordsregel", "terminologi", "ortografi",
                   "eskalering", "historisk", "lukket", "aa/ae/oe",
                   "ascii", "kommando", ".cpp", "filnavn")

KENDTE_FEJL = {
    "rollentabel": "rolletabel",
}

KENDTE_BINDESTREG_FEJL = {
    "genoptagelses-regel": "genoptagelsesregel",
    "genoptagelsesregel-testen": "genoptagelsesregeltesten",
}

BINDESTREG_SAMMENSAT = re.compile(r"\b[A-Za-zÆØÅæøå]+-[A-Za-zÆØÅæøå]+(?:-[A-Za-zÆØÅæøå]+)*\b")

TILLADTE_TEKNISKE = {
    "pr", "ci", "api", "json", "sdk", "qml", "qt", "acp", "rpm", "github",
    "sailfish", "jolla", "harbour", "desktop", "spec", "yaml", "moc",
    "qmake", "sfdk", "mb2", "pkcon", "rpmbuild", "qsettings", "qstring",
    "qcompare", "qvariantlist", "qproperty", "cpp", "hpp", "pro", "adoc",
    "ndjson", "utf", "ascii", "stdio", "sailjail", "defaultuser", "hicolor",
    "aarch64", "x86", "vibe",
}

PROSA_ENDELSER = {".adoc", ".md", ".json", ".py", ".txt"}

ORDLISTE_STIER = ["/usr/share/dict/da", "/usr/share/dict/da_DK",
                  "/usr/share/dict/danish", "/usr/share/dict/dansk"]


def find_ordliste(bruger_sti):
    if bruger_sti:
        return bruger_sti if os.path.exists(bruger_sti) else None
    for sti in ORDLISTE_STIER:
        if os.path.exists(sti):
            return sti
    return None


def las_ordliste(sti):
    ordset = set()
    with open(sti, encoding="utf-8", errors="ignore") as f:
        for linje in f:
            ord = linje.strip().split("/")[0].lower()
            if ord:
                ordset.add(ord)
    return ordset


def tjek_fil(sti, ordliste, filnavne):
    fund = []
    with open(sti, encoding="utf-8", errors="ignore") as f:
        for nr, linje in enumerate(f, 1):
            lav = linje.lower()
            if any(t in lav for t in TILLADTE_LINJER):
                continue
            tekst0 = IDENTIFIKATOR.sub(" ", BACKTICK.sub(" ", linje))
            for m in BINDESTREG_SAMMENSAT.finditer(tekst0):
                ord_ = m.group(0)
                lav = ord_.lower()
                if lav in KENDTE_BINDESTREG_FEJL:
                    fund.append((nr, "bindestreg i enkeltord: %s -> %s" % (ord_, KENDTE_BINDESTREG_FEJL[lav])))
            tekst = KLASSE_NAVN.sub(" ", TEKNISK_SAMMENSAT.sub(" ", tekst0))
            for m in ASCII_UDVANDING.finditer(tekst):
                if m.group(0) in filnavne:
                    continue
                fund.append((nr, "ascii-udvanding: " + m.group(0)))
            for m in ENGELSK_FAGORD.finditer(tekst):
                fund.append((nr, "engelsk fagord: " + m.group(0)))
            for m in STEDORD.finditer(tekst):
                fund.append((nr, "stedord i artefakt: " + m.group(0)))
            for token in TOKEN.finditer(tekst):
                t = token.group(0)
                if t.lower() in KENDTE_FEJL:
                    fund.append((nr, "kendt stavefejl: %s -> %s" % (t, KENDTE_FEJL[t.lower()])))
                elif ordliste is not None and "-" not in t and not any(c.isdigit() for c in t):
                    if t.lower() not in ordliste and t.lower() not in TILLADTE_TEKNISKE:
                        fund.append((nr, "ukendt ord (stavning?): " + t))
    return fund


def main():
    p = argparse.ArgumentParser(description="Sprog- og ortografikontrol (værtsløkke)")
    p.add_argument("--rod", default=ROOT, help="rod-mappe der skannes (default: scriptets mappe)")
    p.add_argument("--ordliste", default=None, help="sti til dansk ordliste (valgfrit)")
    args = p.parse_args()

    ordliste_sti = find_ordliste(args.ordliste)
    ordliste = las_ordliste(ordliste_sti) if ordliste_sti else None

    filnavne = set()
    prosa_filer = []
    for dirpath, dirnames, filenames in os.walk(args.rod):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for navn in filenames:
            if navn == SELV:
                continue
            if os.path.splitext(navn)[1].lower() not in PROSA_ENDELSER:
                continue
            sti = os.path.join(dirpath, navn)
            prosa_filer.append(sti)
            filnavne.add(os.path.splitext(navn)[0].lower())
    if ordliste_sti:
        print("ordliste: %s (%d ord)" % (ordliste_sti, len(ordliste)))
    else:
        print("ordliste: ingen system-ordliste fundet — bruger kun indbygget KENDTE_FEJL")

    alle_fund = []
    for sti in prosa_filer:
        for nr, besked in tjek_fil(sti, ordliste, filnavne):
            alle_fund.append("%s:%d: %s" % (os.path.relpath(sti, args.rod), nr, besked))

    if alle_fund:
        print("SPROG/ORTOGRAFI FEJL (%d):" % len(alle_fund))
        for f in alle_fund:
            print("  " + f)
        return 1
    print("sprog og ortografi ok — ingen fund")
    return 0


if __name__ == "__main__":
    sys.exit(main())
