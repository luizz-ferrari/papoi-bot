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
        {"key": "defesa", "label": "Defesa", "emoji": "🛡️", "capacity": 1, "required_role": "PP-Defesa"},
        {"key": "flame", "label": "Flame", "emoji": "🔥", "capacity": 2, "required_role": "PP-Flame"},
        {"key": "elefante", "label": "Elefante", "emoji": "🐘", "capacity": 1, "required_role": "PP-Elefante"},
        {"key": "hwatcha", "label": "Hwatcha", "emoji": "💀", "capacity": 1, "required_role": "PP-Hwacha"},
        {"key": "shai", "label": "Shai", "emoji": "🎵", "capacity": 2, "required_role": "PP-Shai"},
        {"key": "ranged", "label": "Ranged", "emoji": "🏹", "capacity": 4, "required_role": "PP-Ranged"},
        {"key": "ataque", "label": "Ataque", "emoji": "⚔️", "capacity": 8, "required_role": "PP-Ataque"},
        {"key": "liao", "label": "Lião", "emoji": "🦁", "capacity": 3, "required_role": "PP-Especial"},
        {"key": "bomber", "label": "Bomber", "emoji": "💣", "capacity": 2, "required_role": "PP-Bomber"},
    ],
    "30": [
        {"key": "caller", "label": "Caller", "emoji": "🔊", "capacity": 1, "required_role": "PP-Caller"},
        {"key": "defesa", "label": "Defesa", "emoji": "🛡️", "capacity": 1, "required_role": "PP-Defesa"},
        {"key": "flame", "label": "Flame", "emoji": "🔥", "capacity": 2, "required_role": "PP-Flame"},
        {"key": "elefante", "label": "Elefante", "emoji": "🐘", "capacity": 1, "required_role": "PP-Elefante"},
        {"key": "hwatcha", "label": "Hwatcha", "emoji": "💀", "capacity": 1, "required_role": "PP-Hwacha"},
        {"key": "shai", "label": "Shai", "emoji": "🎵", "capacity": 2, "required_role": "PP-Shai"},
        {"key": "ranged", "label": "Ranged", "emoji": "🏹", "capacity": 5, "required_role": "PP-Ranged"},
        {"key": "ataque", "label": "Ataque", "emoji": "⚔️", "capacity": 12, "required_role": "PP-Ataque"},
        {"key": "liao", "label": "Lião", "emoji": "🦁", "capacity": 3, "required_role": "PP-Especial"},
        {"key": "bomber", "label": "Bomber", "emoji": "💣", "capacity": 2, "required_role": "PP-Bomber"},
    ],
}

# Mantido por compatibilidade (usado como padrão caso algo peça DEFAULT_ROLES).
DEFAULT_ROLES = ROLE_TEMPLATES["25"]

# Nome EXATO do cargo do Discord que pode usar /evento criar e /evento deletar
# (além de quem tem permissão "Gerenciar Servidor"/"Gerenciar Eventos").
# A comparação ignora maiúsculas/minúsculas.
STAFF_ROLE_NAME = "Staff"

# Fuso horário usado para interpretar o campo "Agendar publicação" do
# formulário de criação de evento (ex: "America/Sao_Paulo", "America/Manaus").
TIMEZONE = "America/Sao_Paulo"

# Por quantos dias os dados ficam guardados antes de serem apagados
# automaticamente: eventos criados há mais tempo que isso (mesmo que nunca
# tenham sido concluídos/deletados manualmente) e linhas do histórico em
# Excel mais antigas que isso. Ajuste esse número livremente.
DATA_RETENTION_DAYS = 15

EMBED_COLOR = 0x5865F2
