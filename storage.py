# -*- coding: utf-8 -*-
"""
Armazenamento simples em JSON para os eventos criados pelo bot.

Guarda tudo em data/events.json. Não é um banco de dados robusto,
mas é suficiente para um bot de inscrições de um servidor/comunidade
e sobrevive a reinícios do bot.
"""

import datetime as dt
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


def purge_old_events(max_age_days):
    """
    Remove eventos criados há mais de `max_age_days` dias (independente de
    já terem sido publicados ou não) — evita que eventos esquecidos/nunca
    concluídos fiquem acumulando para sempre.

    Eventos sem "created_at" (criados por uma versão antiga do bot) não são
    removidos automaticamente, por segurança.

    Retorna a lista de (event_id, event_data) que foram removidos, para que
    quem chamou possa, por exemplo, tentar apagar a mensagem no Discord.
    """
    with _lock:
        _ensure_loaded()
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_age_days)
        removed = []
        for event_id in list(_cache.keys()):
            event = _cache[event_id]
            created_at = event.get("created_at")
            if not created_at:
                continue
            try:
                created_dt = dt.datetime.fromisoformat(created_at)
            except ValueError:
                continue
            if created_dt <= cutoff:
                removed.append((event_id, json.loads(json.dumps(event))))
                del _cache[event_id]
        if removed:
            _persist()
        return removed
