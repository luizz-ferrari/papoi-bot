# -*- coding: utf-8 -*-
"""
Configuração das funções (roles) usadas nos eventos.

Cada função tem:
- key: identificador interno único (usado nos botões e no armazenamento)
- label: nome exibido
- emoji: emoji exibido no botão e no embed
- capacity: número de vagas para aquela função
- required_role: nome EXATO de um cargo do Discord que o membro precisa ter
  para conseguir se inscrever nessa função. Deixe como None para não exigir
  nenhum cargo específico.

  Exemplo: se só quem tem o cargo do Discord "Caller" pode se inscrever como
  Caller no evento, defina:
      {"key": "caller", ..., "required_role": "Caller"}

  A comparação ignora maiúsculas/minúsculas, mas o nome precisa ser igual ao
  cargo cadastrado no servidor (Configurações do Servidor > Cargos).

ROLE_TEMPLATES define um conjunto de limites por cargo para cada tamanho de
evento (25 ou 30 pessoas). Ao usar /evento criar, você escolhe o tamanho e o
bot usa o template correspondente.
"""

ROLE_TEMPLATES = {
    "25": [
        {"key": "caller", "label": "Caller", "emoji": "🔊", "capacity": 1, "required_role": "PP-Caller"},
        {"key": "defesa", "label": "Defesa", "emoji": "🛡️", "capacity": 2, "required_role": "PP-Defesa"},
        {"key": "flame", "label": "Flame", "emoji": "🔥", "capacity": 2, "required_role": "PP-Flame"},
        {"key": "elefante", "label": "Elefante", "emoji": "🐘", "capacity": 1, "required_role": "PP-Elefante"},
        {"key": "hwatcha", "label": "Hwatcha", "emoji": "💀", "capacity": 1, "required_role": "PP-Hwacha"},
        {"key": "shai", "label": "Shai", "emoji": "🎵", "capacity": 2, "required_role": "PP-Shai"},
        {"key": "ranged", "label": "Ranged", "emoji": "🏹", "capacity": 4, "required_role": "PP-Ranged"},
        {"key": "ataque", "label": "Ataque", "emoji": "⚔️", "capacity": 10, "required_role": "PP-Ataque"},
        {"key": "liao", "label": "Lião", "emoji": "🦁", "capacity": 3, "required_role": "PP-Especial"},
    ],
    "30": [
        {"key": "caller", "label": "Caller", "emoji": "🔊", "capacity": 1, "required_role": "PP-Caller"},
        {"key": "defesa", "label": "Defesa", "emoji": "🛡️", "capacity": 2, "required_role": "PP-Defesa"},
        {"key": "flame", "label": "Flame", "emoji": "🔥", "capacity": 2, "required_role": "PP-Flame"},
        {"key": "elefante", "label": "Elefante", "emoji": "🐘", "capacity": 1, "required_role": "PP-Elefante"},
        {"key": "hwatcha", "label": "Hwatcha", "emoji": "💀", "capacity": 1, "required_role": "PP-Hwacha"},
        {"key": "shai", "label": "Shai", "emoji": "🎵", "capacity": 2, "required_role": "PP-Shai"},
        {"key": "ranged", "label": "Ranged", "emoji": "🏹", "capacity": 5, "required_role": "PP-Ranged"},
        {"key": "ataque", "label": "Ataque", "emoji": "⚔️", "capacity": 15, "required_role": "PP-Ataque"},
        {"key": "liao", "label": "Lião", "emoji": "🦁", "capacity": 3, "required_role": "PP-Especial"},
    ],
}

# Mantido por compatibilidade (usado como padrão caso algo peça DEFAULT_ROLES).
DEFAULT_ROLES = ROLE_TEMPLATES["25"]

# Nome EXATO do cargo do Discord que pode usar /evento criar e /evento deletar
# (além de quem tem permissão "Gerenciar Servidor"/"Gerenciar Eventos").
# A comparação ignora maiúsculas/minúsculas.
STAFF_ROLE_NAME = "STAFF"

EMBED_COLOR = 0x5865F2
