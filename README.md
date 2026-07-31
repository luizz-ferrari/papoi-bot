# Bot de Eventos (Nodewar) para Discord

Bot em Python (discord.py) que recria o sistema de inscrição em eventos das
imagens de referência: embed com funções (Caller, Defesa, Bandeira, Flame,
Elefante, Hwatcha, Shai, Frontline, Striker/Mística, Bomber, Ranged, Ataque,
Ataque 500k+), botões para cada função, fila de espera automática e botão
"Não vou".

## Funcionalidades

- `/evento criar tamanho:25|30` abre um formulário para criar o evento
  (título, descrição, início, fechamento do RSVP). O tamanho escolhido define
  automaticamente o limite de vagas de cada cargo (ver `config.py`).
- Cada função pode exigir que o membro tenha um **cargo específico do
  Discord** para se inscrever nela (configurável em `config.py`).
- Um botão por função. Clicar inscreve o usuário; clicar de novo remove.
- Se a função está cheia, o usuário entra automaticamente na **fila de
  espera**; quando alguém sai, o primeiro da fila sobe para a lista principal.
- Um usuário só pode estar inscrito em **uma função por vez** (trocar de
  função remove a inscrição anterior).
- Botão **Não vou** marca o usuário como ausente.
- Botão **Recarregar** atualiza o embed (útil se algo ficar dessincronizado).
- Botão **Deletar Evento** só funciona para quem criou o evento ou para
  administradores (permissão "Gerenciar Servidor" ou "Gerenciar Eventos").
- Os dados ficam salvos em `data/events.json`, então os eventos e os botões
  continuam funcionando mesmo depois de reiniciar o bot.

## Estrutura do projeto

```
nodewar_bot/
├── bot.py              # ponto de entrada
├── config.py           # lista de funções (roles) e capacidades — edite aqui
├── embeds.py           # monta o embed do evento
├── logic.py            # regras de inscrição / fila de espera
├── storage.py          # persistência em JSON
├── cogs/
│   └── events.py        # botões, modal e comando /evento criar
├── data/
│   └── events.json      # criado automaticamente
├── requirements.txt
└── .env.example
```

## Configuração

### 1. Criar a aplicação no Discord

1. Acesse https://discord.com/developers/applications e clique em **New
   Application**.
2. Vá em **Bot** → **Add Bot**.
3. Não é necessário ativar nenhuma *Privileged Gateway Intent* (o bot só usa
   slash commands e botões).
4. Copie o **Token** do bot.

### 2. Convidar o bot para o servidor

Em **OAuth2 → URL Generator**, marque:

- Scopes: `bot`, `applications.commands`
- Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`

Abra o link gerado e adicione o bot ao seu servidor.

### 3. Instalar e configurar

```bash
cd nodewar_bot
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edite o .env e cole o token do bot em DISCORD_TOKEN=
```

### 4. Rodar o bot

```bash
python bot.py
```

Se aparecer `Conectado como ...` no terminal, está tudo certo. Os comandos
slash podem levar até 1 hora para aparecer globalmente na primeira vez; para
testes rápidos você pode sincronizar os comandos apenas no seu servidor
(posso adaptar o `setup_hook` para isso se quiser).

## Como usar

1. Em qualquer canal do servidor, digite `/evento criar`.
2. Preencha o formulário (título, descrição, início, fechamento do RSVP,
   máximo de participantes) e envie.
3. O bot posta o embed com todos os botões de função.
4. Cada membro clica na função desejada para se inscrever. Clicar de novo
   remove a inscrição.

## Exigir um cargo do Discord para cada função

Em `config.py`, cada função tem um campo `"required_role"`. Por padrão está
`None` (qualquer pessoa pode se inscrever). Para exigir um cargo específico,
coloque o **nome exato do cargo do Discord** (Configurações do Servidor >
Cargos), por exemplo:

```python
{"key": "caller", "label": "Caller", "emoji": "🔊", "capacity": 2, "required_role": "Caller"},
```

Isso significa que só quem tiver o cargo `@Caller` no servidor vai conseguir
clicar no botão "Caller" e se inscrever — quem não tiver recebe um aviso
explicando qual cargo é necessário. Sair da função (clicar de novo para
cancelar) sempre é permitido, mesmo sem o cargo.

A comparação do nome ignora maiúsculas/minúsculas, mas precisa ser
exatamente o mesmo nome do cargo cadastrado no servidor. Você pode definir
`required_role` para algumas funções e deixar `None` em outras.

## Personalizando as funções e os tamanhos de evento

Em `config.py`, `ROLE_TEMPLATES` guarda um conjunto de cargos e limites para
cada tamanho de evento ("25" ou "30"). Edite os números à vontade — por
exemplo, mudar "Flame" de 2 para 3 vagas no template de 25 pessoas.

Para adicionar um novo tamanho (ex: evento de 35 pessoas):

1. Em `config.py`, adicione uma nova chave em `ROLE_TEMPLATES`, ex: `"35": [...]`
   (não esqueça de incluir `"required_role"` em cada função, mesmo que `None`).
2. Em `cogs/events.py`, no comando `criar`, adicione a opção correspondente:
   ```python
   app_commands.Choice(name="35 pessoas", value="35"),
   ```

Alterações em `config.py` valem apenas para eventos criados **depois** da
alteração — eventos já existentes mantêm os limites com que foram criados.
