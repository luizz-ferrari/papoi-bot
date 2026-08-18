# -*- coding: utf-8 -*-
"""Monta o embed (cartão) do evento, no mesmo estilo das imagens de referência."""

import discord

import config
import logic


def build_embed(event: dict) -> discord.Embed:
    embed = discord.Embed(
        title=event["title"],
        description=f'"{event["description"]}"' if event.get("description") else None,
        color=config.EMBED_COLOR,
    )

    embed.add_field(name="Organizador", value=event.get("creator_name", "—"), inline=True)

    total = logic.total_confirmed(event)
    embed.add_field(
        name=f'👥 Participantes ({total}/{event["max_participants"]})',
        value="\u200b",
        inline=False,
    )

    for role in event["roles_config"]:
        rd = event["roles"].get(role["key"], {"active": [], "waiting": []})
        active = rd["active"]
        waiting = rd["waiting"]
        cap = role["capacity"]

        lines = [f"<@{uid}>" for uid in active] if active else ["vazio"]
        if waiting:
            lines.append("⏳ *Waitlist:*")
            lines.extend(f"<@{uid}>" for uid in waiting)

        embed.add_field(
            name=f'{role["emoji"]} {role["label"]} ({len(active)}/{cap})',
            value="\n".join(lines),
            inline=True,
        )

    nao_vou = event.get("nao_vou", [])
    nv_lines = [f"<@{uid}>" for uid in nao_vou] if nao_vou else ["vazio"]
    embed.add_field(
        name=f"❌ Não vou ({len(nao_vou)}/∞)",
        value="\n".join(nv_lines),
        inline=True,
    )

    embed.set_footer(text="Clique nos botões abaixo para se inscrever ou sair de uma função.")
    return embed
