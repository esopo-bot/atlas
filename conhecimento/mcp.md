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

Dois cuidados de desenho:

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

## Onde declarar

A mecânica — tipos de servidor, os três escopos, `claude mcp add` — está na
[doc oficial de MCP do Claude Code](https://docs.claude.com/en/docs/claude-code/mcp).
A síntese: `.mcp.json` na raiz vale para quem clonar o repositório e entra no
git; os escopos de usuário e local são da máquina e não se editam à mão —
nascem pelo comando da ferramenta. A escolha é uma pergunta só: **quem mais
deve receber esse plugue?** Todo mundo que clona — projeto. Só você —
usuário ou local.

### A declaração é de cada ferramenta; só o programa é neutro

Os arquivos acima são convenção do Claude Code. **Outro agente aberto na mesma
pasta pode simplesmente não lê-los** — e o sintoma é silencioso: ele relata
"nenhum servidor", nunca "achei um arquivo que não entendo". Medido num
workspace com três servidores declarados na raiz: outro agente, aberto na
mesma raiz, listou **zero servidores e zero ferramentas**.

Daí a divisão que a camada faz. O **programa** do servidor é neutro e mora em
`.agents/mcp/<nome>/`, onde qualquer ferramenta o alcança. A **declaração**
não viaja: repete-se na configuração de cada ferramenta que você usa,
apontando o caminho relativo do programa:

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
no `.credenciais/mcp.env` (seção abaixo). Ligou um servidor e outro agente
não o vê? Confira a declaração dele naquela ferramenta antes de investigar
o servidor.

#### A declaração da outra ferramenta se cria pelo comando dela

Nunca à mão, e nunca gerada a partir do arquivo da primeira. Motivo medido:
a doc e o programa instalado do Devin CLI discordam de arquivo e de formato
(história no `CHANGELOG.md`) — o arquivo é detalhe de implementação; **o
comando é o contrato**, e o escopo se escolhe por bandeira. Pelo mesmo
motivo, o `--sincronizar` espelha skills e não gera declaração de MCP.

| Ferramenta  | Registra com     | Confere com       |
| ----------- | ---------------- | ----------------- |
| Claude Code | `claude mcp add` | `claude mcp list` |
| Devin CLI   | `devin mcp add`  | `devin mcp list`  |

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

E há um quarto, que engana no sentido oposto a todos os outros: **servidor
declarado sem as variáveis que usa sobe do mesmo jeito**, aparece na lista de
ferramentas e só falha na primeira chamada. O valor não faz falta para
responder ao `initialize` nem para descrever as ferramentas — só para atender
a chamada de verdade. Medido com uma sonda (17/08/2026), com a variável fora
do ambiente: o `initialize` respondeu, o `tools/list` trouxe a ferramenta, o
processo seguiu vivo, e o erro só apareceu no `tools/call`. Tudo parece vivo
até o uso.

O conserto é declarar o nome onde algum instrumento o leia: `${VARIAVEL}` na
própria declaração — o `conferir-ambiente.py` extrai daí e acusa a falta na
abertura da sessão — ou uma linha `variavel NOME` no `ambiente.txt` da raiz,
quando é o programa do servidor que lê a variável por conta. Nome que ninguém
declara é falta que ninguém acusa.

Por causa do segundo caso e do quarto, **checar arquivo não basta: prove com
sonda**. Uma sonda sobe o servidor de verdade, manda o `initialize` e chama
uma ferramenta com dado real. É o único teste que separa "o disco tem bytes"
de "a ferramenta funciona" — e o que separa o quarto caso é justamente a
chamada: quem para no `initialize` recebe o verde de um servidor que vai
falhar no primeiro uso. Servidor local merece uma sonda ao lado do código,
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

E o caminho é só uma das coisas que a mudança de raiz mata. O mapa inteiro
do que morre — e como declarar e conferir o que a casa precisa do ambiente
— está em [o estado que não viaja](estado-que-nao-viaja.md).

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

**E a variável precisa chegar em quem abre o programa.** Medido num Linux de
área de trabalho (17/08/2026): aplicativo aberto pelo ícone nasce do gestor
de sessão gráfica, não do shell — e não herda o que o perfil do shell
exporta. O sintoma engana por completo: o `mcp.env` está certo, o terminal
enxerga a variável, e o servidor MCP morre em silêncio só quando o programa
vem do ícone. Abrir o aplicativo por um terminal "conserta" — e é assim que
se diagnostica: se pelo terminal funciona e pelo ícone não, o problema é o
canal, não o arquivo. O conserto durável, em sistemas com systemd, é
publicar as variáveis onde a sessão gráfica também lê — um drop-in em
`~/.config/environment.d/` (`NOME=valor`, um por linha, e relogar para
valer). É por isso que o publicador escreve nesse canal, não no perfil do
shell.

## O custo que ninguém declara

Cada servidor ligado descreve as suas ferramentas ao agente, e essa descrição
ocupa contexto da sessão inteira — usando ou não. Ligue o que resolve um
problema que você tem hoje; desligue o que ficou de enfeite.

E a rede cobra o dela: chamar só quando a tarefa exigir, espaçar, recuar no
`403`/`429` é a regra 7 — [as regras da camada](regras-da-camada.md).
