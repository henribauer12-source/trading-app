"""Datenquellen-Adapter.

Jede Quelle liefert geprüfte ``Bar``-Objekte. Rohe dicts verlassen ein
Adapter-Modul nicht — sonst wandert die Eingangsprüfung an den Aufrufer,
und dort wird sie vergessen.
"""
