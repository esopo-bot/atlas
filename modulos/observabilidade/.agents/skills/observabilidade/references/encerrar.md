# Encerrar — e é uma conversa, não uma extração

Achou a causa. Faltam três coisas, nesta ordem: atacar a conclusão, abrir a
mesa do que guardar, e só então escrever.

## 1. Ataque a conclusão antes de guardá-la

Rode a skill `cetico` na conclusão. Aqui ela é obrigatória e não decorativa:
o que você guardar agora vai ser lido daqui a seis meses como se fosse fato,
por alguém que não viu esta investigação. Conclusão errada guardada é pior que
conclusão errada esquecida.

E se metade do raciocínio se apoia em consulta que ninguém rodou, diga isso
na mesma frase da conclusão, não numa nota de rodapé.

## 2. Abra a mesa — proponha, não aplique

Memória que se enche sozinha vira depósito, e depósito ninguém lê. Então
proponha os candidatos **um a um, com o motivo**, e deixe o dono escolher:

> "Destes achados, o que compensa guardar? Eu proponho quatro:
>
> 1. a consulta `<X>` virou consulta de gaveta — ela responde `<pergunta>` e
>    não é a óbvia porque `<motivo>`;
> 2. a ligação entre `<A>` e `<B>` não estava no desenho — proponho que você
>    acrescente;
> 3. o caminho `<Y>` não deu em nada — vale registrar para ninguém repetir;
> 4. o sintoma `<Z>` entra na página da `<aplicação>`.
>
> O que fica de fora?"

Três coisas que você **não** decide sozinho:

| Coisa | Por quê |
| --- | --- |
| acrescentar ao `desenho.md` | o desenho é entrada, não descoberta — você propõe, quem escreve é o dono |
| guardar achado que só uma consulta não rodada sustenta | seria registrar hipótese como fato |
| apagar página inteira | pode haver ali coisa que você não leu nesta sessão |

## 3. Escreva o que ele aprovou — e diga o que ficou sem prova

| Onde | O que vai |
| --- | --- |
| `aplicacao-<nome>.md` | sintoma novo, caminho morto novo, ponteiro para consulta |
| `consultas-<ferramenta>.md` | a que funcionou **e** as que mentiram, com os cinco campos de `references/ingestao.md` |
| `incidente-<data>-<slug>.md` | o que era, como se achou, o que não deu em nada, o que ficou sem prova |
| `LEIAME.md` | uma linha, se nasceu arquivo novo |
| `desenho.md` | **nada** — só a proposta, na conversa |

A página de aplicação não existe ainda? Crie-a a partir de
`aplicacao-exemplo.md`; o registro de incidente nasce de
`incidente-exemplo.md`. Um arquivo por aplicação, nome `aplicacao-<nome>.md`,
tudo plano — sem pasta dentro de pasta, porque o site publica um nível de
subpasta e para ali.

A tabela apagar-ou-guardar do corpo vale aqui dobrado: é na escrita final
que malsucedido se registra e errado se apaga inteiro.

### Antes de fechar

Termine dizendo, em uma linha, **o que ficou sem prova**. É o último lugar
onde uma suposição ainda pode ser marcada como suposição — depois disso ela
vira texto na memória, e texto na memória se lê como fato.
