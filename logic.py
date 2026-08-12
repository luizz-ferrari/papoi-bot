# -*- coding: utf-8 -*-
"""
Regras de negócio das inscrições:
- um usuário só pode estar em UMA função (ou em "não vou") por vez
- clicar de novo na função em que já está remove a inscrição
- se a função estiver cheia, o usuário entra na fila de espera (waitlist)
- ao sair alguém de uma função cheia, o primeiro da fila de espera sobe
  automaticamente para a lista principal
"""


def get_roles_dict(event):
    return {r["key"]: r for r in event["roles_config"]}


def find_user_location(event, user_id):
    """
    Retorna (tipo, role_key) indicando onde o usuário está:
    - ("active", role_key)
    - ("waiting", role_key)
    - ("nao_vou", None)
    - None se não estiver inscrito em nada
    """
    uid = str(user_id)
    for role_key, rd in event["roles"].items():
        if uid in rd["active"]:
            return ("active", role_key)
        if uid in rd["waiting"]:
            return ("waiting", role_key)
    if uid in event.get("nao_vou", []):
        return ("nao_vou", None)
    return None


def remove_user(event, user_id):
    """
    Remove o usuário de qualquer função/fila/"não vou" em que esteja.
    Retorna uma lista de tuplas (role_key, promoted_user_id) para cada
    pessoa que foi promovida da fila de espera para a lista ativa como
    consequência dessa remoção.
    """
    uid = str(user_id)
    promotions = []
    for role_key, rd in event["roles"].items():
        if uid in rd["active"]:
            rd["active"].remove(uid)
            if rd["waiting"]:
                promoted_uid = rd["waiting"].pop(0)
                rd["active"].append(promoted_uid)
                promotions.append((role_key, promoted_uid))
        elif uid in rd["waiting"]:
            rd["waiting"].remove(uid)
    if uid in event.get("nao_vou", []):
        event["nao_vou"].remove(uid)
    return promotions


def toggle_role(event, user_id, role_key):
    """
    Alterna a inscrição do usuário na função `role_key`.
    Retorna (resultado, promocoes):
    - resultado: "removed" | "joined_active" | "joined_waiting"
    - promocoes: lista de (role_key, promoted_user_id) — quem subiu da fila
      de espera por causa dessa ação
    """
    uid = str(user_id)
    loc = find_user_location(event, user_id)

    if loc is not None and loc[0] in ("active", "waiting") and loc[1] == role_key:
        promotions = remove_user(event, user_id)
        return "removed", promotions

    promotions = remove_user(event, user_id)
    rd = event["roles"].setdefault(role_key, {"active": [], "waiting": []})
    cap = get_roles_dict(event)[role_key]["capacity"]

    if len(rd["active"]) < cap:
        rd["active"].append(uid)
        return "joined_active", promotions

    if uid not in rd["waiting"]:
        rd["waiting"].append(uid)
    return "joined_waiting", promotions


def toggle_nao_vou(event, user_id):
    """Alterna o status "não vou" do usuário. Retorna (resultado, promocoes)."""
    uid = str(user_id)
    loc = find_user_location(event, user_id)

    if loc is not None and loc[0] == "nao_vou":
        event["nao_vou"].remove(uid)
        return "removed", []

    promotions = remove_user(event, user_id)
    event.setdefault("nao_vou", []).append(uid)
    return "joined", promotions


def total_confirmed(event):
    return sum(len(rd["active"]) for rd in event["roles"].values())


def has_required_role(member, required_role_name):
    """
    Verifica se `member` (discord.Member) possui um cargo do Discord com o
    nome `required_role_name` (comparação sem diferenciar maiúsculas/
    minúsculas). Se `required_role_name` for None/vazio, não há restrição.
    """
    if not required_role_name:
        return True
    target = required_role_name.strip().lower()
    return any(r.name.strip().lower() == target for r in getattr(member, "roles", []))
