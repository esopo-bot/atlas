# Ingestão — as duas portas

Duas coisas chegam de fora: log cru e consulta. As duas entram destiladas, e
**nas duas você confirma em uma linha o que guardou e o que jogou fora**.
Ingestão silenciosa é ingestão que ninguém audita — e memória que ninguém
audita vira depósito.

## Porta 1: "toma esse log"

O dono cola saída crua. Você extrai o que dura e **descarta o original**.

**Não cole a saída crua na memória.** Nem "só um trecho", nem "só o exemplo
que ilustra". Log é grande, envelhece no mesmo dia, e cada linha colada
empurra para fora conhecimento que ainda vale.

Do log, sobrevive **isto e só isto**: os seis itens da tabela
sobrevive/morre de `conhecimento/observabilidade.md` — sem sétimo. Dois
lembretes na hora de escrever: o padrão vai com marcador no lugar do variável
(`Timeout ao chamar <serviço>`, nunca a linha inteira), e "ainda não se sabe"
é resposta válida para o que aquilo era.

Normalizar quer dizer: **fora identificador, fora horário, fora corpo de
requisição, fora qualquer coisa que só valha para aquela ocorrência.** Se o
que você escreveu só serve para reencontrar aquele exato evento, você guardou
log com outro nome.

Depois de destilar, diga em uma linha:

> "Guardei: o padrão `<padrão>`, o serviço `<serviço>` e o caminho morto
> `<caminho>`. Joguei fora: as 340 linhas coladas, os identificadores e os
> horários."

## Porta 2: o caderno de consultas

Ele enche por dois lados, e o segundo é o que importa.

**O dono dita.** "Essa consulta funciona, salva."

**Você compõe.** Conhecendo a aplicação, escreva a consulta e proponha — o
campo certo, o serviço certo, a janela certa. É aqui que o investimento na
memória aparece: quem sabe que o serviço se chama `<algo>-api` e que 4xx sai
como `info` compõe numa tentativa o que sem isso leva quatro.

### O afinamento é o coração disto

Consulta nasce ruim, de um dos dois jeitos:

| O dono diz | O que aconteceu | O que você faz |
| --- | --- | --- |
| "não veio nada" | filtro errado, nome errado, ou janela curta | uma hipótese por vez — troque **um** filtro e proponha de novo |
| "veio ruído demais" | falta recorte | acrescente o recorte mais barato: ambiente, depois serviço, depois nível |

Uma mudança por rodada. Duas de uma vez e ninguém sabe qual delas resolveu —
e o caderno registraria a razão errada.

### Cada entrada guarda cinco coisas

1. **a consulta**;
2. **a pergunta que ela responde** — consulta sem a pergunta é ruído em seis
   meses;
3. **a aplicação ou serviço** a que serve;
4. **por que não é a consulta óbvia** — o campo que parecia certo e não era, o
   filtro que faltava, o nome que a aplicação usa e ninguém adivinha. É o que
   custou caro para descobrir e o que ninguém registra;
5. **quando ela mente** — a condição em que devolve vazio havendo dado.

### As que falharam ficam

Consulta que não funcionou **não é lixo** — é armadilha mapeada, e vai para a
segunda tabela do caderno com o motivo. Sem ela, a sessão de daqui a três
meses reescreve a mesma consulta errada e perde a mesma meia hora.

Consulta que devolve zero é o engano mais barato de acreditar: falso
negativo tem cara de resposta. Campo com `@` onde não devia, serviço com
nome diferente do que se imagina, janela curta demais — os três devolvem vazio
com cara de resposta.
