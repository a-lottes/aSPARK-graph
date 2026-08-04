# Backlog — aSPARK-graph

**Stand:** 2026-07-25 · **Repo-Version:** `0.5.0` · **Herkunft:** Antwort auf das Architektur-Review
**Master-Dokument:** `~/aSPARK Doku/REVIEW-RESPONSE.md` (enthält die normativen Cross-Repo-Verträge)

> **Für die Session in diesem Repo.** Autonom lesbar — die anderen Repos musst du nicht öffnen. Was du
> über Core und policy wissen musst, steht in §2. Reihenfolge ist Abhängigkeitsreihenfolge.
>
> **Achtung: `.spark/` ist hier getrackt** (nur `.aspark-graph/` ist ignoriert). Was du committest, wird
> öffentlich.

## 1. Wo dieses Repo steht

**Das Review unterschätzt dieses Repo massiv** — es behauptet „no knowledge graph, no MCP server in play"
und „v0.4.1 isn't even on a package index". Tatsächlich, verifiziert: v0.5.0, 2.818 LOC, echter
MCP-stdio-Server (FastMCP), tree-sitter-Extraktoren für Python/TS/Java/Go/Rust mit **exakt gepinnten**
Grammatiken zur Sicherung der byte-stabilen Rebuild-Garantie, inkrementeller Parse-Cache, 9 Queries, 27
Testdateien, 6 Release-Tags. Das Review hat nur ins Pilot-Repo gesehen, wo der Graph nicht eingebunden ist.

Nach Core ist das das reifste Produkt der Familie. Die offenen Punkte sind entsprechend spezifisch:

1. **Ein MCP-Server ist ausgeliefert und ungehärtet.** `grep -riE "prompt injection|threat|exfiltrat"` über
   `README.md` und `CLAUDE.md` → null Treffer. Es gibt kein `SECURITY.md`.
2. **Die Traceability-Kette endet vor dem Release.** `NodeType` kennt keinen `Release`- und keinen
   `Commit`-Knoten. Beworben wird „Story → Task → Code → Test → Release".
3. **Nicht auf PyPI** — der größte Adoptionsblocker eines fertigen Produkts.

## 2. Was du über die Nachbar-Repos wissen musst

### `aSPARK` Core v0.3.1 — der Lieferant der Artefakte

Das Claude-Code-Plugin, das `.spark/`-Artefakte erzeugt, die dieses Repo parst. Es enthält heute
**keinen einzigen Verweis** auf `aspark-graph` — die Integrationsanleitung in
`docs/aspark-integration.md` ist Copy-Paste-Material für Zielprojekte. Das wird dort gerade behoben
(Core-Item C1, `tools/aspark-graph.md`). **Konsequenz für dich:** die Query-Oberfläche wird zum Vertrag.

**Normativ — nicht einseitig ändern:** Query-Namen (`get_node`, `story_trace`, `impact`, `gate_health`,
`staleness`, `find_nodes`, `get_neighbors`, `shortest_path`), ihre Argumentnamen, die Namensgleichheit
CLI↔MCP, JSON-auf-stdout, Exit 1 bei ungebautem Graph, und die Form
`{"found": false, "reason": …}`. Die Core-Skills rufen genau das auf. Umbenennungen brauchen einen
koordinierten Core-Change.

### `aspark-policy` v0.1.0 — noch nicht anschlussfähig

11 Packs, aber 8 Zeilen Python: kein Resolver, keine CLI, keine stabilen Pack-Identifier. **Deshalb wird
in diesem Backlog kein `Policy`-Knoten eingeführt** — erst reservieren, wenn dort `resolve` existiert und
Pack-IDs stabil sind.

### Reserviertes Vokabular (im Master-Dokument festgelegt, damit es nicht doppelt erfunden wird)

| Knoten | Quelle | Pflicht-Attribute |
|---|---|---|
| `Release` | `release-notes.md` Kopf-Tabelle + git-Tag | `version`, `status`, `date`, `commit` (nullable) |
| `Commit` | `git.py::log_records` | `sha`, `date`, `author_date` |

| Kante | Richtung |
|---|---|
| `released_as` | `Feature` → `Release` |
| `part_of` | `Commit` → `Feature` |

`Test` wird **nicht** als Knotentyp eingeführt, sondern als Attribut `is_test: bool` auf `Function`/`File`
— bewusste Entscheidung gegen Nomen-Inflation. `Policy` und `Debt` bleiben unbelegt.

---

## 3. Features in Abhängigkeitsreihenfolge

### G1 · `release-nodes` — Release und Commit als erstklassige Knoten

**Priorität: Sofort.** Vorbedingung für G2, für Debt-Modellierung und für alles, was einmal
`aSPARK-insights` heißen soll.

Der Ausgangspunkt ist besser als das Review annimmt: `artifacts.py` parst `release-notes.md` **schon**
(`_release_version`, `_status`) und stempelt `release_status` + `version` auf den Feature-Knoten
(`artifacts.py` ~Zeile 106). Und `git.py` liest Commits offline via `subprocess` (`log_records`,
`commits_touching`) — ohne neue Abhängigkeit, ohne Netz.

Was fehlt, ist die Promotion zu echten Knoten **mit Datum**, denn ohne Zeitstempel ist keine
Delivery-Metrik berechenbar.

Zu klären beim Umsetzen:
- **Commit-Auflösung.** Wie kommt `Release.commit` zustande — git-Tag passend zur Version, oder ein
  explizit in `release-notes.md` notierter SHA? Tag-Auflösung ist deterministisch und braucht keine
  Core-Änderung; sie scheitert aber, wenn ein Projekt anders taggt. Fällt sie aus, ist `commit` `null` —
  **nicht raten.**
- **Determinismus.** Ein `Release`-Knoten muss die byte-stabile Rebuild-Garantie (AC-1.2) einhalten. Die
  ID darf nur aus Feature + Version gebildet werden, niemals aus Build-Zeit.
- **Confidence.** Aus `release-notes.md` gelesene Werte sind `declared`. Aus git-Historie abgeleitete
  Zuordnungen sind `inferred`. Nicht vermischen.
- **`Commit`-Menge begrenzen.** Nicht die ganze Historie als Knoten materialisieren — nur Commits, die
  einem Feature zuordenbar sind (`commits_touching` hat die Logik bereits, inklusive der
  Cross-Feature-Kollisionsauflösung aus Commit `c8d7ce4`). Sonst explodiert `graph.json`.

```
/spark release-nodes — Release und Commit als erstklassige Knotentypen einführen.
Release aus der release-notes.md-Kopftabelle (version, status, date) plus Commit-Auflösung über den
git-Tag; Commit aus git.py::log_records, aber nur für Commits, die einem Feature zuordenbar sind.
Kanten: Feature -[released_as]-> Release, Commit -[part_of]-> Feature.
Bindend: byte-stabiler Rebuild (AC-1.2) bleibt erhalten, Node-IDs nur aus Inhalt und Ort,
declared vs. inferred nicht vermischen, keine geratenen Commits. Details in .spark/BACKLOG.md §3/G1.
```

---

### G2 · `dora-query` — 3 von 4 DORA-Metriken, ehrlich

**Priorität: Sofort, direkt nach G1.** Das Review sortiert DORA unter „Next" ein und hält es für Aufbau
eines Analytics-Produkts. Nach G1 ist es **eine Query**.

Berechenbar, deterministisch, offline:

| Metrik | Ableitung |
|---|---|
| **Deployment Frequency** | `Release`-Knoten pro Zeitfenster |
| **Lead Time for Changes** | erster `Commit` eines Features → `Release.date` |
| **Change Failure Rate** | Releases mit nachfolgenden Blocker/Major-`Finding`s oder `fail`-`QACheck`s ÷ alle Releases |

**MTTR bewusst nicht.** aSPARK hat kein Incident-Artefakt; jede Zahl dafür wäre erfunden. Die Query gibt
`"mttr": null` mit `"reason": "no incident artifact in aSPARK"` zurück. Das ist keine Lücke, sondern die
Glaubwürdigkeit, die dieses Produkt verkauft.

**Vorbehalt: die Bezugsgröße ist agenten-erzeugte Historie, nicht Team-Durchsatz.** In einem
SPARK-Projekt schreiben Agenten die Commits, und sie committen grobkörnig: `1f2c935`
(„ship v0.6.0") berührt 23 Dateien, `31b2a0d` 16 — ein Feature ist typischerweise *ein* Commit.
Damit misst Deployment Frequency die Kadenz des Agenten und der Release-Gates, und Lead Time
(erster `Commit` → `Release.date`) kollabiert auf die Dauer eines `/spark`-Durchlaufs. Beide Zahlen
sind deterministisch korrekt und als klassische Delivery-Metrik trotzdem irreführend — sie sind mit
Werten aus einem menschlich committeten Repo **nicht vergleichbar**.

Konsequenz beim Umsetzen, im Geist der MTTR-Entscheidung: die Query gibt die Zahlen aus, aber nie
nackt. Jede Metrik trägt die Grundgesamtheit mit, aus der sie stammt (Anzahl Releases, Anzahl
Commits, Median berührter Dateien pro Commit), damit der Leser die Grobkörnigkeit sieht statt sie
raten zu müssen. README und Query-Ausgabe sagen ausdrücklich, dass die Metrik den SPARK-Zyklus misst.
**Kein Benchmarking gegen DORA-Industriewerte** — das wäre dieselbe erfundene Zahl wie ein geratener
MTTR, nur besser getarnt.

Verwandt: `Commit`-Knoten aus AI-Historie speisen sich in denselben Agenten-Kontext zurück, aus dem
sie stammen (§3/G3). Eine Delivery-Zahl, die ein Agent über seine eigene Arbeit berechnet und dann
als Kontext wieder liest, braucht denselben Misstrauensvorschuss wie eine `inferred`-Kante.

Ebenfalls hier: `is_test`-Attribut auf `File`/`Function` (Erkennung über Pfad- und Namenskonventionen der
sechs unterstützten Sprachen), damit „Test" im Traceability-Pfad überhaupt auftaucht — **als Attribut, nicht
als Knotentyp.**

```
/spark dora-query — Query `dora` mit Deployment Frequency, Lead Time for Changes und Change Failure Rate
aus Release-, Commit-, Finding- und QACheck-Knoten. MTTR gibt explizit null mit Begründung zurück statt
einer erfundenen Zahl. Zusätzlich: is_test-Attribut auf File/Function (kein neuer Knotentyp).
Bindend: die Metriken messen agenten-erzeugte Historie, also trägt jede Zahl ihre Grundgesamtheit
mit (Releases, Commits, Median Dateien/Commit), und Query-Ausgabe wie README sagen ausdrücklich, dass
der SPARK-Zyklus gemessen wird — kein Benchmarking gegen DORA-Industriewerte.
Setzt release-nodes (G1) voraus. Details in .spark/BACKLOG.md §3/G2.
```

---

### G3 · `security-posture` — Threat-Model für einen bereits laufenden Server

**Priorität: Sofort. Betrifft ausgelieferten Code, nicht die Roadmap.**

Das Review verlangt ein MCP-Threat-Model und behandelt es als Dokumentationslücke für ein künftiges
Produkt. Es ist eine Lücke in v0.5.0. Zwei konkrete, am Code verifizierte Befunde:

**Befund 1 — die MCP-Oberfläche ist nicht read-only.** `build_graph` ist ein `@mcp.tool()`
(`server.py:21-22`). Der Server kann also auf Anweisung eines Agenten schreiben (`.aspark-graph/`).
Die Dokumentation legt „read-only context service" nahe. Das stimmt nicht.

**Befund 2 — `repo`/`path` sind unbeschränkt.** Jedes Tool nimmt `repo: str = "."` bzw. `path: str = "."`
ohne Confinement. Ein Agent — oder eine per präpariertem Artefakt/Codekommentar injizierte Anweisung — kann
den Server auf ein beliebiges Verzeichnis der Maschine richten, dessen Dateien parsen lassen und Inhalte
als Tool-Ausgabe zurückholen. Das ist ein konkreter Exfiltrationspfad, keine abstrakte MCP-Sorge.

Verschärfend, und der Kern des Threat-Models: **der Graph liest sowohl `.spark/`-Artefakte als auch
Quellcode und speist beides als Agenten-Kontext.** Damit ist jeder Inhalt, der in diesem Repo landen kann,
ein potenzieller Injection-Vektor — Text in einem Spec, ein Codekommentar, ein Finding.

Umfang:
- `SECURITY.md`: Bedrohungsmodell (STRIDE-Skizze reicht), Vertrauensgrenzen, was der Server ausdrücklich
  **nicht** garantiert, Meldeweg.
- Pfad-Confinement für `repo`/`path`, plus Größen-/Tiefenbegrenzung beim Parsen.
- Ehrliche Aussage zur Transport-Sicherheit: lokal, stdio, kein Auth, kein HTTP — und dass die
  `mcp<1.20`-Obergrenze im `pyproject.toml` genau deshalb steht (kein serverseitiges OAuth in Benutzung).
- Ein Absatz „Injection über Inhalte": Graph-Ausgabe ist Daten, keine Anweisung. Gehört auch nach
  `docs/aspark-integration.md`.

```
/spark security-posture — SECURITY.md mit Threat-Model für den ausgelieferten MCP-Server, plus
Pfad-Confinement für die unbeschränkten repo/path-Parameter aller MCP-Tools. Zwei zu adressierende
Befunde: (1) build_graph ist ein schreibendes MCP-Tool, die Doku suggeriert read-only;
(2) repo/path erlauben das Parsen beliebiger Verzeichnisse und damit einen Exfiltrationspfad.
Kern des Modells: der Graph speist Artefakt- und Quellcode-Inhalte als Agenten-Kontext, also ist
jeder Repo-Inhalt ein möglicher Injection-Vektor. Details in .spark/BACKLOG.md §3/G3.
```

---

### G4 · `pypi-publish` — Veröffentlichen

**Priorität: Danach.** Im `CLAUDE.md` bewusst als out-of-scope geführt („deferred; install-from-source
only, so keep the README free of `uvx`/PyPI claims"). Diese Zurückhaltung war korrekt, solange das Produkt
unreif war. Bei v0.5.0 ist „Install from a checkout of this repository" der größte Adoptionsblocker.

`dist/` enthält nur noch `0.3.0`-Artefakte — vor dem Publish neu bauen.

Zu beachten: Publish macht die Grammatik-Pins zu einem öffentlichen Determinismus-Versprechen. Die
Begründung dafür steht schon im `pyproject.toml` und sollte in die README-Install-Sektion wandern, damit
Nutzer verstehen, warum `uv.lock` Teil des Vertrags ist.

```
/spark pypi-publish — aspark-graph 0.5.x auf PyPI veröffentlichen. dist/ neu bauen (enthält nur 0.3.0),
README-Install-Sektion von "install from a checkout" auf den veröffentlichten Pfad umstellen und die
uv.lock/Grammatik-Pin-Begründung dort sichtbar machen. Die out-of-scope-Notiz im CLAUDE.md entsprechend
auflösen.
```

---

### G5 · `template-version-guard` — Drift als Versionskonflikt melden

**Priorität: Danach. Koordiniert mit Core — beide Repos im selben Zug.**

Heute pinnt `artifacts.py:34` `SUPPORTED_TEMPLATE = "aspark/0.1.0"` und `TemplateDriftError` rät
strukturell („task table missing a 'story' column"). Core-Templates tragen keine Versionsmarkierung, also
ist jede Core-Template-Änderung ein stiller Breaking Change hier.

**Core-Anteil (dort Item C3):** `<!-- aspark-template: aspark/0.1.0 -->` als erste Zeile jeder
Template-Datei. **Dein Anteil:** Marker lesen, wenn vorhanden, mit `SUPPORTED_TEMPLATE` vergleichen, bei
Abweichung einen expliziten Versionskonflikt melden — und bei **fehlendem** Marker unverändert auf die
heutige strukturelle Prüfung zurückfallen (Altbestand von Artefakten muss weiter bauen).

```
/spark template-version-guard — den optionalen Marker <!-- aspark-template: <version> --> in .spark-
Artefakten lesen und gegen SUPPORTED_TEMPLATE prüfen, um Template-Drift als klaren Versionskonflikt
statt als strukturelle Vermutung zu melden. Fehlender Marker fällt auf die heutige Strukturprüfung
zurück. Gegenseite ist Item C3 im aSPARK-Repo — nicht ohne sie releasen.
```

---

## 4. Bewusst nicht in diesem Backlog

| Review-Empfehlung | Warum nicht |
|---|---|
| Graph-Federation, Partitionierung, Multi-Million-Node-Betrieb | Zurückgestellt. Erst **messen**: es gibt `slow`-markierte Benchmarks im Repo — daraus einen ehrlichen Limit-Satz in die README schreiben ist billig und beantwortet die Kritik. Föderation ohne gemessenes Limit ist Architektur auf Verdacht. |
| `Policy`-Knoten | Blockiert: `aspark-policy` hat keine stabilen Pack-Identifier. |
| `Debt` als erstklassige Entität | Zurückgestellt bis nach G1/G2 — Debt braucht Zeitachse und Release-Bezug, sonst ist der „Interest Rate" nicht berechenbar. |
| `Test` als Knotentyp | Abgelehnt. Als `is_test`-Attribut in G2. |
| MTTR | Nicht ableitbar. Gibt in G2 explizit `null` mit Begründung zurück. |
| Neo4j / OSLC als Backend | Nicht adressiert. Lokal + NetworkX ist eine bewusste Entscheidung und Teil des Determinismus-Versprechens. |
