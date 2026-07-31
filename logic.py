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
    Remove o usuário de qualquer função/fila/"não vou".

    Retorna:
        (user_id_promovido, role_key) caso alguém seja promovido;
        None caso nenhuma promoção aconteça.
    """
    uid = str(user_id)
    promotion = None

    for role_key, rd in event["roles"].items():
        if uid in rd["active"]:
            rd["active"].remove(uid)

            if rd["waiting"]:
                promoted = rd["waiting"].pop(0)
                rd["active"].append(promoted)
                promotion = (promoted, role_key)

        elif uid in rd["waiting"]:
            rd["waiting"].remove(uid)

    if uid in event.get("nao_vou", []):
        event["nao_vou"].remove(uid)

    return promotion


def toggle_role(event, user_id, role_key):
    """
    Alterna a inscrição do usuário na função.

    Retorna:
        (resultado, promotion)

    promotion será:
        (user_id_promovido, role_key)
    ou:
        None
    """
    uid = str(user_id)
    loc = find_user_location(event, user_id)

    if (
        loc is not None
        and loc[0] in ("active", "waiting")
        and loc[1] == role_key
    ):
        promotion = remove_user(event, user_id)
        return "removed", promotion

    # Se estava em outra função, pode abrir vaga nela e promover alguém.
    promotion = remove_user(event, user_id)

    rd = event["roles"].setdefault(
        role_key,
        {"active": [], "waiting": []},
    )
    cap = get_roles_dict(event)[role_key]["capacity"]

    if len(rd["active"]) < cap:
        rd["active"].append(uid)
        return "joined_active", promotion

    if uid not in rd["waiting"]:
        rd["waiting"].append(uid)

    return "joined_waiting", promotion


def toggle_nao_vou(event, user_id):
    """
    Alterna o status "não vou".

    Retorna:
        (resultado, promotion)
    """
    uid = str(user_id)
    loc = find_user_location(event, user_id)

    if loc is not None and loc[0] == "nao_vou":
        event["nao_vou"].remove(uid)
        return "removed", None

    promotion = remove_user(event, user_id)
    event.setdefault("nao_vou", []).append(uid)

    return "joined", promotion


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
