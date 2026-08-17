# História em issue

Todo trabalho ganha um endereço antes de começar: **uma história, uma issue**.
A sessão de IA recebe o endereço, não uma explicação do zero — e o que foi
feito fica registrado onde qualquer um acha.

Esta página é o desenho e o porquê. **O que se executa — o template da issue,
as regras de abertura, a sequência da sessão e o recibo de verificação — está
na skill `trabalho-por-issue`**, que roda de verdade. Um fato, uma casa.

## O desenho

| Peça                      | Vira                      | Fecha quando               |
| ------------------------- | ------------------------- | -------------------------- |
| História — o que se quer  | issue                     | os critérios dela passaram |
| Tarefa — um passo         | critério dentro da issue  | o instrumento provou       |
| Lição — o que se aprendeu | página em `conhecimento/` | não fecha — fica           |

## A fila e o nome

As regras de fluxo valem em qualquer casa; o **endereço** é de cada uma:

- **Onde a issue nasce é configuração, não decisão de sessão.** O
  repositório-casa das issues está em `configuracao-da-casa.md`, na raiz — a
  camada cria o molde, a casa preenche, e sessão e corrente leem antes de
  criar. Sem o arquivo preenchido, pergunta-se ao dono. Casa que concentra
  as issues num repositório só continua concentrando, mesmo com o código
  espalhado em outros.
- **Nome e fila também são configuração.** O padrão de nome e onde o novo
  entra moram no mesmo `configuracao-da-casa.md`; a skill lê de lá. Um
  exemplo que funciona: `semana_<número ISO>_hist_<n>` — o nome carrega
  quando e a ordem, e o título fica livre para o assunto.
- **Achado novo não fura a fila.** Entra na próxima posição, nunca na
  frente — fila que fura vira trabalho sem fim.
- **Uma sessão termina um trabalho.** Começou uma issue, termina a issue.
  Achado pequeno resolve na mesma sessão; épico vira pergunta ao dono antes
  de entrar na fila.

## Por que sem hierarquia

A regra — critério dentro, link em vez de sub-issue — mora na skill. O porquê:

Hierarquia só se paga quando outra sessão pega o pedaço sozinha, e mesmo aí
custa peça a mais para desatualizar. Duas issues ligadas por link envelhecem
cada uma por conta; issue-mãe e issue-filha envelhecem **uma contra a outra**,
e a partir daí alguém tem que decidir qual das duas está mentindo.

## Por que o corpo é o estado e o comentário é o evento

O corpo se reescreve e diz o que é verdade **agora**. O comentário não se
apaga e diz o que **aconteceu**. Invertido, o corpo vira histórico e passa a
mentir sobre o presente — e a próxima sessão, que lê o corpo primeiro, começa
o trabalho com a foto errada.

## O corte que importa

**O chamado vira issue e fecha; a lição é conhecimento e fica.**

Issue é registro de trabalho: nasce, anda, morre — e issue fechada é arquivo
morto, ninguém relê. O que se aprendeu no caminho não pode morar ali. Técnica,
armadilha, decisão com motivo: isso vai para `conhecimento/`, onde a próxima
sessão encontra sem escavar.

O teste para saber de que lado algo cai: **se o mesmo texto servir daqui a seis
meses, é conhecimento.** Se só fizer sentido neste trabalho, morre com a issue.
