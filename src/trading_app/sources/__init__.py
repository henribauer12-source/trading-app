"""Datenquellen-Adapter.

Jede Quelle liefert geprüfte ``Bar``-Objekte oder, bei ``dokumente``, eine
abgelegte PDF-Datei. Rohe dicts verlassen ein Adapter-Modul nicht — sonst wandert die Eingangsprüfung an den Aufrufer,
und dort wird sie vergessen.
"""
