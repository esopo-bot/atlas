# MCP: dar ao agente uma ferramenta que ele não tem

MCP é o plugue que liga o agente a um serviço de fora: o quadro de tarefas, o
banco de dados, o navegador. Declara-se o servidor num arquivo; a partir daí o
agente enxerga as ferramentas dele e as chama pelo nome.

## Primeiro: você precisa mesmo de MCP?

Muita coisa que parece pedir MCP já funciona sem ele. O agente executa
comandos — e o que vive no terminal não precisa de plugue.

| Você quer                                        | Use                      |
| ------------------------------------------------ | ------------------------ |
| git, build, teste, lint, `gh`, `docker`          | o terminal — já funciona |
| ler e escrever num serviço (quadro, banco, SaaS) | MCP                      |
| uma regra ou um processo seu                     | `AGENTS.md` ou skill     |

O caso que decide: git parece integração, mas é um programa no seu disco. O
agente roda `git log` como roda qualquer comando. MCP entra quando **não existe
comando** — o dado mora numa API e alguém precisa falar o protocolo dela.

## Quando vale escrever o seu

O gatilho é repetição medida, não vontade: **o mesmo ritual de consulta
reescrito à mão três, quatro, seis vezes** — a sequência de comandos, a
conversão de formato, o parâmetro que sempre esquecem. Uma vez é tarefa; a
partir da segunda, é candidato; quando você já perdeu tempo com a mesma
pegadinha duas vezes, o servidor se paga.

Dois cuidados que vêm da experiência de errar:

- **Parâmetro que causa erro silencioso vira obrigatório.** Se esquecer o
  ambiente ou a região devolve vazio em vez de erro, o servidor não deve
  aceitar a chamada sem ele.
- **O padrão do servidor é o caminho que funciona.** Quando duas formas de
  consultar existem e uma engana (devolve vazio onde a outra acha), a que
  funciona é o padrão — a outra fica como opção declarada.

## Onde o servidor vive

| Tipo             | Onde roda                       | O que você declara   |
| ---------------- | ------------------------------- | -------------------- |
| Remoto (HTTP)    | na máquina de quem oferece      | a URL                |
| Local (processo) | no seu disco, o agente o inicia | o comando que o sobe |

Servidor remoto é da outra pessoa: você aponta a URL e pronto — nada para
instalar, nada para manter. Servidor local é um programa seu: o agente o inicia
quando a sessão abre, e ele morre com ela.

## Onde declarar

| Arquivo                                 | Vale para                 | Entra no git?      |
| --------------------------------------- | ------------------------- | ------------------ |
| `.mcp.json` na raiz do projeto          | quem clonar o repositório | sim                |
| `~/.claude.json` (do usuário)           | você, em qualquer projeto | não — é da máquina |
| `~/.claude.json`, na entrada do projeto | você, só neste projeto    | não                |

A escolha é uma pergunta só: **quem mais deve receber esse plugue?** Todo mundo
que clona — projeto. Só você, em todo lugar — usuário. Só você, só aqui — o
escopo local, que a ferramenta guarda na entrada do projeto dentro do mesmo
arquivo do usuário. Os dois últimos não se editam à mão: nascem pelo comando da
ferramenta — no Claude Code, `claude mcp add`.

### A declaração é de cada ferramenta; só o programa é neutro

Os arquivos acima são convenção do Claude Code. **Outro agente aberto na mesma
pasta pode simplesmente não lê-los** — e o sintoma é silencioso: ele relata
"nenhum servidor", nunca "achei um arquivo que não entendo". Medido num
workspace com três servidores declarados na raiz: outro agente, aberto na
mesma raiz, listou **zero servidores e zero ferramentas**.

Daí a divisão que a camada faz. O **programa** do servidor é neutro e mora em
`.agents/mcp/<nome>/`, onde qualquer ferramenta o alcança. A **declaração**
não viaja: repete-se na configuração de cada ferramenta que você usa. Ligou um
servidor e outro agente não o vê? Confira a declaração dele naquela
ferramenta antes de investigar o servidor.

#### A declaração da outra ferramenta se cria pelo comando dela

Nunca à mão, e nunca gerada a partir do arquivo da primeira. O motivo é
medido: **a documentação e o programa instalado discordam.** A doc oficial do
Devin CLI manda declarar MCP num arquivo próprio (`.devin/mcp_config.json`);
o `devin mcp add` rodado numa máquina escreveu a seção `mcpServers` dentro do
`.devin/config.json` — o formato que a doc já dava por substituído.

Quem tivesse gerado o arquivo pela doc teria acertado a doc e errado a
máquina. E erraria em silêncio, do jeito da seção seguinte: declaração no
lugar que ninguém lê é servidor que nunca existiu.

Daí a regra chata que envelhece melhor: **cada ferramenta declara pelo
comando dela**, e o escopo se escolhe por bandeira, não por caminho de
arquivo. O arquivo é detalhe de implementação da ferramenta; o comando é o
contrato.

| Ferramenta  | Registra com     | Confere com       |
| ----------- | ---------------- | ----------------- |
| Claude Code | `claude mcp add` | `claude mcp list` |
| Devin CLI   | `devin mcp add`  | `devin mcp list`  |

É também por isso que a camada não gera a segunda declaração no
`--sincronizar`, embora espelhe skills. Skill é texto nosso num caminho que
escolhemos; declaração de MCP é formato da outra ferramenta, e ele já mudou
de arquivo uma vez.

## Quando o servidor some da lista

Servidor declarado que não sobe **não dá erro nenhum**: ele some da lista de
ferramentas como se nunca tivesse sido configurado. Falha de conexão e
"nunca existiu" têm o mesmo sintoma — e a sessão trabalha sem a ferramenta
sem saber que deveria tê-la.

Duas causas respondem por quase tudo, medidas em falhas reais:

- **Caminho morto.** O `command`, um item de `args` ou o ajudante de
  cabeçalho apontam para arquivo que não existe — nunca commitado, movido,
  ou deixado para trás. Ninguém valida isso na declaração. O gancho
  `conferir-mcp.py` da camada confere na abertura da sessão e avisa.
- **O processo morre antes de falar o protocolo.** O arquivo existe, o
  servidor sobe e sai com erro antes de responder ao `initialize` — um
  import que falha, uma dependência ausente. O cliente desiste calado.

E há um terceiro sintoma, mais enganoso que os dois: **a lista da ferramenta
diz "declarado", não "funciona"**. `claude mcp list` e o equivalente do outro
agente leem a configuração — não sobem servidor nenhum. Registro recém-criado
aparece ali mesmo quando o comando declarado está errado. É o falso positivo
mais barato de acreditar, porque chega logo depois de você registrar e tem
cara de confirmação.

Por causa do segundo caso, **checar arquivo não basta: prove com sonda**.
Uma sonda sobe o servidor de verdade, manda o `initialize` e chama uma
ferramenta com dado real. É o único teste que separa "o disco tem bytes" de
"a ferramenta funciona". Servidor local merece uma sonda ao lado do código,
em `.agents/mcp/<nome>/`, rodável num comando.

### A regra do caminho que atravessa mudança de raiz

Caso particular do caminho morto, e o mais traiçoeiro: configuração escrita
com **caminho absoluto** (`D:/raiz-antiga/...`) quebra em silêncio quando a
pasta muda de nome — e quebra tudo junto: chave de SSH, ajudante de
cabeçalho, script apontado por declaração. A regra que evita:

- Dentro do repositório, caminho **relativo à raiz**, sempre.
- Caminho absoluto inevitável (chave fora do git, ferramenta da máquina)
  precisa de uma verificação que fale quando o alvo sumir — um gancho de
  abertura, um teste, qualquer instrumento que transforme o silêncio em
  aviso.

## Onde mora o programa do servidor local

O código de um servidor local é neutro — qualquer agente o usa. Por isso mora
com as coisas neutras da camada: `.agents/mcp/<nome-do-servidor>/`. A
declaração aponta o caminho relativo:

```json
{
  "mcpServers": {
    "meu-servico": {
      "command": "python",
      "args": [".agents/mcp/meu-servico/servidor.py"]
    }
  }
}
```

Assim servidor e declaração viajam juntos no git do workspace — quem clona
recebe os dois prontos. O que nunca viaja é o token: cada máquina põe o seu
no `.credenciais/mcp.env` (seção abaixo).

## A regra do token

O `.mcp.json` aceita `${VARIAVEL}`: o valor vem da variável de ambiente na hora
de usar. Segredo nunca fica escrito dentro do arquivo.

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

Assim o arquivo pode entrar no git de um repositório compartilhado: cada máquina
põe o seu token na variável, e o arquivo continua limpo. Token escrito dentro
transforma o arquivo inteiro em segredo — aí ele tem que sair do git, e todo
mundo perde a declaração junto.

O esqueleto do workspace já traz o par que faz isso funcionar: os valores
moram em `.credenciais/mcp.env` (`NOME=valor`, um por linha) e
`python .credenciais/publicar-mcp-env.py` os publica como variáveis do
usuário — mostrando só os nomes, nunca os valores. Trocou um token: edite o
`mcp.env` e rode o publicador de novo.

## A cortesia das requisições

Servidor MCP e API respondem melhor a quem pede pouco. Proxies e limites de
taxa derrubam quem abusa — o sintoma é `403`/`429` depois de uma rajada de
chamadas.

- **Só chame a rede se a tarefa exigir.** Antes, pergunte se o dado já está
  no disco: a wiki, o índice, o clone local.
- **Espace as chamadas.** Rajada de dezenas de requisições seguidas é o que
  o bloqueio caça. Em trabalho grande, pause entre uma chamada e outra.
- **Recue no primeiro `403`/`429`.** Não insista no ritmo que causou o
  bloqueio: espere, reduza o volume — e se persistir, avise o dono em vez de
  tentar de novo em rajada.

## O custo que ninguém declara

Cada servidor ligado descreve as suas ferramentas ao agente, e essa descrição
ocupa contexto da sessão inteira — usando ou não. Ligue o que resolve um
problema que você tem hoje; desligue o que ficou de enfeite.
