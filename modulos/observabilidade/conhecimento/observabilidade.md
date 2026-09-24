# Observabilidade

O agente consulta a sua ferramenta de observabilidade quando existe rota
autorizada, ensina a investigar quando não existe, e guarda o que cada
incidente ensinou — para que a investigação de daqui a três meses comece onde
esta terminou.

Esta página tem o método (vale para qualquer ferramenta) e a tradução para a
ferramenta que o módulo hospeda hoje. A skill `observabilidade` conduz; a
memória mora em [`observabilidade/`](observabilidade/LEIAME.md) e nunca sai
da sua máquina.

## O agente consulta por rota autorizada — e isso é desenho

Rota autorizada é uma de duas: o **servidor de consulta declarado** no
workspace, ou o **navegador do dono**, na sessão que ele já abriu. Fora
delas, o agente compõe a consulta e entrega para quem tem acesso rodar.

Em nenhuma das duas o agente pede, copia ou imprime credencial, token ou
cookie: ele usa a porta que já está aberta, nunca a chave.

O que isso muda na prática:

| Quem faz | O quê |
| --- | --- |
| o agente | compõe a consulta, explica por que é aquela, diz o que esperar |
| o agente, se houver rota | roda, lê a saída e diz de que intervalo ela saiu |
| você, se não houver | roda, e cola o resultado se quiser |

**Consulta que ninguém rodou é hipótese.** Sugerida e não executada, ela não
pode ser chamada de prova, nem de "confirmado", nem de "encontrei": é a [regra
2 da camada](regras-da-camada.md) num lugar onde errar é barato e caro ao
mesmo tempo — barato de escrever, caro de acreditar. O que conta como medido é
a saída vista, tanto faz quem a rodou.

**O limite que continua valendo: rajada.** Ferramenta de observabilidade fica
lenta para o workspace inteiro quando alguém a martela — é a [regra 7 da
camada](regras-da-camada.md) aplicada onde ela dói. Consulta larga se faz uma
vez, com janela declarada, não em sequência para tatear.

Uma linha honesta sobre os dois caminhos: o que você colar vai para o modelo,
e o que o agente consultar também. Tire identificador de cliente e dado
pessoal antes. Consultar por servidor **não** é mais nem menos seguro que
colar log — muda quem escolhe o quê, não o destino.

### Por que o agente consulta, e o que ficou de pé

A regra aqui já foi o oposto: o agente **não** consultava, por dois motivos.
Um caiu e o outro ficou.

| O motivo antigo | Onde está hoje |
| --- | --- |
| licença custa por assento | **caiu**: a consulta sai pela credencial de quem já tem assento, e não cria um novo |
| agente consulta em rajada | **ficou**, como limite de uso, não como proibição |

O que derrubou o primeiro foi a prática ao lado: a própria camada já consulta
o serviço de log da nuvem por servidor declarado, somente leitura, pelo módulo
`insights`. A regra dizia "nunca" enquanto o módulo vizinho dizia "sim, e está
provado".

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

**Tudo plano, sem pasta dentro de pasta.** Se o publicador de quem instala
só transforma em rota um nível de subpasta de `conhecimento/`, a página mais
funda existe no disco e fica sem endereço; plana, a pasta serve a qualquer
publicador. O nome da ferramenta vai no arquivo, nunca na pasta.

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

## Investigação de incidente

Algo quebrou e a pergunta é "o que mudou?". A ordem abaixo estreita o campo
a cada passo; as armadilhas de medição, no fim, são o que faz uma conclusão
errada passar por prova.

### A ordem

1. **Reproduza o sintoma, com a chamada do cliente real.** Opção a mais na
   sua chamada percorre outro caminho e fabrica defeito. Não reproduziu? O
   primeiro trabalho é descobrir para quem acontece.
2. **Ache no código a mensagem que a pessoa vê** — o fio mais curto entre a
   tela e a linha.
3. **Extraia o identificador de rastreio.** Sem ele você lê log por horário —
   e lê o log errado.
4. **Ache a requisição exata**, inteira, com começo e fim.
5. **Ancore a linha do tempo**: não "está falhando?" — **"desde quando?"**,
   com contagem por período. Sem nomear o instante do começo, você ainda não
   investigou o suficiente para acusar nada.
6. **Diferencie o que mudou**, preferindo artefato imutável a memória: versão
   publicada, data de implantação, trilha de auditoria. Quatro suspeitos:
   código, configuração, infraestrutura, rede.
7. **Separe defeito seu de dependência externa** — muda o que se faz a
   seguir.
8. **Rode o cético** (skill `verificacao-adversarial`) antes de concluir.
9. **Conclua — e diga o que ficou sem prova.**

O raciocínio que fecha: código idêntico + infraestrutura idêntica + hora exata
de uma mudança de configuração = a configuração é a variável.

Os passos 3 a 7 mudam de forma conforme a ferramenta de observabilidade; os
outros quatro não mudam. As armadilhas abaixo mordem principalmente nos
passos 3 e 5.

### O pedido que se leva a quem pode consertar

Quando o defeito é do outro lado da fronteira, o que se manda vale mais que o
quanto se manda:

| O que entra | Por quê |
| --- | --- |
| o sintoma em uma frase, do ponto de vista de quem usa | quem recebe reconhece o problema como real |
| o escopo **medido** — quantos afetados sobre quantos tentaram | amostra pequena vira prioridade baixa, e quem não reclama some da conta |
| o instante exato em que começou | sem ele não se sabe onde procurar |
| identificadores que **quem recebe** consegue procurar | o seu identificador não serve na ferramenta de quem recebe |
| o que mudou do seu lado, com hora | antecipa a pergunta de volta |
| **o pedido acionável**: o que verificar, e o que fazer em cada resultado | evidência sem pedido é meia entrega |
| como a correção será validada em tempo real | fecha sem segunda rodada |

Sem acusação e sem adjetivo. O que não estiver medido entra como "não
medido" — nunca estimado.

### As armadilhas de medição

#### Retenção é parte da prova

Todo log, toda métrica e todo rastro tem uma janela de retenção. Antes de
concluir qualquer coisa a partir de uma busca, confira se o período pedido cabe
dentro da janela — sem isso, a busca não prova nada sobre o que aconteceu antes
dela.

#### "Não achei" fora da janela não significa nada

Buscar um identificador e não encontrá-lo só é evidência de ausência quando a
busca cobriu o período inteiro em que o evento poderia ter acontecido. Fora da
janela de retenção, "não achei" quer dizer "não sei" — nunca "não aconteceu".

#### Ausência de linha não é ausência de falha

Sistema que não grava toda categoria de evento tem zero na tabela mesmo quando
o evento aconteceu. Antes de tratar um zero como fato, confirme que o
instrumento realmente registraria o que se procura — comparando com uma
categoria vizinha de volume conhecido, por exemplo.

#### O identificador da requisição costuma dizer a hora em que ela começou

Muitos formatos de identificador de rastreio (trace id, request id) embutem um
carimbo de tempo. Antes de assumir que o evento é recente, ou de descartá-lo
por estar fora de uma janela estimada, decodifique o identificador — ele pode
apontar para um instante bem mais antigo do que a hora em que foi observado.

## No Datadog

### O que já existe pronto, e não se reescreve

A própria Datadog publica o que um agente precisa para **consultar** a
ferramenta: há um plugin no catálogo `anthropics/claude-plugins-official` com
`author.name: "Datadog"`, empacotando o servidor de consulta oficial, e um
conjunto de skills em `github.com/datadog-labs/agent-skills` (licença MIT)
para log, rastreamento, monitores, auditoria e documentação.

Se um dia você quiser automatizar de verdade, o endereço é esse — não este
módulo. E leve o custo junto: o servidor oficial trabalha com limite de
rajada e teto mensal de chamadas, que é exatamente o motivo de a consulta
daqui ser uma por pergunta, com janela declarada, e não um laço que tateia.

Este módulo faz a outra metade, a que ninguém publica: **conhecer a sua
arquitetura**.

### Os nove passos, traduzidos

A ordem genérica está em "Investigação de incidente", acima. O que
muda por ferramenta é onde se olha:

| Passo | No Datadog |
| --- | --- |
| 3 — identificador de rastreio | `dd.trace_id` no registro liga o log ao rastreamento |
| 4 — a requisição exata | do `dd.trace_id`, abra o rastreamento inteiro: a requisição real, com começo e fim |
| 5 — desde quando | contagem por período sobre a mesma busca, antes e depois |
| 6 — o que mudou | implantações e eventos na linha do tempo, mais a trilha de auditoria de quem alterou o quê |
| 7 — nosso ou de terceiro | o mapa de dependências entre serviços mostra de que lado o erro nasce |

Os passos 1, 2, 8 e 9 não mudam de ferramenta.

### A sintaxe que decide se a busca mente

Não é enfeite: é o que separa "não existe" de "escrevi errado". Cada engano
abaixo devolve **vazio com cara de resposta**, que é o assunto de
falso negativo.

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
