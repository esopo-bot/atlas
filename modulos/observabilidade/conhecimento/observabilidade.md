# Observabilidade

O agente consulta a ferramenta de observabilidade por rota autorizada,
ensina a investigar quando não há rota, e guarda o que cada incidente
ensinou. A skill `observabilidade` conduz; a memória mora em
[`observabilidade/`](observabilidade/LEIAME.md) e nunca sai da sua máquina.

## A rota, e o que conta como medido

| Quem faz | O quê |
| --- | --- |
| o agente | compõe a consulta, diz por que é aquela e o que esperar |
| o agente, se houver rota (servidor declarado ou navegador do dono já autenticado) | roda, lê a saída e diz de que intervalo ela saiu |
| você, se não houver | roda, e cola o resultado se quiser |

Em nenhuma rota o agente pede, copia ou imprime credencial. **Consulta que
ninguém rodou é hipótese** (regra 2): medido é a saída vista, tanto faz quem
rodou. Consulta larga se faz uma vez, com janela declarada, não em rajada
(regra 7). O que se cola e o que se consulta vai para o modelo: tire
identificador de cliente e dado pessoal antes.

## O log se descarta; o conhecimento se guarda

| Do log, sobrevive | Do log, morre |
| --- | --- |
| o sintoma, nas palavras de quem viu | a linha inteira |
| a aplicação e o serviço | identificador, horário, corpo de requisição |
| o padrão da mensagem, normalizado | o exemplar concreto |
| o que aquilo acabou sendo | o rastro de como se chegou lá |
| a consulta que achou | as repetidas |
| o caminho que não deu em nada | — |

A memória é plana, em tabela e lista (a IA atualiza célula; parágrafo se
reescreve inteiro): `desenho.md` (você escreve; quem chama quem),
`aplicacao-<nome>.md`, `consultas-<ferramenta>.md`,
`incidente-<data>-<slug>.md` e `LEIAME.md` como índice. A skill abre só o
índice, o desenho e o caderno; o resto sob demanda.

## Investigação de incidente

1. Reproduza o sintoma com a chamada do cliente real.
2. Ache no código a mensagem que a pessoa vê.
3. Extraia o identificador de rastreio; sem ele você lê o log errado.
4. Ache a requisição exata, com começo e fim.
5. Ancore a linha do tempo: desde quando, com contagem por período.
6. Diferencie o que mudou, preferindo artefato imutável a memória: código,
   configuração, infraestrutura, rede.
7. Separe defeito seu de dependência externa.
8. Rode o cético (skill `verificacao-adversarial`).
9. Conclua, dizendo o que ficou sem prova.

Armadilhas: retenção é parte da prova; "não achei" fora da janela quer
dizer "não sei"; zero na tabela só é fato quando o instrumento registraria o
evento (compare com categoria vizinha); o identificador de rastreio costuma
embutir a hora em que a requisição começou.

O pedido a quem pode consertar leva: o sintoma em uma frase, o escopo
medido (afetados sobre tentativas), o instante em que começou, identificador
que quem recebe consegue procurar, o que mudou do seu lado com hora, o
pedido acionável e como a correção será validada. Sem adjetivo; o que não
foi medido entra como "não medido".

## No Datadog

A própria Datadog publica o servidor de consulta oficial (plugin no catálogo
`anthropics/claude-plugins-official`) e skills MIT em
`github.com/datadog-labs/agent-skills`; a consulta daqui é uma por
pergunta porque o servidor tem limite de rajada e teto mensal. Este módulo
faz a outra metade: conhecer a sua arquitetura.

| Passo | No Datadog |
| --- | --- |
| 3 | `dd.trace_id` no registro liga o log ao rastreamento |
| 4 | do `dd.trace_id`, o rastreamento inteiro |
| 5 | contagem por período sobre a mesma busca |
| 6 | implantações e eventos na linha do tempo, e a trilha de auditoria |
| 7 | o mapa de dependências entre serviços |

A sintaxe que devolve vazio com cara de resposta:

| Regra | Certo | Errado |
| --- | --- | --- |
| atributo leva `@`; reservado (`host`, `service`, `status`, `message`) não | `@usuario.id:42`, `service:vitrine` | `@service:vitrine` |
| operador em maiúscula | `status:error AND service:vitrine` | `and` |
| exclusão com `-` | `service:vitrine -status:info` | `NOT` |
| curinga `*` vários, `?` um | `service:vitrine-*` | `?` para vários |
| faixa com `TO` | `@http.status_code:[400 TO 499]` | `400-499` |
| ambiente explícito | `env:producao service:vitrine` | contar com o padrão |

Procedência: documentação oficial da Datadog, lida e resumida. Sintaxe
muda; quando uma consulta parar de funcionar, a fonte é a doc.
