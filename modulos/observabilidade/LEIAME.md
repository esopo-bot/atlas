# observabilidade

Copiloto de investigação em ferramenta de observabilidade. Ele **não se
conecta a ferramenta nenhuma** — ensina a investigar, guarda o que cada
incidente ensinou, e vai compondo consulta melhor à medida que conhece as
aplicações da casa.

Primeira ferramenta hospedada: **Datadog**. O módulo foi desenhado para
receber uma segunda sem renomear nada — o que é método mora no nível do
módulo, o que é sintaxe mora identificado por ferramenta.

```bash
python montar.py --modulo observabilidade
```

## O que ele instala

| Destino | O que é |
| --- | --- |
| `conhecimento/observabilidade.md` | a página da camada: método, sintaxe, formato da memória |
| `conhecimento/observabilidade/` | o **molde vazio** da memória — o conteúdo nasce na máquina de quem usa |
| `.agents/skills/observabilidade/` | a skill que conduz, ingere e encerra |

## Por que ele não viaja com a camada

Quem não usa observabilidade não deveria pagar contexto por ela — e quem usa
outra ferramenta receberia sintaxe errada. É a barreira do custo aplicada
literalmente: o que entra tem que valer o que cobra, e aqui só vale para
quem instalou.

## A linha que não se apaga na revisão

O objetivo deste módulo é **acumular nome de aplicação, de serviço e de
incidente** — exatamente o que nunca pode entrar num repositório público.
Por isso a fronteira é física: a camada entrega molde vazio, e todo exemplo
usa nome inventado que ninguém confunde com casa real. Se um exemplo aqui
começar a parecer plausível, ele está errado.
