# Design-Anleitung

## Grundsatz

Die Oberfläche soll ruhig, kompakt und klar bedienbar bleiben. Keine groben, klobigen Elemente und keine unnötig dominanten Rahmen, wenn eine einfache Textzeile reicht.

## Kleine Aufklapp-Funktionen

Für interne Detail-Aufklapper wie `Eingabedaten und Trace anzeigen`, `LLM Analyse-Historie anzeigen`, Diagnose-, Trace- oder Historie-Zeilen gilt:

- Geschlossen: blauer Text mit kleinem Pfeil davor.
- Offen: grauer Text ohne Pfeil.
- Die Zeile bleibt schlicht im bestehenden Feld.
- Keine zusätzliche große Leiste.
- Keine neue dominante Rahmen- oder Button-Optik.
- Kein eigener großer farbiger Balken.
- Vorhandene Container-/Feldstruktur bleibt erhalten.

Diese Regel gilt nur für kleine interne Detail-Aufklapper, nicht für große Hauptbereiche.

## Hauptbereiche

Große Bereiche wie `Bot Übersicht`, `Bot Steuerung`, `LLM Rollenteam`, `LLM Status / Kosten`, `Live-Analyse Pipeline`, `Trades / Bot Daten`, `Debug / Lernspeicher` und `Letzter Zyklus` dürfen als eigene Header-/Section-Zeilen dargestellt werden.

Dashboard-Section-Header wie `Bot Steuerung` sind die Vorlage für vergleichbare Hauptbereiche im Projekt.

Für Hauptbereiche gilt:

- Kompakte Header.
- Klare linke Farbakzentkante.
- Sehr leichter semantischer Hintergrund-Tint passend zur Farbakzentkante.
- Eingeklappt läuft die Farbakzentkante über die komplette geschlossene Header-Zeile.
- Ausgeklappt läuft die Farbakzentkante nur im Headerbereich und nicht durch den kompletten Inhalt.
- Ausgeklappt bleibt der Header optisch farbbetont wie beim Dashboard-Beispiel `LLM Rollenteam`: farbiger Header-Tint, linke Akzentkante, kleiner `Einklappen`-Button rechts.
- Der Inhaltsbereich darunter bleibt neutral dunkel und bekommt keine weiterlaufende farbige Seitenkante.
- Einheitlicher Abstand zwischen Bereichen.
- `Aufklappen` darf als kleiner Button dargestellt werden.
- Kein überladener Karten-Look.
- Kein dicker farbiger Rahmen um den ganzen Bereich.
- Der Titel steht links oben, die kurze Beschreibung direkt darunter.
- Der Aktionsbutton steht rechts und bleibt klein, rechteckig und ruhig.

## Farblogik

Farben werden semantisch zugeordnet und nicht zufällig pro Kachel gewählt:

- Türkis: Übersicht, Bestände, Trades und normale Datenbereiche.
- Blau: Steuerung, aktive Bedienung, Start/Stop/Reload.
- Cyan: LLM, Rollenberichte, Provider, Kosten und Modellstatus.
- Gelb/Amber: Pipeline, Entscheidungsfluss, Planung, Gate-Status.
- Orange: Debug, technische Diagnose, Lernspeicher und Fehleranalyse.
- Violett: letzter Zyklus, Rohdaten, Historie und Trace-ähnliche Inhalte.

Der Farbakzent soll primär über die linke Kante laufen. Ein sehr leichter Hintergrund-Tint ist erlaubt, darf aber nicht dominant wirken.

## Dashboard-Aufmachung

Das Dashboard ist ein zusammenhängendes Hauptfenster, das mehrere Bereiche umfasst. Es soll wie ein ruhiger Arbeitsbereich wirken, nicht wie lose Karten.

- Der komplette Dashboard-Container nutzt den dunklen Feld-Hintergrund `var(--panel)`.
- Der Dashboard-Header steht oben im gleichen Feld und ist nicht extra eingerahmt.
- Der Header zeigt links `Dashboard` und rechts eine kurze Beschreibung in ruhigem, uppercase Text.
- Zwischen Header und Inhalt reicht eine dezente Trennlinie.
- Die einzelnen Bereiche liegen innerhalb dieses gemeinsamen Feldes.
- Bereichsheader bleiben kompakt und nutzen ihre linke Farbakzentkante.
- Die äußere Dashboard-Fläche darf nicht heller oder transparenter wirken als der Strategy-Setup-Arbeitsbereich.
- Keine zusätzliche Rahmenverschachtelung um den Dashboard-Titel.

Aktuelle Dashboard-Bereiche:

- `Bot Übersicht`
- `Bot Steuerung`
- `LLM Rollenteam`
- `LLM Status / Kosten`
- `Live-Analyse Pipeline`
- `Trades / Bot Daten`
- `Debug / Lernspeicher`
- `Letzter Zyklus`

## Strategie Setup

Das Strategie Setup soll wie ein Arbeitsbereich wirken, nicht wie eine Sammlung großer Einzelkarten.

- Analysten-Rollen sind die Hauptstruktur.
- Datenquellen bleiben im Feld ihres Analysten.
- Inaktive Datenquellen werden nicht in ein separates Inaktiv-Feld verschoben.
- Nur aktive Datenquellen werden an das LLM-Rollenteam übergeben.
- LLM-Rollen zeigen Prompt, Daten und Antwort nachvollziehbar an.

## Sprache und Text

- Deutsche Umlaute korrekt schreiben: ä, ö, ü, Ä, Ö, Ü, ß.
- Keine Mojibake-/Hieroglyphen-Texte oder defekte Ersatzzeichen.
- Sichtbare Begriffe sollen fachlich passen: eher `Signalquelle`, `Datenquelle`, `Analyst`, `Rolle`, `CEO/Judge` statt überall `Agent`.
- Texte kurz und funktional halten.

## Bedienbarkeit

- Buttons und Eingaben sollen ihre Größe nicht beim Umschalten ändern.
- Abstände zwischen Tabs, Feldern und Bereichen sollen einheitlich bleiben.
- Aufklappen/Einklappen darf keine Bereiche verschieben, die nicht betroffen sind.
- Setup speichern muss gut erreichbar und sichtbar bleiben.
- Keine unnötigen Hover-Dim-Effekte.

## LLM-Anzeige

Die LLM-Ansicht soll zeigen:

- Verbindung und Provider.
- Letzter Rollenlauf.
- Gesendete Datenquellen.
- Rollenberichte.
- CEO/Judge-Entscheidung.
- Eingabedaten und Trace.
- Analyse-Historie mit Skip-Gründen, z. B. aktive Order.

Die Unterhaltung der Rollen ist wichtiger als reine Indikator-Tabellen.
