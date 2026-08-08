# -*- coding: utf-8 -*-
"""
Cog responsável pelos eventos de inscrição (nodewar, guild boss, etc).

Fluxo:
1. /evento criar -> abre um formulário (modal)
2. Ao enviar, o bot posta um embed com botões (uma função por botão)
3. Cada clique inscreve/remove o usuário daquela função, com fila de espera
   automática quando a função está cheia
4. Botões extras: "Não vou", "Recarregar" e "Deletar Evento"
"""

import uuid

import discord
from discord import app_commands
from discord.ext import commands

import config
import embeds
import logic
import storage


def _is_staff(member: discord.Member) -> bool:
    """
    True se `member` pode gerenciar eventos: tem o cargo STAFF_ROLE_NAME
    (definido em config.py) ou tem permissão "Gerenciar Servidor"/
    "Gerenciar Eventos" no Discord.
    """
    perms = member.guild_permissions
    if perms.manage_guild or perms.manage_events:
        return True
    return logic.has_required_role(member, config.STAFF_ROLE_NAME)


async def _notify_promotion(interaction: discord.Interaction, event: dict, role_key: str, uid: str):
    """Envia uma DM para quem acabou de ser promovido da fila de espera."""
    role_cfg = logic.get_roles_dict(event).get(role_key)
    if role_cfg is None:
        return

    try:
        user_id = int(uid)
    except ValueError:
        return

    try:
        user = interaction.client.get_user(user_id) or await interaction.client.fetch_user(user_id)
    except (discord.NotFound, discord.HTTPException):
        return
    if user is None:
        return

    jump_url = None
    if event.get("guild_id") and event.get("channel_id") and event.get("message_id"):
        jump_url = (
            f"https://discord.com/channels/"
            f"{event['guild_id']}/{event['channel_id']}/{event['message_id']}"
        )

    text = (
        f"🎉 Saiu uma vaga e você foi promovido da fila de espera para a função "
        f"**{role_cfg['emoji']} {role_cfg['label']}** no evento **{event['title']}**!"
    )
    if jump_url:
        text += f"\n{jump_url}"

    try:
        await user.send(text)
    except (discord.Forbidden, discord.HTTPException):
        pass

# --------------------------------------------------------------------------- #
# Botões
# --------------------------------------------------------------------------- #

class RoleButton(discord.ui.Button):
    def __init__(self, event_id: str, role: dict, row: int):
        super().__init__(
            label=role["label"],
            emoji=role["emoji"],
            style=discord.ButtonStyle.secondary,
            custom_id=f"nw|{event_id}|role|{role['key']}",
            row=row,
        )
        self.event_id = event_id
        self.role_key = role["key"]

    async def callback(self, interaction: discord.Interaction):
        event = storage.get_event(self.event_id)
        if event is None:
            await interaction.response.send_message("Este evento não existe mais.", ephemeral=True)
            return

        loc = logic.find_user_location(event, interaction.user.id)
        is_removal = loc is not None and loc[0] in ("active", "waiting") and loc[1] == self.role_key

        if not is_removal:
            role_cfg = logic.get_roles_dict(event)[self.role_key]
            required_role = role_cfg.get("required_role")
            if not logic.has_required_role(interaction.user, required_role):
                await interaction.response.send_message(
                    f"Você precisa ter o cargo **{required_role}** no servidor para se inscrever em "
                    f"{role_cfg['emoji']} {role_cfg['label']}.",
                    ephemeral=True,
                )
                return

        result, promotion = logic.toggle_role(
            event,
            interaction.user.id,
            self.role_key,
)

        storage.save_event(self.event_id, event)

        embed = embeds.build_embed(event)
        await interaction.response.edit_message(embed=embed, view=self.view)

        if promotion is not None:
            promoted_uid, promoted_role_key = promotion

            await _notify_promotion(
                interaction,
                event,
                promoted_role_key,
                promoted_uid,
            )

        feedback = {
            "removed": "Você saiu dessa função.",
            "joined_active": "Você entrou na função! ✅",
            "joined_waiting": "Função cheia — você entrou na fila de espera. ⏳",
        }[result]
        await interaction.followup.send(feedback, ephemeral=True)


class NaoVouButton(discord.ui.Button):
    def __init__(self, event_id: str, row: int):
        super().__init__(
            label="Não vou",
            emoji="❌",
            style=discord.ButtonStyle.danger,
            custom_id=f"nw|{event_id}|naovou",
            row=row,
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        event = storage.get_event(self.event_id)
        if event is None:
            await interaction.response.send_message("Este evento não existe mais.", ephemeral=True)
            return

        result, promotion = logic.toggle_nao_vou(
        event,
        interaction.user.id,
        )

        storage.save_event(self.event_id, event)

        embed = embeds.build_embed(event)
        await interaction.response.edit_message(embed=embed, view=self.view)

        if promotion is not None:
            promoted_uid, promoted_role_key = promotion

        await _notify_promotion(
        interaction,
        event,
        promoted_role_key,
        promoted_uid,
        )

        feedback = (
        "Você foi removido da lista de ausentes."
        if result == "removed"
        else "Marcado como ausente. ❌"
        )

        await interaction.followup.send(feedback, ephemeral=True)


class RecarregarButton(discord.ui.Button):
    def __init__(self, event_id: str, row: int):
        super().__init__(
            label="Recarregar",
            emoji="🔄",
            style=discord.ButtonStyle.secondary,
            custom_id=f"nw|{event_id}|recarregar",
            row=row,
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        event = storage.get_event(self.event_id)
        if event is None:
            await interaction.response.send_message("Este evento não existe mais.", ephemeral=True)
            return

        embed = embeds.build_embed(event)
        await interaction.response.edit_message(embed=embed, view=self.view)


class DeletarButton(discord.ui.Button):
    def __init__(self, event_id: str, row: int):
        super().__init__(
            label="Deletar Evento",
            emoji="🗑️",
            style=discord.ButtonStyle.danger,
            custom_id=f"nw|{event_id}|deletar",
            row=row,
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        event = storage.get_event(self.event_id)
        if event is None:
            await interaction.response.send_message("Este evento já foi deletado.", ephemeral=True)
            return

        is_creator = str(interaction.user.id) == str(event["creator_id"])

        if not (is_creator or _is_staff(interaction.user)):
            await interaction.response.send_message(
                f"Apenas quem criou o evento ou membros com o cargo **{config.STAFF_ROLE_NAME}** "
                "podem deletá-lo.",
                ephemeral=True,
            )
            return

        storage.delete_event(self.event_id)
        await interaction.response.send_message("Evento deletado. 🗑️", ephemeral=True)
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass


# --------------------------------------------------------------------------- #
# View
# --------------------------------------------------------------------------- #

class EventView(discord.ui.View):
    """View persistente (timeout=None) reconstruída a partir dos dados salvos."""

    def __init__(self, event_id: str):
        super().__init__(timeout=None)
        self.event_id = event_id

        event = storage.get_event(event_id)
        if event is None:
            return

        roles = event["roles_config"]
        for idx, role in enumerate(roles):
            row = idx // 5
            self.add_item(RoleButton(event_id, role, row))

        nao_vou_row = (len(roles) // 5)
        self.add_item(NaoVouButton(event_id, nao_vou_row))

        util_row = min(nao_vou_row + 1, 4)
        self.add_item(RecarregarButton(event_id, util_row))
        self.add_item(DeletarButton(event_id, util_row))


# --------------------------------------------------------------------------- #
# Modal de criação
# --------------------------------------------------------------------------- #

class CreateEventModal(discord.ui.Modal):
    titulo = discord.ui.TextInput(
        label="Título",
        placeholder="Ex: NODEWAR T1 - 25",
        max_length=100,
    )
    descricao = discord.ui.TextInput(
        label="Descrição",
        placeholder="Ex: Roubo de vagas as 20:30",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph,
    )
    inicio = discord.ui.TextInput(
        label="Início",
        placeholder="Ex: 2026-07-19 21:00 GMT-3",
        max_length=50,
    )
    fechamento = discord.ui.TextInput(
        label="Fechamento RSVP",
        placeholder="Ex: 2026-07-20 20:59 GMT-3",
        max_length=50,
    )

    def __init__(self, tamanho: str):
        super().__init__(title=f"Criar Evento — {tamanho} pessoas")
        self.tamanho = tamanho

    async def on_submit(self, interaction: discord.Interaction):
        roles_config = config.ROLE_TEMPLATES[self.tamanho]
        max_p = int(self.tamanho)

        event_id = uuid.uuid4().hex
        event = {
            "guild_id": interaction.guild_id,
            "channel_id": interaction.channel_id,
            "message_id": None,
            "creator_id": str(interaction.user.id),
            "creator_name": interaction.user.display_name,
            "title": str(self.titulo.value),
            "description": str(self.descricao.value) if self.descricao.value else "",
            "start": str(self.inicio.value),
            "rsvp_close": str(self.fechamento.value),
            "max_participants": max_p,
            "roles_config": roles_config,
            "roles": {r["key"]: {"active": [], "waiting": []} for r in roles_config},
            "nao_vou": [],
        }
        storage.save_event(event_id, event)

        view = EventView(event_id)
        embed = embeds.build_embed(event)

        await interaction.response.send_message(embed=embed, view=view)
        msg = await interaction.original_response()

        event["message_id"] = msg.id
        storage.save_event(event_id, event)
        interaction.client.add_view(view, message_id=msg.id)


# --------------------------------------------------------------------------- #
# Cog / comandos
# --------------------------------------------------------------------------- #

class EventosCog(commands.GroupCog, name="evento", description="Gerencia eventos de inscrição"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()

    @app_commands.command(name="criar", description="Cria um novo evento de inscrição (nodewar, guild boss, etc.)")
    @app_commands.describe(tamanho="Tamanho do evento — define o limite de vagas por cargo")
    @app_commands.choices(
        tamanho=[
            app_commands.Choice(name="25 pessoas", value="25"),
            app_commands.Choice(name="30 pessoas", value="30"),
        ]
    )
    async def criar(self, interaction: discord.Interaction, tamanho: app_commands.Choice[str]):
        if interaction.guild is None:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return

        if not _is_staff(interaction.user):
            await interaction.response.send_message(
                f"Apenas membros com o cargo **{config.STAFF_ROLE_NAME}** podem criar eventos.",
                ephemeral=True,
            )
            return

        await interaction.response.send_modal(CreateEventModal(tamanho.value))


async def setup(bot: commands.Bot):
    await bot.add_cog(EventosCog(bot))