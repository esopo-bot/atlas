# MCP: dar ao agente uma ferramenta que ele não tem

MCP é o plugue que liga o agente a um serviço de fora. Declara-se o servidor
num arquivo; o agente enxerga as ferramentas dele e as chama.

## Primeiro: você precisa mesmo de MCP?

| Você quer                                        | Use                      |
| ------------------------------------------------ | ------------------------ |
| git, build, teste, lint, `gh`, `docker`          | o terminal — já funciona |
| ler e escrever num serviço (quadro, banco, SaaS) | MCP                      |
| uma regra ou um processo seu                     | `AGENTS.md` ou skill     |

MCP entra quando **não existe comando** — o dado mora numa API. Escrever o seu,
só com repetição medida: o mesmo ritual refeito à mão três, quatro vezes. Dois
cuidados de desenho: parâmetro cuja falta devolve vazio em vez de erro vira
obrigatório; quando duas formas de consultar existem e uma engana, a que
funciona é o padrão.

## Onde declarar

| Tipo             | Onde roda                       | O que você declara   |
| ---------------- | ------------------------------- | -------------------- |
| Remoto (HTTP)    | na máquina de quem oferece      | a URL                |
| Local (processo) | no seu disco, o agente o inicia | o comando que o sobe |

- Mecânica completa (escopos, `claude mcp add`):
  [doc oficial](https://code.claude.com/docs/en/mcp).
- `.mcp.json` na raiz entra no git e vale para quem clonar — **mas quem clona
  aprova os servidores na primeira sessão interativa**; aprovação pendente
  também é causa de "sumiu da lista".
- Escopos de usuário e local são da máquina: nascem pelo comando da
  ferramenta, nunca à mão.
- **A declaração é de cada ferramenta; só o programa é neutro.** O programa
  mora em `.agents/mcp/<nome>/`; a declaração se repete na configuração de cada
  agente, apontando o caminho relativo. Registre pelo comando
  (`claude mcp add`, `devin mcp add`) — o comando é o contrato, o arquivo é
  detalhe.

## Quando o servidor some da lista

| Causa                                   | Como pega                                                        |
| --------------------------------------- | ---------------------------------------------------------------- |
| caminho morto na declaração             | o gancho `verificar-mcp.py` acusa na abertura                     |
| processo morre antes de falar protocolo | sonda                                                            |
| aprovação pendente de quem clonou       | `claude mcp list` mostra o status                                |
| variável `${...}` sem valor             | sobe, lista, e falha só no `tools/call` — sonda com chamada real |

- `claude mcp list` conecta e mostra a saúde de cada servidor. Em outros
  agentes o sumiço é silencioso — desconfie de lista que só lê configuração.
- **Checar arquivo não basta: prove com sonda** — subir o servidor, mandar o
  `initialize` e chamar uma ferramenta com dado real. Quem para no
  `initialize` dá verde a servidor que falha no primeiro uso.
- Declare o nome da variável onde algum instrumento leia: `${VARIAVEL}` na
  declaração (o `verificar-ambiente.py` extrai daí) ou na lista `variavel`
  do `nucleo/ambiente.json`.

## Caminho e token

Caminho **relativo à raiz**, sempre — absoluto quebra em silêncio quando a
pasta muda de nome. O que morre na mudança:
[o estado que não viaja](estado-que-nao-viaja.md).

```json
{
  "mcpServers": {
    "meu-servico": {
      "type": "http",
      "url": "https://exemplo.com/mcp",
      "headers": { "Authorization": "Bearer ${MEU_TOKEN}" }
    }
  }
}
```

- Segredo nunca no arquivo: `${VARIAVEL}`, valor na variável de ambiente —
  assim a declaração entra no git e cada máquina põe o seu token.
- Os valores moram em `.credenciais/mcp.env`;
  `python .credenciais/publicar-mcp-env.py` publica como variáveis do usuário,
  mostrando só nomes.
- **A variável precisa chegar a quem abre o programa**: aplicativo aberto pelo
  ícone não herda o perfil do shell. Funciona pelo terminal e não pelo ícone? O
  problema é o canal — em Linux/systemd ele é `~/.config/environment.d/`, onde
  o publicador escreve.

## O custo

Por padrão só nomes de ferramenta e instruções do servidor entram na largada; a
definição completa entra sob demanda. Ainda assim: ligue o que resolve problema
de hoje. Rede com cortesia é a regra 7 —
[as regras da camada](regras-da-camada.md).
