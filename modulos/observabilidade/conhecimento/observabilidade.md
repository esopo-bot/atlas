# Observabilidade

O agente não abre a sua ferramenta de observabilidade. Ele te ensina a abrir,
e guarda o que cada incidente ensinou — para que a investigação de daqui a
três meses comece onde esta terminou.

Esta página tem o método (vale para qualquer ferramenta) e a tradução para a
ferramenta que o módulo hospeda hoje. A skill `observabilidade` conduz; a
memória mora em [`observabilidade/`](observabilidade/LEIAME.md) e nunca sai
da sua máquina.

## O agente não consulta a ferramenta — e isso é desenho

**Não é falta de permissão.** Quem investiga tem acesso pleno; o agente é que
fica de fora, por dois motivos que valem em quase toda casa:

- **Licença custa por assento.** Um agente consultando não é um leitor a mais
  de graça.
- **Agente consulta em rajada.** Ferramenta de observabilidade fica lenta para
  a casa inteira quando alguém a martela — é a [regra 7 da
  camada](regras-da-camada.md) aplicada onde ela dói.

O que isso muda na prática:

| Quem faz | O quê |
| --- | --- |
| o agente | compõe a consulta, explica por que é aquela, diz o que esperar |
| você | roda, e cola o resultado se quiser |
| o agente | lê o que você colou — e só isso conta como medido |

**Consulta que o agente sugeriu e ninguém rodou é hipótese.** Ele não pode
chamá-la de prova, nem de "confirmado", nem de "encontrei": é a [regra 2 da
camada](regras-da-camada.md) num lugar onde errar é barato e caro ao mesmo
tempo — barato de escrever, caro de acreditar.

Uma linha honesta sobre o outro caminho: o que você colar vai para o modelo.
Tire identificador de cliente e dado pessoal antes. Não usar servidor de
consulta automática **não** torna nada seguro — muda quem escolhe o quê, não
o destino.

## O log se descarta; o conhecimento se guarda

É a espinha do módulo, e vale a pena entender o porquê antes da regra.

Log é grande, envelhece no mesmo dia e não cabe em janela de contexto
nenhuma. Conhecimento é curto e **composto**: serve no próximo incidente, e
no seguinte. Guardar log colado enche a memória de coisa que já não é
verdade e empurra para fora o que ainda é.

Então nada de colar saída crua na memória. Guarda-se o que ela ensinou:

| Do log, sobrevive | Do log, morre |
| --- | --- |
| o sintoma, nas palavras de quem viu | a linha inteira |
| a aplicação e o serviço envolvidos | identificador, horário, corpo de requisição |
| o **padrão** da mensagem, normalizado | o exemplar concreto dele |
| o que aquilo acabou sendo | o rastro de como se chegou lá |
| a consulta que achou | as consultas idênticas repetidas |
| **o caminho que não deu em nada** | — |

O último item é o que ninguém registra e o que mais economiza tempo na
segunda vez.

## A memória: o formato

Cinco peças, cada uma por um motivo diferente:

| Peça | Quem escreve | Para quê |
| --- | --- | --- |
| `desenho.md` | **você, à mão** | quem chama quem — é o que permite dizer "olhe também a aplicação vizinha" |
| `aplicacao-<nome>.md` | a skill, ao investigar | o que ela faz, o que costuma quebrar, onde se olha |
| `consultas-<ferramenta>.md` | a skill, quando você mandar | a consulta pronta e a pergunta que ela responde |
| `incidente-<data>-<slug>.md` | a skill, ao encerrar | o que era, como se achou, o que não deu em nada |
| `LEIAME.md` | a skill, na criação | o índice: o que mora ali, em uma linha |

**Tudo plano, sem pasta dentro de pasta.** Medido: o site publica um nível de
subpasta de `conhecimento/` e para ali — página no terceiro nível existe no
disco e não vira rota. O nome da ferramenta vai no arquivo, nunca na pasta.

**E tudo em tabela e lista, não em prosa.** Isto contraria o estilo do resto
do guia de propósito: as páginas do guia são para gente ler; a memória é para
a IA ler e **atualizar**. Parágrafo não se corrige — se reescreve inteiro, e
por isso ninguém corrige. Célula de tabela se troca sozinha.

**O `desenho.md` é entrada, não descoberta.** Você escreve; a skill lê. Ela
pode propor um acréscimo quando um incidente revelar uma ligação — propõe,
não escreve. E se o desenho não existir, ela avisa na primeira mensagem o que
está perdendo: sem ele, ela não aponta aplicação vizinha e volta a perguntar o
que já poderia saber.

**A abertura é enxuta por construção** — a skill abre só o índice, o desenho
e o caderno; o resto, sob demanda. Sem esse corte, em seis meses a abertura
carrega tudo e a janela acaba antes de a investigação começar.

## No Datadog

### O que já existe pronto, e não se reescreve

A própria Datadog publica o que um agente precisa para **consultar** a
ferramenta: há um plugin no catálogo `anthropics/claude-plugins-official` com
`author.name: "Datadog"`, empacotando o servidor de consulta oficial, e um
conjunto de skills em `github.com/datadog-labs/agent-skills` (licença MIT)
para log, rastreamento, monitores, auditoria e documentação.

Se um dia você quiser automatizar de verdade, o endereço é esse — não este
módulo. E leve o custo junto: o servidor oficial trabalha com limite de
rajada e teto mensal de chamadas, que é exatamente o motivo de o copiloto
daqui não consultar nada.

Este módulo faz a outra metade, a que ninguém publica: **conhecer a sua
arquitetura**.

### Os nove passos, traduzidos

A ordem genérica está em [investigação de
incidente](../fluxos/investigacao-de-incidente.md) e não se repete aqui. O que
muda por ferramenta é onde se olha:

| Passo | No Datadog |
| --- | --- |
| 3 — identificador de rastreio | `dd.trace_id` no registro liga o log ao rastreamento |
| 4 — a requisição exata | do `dd.trace_id`, abra o rastreamento inteiro: a requisição real, com começo e fim |
| 5 — desde quando | contagem por período sobre a mesma busca, antes e depois |
| 6 — o que mudou | implantações e eventos na linha do tempo, mais a trilha de auditoria de quem alterou o quê |
| 7 — nosso ou de terceiro | o mapa de dependências entre serviços mostra de que lado o erro nasce |

Os passos 1, 2, 8 e 9 não mudam de ferramenta — a ordem inteira está no fluxo.

### A sintaxe que decide se a busca mente

Não é enfeite: é o que separa "não existe" de "escrevi errado". Cada engano
abaixo devolve **vazio com cara de resposta**, que é o assunto de [zero que
mente](zero-que-mente.md).

| Regra | Certo | Errado, e devolve vazio |
| --- | --- | --- |
| Atributo leva `@`; reservado não | `@usuario.id:42`, `service:vitrine` | `@service:vitrine` |
| Os reservados são poucos | `host`, `service`, `status`, `message` | tratá-los como atributo |
| Operador em maiúscula | `status:error AND service:vitrine` | `status:error and service:vitrine` |
| Exclusão com `-` | `service:vitrine -status:info` | `service:vitrine NOT status:info` |
| Curinga: `*` vários, `?` um | `service:vitrine-*` | esperar que `?` case vários |
| Faixa numérica com `TO` maiúsculo | `@http.status_code:[400 TO 499]` | `@http.status_code:400-499` |
| Ambiente sempre explícito | `env:producao service:vitrine` | contar com o padrão |

A marcação unificada — `env`, `service`, `version` — é o que faz log,
rastreamento e métrica falarem da mesma coisa. Onde ela não estiver aplicada,
a correlação não acontece, e nada avisa.

Procedência: documentação oficial da Datadog sobre busca de log
(`docs.datadoghq.com`), lida e resumida — nunca copiada. Sintaxe muda; quando
uma consulta que funcionava parar de funcionar, a fonte é a doc, não esta
tabela.
