# -*- coding: utf-8 -*-
"""
Armazenamento simples em JSON para os eventos criados pelo bot.

Guarda tudo em data/events.json. Não é um banco de dados robusto,
mas é suficiente para um bot de inscrições de um servidor/comunidade
e sobrevive a reinícios do bot.
"""

import json
import os
from threading import Lock

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DATA_FILE = os.path.join(DATA_DIR, "events.json")

_lock = Lock()
_cache = None


def _ensure_loaded():
    global _cache
    if _cache is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                try:
                    _cache = json.load(f)
                except json.JSONDecodeError:
                    _cache = {}
        else:
            _cache = {}


def _persist():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(_cache, f, ensure_ascii=False, indent=2)


def load_all():
    """Retorna um dicionário {event_id: event_data} com todos os eventos."""
    with _lock:
        _ensure_loaded()
        return json.loads(json.dumps(_cache))


def get_event(event_id):
    """Retorna os dados de um evento (cópia) ou None se não existir."""
    with _lock:
        _ensure_loaded()
        ev = _cache.get(event_id)
        return json.loads(json.dumps(ev)) if ev is not None else None


def save_event(event_id, event):
    """Cria ou atualiza um evento."""
    with _lock:
        _ensure_loaded()
        _cache[event_id] = event
        _persist()


def delete_event(event_id):
    """Remove um evento do armazenamento."""
    with _lock:
        _ensure_loaded()
        if event_id in _cache:
            del _cache[event_id]
            _persist()
