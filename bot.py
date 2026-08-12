# -*- coding: utf-8 -*-
"""Ponto de entrada do bot."""

import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

import storage
from cogs.events import EventView

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# Nenhuma intent privilegiada é necessária: o bot só usa slash commands e botões.
intents = discord.Intents.default()


class NodewarBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.load_extension("cogs.events")

        # Re-registra as views persistentes de eventos já publicados
        # (necessário para os botões continuarem funcionando após reiniciar o bot).
        # Eventos ainda não publicados (agendados) recebem sua view quando a
        # tarefa de publicação automática os posta.
        events = storage.load_all()
        for event_id, event in events.items():
            message_id = event.get("message_id")
            if message_id:
                view = EventView(event_id)
                self.add_view(view, message_id=message_id)

        await self.tree.sync()


bot = NodewarBot()


@bot.event
async def on_ready():
    print(f"Conectado como {bot.user} (ID: {bot.user.id})")
    print("Bot pronto! Use /evento criar em um servidor para criar um evento.")


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit(
            "Defina a variável de ambiente DISCORD_TOKEN (crie um arquivo .env "
            "com base no .env.example) antes de iniciar o bot."
        )
    bot.run(TOKEN)
