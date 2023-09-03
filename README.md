# Channel List

Bot do Telegram que cria uma lista de canais, onde os canais são anúnciados 
entre os canais participantes

## Instalação

Clone o repositório:

`git clone https://github.com/riguima/channel-list`

Instale as dependencias:

`pip install -r requirements.txt`

Ou se você utiliza poetry:

`poetry install`

Crie um app no Telegram seguindo esse [tutorial](https://core.telegram.org/api/obtaining_api_id)

Altere o arquivo base_config.toml inserindo as informações do seu bot:

```toml
BOT_NAME = "arroba_do_bot"
BOT_TOKEN = "token_do_bot"
API_ID = "seu_api_id"
API_HASH = "seu_api_hash"
DATABASE_URI = "sqlite:///database.db" # URI do banco de dados SQLAlchemy
ADMINS = ["username1", "username2"] # Lista com os usernames dos administradores do bot
```

Depois renomeie o arquivo para config.toml
