# -*- coding: utf-8 -*-
"""
Cog responsável pelos eventos de inscrição (nodewar, guild boss, etc).

Fluxo:
1. /evento criar -> abre um formulário (modal)
2. Ao enviar:
   - se o campo "Agendar publicação" ficou vazio, o bot posta o evento na hora
   - se foi preenchido, o evento fica guardado e uma tarefa em segundo plano
     publica automaticamente no horário escolhido
3. O embed tem um botão por função. Cada clique inscreve/remove o usuário,
   com fila de espera automática quando a função está cheia. Quem é
   promovido da fila de espera recebe uma DM avisando.
4. Botões extras: "Não vou", "Recarregar" e "Deletar Evento".
"""

import datetime as dt
import uuid
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

import config
import embeds
import history
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


async def _notify_promotion(client: discord.Client, event: dict, role_key: str, uid: str):
    """Envia uma DM para quem acabou de ser promovido da fila de espera."""
    role_cfg = logic.get_roles_dict(event).get(role_key)
    if role_cfg is None:
        return

    try:
        user_id = int(uid)
    except ValueError:
        return

    try:
        user = client.get_user(user_id) or await client.fetch_user(user_id)
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
        pass  # usuário com DMs fechadas — ignora silenciosamente


async def _resolve_names(guild: discord.Guild, uids: list) -> list:
    """Resolve uma lista de IDs (strings) para nomes de exibição, para o histórico."""
    names = []
    for uid in uids:
        try:
            user_id = int(uid)
        except ValueError:
            continue
        member = guild.get_member(user_id) if guild else None
        if member is None and guild is not None:
            try:
                member = await guild.fetch_member(user_id)
            except (discord.NotFound, discord.HTTPException):
                member = None
        names.append(member.display_name if member else f"(saiu do servidor: {uid})")
    return names


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

        result, promoted = logic.toggle_role(event, interaction.user.id, self.role_key)
        storage.save_event(self.event_id, event)

        embed = embeds.build_embed(event)
        await interaction.response.edit_message(embed=embed, view=self.view)

        feedback = {
            "removed": "Você saiu dessa função.",
            "joined_active": "Você entrou na função! ✅",
            "joined_waiting": "Função cheia — você entrou na fila de espera. ⏳",
        }[result]
        await interaction.followup.send(feedback, ephemeral=True)

        for promoted_role_key, promoted_uid in promoted:
            await _notify_promotion(interaction.client, event, promoted_role_key, promoted_uid)


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

        result, promoted = logic.toggle_nao_vou(event, interaction.user.id)
        storage.save_event(self.event_id, event)

        embed = embeds.build_embed(event)
        await interaction.response.edit_message(embed=embed, view=self.view)

        feedback = "Você foi removido da lista de ausentes." if result == "removed" else "Marcado como ausente. ❌"
        await interaction.followup.send(feedback, ephemeral=True)

        for promoted_role_key, promoted_uid in promoted:
            await _notify_promotion(interaction.client, event, promoted_role_key, promoted_uid)


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


class ConcluirButton(discord.ui.Button):
    def __init__(self, event_id: str, row: int):
        super().__init__(
            label="Evento Concluído",
            emoji="✅",
            style=discord.ButtonStyle.success,
            custom_id=f"nw|{event_id}|concluir",
            row=row,
        )
        self.event_id = event_id

    async def callback(self, interaction: discord.Interaction):
        event = storage.get_event(self.event_id)
        if event is None:
            await interaction.response.send_message("Este evento já não existe mais.", ephemeral=True)
            return

        is_creator = str(interaction.user.id) == str(event["creator_id"])
        if not (is_creator or _is_staff(interaction.user)):
            await interaction.response.send_message(
                f"Apenas quem criou o evento ou membros com o cargo **{config.STAFF_ROLE_NAME}** "
                "podem marcá-lo como concluído.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        role_names = {}
        for role_key, rd in event["roles"].items():
            role_names[role_key] = await _resolve_names(guild, rd["active"])
        nao_vou_names = await _resolve_names(guild, event.get("nao_vou", []))

        tz = ZoneInfo(config.TIMEZONE)
        concluded_at_str = dt.datetime.now(tz).strftime("%d/%m/%Y %H:%M")

        history.add_event_record(event, role_names, nao_vou_names, concluded_at_str, interaction.user.display_name)

        embed = embeds.build_embed(event)
        embed.title = f"✅ {event['title']} — Concluído"
        embed.color = discord.Color.green()
        embed.set_footer(
            text=f"Evento concluído por {interaction.user.display_name} em {concluded_at_str} "
            "— registrado no histórico."
        )

        await interaction.message.edit(embed=embed, view=None)
        await interaction.followup.send(
            "Evento marcado como concluído e adicionado ao histórico em Excel. Use `/evento historico` "
            "para baixar a planilha. ✅",
            ephemeral=True,
        )

        storage.delete_event(self.event_id)


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

        if roles:
            last_role_row = (len(roles) - 1) // 5
            items_in_last_row = len(roles) - last_role_row * 5
            nao_vou_row = last_role_row if items_in_last_row < 5 else last_role_row + 1
        else:
            nao_vou_row = 0
        self.add_item(NaoVouButton(event_id, nao_vou_row))

        util_row = min(nao_vou_row + 1, 4)
        self.add_item(RecarregarButton(event_id, util_row))
        self.add_item(DeletarButton(event_id, util_row))
        self.add_item(ConcluirButton(event_id, util_row))


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
    agendar_para = discord.ui.TextInput(
        label="Agendar publicação (opcional)",
        placeholder="DD/MM/AAAA HH:MM — deixe vazio para publicar agora",
        required=False,
        max_length=20,
    )

    def __init__(self, tamanho: str):
        super().__init__(title=f"Criar Evento — {tamanho} pessoas")
        self.tamanho = tamanho

    async def on_submit(self, interaction: discord.Interaction):
        publish_at_iso = None
        publish_dt_local = None

        raw_data = str(self.agendar_para.value).strip() if self.agendar_para.value else ""
        if raw_data:
            try:
                naive = dt.datetime.strptime(raw_data, "%d/%m/%Y %H:%M")
            except ValueError:
                await interaction.response.send_message(
                    "Data/hora de agendamento inválida. Use o formato **DD/MM/AAAA HH:MM**, "
                    "ex: `19/07/2026 20:00`.",
                    ephemeral=True,
                )
                return

            tz = ZoneInfo(config.TIMEZONE)
            publish_dt_local = naive.replace(tzinfo=tz)
            now_local = dt.datetime.now(tz)

            if publish_dt_local <= now_local:
                await interaction.response.send_message(
                    "A data/hora de agendamento precisa ser no futuro.", ephemeral=True
                )
                return

            publish_at_iso = publish_dt_local.astimezone(dt.timezone.utc).isoformat()

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
            "max_participants": max_p,
            "roles_config": roles_config,
            "roles": {r["key"]: {"active": [], "waiting": []} for r in roles_config},
            "nao_vou": [],
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "publish_at": publish_at_iso,
            "published": publish_at_iso is None,
        }
        storage.save_event(event_id, event)

        if publish_at_iso is None:
            # Sem agendamento: publica imediatamente, como antes.
            view = EventView(event_id)
            embed = embeds.build_embed(event)

            await interaction.response.send_message(embed=embed, view=view)
            msg = await interaction.original_response()

            event["message_id"] = msg.id
            storage.save_event(event_id, event)
            interaction.client.add_view(view, message_id=msg.id)
        else:
            timestamp = int(publish_dt_local.timestamp())
            await interaction.response.send_message(
                f"📅 Evento agendado! Vou publicar automaticamente neste canal em "
                f"<t:{timestamp}:F> (<t:{timestamp}:R>).",
                ephemeral=True,
            )


# --------------------------------------------------------------------------- #
# Cog / comandos
# --------------------------------------------------------------------------- #

class EventosCog(commands.GroupCog, name="evento", description="Gerencia eventos de inscrição"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
        self.publish_scheduled_events.start()
        self.cleanup_old_data.start()

    def cog_unload(self):
        self.publish_scheduled_events.cancel()
        self.cleanup_old_data.cancel()

    @tasks.loop(seconds=30)
    async def publish_scheduled_events(self):
        now_utc = dt.datetime.now(dt.timezone.utc)
        events = storage.load_all()
        for event_id, event in events.items():
            if event.get("published", True):
                continue
            publish_at = event.get("publish_at")
            if not publish_at:
                continue
            try:
                scheduled = dt.datetime.fromisoformat(publish_at)
            except ValueError:
                continue
            if scheduled <= now_utc:
                await self._publish_event(event_id, event)

    @publish_scheduled_events.before_loop
    async def before_publish_scheduled_events(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=24)
    async def cleanup_old_data(self):
        """
        Apaga automaticamente dados com mais de config.DATA_RETENTION_DAYS
        dias: eventos esquecidos (nunca concluídos/deletados) e linhas
        antigas do histórico em Excel. Roda uma vez por dia.
        """
        removed_events = storage.purge_old_events(config.DATA_RETENTION_DAYS)
        for event_id, event in removed_events:
            channel_id = event.get("channel_id")
            message_id = event.get("message_id")
            if not (channel_id and message_id):
                continue
            channel = self.bot.get_channel(channel_id)
            if channel is None:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    continue
            try:
                msg = await channel.fetch_message(message_id)
                await msg.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        removed_rows = history.purge_old_records(config.DATA_RETENTION_DAYS)

        if removed_events or removed_rows:
            print(
                f"[limpeza automática] {len(removed_events)} evento(s) antigo(s) removido(s), "
                f"{removed_rows} linha(s) do histórico removida(s) "
                f"(retenção: {config.DATA_RETENTION_DAYS} dias)."
            )

    @cleanup_old_data.before_loop
    async def before_cleanup_old_data(self):
        await self.bot.wait_until_ready()

    async def _publish_event(self, event_id: str, event: dict):
        channel = self.bot.get_channel(event["channel_id"])
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(event["channel_id"])
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                return

        view = EventView(event_id)
        embed = embeds.build_embed(event)
        try:
            msg = await channel.send(embed=embed, view=view)
        except discord.HTTPException:
            return

        event["message_id"] = msg.id
        event["published"] = True
        storage.save_event(event_id, event)
        self.bot.add_view(view, message_id=msg.id)

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

    @app_commands.command(name="historico", description="Baixa a planilha com o histórico de eventos concluídos")
    async def historico(self, interaction: discord.Interaction):
        if interaction.guild is None:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return

        if not _is_staff(interaction.user):
            await interaction.response.send_message(
                f"Apenas membros com o cargo **{config.STAFF_ROLE_NAME}** podem acessar o histórico.",
                ephemeral=True,
            )
            return

        if not history.history_file_exists():
            await interaction.response.send_message("Ainda não há eventos concluídos no histórico.", ephemeral=True)
            return

        await interaction.response.send_message(
            "📊 Histórico de eventos concluídos:",
            file=discord.File(history.HISTORY_FILE),
            ephemeral=True,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(EventosCog(bot))
