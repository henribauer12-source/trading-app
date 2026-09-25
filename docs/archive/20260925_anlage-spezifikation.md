---
title: Trading-Analyse-App – Anlage-Spezifikation (Kernmodul Anlageberater)
date: 20260925
status: v1.3; bis v1.2 unabhängig geprüft, Befunde eingearbeitet; Ergänzungen v1.3 (A5.1, A5.2) noch nicht unabhängig geprüft
owner: Henri
basis: 20260925_trading-app-plan-v9.md, 20260925_rechenkern-spezifikation-v1.4.md, 20260925_strategie-katalog.md, 20260924_trading-app-qualitaetsstandards.md
superseded_by: ../20260925_anlage-spezifikation_en.md
binding: no (superseded German original, archived 20260925)
---

# Anlage-Spezifikation v1.3 – Kernmodul "Anlegen"

> **Superseded German original — not binding.** Since 20260925 the English text `../20260925_anlage-spezifikation_en.md` is binding. It stops at v1.3 and lacks the v1.4 decisions (starting indices, full calendar years, fund-size currency conversion, KID precedence). Kept for reference only. Do not implement from it.

**Hinweis:** Dieses Dokument spezifiziert ein privates Analysewerkzeug. Es ist keine Anlage- oder Steuerberatung. Die Steuerregeln sind nach bestem Wissen aus Gesetzestext und BMF-Schreiben abgeleitet und vor produktiver Nutzung mit einer Steuerberatung abzugleichen.

## 0. Zweck und Grundsätze

Das Modul "Anlegen" ist der Kern der App. Es beantwortet jeden Monat eine Frage: **Was soll ich mit meinem Geld tun, und warum?** Es übersetzt persönliche Angaben in eine strategische Aufteilung, wählt konkrete Produkte, plant Sparplan und Umschichtungen steueroptimiert, zeigt ehrliche Projektionen und hält alles in einer persönlichen Anlagerichtlinie (IPS) fest.

**Grundsätze:**
1. **Belegte Einfachheit vor Raffinesse.** Die Standardempfehlung ist ein breit gestreutes, kostengünstiges Weltaktien-Portfolio plus Sicherheitsbaustein. Abweichungen (taktische Overlays, Faktoren, Einzelaktien, Gold) sind begrenzt, begründet und nur erlaubt, wenn sie ihre Prüfung bestanden haben.
2. **Die Reihenfolge der Finanzen zählt mehr als die Produktwahl:** teure Schulden, Notgroschen, dann Investieren.
3. **Alles nach Kosten und nach deutscher Steuer.** Eine Maßnahme, die vor Steuern besser ist und nach Steuern schlechter, wird nicht empfohlen.
4. **Unsicherheit wird gezeigt, nicht versteckt.** Projektionen als Bandbreiten in heutigen Euro, nie als Punktprognose.
5. **"Nichts tun" ist eine vollwertige Empfehlung.** Die meisten Monate lautet sie: Sparplan läuft weiter, keine Umschichtung nötig.
6. **Die Entscheidung trifft Henri.** Die App empfiehlt, erklärt und dokumentiert; sie handelt nicht selbstständig.

**Status-Kennzeichnung** wie in der Rechenkern-Spezifikation: VERIFIZIERT (Primärquelle gelesen), REPRODUZIERT, ENTSCHEIDUNG (begründete eigene Festlegung), UNVERIFIZIERT (vor Implementierung prüfen).

**Rundung und Arithmetik:** Alle Steuer- und Geldbeträge mit `Decimal`, nicht mit Gleitkomma (in der Prüfung ergab Gleitkomma Cent-Abweichungen beim Solidaritätszuschlag). Rundungsregeln je Größe in Abschnitt A8.

---

## 1. Gesamtablauf

```
A1 Profil & Ziele ──► A2 Vorbedingungen ──► A3 Aktienquote je Ziel ──► A4 Bausteine & Gewichte
                                                                              │
A11 Anlagerichtlinie (IPS) ◄── A10 Monatsempfehlung ◄── A9 Projektion ◄── A5 Produktauswahl
          │                            ▲                                      │
          └──► A12 Leitplanken         └── A6 Sparplan & Umschichtung ◄───────┘
                                       └── A7 Taktische Overlays (Strategie-Katalog)
                                       └── A8 Steuer-Engine (für A6, A7, A9, A10)
```

Jede Ausgabe ist mit Zeitstempel, Eingabedaten, Parametern und Code-Version gespeichert (Qualitätsstandards 2.4), sodass jede Empfehlung später nachvollziehbar ist.

---

## A1 Profil und Ziele

### A1.1 Eingaben

**Struktur nach den ESMA-Leitlinien zur Geeignetheitsprüfung** (ESMA35-43-3172, anwendbar seit 20231003; Rn. 24: Familienstand, Alter, Beschäftigung, Liquiditätsbedarf, Kenntnisse und Erfahrung, finanzielle Lage einschließlich Verlusttragfähigkeit, Ziele einschließlich Risikotoleranz, Nachhaltigkeitspräferenzen). VERIFIZIERT.

| Nr. | Angabe | Typ | Verwendung |
|---|---|---|---|
| P1 | Geburtsjahr | Zahl | Horizont-Plausibilität, Altersvorsorge-Hinweise (A13) |
| P2 | Nettoeinkommen pro Monat, Einkommensart (fest / schwankend / Nebenjob / Studium) | Zahl, Auswahl | Kapazität (A3.2), Steuerprüfung (A8) |
| P3 | Notwendige Ausgaben pro Monat | Zahl | Notgroschen-Ziel (A2) |
| P4 | Vorhandene liquide Mittel (Girokonto, Tagesgeld) | Zahl | Notgroschen-Status |
| P5 | Schulden mit Zinssatz (Dispo, Kreditkarte, Kredite, BAföG-Darlehen) | Liste | Vorbedingung (A2) |
| P6 | Angehörige, die finanziell von dir abhängen | Ja/Nein | Kapazität |
| P7 | Hängt dein Einkommen am Aktienmarkt oder an einer Branche? | Auswahl | Kapazität, Länderstreuung |
| P8 | Ziele: Name, Betrag (optional), Zieldatum oder "langfristig/Altersvorsorge" | Liste | Horizont je Ziel (A3.1) |
| P9 | Monatliche Sparrate und geplante Steigerung pro Jahr | Zahl, % | Sparplan (A6), Projektion (A9) |
| P10 | Einmalbeträge (vorhanden oder erwartet) | Liste | Umsetzung (A6.4) |
| P11 | Verlustfrage in Euro (A1.2) | Zahl | Toleranz (A3.3) |
| P12 | Risikotoleranz-Skala (A1.3) | Fragebogen | Toleranz (A3.3) |
| P13 | Zwei Verständnisfragen (A1.4) | Auswahl | Konsistenz, Lernmodul |
| P14 | Steuerliche Angaben: Kirchensteuer (keine / 8 % / 9 %), voraussichtliches zu versteuerndes Einkommen, Depot bei deutscher oder ausländischer Bank | Auswahl, Zahl | A8 |
| P15 | Präferenzen: ausschüttend/thesaurierend, Nachhaltigkeit, Gold ja/nein, Einzelaktien ja/nein, Sparplan-fähig beim Broker | Auswahl | A4, A5 |
| P16 | Beziehst du BAföG? | Ja/Nein | Vermögensgrenze (A6.3) |
| P17 | Bist du beitragsfrei familienversichert? | Ja/Nein | Einkommensgrenze (A6.3) |

### A1.2 Verlustfrage in Euro

Die App zeigt einen Balken mit dem voraussichtlichen Depotwert in 5 Jahren (B5, nach A9 Basisszenario) und darunter denselben Wert nach einem Rückgang um 50 %. Frage: **"Bis zu welchem Verlust in Euro würdest du durchhalten, ohne zu verkaufen?"** Eingabe L€.
Begründung: ESMA-Leitlinien Rn. 44, 46, 48 verlangen praktische Verlustszenarien mit "konkreten Zahlen" statt Selbsteinschätzung. VERIFIZIERT.

### A1.3 Risikotoleranz-Skala

- Vollständige 13-Fragen-Skala nach Grable & Lytton (1999); Reliabilität in der Originalstudie α = 0,75, in der 15-Jahres-Auswertung (n = 160.279) α = 0,77. VERIFIZIERT
- **Nur vollständig** verwenden (eine Teilmenge ist nicht validiert) und als Einordnung, nicht als alleinige Grundlage: Fragebögen erklären nur einen kleinen Teil des tatsächlichen Risikoverhaltens (Klement, 2015: 13,1 %). VERIFIZIERT
- **Nutzungsrechte** der Skala vor Implementierung prüfen (UNVERIFIZIERT). Falls nicht nutzbar: Skala entfällt, A3.3 stützt sich allein auf die Verlustfrage

### A1.4 Verständnis- und Konsistenzprüfung

- Zwei Verständnisfragen (z. B. "Was passiert mit einem Welt-ETF, wenn die Aktienmärkte 40 % fallen?"; "Was bedeutet eine Aktienquote von 80 %?"), nach ESMA Rn. 52
- Widerspruchsprüfung nach ESMA Rn. 51: z. B. hohe Verlustbereitschaft bei Horizont < 3 Jahre, oder hohe Skalenwerte bei falsch beantworteten Verständnisfragen → Hinweis und Rückfrage, das niedrigere Ergebnis gilt bis zur Klärung. VERIFIZIERT (Struktur), Regeln ENTSCHEIDUNG

### A1.5 Wiederholung

- Jährliche Überprüfung des Profils (Erinnerung im IPS-Termin)
- **Keine Neuprofilierung während eines Drawdowns** ohne Wartefrist (A12): Risikoaversion steigt nach Krisen deutlich an (Guiso, Sapienza & Zingales, 2018), eine Senkung der Aktienquote im Tief realisiert Verluste. VERIFIZIERT (Befund), Regel ENTSCHEIDUNG

---

## A2 Vorbedingungen (Reihenfolge der Finanzen)

| Schritt | Bedingung | Empfehlung |
|---|---|---|
| V1 | Schulden mit Zinssatz über 5 % p. a. nominal (Dispo, Kreditkarte, Konsumkredit) | Tilgung vor dem Investieren; höchstens ein symbolischer Sparplan (z. B. 25 €) zur Gewohnheitsbildung |
| V2 | Liquide Mittel < Starter-Reserve R_S = max(1.000 €; 1 × P3) | 100 % der Sparrate in die Reserve |
| V3 | Liquide Mittel < Ziel-Reserve R_Z = max(R_S; 3 × P3), bzw. max(R_S; 6 × P3) bei schwankendem Einkommen oder Angehörigen | 50 % der Sparrate in die Reserve, 50 % in den Anlageplan (auf die Töpfe verteilt wie ihre geplanten Sparraten) |
| V4 | Reserve erreicht | 100 % der Sparrate in den Anlageplan |

- **Begründung V1:** Tilgung bringt eine **sichere** Rendite in Höhe des Zinssatzes. Ab etwa 5 % nominal liegt sie in der Größenordnung der **unsicheren** Aktienrendite (Basisannahme 4 % real im Median, bei rund 2 % Inflation etwa 6 % nominal, A9.2) und ist ihr risikobereinigt überlegen. Schwelle ENTSCHEIDUNG
- **Reserve** liegt auf Tagesgeld bei einer Bank mit gesetzlicher Einlagensicherung (100.000 € je Einleger und Bank; VERIFIZIERT, BMF). Sie zählt **nicht** zur Aktienquote und nicht zum Depot
- **BAföG-Darlehen** (zinslos) sind keine teuren Schulden (V1 gilt nicht)
- **Evidenz:** Notgroschen gehen mit höherem finanziellem Wohlbefinden einher (Vanguard-Umfrage 2024, korrelativ, nicht begutachtet); die Verbraucherzentrale empfiehlt 2–3 Nettogehälter. Eine begutachtete Herleitung einer optimalen Monatszahl gibt es nicht. VERIFIZIERT (Quellen), Schwellen ENTSCHEIDUNG

---

## A3 Strategische Aktienquote je Ziel

Jedes Ziel (P8) bekommt einen eigenen Topf p mit Horizont h_p (Jahre bis zur geplanten Entnahme) und eigener Risikoquote q_p. Standardziel ohne Datum: "Langfristiges Vermögen / Altersvorsorge" (h = 30).

**q_p = min(q_Horizont(h_p), q_Kapazität, q_Toleranz,p), abgerundet auf 10 Prozentpunkte.** Die Risikoquote q_p ist das Budget für Welt-Aktien und alle Satelliten (A4); die angezeigte reine Aktienquote kann darunter liegen, wenn Gold enthalten ist.

### A3.1 Horizont-Obergrenze (Gleitpfad)

Stützpunkte, dazwischen **monatlich linear interpoliert**:

| Horizont h | q_Horizont |
|---|---|
| ≥ 15 Jahre | 100 % |
| 10 Jahre | 80 % |
| 5 Jahre | 60 % |
| 3 Jahre | 30 % |
| ≤ 1 Jahr | 0 % |

- q_Horizont wird **monatlich** neu berechnet. Weil q_p auf 10 Prozentpunkte abgerundet wird, sinkt die wirksame Quote in Stufen von 10 Prozentpunkten; die Interpolation bestimmt, **wann** die nächste Stufe fällig wird (zwischen 10 und 5 Jahren etwa alle 30 Monate, zwischen 5 und 1 Jahr etwa alle 8 Monate). Das verhindert eine einzelne große Umschichtung an einem Stichtag
- Umsetzung einer Stufe: zuerst über neue Sparraten (A6.1); Verkäufe nach A6.2 einschließlich der Gleitpfad-Regel für die letzten 36 Monate, verteilt über Steuerjahre, soweit es der Zeitplan erlaubt, um jeweils den Sparer-Pauschbetrag zu nutzen
- **Begründung der Richtung:** Reale Aktien-Drawdowns über 70 % kamen vor (Dimson, Marsh & Staunton, Yearbook 2026). US-Aktien lagen nach 1929 real bis 1945 unter ihrem Hoch (etwa 15,5 Jahre); der japanische Nikkei-Kursindex (ohne Dividenden) brauchte 34 Jahre bis zum Stand von 1989. Über 30 Jahre hatte ein breit gestreuter Anleger in 39 Industrieländern eine Wahrscheinlichkeit von 12 %, real zu verlieren (Anarkulova, Cederburg & O'Doherty, 2022); im zugehörigen Working Paper "Long-Horizon Losses" 13 % für inländische und 4 % für internationale Aktien. VERIFIZIERT (Befunde)
- Stützpunkte ENTSCHEIDUNG (keine Einzelquelle)

### A3.2 Kapazitäts-Obergrenze

- Einkommen schwankend (P2) oder Angehörige (P6): q_Kapazität = 70 %
- Einkommen stark mit dem Aktienmarkt korreliert (P7): q_Kapazität = 80 % und Hinweis auf internationale Streuung (Anarkulova et al., Working Paper: bei Korrelation 0,5 zwischen Einkommen und Heimatmarkt sinkt der optimale Heimatanteil von 33 % auf 18 %)
- sonst 100 %
- Stufen ENTSCHEIDUNG; Richtung belegt: Humankapital wirkt bei jungen Menschen mit sicherem Einkommen wie eine Anleihe (Cocco, Gomes & Maenhout, 2005). VERIFIZIERT

### A3.3 Toleranz-Obergrenze (gemeinsam über alle Töpfe)

1. **B5 je Topf** deterministisch und ohne Zirkelschluss: B5_p = heutiger Wert des Topfs + geplante Einzahlungen der nächsten 5 Jahre, verzinst mit 4 % real bei **q = 100 %**. Das ist die obere Schätzung und damit die vorsichtige Wahl für die Grenze
2. **D_Stress** = realer Stress-Drawdown des Welt-Aktien-Portfolios; Platzhalter **0,60**, bis er in Phase 1 aus der gepoolten Historie (A9.1) als größter realer Rückgang des Weltportfolios kalibriert ist (UNVERIFIZIERT bis dahin)
3. **Verteilung des Verlustbudgets L€ über die Töpfe**, längster Horizont zuerst (dort ist Risiko am besten tragbar): für Töpfe in absteigender Reihenfolge von h_p gilt q_Toleranz,p = min(1; L_rest / (D_Stress × B5_p)), danach L_rest = L_rest − q_Toleranz,p × D_Stress × B5_p
4. Liegt die Grable-Lytton-Punktzahl im unteren Drittel, wird jedes q_Toleranz,p um 20 Prozentpunkte gesenkt, nicht unter 0
5. **Untergrenze:** Ist Σ_p B5_p < 1.000 €, entfällt die Toleranzgrenze; die App zeigt stattdessen einen Hinweis, die Verlustfrage nach einem Jahr zu wiederholen
6. **Stabilität:** q_Toleranz,p und q_Kapazität werden nur beim jährlichen Profil-Termin neu berechnet; eine dadurch ausgelöste Änderung von q_p wird nur wirksam, wenn sie mindestens 10 Prozentpunkte beträgt (Hysterese). **q_Horizont ist davon ausgenommen** und wird monatlich ausgewertet (A3.1), damit die Absenkung vor dem Zieldatum nicht bis zu einem Jahr hinterherläuft. So sinkt die Quote nicht jedes Jahr schrittweise, nur weil das Depot wächst; die App fragt stattdessen, ob L€ noch passt
- ENTSCHEIDUNG

### A3.4 Standardergebnis und Einordnung

Für ein langfristiges Ziel (≥ 15 Jahre), stabiles Einkommen, keine teuren Schulden, vollständige Reserve und ausreichende Verlustbereitschaft ergibt sich **q = 100 % Risikobudget im Depot**, mit der Reserve als Sicherheitsbaustein außerhalb. Bezogen auf alle liquiden Mittel liegt die Aktienquote zu Beginn deutlich niedriger (Beispiel: Reserve 3.000 €, Depot 1.000 € ergibt 25 %) und steigt, sobald das Depot die Reserve deutlich übersteigt.

Zwei Sichtweisen werden im Lernmodul offen dargestellt:
- **Lebenszyklus-Sicht** (Cocco et al., 2005; Vanguard-Gleitpfad 2022: etwa 90 % Aktien bis Alter 40): Aktienquote sinkt über das Leben
- **Vollaktien-Sicht** (Anarkulova, Cederburg & O'Doherty, Working Paper "Beyond the Status Quo", erstmals 2023, überarbeitet 2026, nicht begutachtet): 100 % Aktien über das ganze Leben, davon ein Drittel Heimatmarkt, liefert im 39-Länder-Bootstrap mehr Vermögen bei geringerer Wahrscheinlichkeit, im Alter das Geld aufzubrauchen (7,0 % gegenüber 19,7 % beim Zieldatumsfonds); die Autoren nennen selbst einen möglichen Drawdown im Ruhestand von 74 % (95. Perzentil) und das Risiko, im Crash aufzugeben. Kritik (Asness, nur Presse): Diversifikation über Anlageklassen ist pro Risikoeinheit überlegen
- VERIFIZIERT (Zahlen), Standardregel ENTSCHEIDUNG

---

## A4 Bausteine und Gewichte

### A4.1 Kern (immer)

| Baustein | Inhalt | Anteil |
|---|---|---|
| K1 Aktien Welt | Ein ETF auf einen marktkapitalisierungsgewichteten Weltindex inklusive Schwellenländer (MSCI ACWI oder FTSE All-World) **oder** Industrieländer + Schwellenländer im Marktgewicht (etwa 88/12) | q_p − Σ Satelliten |
| K2 Sicherheit im Depot | Nach Horizont des Topfs: < 3 Jahre €STR-Geldmarkt-ETF (bzw. Tagesgeld außerhalb des Depots); 3–10 Jahre EUR-Staatsanleihen oder globale Anleihen EUR-abgesichert, Laufzeit passend zum Horizont; > 10 Jahre (nur falls q < 100 %) EUR-Staatsanleihen oder globale Anleihen EUR-abgesichert | 1 − q_p |

- **Marktgewicht statt Heimatbias:** Anleger weltweit übergewichten ihren Heimatmarkt; ein globaler Index ist für einen deutschen Anleger bereits die Korrektur (Vanguard, 2021; French & Poterba, 1991). VERIFIZIERT
- **Schwellenländer-Übergewichtung** (z. B. 70/30) ist eine aktive Wette ohne robuste Evidenz; nur als ausdrückliche Nutzerwahl, als Satellit gezählt. Regel ENTSCHEIDUNG
- **Anleihen in Fremdwährung nur EUR-abgesichert:** Währungsabsicherung senkt bei Anleihen fast immer das Risiko (Vanguard, 2026). VERIFIZIERT
- **Stand der Indizes (Factsheets 20260831):** MSCI World 1.280 Werte, USA 72,14 %, Top 10 26,61 %; MSCI ACWI 2.458 Werte, USA 63,59 %, Schwellenländer etwa 11,9 %; FTSE All-World 4.264 Werte, USA 61,71 %. Die App zeigt die aktuelle Länder- und Konzentrationsstruktur des gewählten Index an (Klumpenhinweis USA und Top 10). VERIFIZIERT

### A4.2 Satelliten (optional, nur auf ausdrücklichen Wunsch)

Alle Satelliten eines Topfs zusammen höchstens **20 % des Risikobudgets q_p** (also 0,20 × q_p des Topfs). Obergrenzen je Satellit ebenfalls relativ zu q_p.

| Satellit | Obergrenze (Anteil an q_p) | Evidenz | Bedingung |
|---|---|---|---|
| S-Gold | 10 % | Gold ist über praktikable Horizonte ein unzuverlässiger Inflationsschutz (Erb & Harvey, 2013); Nutzen als Streuung, nicht als Renditequelle | Nur physisch hinterlegtes Gold-ETC mit **ausschließlichem** Anspruch auf Lieferung oder auf den Erlös des hinterlegten Goldes (BMF 20250514 Rn. 57); steuerfrei nach > 1 Jahr (A8.7) |
| S-Faktor | 10 % | Faktorprämien schrumpfen nach Veröffentlichung um etwa 58 % (McLean & Pontiff, 2016); 65 % von 452 Anomalien scheitern schon an t = 1,96 (Hou, Xue & Zhang, 2020); Smart-Beta-Indizes zeigen nach ETF-Auflage keinen Mehrwert mehr (Huang, Song & Xiang); US-Value lag 2007–2020 rund −56 % zurück; Profitabilität (Novy-Marx, 2013) am robustesten | Nur Qualität/Profitabilität oder Multi-Faktor; schriftliche IPS-Verpflichtung zu ≥ 15 Jahren Haltedauer |
| S-Einzelaktien | 10 % gesamt, 2 % je Titel | 57 % der US-Aktien schnitten über ihre Lebenszeit schlechter ab als einmonatige T-Bills; die gesamte Nettowertschöpfung seit 1926 stammt aus 4 % der Aktien (Bessembinder, 2018) | Nur wenn der Topf ≥ 25.000 € ist (sonst liegen 2 % unter üblichen Ordergrößen); jede Position wird gegen K1 gemessen; Basisrate im Kaufdialog angezeigt |
| S-Taktik | 10 % | Strategie-Katalog L3 (Rotation), S1 (Trendfolge) als eigenständige Teilportfolios mit eigenem Universum | Nur Strategien, die ihre Gates **und** das Nachsteuer-Gate (A8.11) bestanden haben |
| S-EM-Übergewicht | 10 % | keine robuste Evidenz | nur Nutzerwahl |

VERIFIZIERT (Zahlen), Obergrenzen ENTSCHEIDUNG. Die Overlays aus A7 verändern Gewichte zeitweise, sind keine Satelliten und zählen nicht zur 20-%-Grenze.

### A4.3 Zielgewichte

Für jeden Topf mit Risikobudget q_p:
- w(K2) = 1 − q_p
- Σ_j w(S_j) ≤ 0,20 × q_p, jeder Satellit ≤ seiner Obergrenze × q_p
- w(K1) = q_p − Σ_j w(S_j)
- Angezeigt werden getrennt: Aktienquote = w(K1) + Aktien-Satelliten; Goldanteil; Sicherheitsanteil
- ENTSCHEIDUNG

### A4.4 Töpfe und Unterdepots

FIFO gilt steuerlich **je Depot, wobei ein Unterdepot als eigenes Depot zählt** (BMF 20250514 Rn. 97–98; VERIFIZIERT durch die Prüfung). Töpfe, die nur in der App existieren, teilen sich im selben Depot die FIFO-Reihenfolge. Die App empfiehlt daher **ein Unterdepot je Topf**; ohne Unterdepots führt sie FIFO über das gesamte Depot und weist darauf hin, dass ein Verkauf "aus Topf A" steuerlich die ältesten Anteile des ganzen Depots betrifft.

---

## A5 Produktauswahl (konkrete ETFs und ETCs)

### A5.1 Datenbeschaffung (regelkonform)

- **Kuratierte Kandidatenliste** von etwa 30 ISINs über alle Bausteine, **vierteljährlich** aktualisiert aus frei veröffentlichten Pflichtdokumenten: PRIIPs-Basisinformationsblatt (KID) und Factsheet des Emittenten, manuell oder als einzelner Download öffentlicher PDFs mit niedriger Frequenz
- Je Feld gespeichert: Wert, Quell-URL, Stand-Datum, Abrufdatum (bitemporal, K2)
- **Zeitachsen und Vorrang** (v1.3): Point-in-time-Schlüssel ist das **Abrufdatum**, nicht das Stand-Datum; ab dem Abruf gilt ein Wert als bekannt. Das ist konservativ: Die tatsächliche Veröffentlichung liegt zwischen Stand und Abruf und ist aus dem Dokument meist nicht ablesbar. Ein Abruf vor dem Stand-Datum ist unzulässig. Eine Korrektur ist ein neuer Eintrag mit späterem Abrufdatum; nichts wird überschrieben. Sind zu einem Feld mehrere Werte bekannt, gilt der mit dem jüngsten Stand-Datum, bei gleichem Stand der zuletzt abgerufene. Jahreswerte (Tracking-Differenz je Kalenderjahr) tragen ihr Jahr und können kein Stand-Datum vor dem 31.12. dieses Jahres haben. ENTSCHEIDUNG
- **Prüfstatus je Wert** (v1.3): VERIFIZIERT, wenn der Wert im Primärdokument gelesen wurde (KID, Factsheet, Verkaufsprospekt, Jahresbericht, Veröffentlichung des Emittenten oder der Börse, Gesetzestext); sonst UNVERIFIZIERT (zweite Hand, etwa ein Vergleichsportal, oder noch nicht abgeglichen). Werte zweiter Hand dürfen gespeichert werden, sind aber nie VERIFIZIERT. ENTSCHEIDUNG
- **Verboten:** automatisierte Abfragen bei justETF (AGB § 3.1 untersagt "Einsatz von Programmen zur automatisierten Kursabfrage") und Vanguard (Nutzungsbedingungen untersagen automatisierten Zugriff); undokumentierte interne APIs von Emittenten (z. B. iShares). VERIFIZIERT (Recherche; von der Prüfung nicht erneut geprüft)
- **Kurse:** verzögerte Daten der Deutschen Börse (MiFIR-Pflichtveröffentlichung, JSON-Download) nach Prüfung der Lizenzbedingungen für die private Nutzung (UNVERIFIZIERT), sonst kostenlose Quellen aus dem Rechenkern bzw. Broker-Export
- Identifier-Abgleich ISIN ↔ Börsenkürzel über OpenFIGI (kostenlos, 25 Anfragen pro Minute ohne Schlüssel; Nutzungsbedingungen UNVERIFIZIERT)

### A5.2 Harte Filter (ja/nein je Baustein)

1. UCITS-Fonds bzw. bei Gold ein ETC deutschen Rechts mit ausschließlichem Liefer- oder Erlösanspruch auf hinterlegtes Gold; an Xetra oder einem deutschen Handelsplatz handelbar; KID auf Deutsch vorhanden
2. Index passt zum Baustein (Tabelle A5.5)
3. Fondsvolumen ≥ 100 Mio. € (Break-even-Größe laut Branchenangaben, Lipper 2025, VERIFIZIERT); für K1 und Geldmarkt ≥ 500 Mio. € (ENTSCHEIDUNG; eine Fondsschließung realisiert in Deutschland Gewinne und beendet den Steueraufschub)
4. Mindestens 3 volle Kalenderjahre Historie; jüngere Fonds nur mit Kennzeichnung "neu" und Bewertung der Nettokosten über die TER mit 5 Punkten Abschlag
5. Aktien-ETFs erfüllen die Aktienfonds-Definition (> 50 % Kapitalbeteiligungen, § 2 Abs. 6 InvStG) → 30 % Teilfreistellung. VERIFIZIERT
6. Anleihen in Fremdwährung: EUR-abgesichert
7. Optional: beim Broker des Nutzers sparplanfähig (P15)

**Auswertung** (v1.3): Jede Prüfung endet mit *erfüllt*, *verletzt* oder *offen*. Offen ist sie, wenn der Wert zum Stichtag fehlt oder UNVERIFIZIERT ist: Ein Wert zweiter Hand lässt einen Filter nie bestehen, schließt aber auch nicht endgültig aus. Zulässig ist ein Produkt nur, wenn keine Prüfung verletzt und keine offen ist. Eine Ausnahme würde einen einzigen ungeprüften Wert die Auswertung aller Kandidaten blockieren lassen; eine bloße Warnung ließe das Produkt durch. Präzisierungen:
- Zu 1: nicht an Xetra handelbar → offen, weil ein anderer deutscher Handelsplatz zulässig ist, aber nicht als Feld erfasst wird
- Zu 2: mechanisch nur, wo A5.5 konkrete Indizes nennt (K1, K2 Geldmarkt); der Indexname wird dafür in der Schreibweise von A5.5 gespeichert. Wo A5.5 nur eine Indexfamilie nennt (K2 Anleihen, S-Gold, S-Faktor), bleibt die Prüfung offen, bis A5.5 konkrete Indizes nennt. Die Alternative MSCI World + MSCI EM (A5.4, auf Nutzerwunsch) ist nicht abgebildet
- Zu 4: gezählt werden die Kalenderjahre, die vollständig zwischen Auflagedatum und Stichtag liegen; das laufende Jahr zählt nie. Jüngere Fonds sind nicht ausgeschlossen, sondern "neu"
- Zu 5: gilt für K1 und S-Faktor. Zu 6: gilt für K2 Globale Anleihen
- Zu 7: nutzerbezogen (P15), kein Teil der Instrument-Stammdaten und dort nicht geprüft
- ENTSCHEIDUNG

### A5.3 Bewertung auf festen Skalen (0–100)

**Vergleichsgruppe:** nur Fonds auf **denselben Index** (Tracking-Differenzen gegen verschiedene Indizes sind nicht vergleichbar). Die Wahl zwischen Indizes ist eine eigene Entscheidung (A5.4).

**Feste, absolute Skalen** statt Min-Max-Normierung (damit kleine Unterschiede bei wenigen Kandidaten nicht künstlich aufgebläht werden und das Hinzufügen eines Fonds die übrigen nicht umsortiert). Tracking-Differenz TD = Fonds-NAV-Gesamtrendite − Index-Nettogesamtrendite in Prozentpunkten pro Jahr (positiv = Fonds besser), gerundet auf 0,05 Prozentpunkte (**Wesentlichkeitsschwelle**: kleinere Unterschiede gelten als gleich).

| Kriterium | Gewicht | Punkte | Begründung |
|---|---|---|---|
| Nettokosten (TD, Mittel der letzten 3 Kalenderjahre) | 40 % | clamp(50 + 250 × TD; 0; 100): TD 0 → 50, +0,20 → 100, −0,20 → 0 | TD enthält TER, Quellensteuer, Wertpapierleihe und Handelskosten; iShares Core MSCI World (TER 0,20 %) übertraf seinen Nettoindex 2016–2025 in jedem Jahr, im Mittel um 0,083 Prozentpunkte (Factsheet); Kosten sind das verlässlichste Merkmal (Morningstar, 2024). VERIFIZIERT |
| Stabilität der TD | 5 % | clamp(100 − 500 × Standardabweichung der 3 TD; 0; 100) | Drei Werte sind wenig belastbar, daher geringes Gewicht |
| Fondsgröße | 20 % | clamp(50 × log10(Volumen / 100 Mio. €); 0; 100): 100 Mio. → 0, 1 Mrd. → 50, 10 Mrd. → 100 | Schließungsrisiko |
| Liquidität | 10 % | clamp(100 − 5 × XLM in Basispunkten; 0; 100) | Handelskosten; kostenlos veröffentlicht. VERIFIZIERT |
| Struktur und Gegenparteirisiko | 10 % | physisch vollständig 100, physisch optimiert 90, synthetisch mit mehreren Gegenparteien und transparenten Sicherheiten 75, synthetisch mit einer Gegenpartei 60 | UCITS begrenzt das Gegenparteirisiko auf 10 % des Fondsvermögens (Art. 52 Richtlinie 2009/65/EG, VERIFIZIERT). Der Quellensteuervorteil synthetischer ETFs steckt bereits in der TD und wird nicht zusätzlich belohnt |
| Historie | 5 % | 10 × min(Jahre seit Auflage; 10) | Belastbarkeit der TD |
| Transaktionskosten laut KID | 5 % | clamp(100 − 500 × Transaktionskosten in Prozentpunkten; 0; 100) | standardisiert, vergleichbar |
| Nutzerpräferenz | 5 % | 100, wenn thesaurierend/ausschüttend wie gewünscht, sonst 0 | steuerlich im Wesentlichen neutral (A8.4) |

- **Gold:** statt TD die jährlichen Haltekosten: clamp(100 − 200 × Kosten in %; 0; 100) (z. B. 0 % → 100, 0,36 % → 28), plus Lieferbedingungen als Hinweis
- **Geldmarkt:** TD gegen €STR; Gegenpartei-Gewicht 15 % (zulasten der Größe)
- Alle Skalen und Gewichte sind ENTSCHEIDUNG, gestützt auf die genannte Evidenz; sie werden in der App angezeigt. **Bindungen:** höhere Nettokosten-Punkte, dann größeres Volumen

### A5.4 Indexwahl für K1

MSCI ACWI und FTSE All-World sind für diesen Zweck gleichwertig (sehr ähnliche Länder- und Sektorstruktur). Die App bestimmt je Index den besten Kandidaten (A5.3) und wählt zwischen beiden nach TER; unterscheiden sich die TER um weniger als 0,05 Prozentpunkte, nach Fondsvolumen. ACWI IMI (mit Nebenwerten) und World + EM im Marktgewicht sind gleichwertige Alternativen auf Nutzerwunsch. ENTSCHEIDUNG

### A5.5 Index-Zuordnung je Baustein

| Baustein | Zulässige Indizes |
|---|---|
| K1 Aktien Welt | MSCI ACWI, MSCI ACWI IMI, FTSE All-World; alternativ MSCI World + MSCI EM im Marktgewicht |
| K2 Geldmarkt | €STR |
| K2 EUR-Staatsanleihen | Euro-Staatsanleihenindex (alle Laufzeiten oder Laufzeitbänder) |
| K2 Globale Anleihen | Global Aggregate oder Global Government, EUR-abgesichert |
| S-Gold | physisches Gold, lieferbar |
| S-Faktor | MSCI World Quality bzw. Multi-Faktor-Indizes |

### A5.6 Produktwechsel

Ein bestehendes Produkt wird nicht allein wegen eines besseren Punktwerts ersetzt. **Neue Sparraten gehen immer ins beste Produkt.** Ein Verkauf zum Wechsel wird empfohlen, wenn:
- das alte Produkt einen harten Filter verletzt (z. B. Schließungsankündigung), oder
- das **Endvermögen nach Steuern am Horizont des Topfs** mit Wechsel um mehr als 0,5 % der Position (mindestens 50 €) höher ist als ohne Wechsel. Berechnung mit A8: "Behalten" = alte Nettokosten bis zum Horizont, Steuer beim Verkauf am Ende; "Wechseln" = Steuer jetzt (nach Nutzung von Pauschbetrag und ggf. Günstigerprüfung), neue Nettokosten, Steuer am Ende. Die Steuer beim Wechsel ist dabei überwiegend eine **Vorauszahlung** (sie wäre am Ende ohnehin fällig), kein verlorener Betrag; der Nachteil liegt im verlorenen Steueraufschub
- ENTSCHEIDUNG

### A5.7 Domizil

Für die deutsche Besteuerung ist das Fondsdomizil neutral (§§ 2, 16, 18, 20 InvStG gelten unabhängig vom Sitz; VERIFIZIERT). Relevant ist es nur über die Quellensteuer auf Fondsebene (irische Fonds 15 % auf US-Dividenden, luxemburgische und deutsche 30 %; UNVERIFIZIERT), die sich in der TD niederschlägt.

---

## A6 Sparplan, Einmalbeträge und Umschichtung

### A6.1 Aufteilung der monatlichen Sparrate (Cashflow-Rebalancing)

Gegeben: Zielgewichte w_i (Σ w_i = 1), aktuelle Werte V_i, Gesamtwert V = Σ V_i, Einzahlung C ≥ 0.
1. Zielwerte nach Einzahlung: T_i = w_i × (V + C)
2. Fehlbeträge: F_i = max(0; T_i − V_i). Da Σ T_i = V + C, gilt immer Σ F_i ≥ C
3. Einzahlung x_i = C × F_i / Σ F_i; bei Σ F_i = 0 (nur möglich bei C = 0) ist x_i = 0. Es gilt x_i ≤ F_i, eine Überschreitung des Ziels ist ausgeschlossen
4. **Mindestbetrag** je Sparplanposition (Nutzereinstellung, z. B. 25 €): Positionen mit x_i unter dem Mindestbetrag erhalten in diesem Monat 0; ihr Betrag wird proportional zu den übrigen x_j verteilt. Die zurückgestellten Beträge werden je Position als "offener Anspruch" mitgeführt und in dem Monat ausgezahlt, in dem Anspruch + x_i den Mindestbetrag erreicht, damit keine Position dauerhaft leer ausgeht
5. **Umsetzung als Dauerauftrag:** Die App verfolgt den tatsächlich beim Broker eingerichteten Sparplan (Nutzereingabe) und schlägt eine Änderung nur vor, wenn sich die berechnete Aufteilung um mehr als 10 % der Sparrate davon unterscheidet (halbe Summe der absoluten Differenzen je Position)
- Begründung: Einzahlungen in untergewichtete Bausteine erreichen den Großteil der Risikokontrolle zu deutlich geringeren Kosten (Vanguard, 2010; 2022); in Deutschland vermeiden sie zudem Steuern auf Verkäufe. VERIFIZIERT (Befund, Industriequellen)

### A6.2 Überprüfung, Verkaufs-Rebalancing und Entnahmen

- **Einmal jährlich** (Termin im IPS) prüft die App die Gewichte nach den Zuflüssen des Jahres
- Eine Umschichtung durch Verkauf wird empfohlen, wenn ein Baustein um mehr als **min(5 Prozentpunkte; 25 % seines Zielgewichts)** vom Ziel abweicht (die relative Grenze gilt für kleine Bausteine wie Satelliten)
- Außerhalb des Prüftermins wird eine solche Abweichung nur **angezeigt**; eine Handlungsempfehlung gibt es dann nur, wenn ein Satellit seine Obergrenze um mehr als 25 % überschreitet, oder nach der Gleitpfad-Regel
- **Gleitpfad-Regel für die letzten 36 Monate** eines Topfs: Die App prüft den Topf **quartalsweise**. Senkt eine neue 10-Prozentpunkt-Stufe von q_Horizont (A3.1) die Zielquote und reichen die Sparraten der nächsten 3 Monate nicht aus, um die Abweichung unter das Band zu bringen, wird im selben Quartal ein Verkauf empfohlen. Spätestens **12 Monate vor dem Zieldatum** ist q_p = 0 umgesetzt; ein Verkauf mit Steuer wird dafür nicht in das nächste Steuerjahr verschoben. Begründung: Ein Rückgang von 50 % im letzten Jahr lässt sich vor der Entnahme nicht mehr aufholen; die Steuerersparnis durch Verteilen ist dagegen klein. ENTSCHEIDUNG
- Verkäufe **steueroptimiert** (A8.10) und über mehrere Steuerjahre verteilt, wenn die Abweichung nicht dringlich ist
- **Entnahmen** (C < 0): Verkauf zuerst aus übergewichteten Bausteinen, danach in der Reihenfolge der geringsten Steuer je entnommenem Euro (A8.10)
- Begründung: jährliche Prüfung mit Schwelle kommt mit sehr wenigen Transaktionen aus und erreicht nahezu dieselbe Risikokontrolle wie häufiges Rebalancing; jährliches Rebalancing ist für Anleger ohne Verlustverrechnungsstrategie günstig (Vanguard, 2010; 2022; Industriequellen, akademische Evidenz dünn)
- Mit nur einem Welt-ETF ohne Sicherheitsbaustein im Depot entfällt Rebalancing

### A6.3 Sparer-Pauschbetrag, Günstigerprüfung und steuerfreie Gewinnrealisierung

- Die App schätzt die Kapitalerträge des Jahres (Ausschüttungen, Vorabpauschale, geplante Verkäufe) und empfiehlt die Verteilung des Freistellungsauftrags (1.000 €) auf die deutschen Banken bzw. prüft den Anspruch auf eine NV-Bescheinigung (A8.3)
- **Steuerfreie Gewinnrealisierung:** Bleibt am Jahresende steuerfreier Spielraum, kann ein Verkauf mit anschließendem Rückkauf den Einstandskurs anheben.
  - **Zulässigkeit:** Ein Verkauf und Rückkauf am selben Tag zu unterschiedlichen Kursen ist kein Gestaltungsmissbrauch nach § 42 AO (BFH IX R 60/07 vom 20090825); das BMF-Schreiben vom 20250514 enthält keine Wash-Sale-Regel. VERIFIZIERT (durch die Prüfung). Bedingung: Ausführung über die Börse, keine abgesprochenen Geschäfte zum selben Kurs mit demselben Gegenüber
  - **Spielraum:** mindestens der ungenutzte Sparer-Pauschbetrag; **bei Günstigerprüfung zusätzlich der ungenutzte Grundfreibetrag** (für Werkstudenten mit geringem Einkommen oft der größere Hebel). Die App berechnet den Spielraum mit A8.3
  - **Stückzahl:** lotweise nach FIFO (A4.4); um X € steuerpflichtigen Ertrag aus einem Aktien-ETF zu realisieren, ist ein Rohgewinn von X / 0,7 nötig (Teilfreistellung)
  - **Nutzen:** Die ersparte spätere Steuer fällt erst beim späteren Verkauf an und nur, wenn dieser steuerpflichtig wäre; sie wird mit 3 % p. a. abgezinst und mit der Wahrscheinlichkeit gewichtet, dass der spätere Verkauf steuerpflichtig ist (Standard 0,8, Nutzereinstellung). Empfehlung nur, wenn dieser Nutzen die Handelskosten plus Spread um mindestens das Dreifache übersteigt. ENTSCHEIDUNG
- **Nebenwirkungen prüfen** (P16, P17): Kapitalerträge können zum Gesamteinkommen für die beitragsfreie **Familienversicherung** in der Krankenversicherung zählen (§ 10 SGB V); Depot und Reserve zählen als **Vermögen beim BAföG** (§§ 27–29 BAföG). Die App zeigt die jeweiligen Grenzen, sobald sie verifiziert sind, und warnt vor einer Überschreitung. UNVERIFIZIERT (Grenzbeträge)

### A6.4 Einmalbeträge

- **Standard: sofort investieren**, aufgeteilt nach A6.1 mit C = Einmalbetrag
- Begründung: Einmalanlage schlug gestaffeltes Investieren über 12 Monate in etwa zwei Dritteln der historischen Fälle (Vanguard 2012: USA 67 %, UK 67 %, Australien 66 %; durchschnittlicher Vorsprung 2,3 / 2,2 / 1,3 %); gestaffeltes Investieren ist theoretisch unterlegen (Constantinides, 1979). VERIFIZIERT
- **Option:** Aufteilung über 6 oder 12 Monate als bewusste Verhaltensentscheidung; die App zeigt vorher, dass sie in etwa zwei Dritteln der Fälle Rendite kostet
- Ein monatlicher Sparplan aus dem Einkommen ist kein gestaffeltes Investieren, sondern Investieren, sobald Geld da ist

### A6.5 Sparraten-Steigerung

Optional nach "Save More Tomorrow" (Benartzi & Thaler, 2004: Sparquote stieg von 3,5 % auf 13,6 % in 40 Monaten): automatische Erhöhung der Sparrate um einen festen Prozentsatz bei jeder Einkommenserhöhung, festgelegt im IPS. VERIFIZIERT (Befund)

---

## A7 Taktische Overlays auf den Kern

Overlays verändern zeitweise das Gewicht von K1 zugunsten von K2 (Geldmarkt). Sie sind **eigene, registrierte Varianten** im Strategie-Katalog (Abschnitt "Overlay-Varianten für das Kernmodul") und werden dort wie jede Strategie gezählt und geprüft.

| Overlay | Regel | Grundlage |
|---|---|---|
| OV-L2 Trendfilter auf K1 | Monatsende: Liegt der Total-Return-Kurs von K1 über dem Durchschnitt der letzten 10 Monatsschlusskurse, ist w(K1) wie in A4.3; sonst w(K1) × 0,5, die andere Hälfte in den Geldmarkt-ETF | Faber (2007), auf einen Baustein übertragen; Halbierung statt Vollausstieg begrenzt Fehlsignal-Kosten und Steuer |
| OV-L4 Volatilitätssteuerung auf K1 | w(K1) = (q_p − Σ Satelliten) × max(0,5; min(1; c_t / σ̂²_t)), c_t und σ̂²_t wie Strategie L4 | Moreira & Muir (2017), Marktportfolio ohne Hebel |

- **Nur senken, nie erhöhen:** beide Overlays können das Gewicht von K1 höchstens halbieren
- **Gate:** Das Overlay muss gegen die statische Mischung mit derselben durchschnittlichen Investitionsquote bestehen (Strategie-Katalog G7 Punkt 8, Calmar-Ratio), und zwar **vor und nach deutscher Steuer** mit derselben Kennzahl (A8.11)
- L3 und S1 sind keine Overlays (eigene Universen), sondern können als Satellit S-Taktik gehalten werden (A4.2)
- Standardmäßig **aus**; Aktivierung nur auf ausdrücklichen Wunsch und nach Lernstufe 2, mit Anzeige der Vor- und Nachsteuer-Ergebnisse
- ENTSCHEIDUNG

---

## A8 Steuer-Engine (Deutschland, Stand 2026)

Alle Regeln mit Paragraph; Werte mit Gültigkeitsjahr in einer versionierten Tabelle. **Nicht verfügbare künftige Werte (z. B. Basiszins 2027) werden nie geschätzt**, sondern als "noch nicht veröffentlicht" gekennzeichnet; für Projektionen gilt dann ein ausdrücklich markierter Annahmewert.

### A8.1 Abgeltungsteuer, Solidaritätszuschlag, Kirchensteuer

- Einkommensteuer auf Kapitalerträge: **ESt = (e − 4q) / (4 + k)** (§ 32d Abs. 1 S. 4 EStG), e = Kapitalerträge nach Teilfreistellung und Pauschbetrag, q = anrechenbare ausländische Steuer, k = Kirchensteuersatz **als Dezimalzahl** (0; 0,08; 0,09). Die Dezimalform folgt zwingend aus § 32d Abs. 1 S. 1–3 (ESt = 0,25 e − 0,25 × k × ESt ⇒ ESt = e / (4 + k)); die Schreibweise im BMF-Schreiben (Rn. 133: "9 × 1/12 = 0,75") ist verkürzt. Bei Kirchenmitgliedschaft nur für einen Teil des Jahres wird k zwölftelweise gekürzt (Rn. 133). VERIFIZIERT (durch Herleitung)
- Solidaritätszuschlag: 5,5 % der Steuer, bei Abgeltungsteuer **immer** (die Freigrenze gilt nicht; § 3 Abs. 3 S. 2, § 4 SolZG), auf den Cent abgerundet. VERIFIZIERT
- Kirchensteuer: k × ESt. Welches Bundesland 8 % bzw. 9 % erhebt, ist Nutzereinstellung (Zuordnung UNVERIFIZIERT)
- **Gesamtbelastung** (zweifach nachgerechnet): ohne Kirchensteuer 26,3750 %; mit 8 % 27,8186 %; mit 9 % 27,9951 %

### A8.2 Sparer-Pauschbetrag

1.000 € (Einzelveranlagung), 2.000 € (Zusammenveranlagung); keine tatsächlichen Werbungskosten; höchstens bis zur Höhe der Erträge (§ 20 Abs. 9 EStG). VERIFIZIERT

### A8.3 Günstigerprüfung und NV-Bescheinigung

- **Günstigerprüfung** (§ 32d Abs. 6 EStG): Auf Antrag werden alle Kapitalerträge des Jahres mit dem persönlichen Tarif besteuert, wenn das günstiger ist. Die App rechnet immer beide Varianten und zeigt die günstigere. VERIFIZIERT
- **Tarif 2026** (§ 32a Abs. 1 EStG), zu versteuerndes Einkommen x auf volle Euro abgerundet, Steuer auf volle Euro abgerundet:
  - x ≤ 12.348: 0
  - 12.349 ≤ x ≤ 17.799: (914,51 × y + 1.400) × y, y = (x − 12.348) / 10.000
  - 17.800 ≤ x ≤ 69.878: (173,10 × z + 2.397) × z + 1.034,87, z = (x − 17.799) / 10.000
  - 69.879 ≤ x ≤ 277.825: 0,42 × x − 11.135,63
  - ab 277.826: 0,45 × x − 19.470,38
  - VERIFIZIERT (Recherche), Formelgrenzen zweifach nachgerechnet
- Solidaritätszuschlag im Tarif: Freigrenze 20.350 € Einkommensteuer (2026, Einzelveranlagung). VERIFIZIERT
- **Wann es hilft:** Der Grenzsteuersatz des Tarifs erreicht 25 % bei etwa 20.774 € zu versteuerndem Einkommen (2026). Für Studierende mit geringem Einkommen ist die Tarifbesteuerung fast immer günstiger. VERIFIZIERT (Rechnung)
- **NV-Bescheinigung** (§ 44a Abs. 2 S. 1 Nr. 2 EStG): verhindert den Steuerabzug ohne Betragsgrenze, wenn voraussichtlich auch mit Günstigerprüfung keine Steuer entsteht; höchstens 3 Jahre gültig, endet am 31.12. **Prüfung in der App:** voraussichtliches zu versteuerndes Einkommen einschließlich Kapitalerträgen (nach Teilfreistellung und Pauschbetrag) ≤ Grundfreibetrag (2026: 12.348 €; 2025: 12.096 €). Abzüge für Werkstudenten u. a. Arbeitnehmer-Pauschbetrag 1.230 € (§ 9a), Sonderausgaben-Pauschbetrag 36 € (§ 10c). VERIFIZIERT
- **Hinweis:** Die NV-Bescheinigung wirkt nur bei deutschen Banken; bei ausländischen Brokern erfolgt die Besteuerung in der Steuererklärung

### A8.4 Investmentfonds (InvStG 2018)

- **Fondsarten** (§ 2 InvStG): Aktienfonds > 50 % Kapitalbeteiligungen; Mischfonds ≥ 25 %; Immobilienfonds > 50 % Immobilien. VERIFIZIERT
- **Teilfreistellung** für Privatanleger (§ 20 InvStG): Aktienfonds 30 %, Mischfonds 15 %, Immobilienfonds 60 %, Auslands-Immobilienfonds 80 %; Anleihen-, Geldmarkt- und Rohstofffonds 0 %. Gilt für Ausschüttungen, Vorabpauschale und Veräußerungsgewinne. VERIFIZIERT
- **Thesaurierend vs. ausschüttend:** gleiche Besteuerungssystematik; Unterschied nur im Zeitpunkt (Thesaurierung verschiebt die Steuer auf den Verkauf, soweit die Rendite 70 % des Basiszinses übersteigt). VERIFIZIERT
- **Quellensteuer auf Fondsebene** (z. B. US-Quellensteuer eines irischen Fonds) ist für den Anleger nicht anrechenbar; der Ausgleich erfolgt pauschal über die Teilfreistellung. Quellensteuer auf die Ausschüttung des Fonds selbst ist anrechenbar (Obergrenze auf Basis der Erträge nach Teilfreistellung). VERIFIZIERT (Systematik und BMF-Beispiel)

### A8.5 Vorabpauschale (§ 18 InvStG)

- Basisertrag = Rücknahmepreis (NAV, nicht Börsenkurs) zu Jahresbeginn × Rechnungszins, Rechnungszins = 0,7 × Basiszins mit mindestens 3 Nachkommastellen (BMF Tz. 18.4); bei Anteilsklassen mit NAV in Fremdwährung Umrechnung zum jeweiligen EZB-Kurs (Tz. 18.6)
- Basisertrag gedeckelt auf: Mehrbetrag (Kurs Jahresende − Kurs Jahresanfang) + Ausschüttungen des Jahres
- **Vorabpauschale = max(0; gedeckelter Basisertrag − Ausschüttungen)**
- Im Erwerbsjahr: Minderung um 1/12 je vollem Monat vor dem Erwerbsmonat
- Gilt als zugeflossen am **ersten Werktag des Folgejahres** und damit als Einkommen des Folgejahres; Banken buchen am ersten Bankarbeitstag (für 2026: 20270104)
- Nur für Anteile, die mit Ablauf des 31.12. gehalten werden (BMF Tz. 18.4). VERIFIZIERT
- Rundung: Basisertrag je Anteil mit mindestens 4 Nachkommastellen, kaufmännische Rundung auf 2 Stellen erst nach Multiplikation mit der Stückzahl (BMF Tz. 18.4). VERIFIZIERT
- **Basiszins:** 2023 2,55 %; 2024 2,29 %; 2025 2,53 %; **2026 3,20 %** (BMF-Schreiben vom 20260113); 2027 noch nicht veröffentlicht. VERIFIZIERT (2025, 2026 aus BMF-PDF; 2023, 2024 über wörtliches Zitat)
- **Liquiditätshinweis:** Bei thesaurierenden Fonds und deutschem Depot bucht die Bank die Steuer auf die Vorabpauschale Anfang Januar vom Verrechnungskonto ab; die App erinnert im Dezember, falls der Freistellungsauftrag nicht reicht

### A8.6 Veräußerung von Fondsanteilen

- Gewinn = Erlös − Veräußerungskosten − Anschaffungskosten einschließlich Anschaffungsnebenkosten (FIFO je Depot bzw. Unterdepot, § 20 Abs. 4 S. 1 und S. 7 EStG; BMF 20250514 Rn. 97–98) − **alle während der Haltedauer angesetzten Vorabpauschalen** (in voller Höhe, vor Teilfreistellung; § 19 Abs. 1 InvStG); danach Teilfreistellung. Kann einen Verlust erzeugen. VERIFIZIERT
- Bei ausländischer Verwahrung werden frühere Vorabpauschalen nur abgezogen, wenn sie erklärt wurden oder die Erträge in den Jahren innerhalb des Pauschbetrags lagen (BMF Tz. 19.9). VERIFIZIERT → Die App führt ein **Vorabpauschalen-Register** je Tranche

### A8.7 Gold

- **Physisch hinterlegte Gold-ETCs mit ausschließlichem Anspruch auf Lieferung oder auf den Erlös des hinterlegten Goldes** (Xetra-Gold-Typ): private Veräußerungsgeschäfte nach § 23 Abs. 1 S. 1 Nr. 2 EStG, **steuerfrei nach mehr als einem Jahr** Haltedauer; Lieferung ist keine Veräußerung (BFH VIII R 35/14 und VIII R 4/15 vom 20150512; IX R 33/17 vom 20180206; VIII R 7/17 vom 20200616; BMF 20250514 Rn. 57). VERIFIZIERT
- EUWAX Gold II: gleiche Einordnung wahrscheinlich, aber keine eigene BFH-Entscheidung gefunden. UNVERIFIZIERT
- Nicht lieferbare oder nicht hinterlegte Gold-Zertifikate: Kapitalerträge nach § 20 (Abgeltungsteuer); Goldfonds: Kapitalerträge (BFH VIII R 15/18). VERIFIZIERT
- Gewinne nach § 23 bleiben steuerfrei, wenn ihre Summe im Jahr **weniger als 1.000 €** beträgt (Freigrenze, § 23 Abs. 3 S. 5; ab Veranlagungszeitraum 2024, vorher weniger als 600 €); bei 1.000 € oder mehr ist der gesamte Gewinn steuerpflichtig. Verluste nur mit § 23-Gewinnen verrechenbar. VERIFIZIERT
- Haltefrist nach dem Handelstag (Schlusstag) von Kauf und Verkauf; Fristberechnung nach §§ 187 Abs. 1, 188 Abs. 2 BGB (Kauf 20260310 → steuerfrei ab Verkauf am 20270311). VERIFIZIERT (durch die Prüfung)
- Tranchenfolge: Das Gesetz schreibt FIFO für § 23 nur bei Fremdwährungen ausdrücklich vor; die App führt Gold-Tranchen einzeln und verwendet FIFO als vorsichtige Annahme. UNVERIFIZIERT (Verwaltungsauffassung)
- Die App zeigt je Tranche das Datum, ab dem ein Verkauf steuerfrei ist

### A8.8 Direkte Aktien (Satellit)

- Dividenden aus den USA: 15 % Quellensteuer nach DBA (Art. 10 Abs. 2 lit. b), sofern beim Broker das Formular W-8BEN vorliegt (sonst 30 %), anrechenbar höchstens bis 25 % und bis zur deutschen Steuer auf diese Erträge; **innerhalb des Pauschbetrags geht die Anrechnung verloren** (§ 32d Abs. 5 EStG). VERIFIZIERT
- Verluste aus Aktienverkäufen nur mit Gewinnen aus Aktienverkäufen verrechenbar (§ 20 Abs. 6 S. 4 EStG; Vorlage beim Bundesverfassungsgericht 2 BvL 3/21, Entscheidung zum Stand 20260925 nicht gefunden). ETF-Verluste gehen in den allgemeinen Topf. VERIFIZIERT (Regel), UNVERIFIZIERT (Stand des Verfahrens)

### A8.9 Deutsche vs. ausländische Depotbank

- Deutsche Bank: Steuerabzug, Teilfreistellung, Freistellungsauftrag, Verlusttöpfe, Verlustbescheinigung bis 15.12. beantragbar (§ 43a Abs. 3 EStG). VERIFIZIERT
- Ausländischer Broker (z. B. IBKR): keine Abzugsteuer; alle Erträge einschließlich selbst berechneter Vorabpauschalen sind zu erklären (§ 32d Abs. 3 EStG; Pflichtveranlagung). Die App erzeugt eine **Jahresübersicht für Anlage KAP / KAP-INV**. VERIFIZIERT (Regel), UNVERIFIZIERT (Verhalten von IBKR)
- **Empfehlung für das Kernportfolio:** deutsche Depotbank, wegen automatischer Steuerabwicklung und Freistellungsauftrag; IBKR optional für Trading-Module. ENTSCHEIDUNG

### A8.10 Steueroptimierte Verkaufsreihenfolge

Für jeden empfohlenen Verkauf berechnet die App je Tranche (FIFO ist je Depot bzw. Unterdepot gesetzlich vorgegeben; frei sind die Wahl des Produkts, des Unterdepots und des Zeitpunkts):
1. Nach Steuer verbleibender Betrag je Verkaufsvariante
2. Nutzung von Verlusten und Pauschbetrag
3. Bei Gold: Verschiebung, wenn eine Tranche innerhalb von 60 Tagen die Jahresfrist erreicht und das Overlay/Rebalancing das zulässt
4. Vorschlag des Produkts bzw. Unterdepots, dessen Verkauf am wenigsten Steuer auslöst, sofern es dieselbe Gewichtsabweichung behebt
5. Verteilung nicht dringlicher Verkäufe auf mehrere Steuerjahre, um jeweils Pauschbetrag und ggf. Grundfreibetrag zu nutzen

### A8.11 Nachsteuer-Gate für Overlays und Produktwechsel

- **Overlays (A7):** Der Backtest wird mit realisierten Gewinnen und der Steuer-Engine dieses Abschnitts in der Situation des Nutzers (Pauschbetrag, Günstigerprüfung, Kirchensteuer) nachgerechnet. Das Gate verwendet **dieselbe Kennzahl** wie vor Steuern (Calmar-Ratio gegen die statische Mischung gleicher Investitionsquote, Strategie-Katalog G7 Punkt 8) und muss vor **und** nach Steuern bestanden werden
- **Satellit S-Taktik:** wie Overlays, mit der Kennzahl der jeweiligen Strategie
- **Produktwechsel:** Endvermögen nach Steuern (A5.6)
- ENTSCHEIDUNG

---

## A9 Projektion

### A9.1 Daten und Verfahren

- **Quelle:** Jordà-Schularick-Taylor-Macrohistory-Datenbank (Jahresdaten, 18 Länder ab 1870, Aktien- und Anleihen-Gesamtrenditen, kurzfristige Zinsen, Verbraucherpreise, Wechselkurse; frei für nichtkommerzielle Nutzung, CC BY-NC-SA; letztes Datenjahr UNVERIFIZIERT)
- **Basisfall: Weltportfolio.** Für jedes Jahr wird aus den 18 Ländern ein **BIP-gewichtetes Weltportfolio** für Aktien, Anleihen und kurzfristige Zinsen gebildet, in USD umgerechnet (JST-Wechselkurse) und mit der US-Inflation real gerechnet. Das entspricht einem breit gestreuten Weltindex besser als die Ziehung einzelner Länder und vermeidet, dass Hyperinflationsjahre einzelner Länder den Sicherheitsbaustein prägen. Näherung: Die Perspektive ist USD-real, nicht EUR-real; Wechselkurseffekte EUR/USD sind nicht abgebildet (ENTSCHEIDUNG, erklärt)
- **Verfahren:** stationärer Block-Bootstrap (Politis & Romano, 1994) über die Jahre des Weltportfolios, **mittlere Blocklänge 10 Jahre**, zirkulär innerhalb der Reihe. Aktien, Anleihen, kurzfristige Zinsen und Inflation eines Jahres werden **gemeinsam** gezogen, damit Korrelationen und Inflationsphasen erhalten bleiben
- **Stressfall "schlechtes Land":** Block-Bootstrap innerhalb **einzelner** Länder (Blöcke überschreiten keine Ländergrenze), einschließlich Kriegs- und Hyperinflationsjahren; ausgewiesen wird das 5. Perzentil
- **Nie** allein Normalverteilung oder nur US-Historie: Die US-Stichprobe ist durch Überlebensbias geschönt (Wahrscheinlichkeit eines realen 30-Jahres-Verlusts 1,2 % gegenüber 12 % in 39 Ländern; Anarkulova et al., 2022). VERIFIZIERT

### A9.2 Zentrierung auf konservative Annahmen

Die realen Log-Renditen des Weltportfolios werden je Anlageklasse verschoben: r'_t = r_t − mean(r) + ln(1 + g), wobei der Mittelwert über die **Quellstichprobe** (alle Jahre des Weltportfolios) gebildet wird. Dadurch entspricht g der **mittleren geometrischen realen Wachstumsrate** (dem typischen, mittleren Verlauf), nicht dem arithmetischen Erwartungswert. Bei rund 20 % Volatilität liegt der arithmetische Erwartungswert etwa 2 Prozentpunkte höher, und der Mittelwert des Endvermögens liegt deutlich über dem Median. **Die App bezeichnet g deshalb überall als "mittlere reale Wachstumsrate (Median)"** und zeigt keinen Mittelwert des Endvermögens als Hauptzahl.

| Anlageklasse (real, vor Kosten, geometrisch) | Pessimistisch | Basis | Optimistisch |
|---|---|---|---|
| Welt-Aktien | 2 % | 4 % | 6 % |
| Anleihen / kurzfristige Zinsen | 0 % | 0,5 % | 1,5 % |

- Anker: Weltaktien real 5,2 % p. a. geometrisch 1900–2024, Anleihen 1,7 %, Geldmarkt 0,5 % (Dimson, Marsh & Staunton, Yearbook 2025); vorausschauende Schätzungen der **Risikoprämie** (arithmetisch, über sichere Anlagen) liegen deutlich unter der historischen (Fama & French, 2002: 2,55–4,32 % gegenüber 7,43 % realisiert; Dimson, Marsh & Staunton, 2003: Welt 3,5 %). Die Tabelle ist eine vorsichtige Synthese: ENTSCHEIDUNG
- Die Inflation wird nicht verschoben (historische Verteilung), dient aber in A9.3 nur für die Nominalrechnung

### A9.3 Kosten und Steuern (nominal gerechnet, dann deflationiert)

- Aus realer Rendite und gemeinsam gezogener Inflation entsteht je Pfad eine **nominale** Rendite: (1 + r_nom) = (1 + r_real) × (1 + π)
- Laufende Kosten = TD des gewählten Produkts (A5.3), sonst TER
- **Steuern auf den nominalen Pfad** mit A8: Vorabpauschale jährlich (Deckel = nominaler Wertzuwachs; Basiszins als markierte Annahme: letzter veröffentlichter Wert, Variante 2 %), Pauschbetrag, Teilfreistellung, Steuer beim Verkauf am Zielende
- Danach Rückrechnung in **heutige Euro** mit der Inflation des Pfads
- Darstellung wahlweise vor und nach der Steuer beim Verkauf am Ende

### A9.4 Ausgaben

- **Fächerdiagramm** in heutigen Euro: Perzentile 5, 10, 25, 50, 75, 90
- Wahrscheinlichkeit, am Zielende weniger als die Summe der Einzahlungen (real) zu haben
- Größter Rückgang in Euro im 10., 20. und 30. Jahr (Reihenfolgerisiko: späte Rückgänge treffen große Beträge)
- Wahrscheinlichkeit, einen Zielbetrag (P8) bis zum Zieldatum zu erreichen
- **Stressszenarien:** "Japan 1990" (20 Jahre 0 % real, deterministisch), "−50 % im Jahr N, danach 15 Jahre Erholung" (deterministisch), "schlechtes Land" (A9.1, 5. Perzentil)
- Beschriftung: "So könnte es kommen, keine Vorhersage"

### A9.5 Reproduzierbarkeit

10.000 Pfade, fester gespeicherter Seed, Daten- und Annahmen-Version im Ergebnis.

---

## A10 Monatliche Empfehlung

Am ersten Tag jedes Monats (und bei Ereignissen) erzeugt die App eine Seite mit genau diesen Teilen:

1. **Kernaussage in einem Satz**, z. B. "Sparplan läuft weiter wie bisher, keine Umschichtung nötig."
2. **Konkrete Aktionen** (falls nötig) als Liste: Produkt (Name, ISIN), Betrag in €, Kauf/Verkauf, Grund; bei Verkäufen die erwartete Steuer
3. **Status der Vorbedingungen:** Schulden, Reserve (z. B. "Reserve 2,4 von 3 Monaten")
4. **Portfolio vs. Ziel:** Ist- und Zielgewichte je Topf, Abweichung
5. **Overlay-Status** (falls aktiviert): investiert / teilweise Cash, mit Grund
6. **Steuerjahr:** genutzter Pauschbetrag, erwartete Vorabpauschale im Januar
7. **Projektion kurz:** Median und 10. Perzentil zum Zieldatum je Topf, Veränderung zum Vormonat
8. **"Was sich geändert hat"** gegenüber dem Vormonat
9. **Warum?**-Verknüpfung zu Regeln, Evidenz und IPS

**Ereignisse, die eine Sonderempfehlung auslösen:** Schließungs- oder Fusionsankündigung eines gehaltenen Produkts; Satellit überschreitet seine Obergrenze um mehr als 25 %; neuer Basiszins; Profiländerung; Einmalbetrag; Entnahmewunsch. Gewichtsabweichungen außerhalb des Prüftermins werden nur angezeigt (A6.2).

Die Empfehlung wird mit allen Eingaben gespeichert und ist unveränderlich (append-only).

---

## A11 Anlagerichtlinie (Investment Policy Statement)

Elemente nach CFA Institute (2010), VERIFIZIERT: Zweck und Umfang; Zuständigkeiten und Überprüfung; Rendite- und Risikoziele inklusive Benchmark; Risikotoleranz (rational und emotional); Rahmenbedingungen (Horizont, Liquidität, Steuern, Besonderheiten wie Nachhaltigkeit); Risikomanagement (Messung, Rebalancing-Regeln, Auslöser).

**App-Ergänzungen:** akzeptierter Verlust in Euro; Reserve-Ziel; Sparrate und Steigerungsregel; erlaubte Satelliten mit Obergrenzen; die Zusage "Was ich bei −50 % tue" in eigenen Worten; jährlicher Überprüfungstermin; Depotbank.

- Wird nach dem Profil erstellt und von dir bestätigt (Datum)
- Änderungen nur mit Wartefrist (A12)
- Exportierbar als Markdown-Datei in den Vault

---

## A12 Verhaltens-Leitplanken

| Leitplanke | Regel | Evidenz |
|---|---|---|
| Ansicht | Depotwert standardmäßig quartalsweise bzw. jährlich statt täglich | Häufige Bewertung verstärkt kurzsichtige Verlustaversion und führt zu weniger riskanten Anlageentscheidungen (Gneezy & Potters, 1997; Thaler et al., 1997; nicht erneut geprüft) |
| Verkaufen im Drawdown | Verkauf von Kernpositionen bei einem Rückgang > 20 % vom Hoch zeigt zuerst die eigene IPS-Zusage und die Erholungszeiten aus A3.1 | Dispositionseffekt, Überreaktion (Odean, 1998; Guiso et al., 2018) |
| Wartefrist | Abweichung vom IPS (Quote senken, Kern verkaufen) erst nach 72 Stunden bestätigbar | Keine direkte Evidenz gefunden; ENTSCHEIDUNG |
| Häufigkeit | Warnung bei mehr als 4 manuellen Transaktionen pro Monat im Kernportfolio (Sparplan-Ausführungen zählen nicht) | Überhandeln kostet (Barber & Odean, 2000: aktivstes Fünftel 11,4 % netto gegenüber 17,9 % Marktrendite) |
| Performance-Jagd | Hinweis, wenn ein Satellit nach starker Vorperiode aufgestockt werden soll | Renditelücke durch Ein- und Ausstiege (Dichev, 2007) |
| Rückblick | Jahresrückblick: Was hätte "nichts tun" ergeben? | ENTSCHEIDUNG |

---

## A13 Altersvorsorge-Hinweise (informativ)

- **Altersvorsorgedepot** (Altersvorsorgereformgesetz, vom Bundestag am 20260327 beschlossen, Bundesrat 20260508; Produkte ab **20270101**): gefördertes Depot ohne Garantiepflicht; Zulage 50 % auf Beiträge bis 360 € und 25 % auf Beiträge von 360,01 bis 1.800 € (Grundzulage höchstens 540 €); **einmaliger Berufseinsteigerbonus 200 € bei Vertragsabschluss vor dem 25. Geburtstag**; Kostenobergrenze Standardprodukt 1,0 %; keine Besteuerung der Fondserträge im Vertrag (§ 16 Abs. 2 InvStG), dafür Besteuerung der Auszahlungen. VERIFIZIERT (amtliche Zusammenfassungen; Gesetzestext, Förderberechtigung von Studierenden und Details UNVERIFIZIERT)
- Die App zeigt ab Verfügbarkeit einen Vergleich: gefördertes Altersvorsorgedepot vs. freies Depot für den Topf "Altersvorsorge" (Zulage, Kosten, Nachsteuer bei Auszahlung, eingeschränkte Verfügbarkeit)
- **Betriebliche Altersvorsorge per Entgeltumwandlung** für Werkstudenten: bei Einkommen unter dem Grundfreibetrag kaum Steuerersparnis, spätere Besteuerung der Auszahlung; meist unattraktiv. Die App zeigt die Rechnung, empfiehlt aber nichts ohne Prüfung. VERIFIZIERT (Grenzen § 1a BetrAVG, § 3 Nr. 63 EStG), Sozialversicherungsstatus UNVERIFIZIERT
- **Frühstart-Rente:** nur Kabinettsentwurf, betrifft Kinder von 6 bis 18 Jahren, für dich nicht relevant

---

## A14 Tests

| Nr. | Test | Eingaben | Erwartet |
|---|---|---|---|
| TA1 | Gesamtsteuersatz | k = 0 / 0,08 / 0,09 | 26,3750 % / 27,8186 % / 27,9951 % |
| TA2 | Vorabpauschale Grundfall | 10.000 → 11.000, keine Ausschüttung, Basiszins 3,20 %, Kauf Januar | 224,00 €; steuerpflichtig nach Teilfreistellung 156,80 €; ohne Pauschbetrag 39,20 € + SolZ 2,15 € = 41,35 €; mit Pauschbetrag 0 € |
| TA3 | Deckel | 10.000 → 10.100 | 100,00 € |
| TA4 | Verlustjahr | 10.000 → 9.000 | 0 € |
| TA5 | Ausschüttender Fonds | 10.000 → 10.800, Ausschüttung 150 € | 74,00 € |
| TA6 | Erwerb im März | wie TA2, Kauf 15. März | 186,67 € |
| TA7 | BMF-Beispiel | Basiszins 1 %, Kurs 100 → 100,50, Ausschüttung 0,10; Kauf 10. Juli | 0,50 bzw. 0,25 je Anteil |
| TA8 | Verkauf nach Vorabpauschale | TA2, Verkauf 20270630 zu 12.000, ohne Transaktionskosten | Gewinn 1.776,00 €; nach Teilfreistellung 1.243,20 €; Kapitalerträge 2027 gesamt 1.400,00 € (= 70 % × 2.000); **Veranlagung** ohne Pauschbetrag: 350,00 € + SolZ 19,25 € = 369,25 €; **Bankabzug in zwei Vorgängen** (Vorabpauschale, Verkauf): SolZ 2,15 € + 17,09 € = 19,24 €; mit Pauschbetrag (Veranlagung) 100,00 € + 5,50 € = 105,50 € |
| TA9 | Tarif 2026 | zvE 12.348 / 15.000 / 20.000 / 30.000 | 0 / 435 / 1.570 / 4.217 € |
| TA10 | Günstigerprüfung | Grenzsteuersatz bei 20.774 € | ≈ 25 % |
| TA11 | Gold-Haltefrist und Freigrenze | Kauf 20260310, Verkauf 20270310 bzw. 20270311; Jahresgewinn § 23 von 999,99 € bzw. 1.000,00 € | steuerpflichtig bzw. steuerfrei; 999,99 € steuerfrei, 1.000,00 € voll steuerpflichtig |
| TA12 | Aktienquote | Horizont 20 J., stabiles Einkommen, L€ ausreichend | 100 %; mit schwankendem Einkommen 70 %; Horizont 7 J.: q_Horizont = 60 + (7 − 5)/5 × 20 = 68 % → abgerundet 60 % |
| TA12b | Toleranz über zwei Töpfe | Töpfe A (h 20 J., B5 10.000 €) und B (h 2 J., B5 10.000 €), L€ 5.000 €, D_Stress 0,5 | q_Tol,A = min(1; 5.000/5.000) = 100 %, Restbudget 0; q_Tol,B = 0 % (Horizontgrenze bei 2 J. ohnehin 15 %) |
| TA12c | Toleranz ohne Depot | Σ B5 < 1.000 € | Toleranzgrenze entfällt, Hinweis erscheint |
| TA13 | Cashflow-Rebalancing | w = (0,8; 0,2), V = (9.000; 1.000), C = 500 | T = (8.400; 2.100), F = (0; 1.100), x = (0; 500) |
| TA14 | Cashflow bei geringem Fehlbetrag | w = (0,8; 0,2), V = (8.000; 1.950), C = 500 | T = (8.360; 2.090), F = (360; 140), Σ F = 500, x = (360; 140) |
| TA14b | Mindestbetrag | wie TA14, Mindestbetrag 150 € | Monat 1: x = (500; 0), offener Anspruch Baustein 2: 140 €; Auszahlung, sobald Anspruch + x ≥ 150 € |
| TA14c | Keine Einzahlung | C = 0, Portfolio exakt im Ziel | x = (0; 0), keine Division durch null |
| TA15 | Vorbedingungen | Dispo 12 %; Reserve 1,5 von 3 Monaten | V1 greift; nach Tilgung V3: 50/50 |
| TA16 | ETF-Bewertung | synthetische Kandidaten mit bekannten Kennzahlen | Rangfolge und Punktwerte exakt wie von Hand berechnet; harte Filter schließen zu kleine und zu junge Fonds aus |
| TA17 | Projektion | fester Seed | identische Perzentile bei Wiederholung; Mittelwert der zentrierten Log-Renditen **der Quellstichprobe** = ln(1,04) ± 10⁻¹²; Median des realen Endvermögens einer Einmalanlage über 30 Jahre ohne Kosten und Steuern nahe 1,04³⁰ (Toleranz aus Monte-Carlo-Fehler) |
| TA18 | Nachsteuer-Gate | Overlay mit Vorsteuer-Vorteil 0,3 % p. a., aber jährlicher Gewinnrealisierung | Gate scheitert, wenn der Nachsteuer-Vorteil ≤ 0 |
| TA19 | Look-ahead | Abschneide- und Störtest für ETF-Kennzahlen (Stand-Datum), Basiszins (Veröffentlichung), Projektionseingaben | keine Änderung bis t |
| TA20 | ETF-Skalen | TD −0,10 / −0,11 / +0,20 pp | nach Rundung auf 0,05: −0,10 / −0,10 / +0,20 → 25 / 25 / 100 Punkte |
| TA21 | Produktwechsel | alter Fonds TD −0,30, neuer TD 0,00, Gewinn im Pauschbetrag steuerfrei realisierbar | Wechsel empfohlen; derselbe Fall mit steuerpflichtigem Gewinn und 3 Jahren Resthorizont: kein Wechsel |
| TA22 | Gleitpfad kurz vor dem Ziel | Topf mit Zieldatum 20290930, q_p = 30 % am 20260930, Depot 10.000 €, Sparrate 100 € | Stufe auf 20 % fällig, sobald q_Horizont < 30 % (ab 20261001); Quartalsprüfung 20261231 empfiehlt Verkauf von rund 1.000 € (Sparraten von 300 € reichen nicht); q_p = 0 spätestens 20280930 umgesetzt; jährliche Profil-Hysterese verzögert keine dieser Stufen |

Alle Steuertests mit `Decimal`; Werte TA1–TA10 wurden zweifach unabhängig nachgerechnet.

---

## A15 Offene Punkte

| Punkt | Wann klären |
|---|---|
| Einheit von k in § 32d Abs. 1 S. 4 EStG im Gesetzestext bestätigen | Vor A8 |
| Nutzungsrechte der Grable-Lytton-Skala | Vor A1 |
| Lizenzbedingungen verzögerte Kursdaten der Deutschen Börse; Nutzungsbedingungen DWS, Amundi, SPDR, OpenFIGI | Phase 1 |
| JST-Datenbank: letztes Datenjahr, Lizenz für private Nutzung | Phase 1 |
| Quellensteuer deutscher und luxemburgischer Fonds auf US-Dividenden | Vor A5 |
| Einordnung EUWAX Gold II nach § 23 | Vor Empfehlung von S-Gold |
| Altersvorsorgedepot: Gesetzestext, Förderberechtigung Studierender | Vor 2027 |
| Stand BVerfG 2 BvL 3/21 (Aktienverlusttopf) | Jährlich |
| Grenzen Familienversicherung (§ 10 SGB V) und BAföG-Vermögensfreibetrag | Vor A6.3 |
| Kalibrierung D_Stress aus dem JST-Weltportfolio (Platzhalter 0,60) | Phase 1 |
| Tranchenfolge bei § 23 (Verwaltungsauffassung) | Vor Empfehlung von S-Gold |
| Overlay-Varianten OV-L2, OV-L4 prüfen (im Strategie-Katalog v1.2 registriert) | Phase 3 |
| Basiszins 2027 | Januar 2027 |

---

## Änderungsprotokoll

**v1.3 (20260925)** Instrument-Stammdatenschicht: A5.1 um Zeitachsen, Vorrang und Prüfstatus je Wert ergänzt; A5.2 um die dreiwertige Auswertung (erfüllt / verletzt / offen) und Präzisierungen zu den Filtern 1, 2, 4, 5, 6 und 7. Noch nicht unabhängig geprüft

**v1.2 (20260925)** Eigenprüfung beim Ablegen: Die jährliche Hysterese (A3.3 Punkt 6) galt dem Wortlaut nach für q_p insgesamt und hätte die Gleitpfad-Absenkung in den letzten Jahren vor dem Ziel um bis zu ein Jahr verzögert → gilt nur noch für Toleranz und Kapazität; q_Horizont monatlich; neue Gleitpfad-Regel für die letzten 36 Monate (A6.2) mit Test TA22; Begründung in A3.1 an die 10-Prozentpunkt-Rundung angepasst; Testtabelle geordnet

**v1.1 (20260925)** nach unabhängiger Prüfung (2 kritische, 10 schwere, 11 leichte Befunde; alle Testwerte TA1–TA14 und der Tarif 2026 einschließlich z = (x − 17.799)/10.000 bestätigt):
- Kritisch: Toleranzgrenze war zirkulär und für neue Anleger undefiniert → B5 deterministisch bei q = 100 %, Untergrenze 1.000 €, Verlustbudget über alle Töpfe (längster Horizont zuerst), jährliche Neuberechnung mit Hysterese
- Kritisch: Projektion falsch spezifiziert → g ist die mittlere geometrische Rate (Median), so beschriftet; Steuern auf nominalen Pfaden mit gemeinsam gezogener Inflation; Weltportfolio statt Einzelländer im Basisfall, Einzelländer nur im Stressfall; Jahresdaten, Blocklänge 10 Jahre; Test auf die Quellstichprobe bezogen
- Schwer: FIFO je Depot bzw. Unterdepot, ein Unterdepot je Topf; Gewinnrealisierung mit BFH-Grundlage, Grundfreibetrag-Spielraum, Abzinsung, Nebenwirkungen BAföG und Familienversicherung; Overlays als eigene registrierte Varianten nur auf K1 (L3, S1 als Satellit); linearer Gleitpfad; Produktwechsel über Endvermögen nach Steuern; feste Bewertungsskalen mit Wesentlichkeitsschwelle, Vergleich nur innerhalb eines Index, eigene Indexwahl; D_Stress-Platzhalter 0,60; Cashflow-Algorithmus bereinigt (Nullfall, Mindestbetrag mit offenem Anspruch, Dauerauftrag); Umschichtung nur am Prüftermin mit Band min(5 Pp.; 25 %); Satellitengrenze einheitlich relativ zu q
- Leicht: Einheit von k hergeleitet; Gold-Freigrenze "weniger als 1.000 €" ab 2024, Haltefrist nach BGB bestätigt, Lieferanspruch-Wortlaut; Vorabpauschale mit NAV, Rechnungszins, Stichtag 31.12. verifiziert; Veräußerungskosten; Bankabzug vs. Veranlagung beim SolZ; Reserve-Ziel ≥ Starter-Reserve; Einordnung der Verlustwahrscheinlichkeiten und des Japan-Beispiels; realistische Aktienquote zu Beginn; Transaktionswarnung ohne Sparpläne; Evidenz zur Ansichtshäufigkeit; W-8BEN; Zitate korrigiert (Bessembinder 57 %, Barber & Odean, Grable-Lytton-Retrospektive, Anarkulova-Versionen)

---

## Quellen

**Gesetze und Verwaltung**
- Einkommensteuergesetz (EStG), §§ 9a, 10c, 20, 23, 32a, 32d, 43a, 44a, 52. https://www.gesetze-im-internet.de/estg/
- Investmentsteuergesetz 2018 (InvStG), §§ 2, 16, 18, 19, 20. https://www.gesetze-im-internet.de/invstg_2018/
- Solidaritätszuschlaggesetz (SolZG), §§ 3, 4.
- Bundesministerium der Finanzen. (20250514). *Einzelfragen zur Abgeltungsteuer* (IV C 1 - S 2252/00075/016/070).
- Bundesministerium der Finanzen. (20190521, zuletzt geändert 20251124). *Anwendungsfragen zum Investmentsteuergesetz*.
- Bundesministerium der Finanzen. (20250110; 20260113). *Basiszins zur Berechnung der Vorabpauschale gemäß § 18 Absatz 4 InvStG*.
- Bundesfinanzhof: VIII R 35/14 und VIII R 4/15 (20150512); IX R 33/17 (20180206); VIII R 7/17 (20200616); VIII R 15/18 (20210412); IX R 60/07 (20090825).
- ESMA. (2023). *Guidelines on certain aspects of the MiFID II suitability requirements* (ESMA35-43-3172).
- Richtlinie 2009/65/EG (UCITS), Art. 52.
- Bundesregierung. (20260601). *Reform der privaten Altersvorsorge*. https://www.bundesregierung.de/breg-de/aktuelles/reform-private-altersvorsorge-2400072

**Literatur**
- Anarkulova, A., Cederburg, S., & O'Doherty, M. S. (2022). Stocks for the long run? Evidence from a broad sample of developed markets. *Journal of Financial Economics, 143*(1), 409–433.
- Anarkulova, A., Cederburg, S., & O'Doherty, M. S. (2023, überarbeitet 20260903). *Beyond the status quo: A critical assessment of lifecycle investment advice* [Working paper]. SSRN 4590406.
- Barber, B. M., & Odean, T. (2000). Trading is hazardous to your wealth. *Journal of Finance, 55*(2), 773–806.
- Benartzi, S., & Thaler, R. H. (2004). Save More Tomorrow. *Journal of Political Economy, 112*(S1), S164–S187.
- Bessembinder, H. (2018). Do stocks outperform Treasury bills? *Journal of Financial Economics, 129*(3), 440–457.
- CFA Institute. (2010). *Elements of an investment policy statement for individual investors*.
- Cocco, J. F., Gomes, F. J., & Maenhout, P. J. (2005). Consumption and portfolio choice over the life cycle. *Review of Financial Studies, 18*(2), 491–533.
- Constantinides, G. M. (1979). A note on the suboptimality of dollar-cost averaging as an investment policy. *Journal of Financial and Quantitative Analysis, 14*(2), 443–450.
- Dichev, I. D. (2007). What are stock investors' actual historical returns? *American Economic Review, 97*(1), 386–401.
- Dimson, E., Marsh, P., & Staunton, M. (2003). Global evidence on the equity risk premium. *Journal of Applied Corporate Finance, 15*(4), 27–38.
- Dimson, E., Marsh, P., & Staunton, M. (2025). *UBS Global Investment Returns Yearbook 2025* [Zusammenfassung].
- Erb, C. B., & Harvey, C. R. (2013). The golden dilemma. *Financial Analysts Journal, 69*(4), 10–42.
- Fama, E. F., & French, K. R. (2002). The equity premium. *Journal of Finance, 57*(2), 637–659.
- French, K. R., & Poterba, J. M. (1991). Investor diversification and international equity markets. *American Economic Review, 81*(2), 222–226.
- Gneezy, U., & Potters, J. (1997). An experiment on risk taking and evaluation periods. *Quarterly Journal of Economics, 112*(2), 631–645. (Nicht erneut geprüft.)
- Grable, J. E., & Lytton, R. H. (1999). Financial risk tolerance revisited: The development of a risk assessment instrument. *Financial Services Review, 8*(3), 163–181.
- Kuzniak, S., Rabbani, A., Heo, W., Ruiz-Menjivar, J., & Grable, J. E. (2015). The Grable and Lytton risk-tolerance scale: A 15-year retrospective. *Financial Services Review, 24*(2), 177–192. (Autorenliste nicht erneut geprüft.)
- Guiso, L., Sapienza, P., & Zingales, L. (2018). Time varying risk aversion. *Journal of Financial Economics, 128*(3), 403–421.
- Hou, K., Xue, C., & Zhang, L. (2020). Replicating anomalies. *Review of Financial Studies, 33*(5), 2019–2133.
- Huang, S., Song, Y., & Xiang, H. The smart beta mirage. *Journal of Financial and Quantitative Analysis.* (Jahrgang und Band zu prüfen.)
- Klement, J. (2015). Investor risk profiling: An overview. *CFA Institute Research Foundation Briefs, 1*(1).
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance, 71*(1), 5–32.
- Novy-Marx, R. (2013). The other side of value: The gross profitability premium. *Journal of Financial Economics, 108*(1), 1–28.
- Odean, T. (1998). Are investors reluctant to realize their losses? *Journal of Finance, 53*(5), 1775–1798.
- Thaler, R. H., Tversky, A., Kahneman, D., & Schwartz, A. (1997). The effect of myopia and loss aversion on risk taking: An experimental test. *Quarterly Journal of Economics, 112*(2), 647–661. (Nicht erneut geprüft.)
- Politis, D. N., & Romano, J. P. (1994). The stationary bootstrap. *Journal of the American Statistical Association, 89*(428), 1303–1313.

**Industrie- und Datenquellen (keine begutachtete Evidenz, als solche gekennzeichnet)**
- Jaconetti, C. M., Kinniry, F. M., & Zilbering, Y. (2010). *Best practices for portfolio rebalancing*. Vanguard.
- Shtekhman, A., Tasopoulos, C., & Wimmer, B. (2012). *Dollar-cost averaging just means taking risk later*. Vanguard.
- Vanguard. (2021). *Global equity investing: The benefits of diversification and sizing your allocation*.
- Vanguard. (2022). *Rational rebalancing*.
- Vanguard. (2026). *Currency hedging whitepaper*.
- Morningstar. (20240110). *ETF tracking difference and tracking error*.
- MSCI, FTSE Russell: Index-Factsheets, Stand 20260831. iShares Core MSCI World: Factsheet, Stand 20260831.
- justETF: Allgemeine Geschäftsbedingungen (Stand 20250618).
- Deutsche Börse: Xetra Liquidity Measure; MiFIR-Veröffentlichungen verzögerter Daten.
- Jordà-Schularick-Taylor Macrohistory Database. https://www.macrohistory.net/

