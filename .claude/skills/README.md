# As skills da camada

Dez skills chegam com a camada. Elas não disparam sozinhas: o agente escolhe
pela `description` de cada uma. Esta página é para **gente** — para saber o
que existe, o que é indispensável e o que só serve quando o assunto aparece.

A ordem abaixo é de prioridade: quem tem meia hora lê as duas primeiras
categorias e para.

## Essenciais — valem em qualquer repositório, desde o primeiro dia

| Skill | Para que serve |
| --- | --- |
| `trabalho-por-issue` | O estado do trabalho mora na issue, não no disco. Abre, registra, verifica e vira a sessão. É a que mais muda o resultado quando a sessão morre no meio. |
| `qualidade` | O padrão de código deste repositório — KISS, YAGNI, Tidy First, teste em três atos, erro tratado na fronteira. Entra sozinha por gancho na abertura. |

## Workflow — o ciclo de um trabalho, na ordem em que ele acontece

| Skill | Quando chamar |
| --- | --- |
| `antes-de-criar` | Antes de escrever a primeira linha de código novo: procure o que já existe e cite. Vale para peça de código, nunca para texto. |
| `documentar-processo` | Quando o pedido é escrever ou corrigir documentação de processo — passo a passo, manual, "não bate mais com a realidade". |
| `cetico` | Ao fechar uma conclusão, antes de agir sobre ela: separa o que está provado do que foi suposto e desenha a medição que derrubaria cada suposição. |

## Governança — o que entra na camada, e como o dia fecha

| Skill | Quando chamar |
| --- | --- |
| `portao` | Antes de mudar a própria camada. As nove barreiras, o ritual e quando dizer não. **Só vale no repositório da camada** — em trabalho de projeto ela não se aplica. |
| `analise-de-promocao` | Ao dar UM trabalho por pronto: o que nasceu genérico vira proposta para a camada, o que é do workspace fica. |
| `esfriamento` | Só no fim da sessão: colhe o que o dia ensinou e chama as vizinhas que couberem. |

## Especialistas — um domínio cada, sob demanda

| Skill | Domínio |
| --- | --- |
| `wiki-de-projetos` | Indexa os repositórios do workspace e escreve o perfil de cada um. Chame depois de mudança grande num projeto. |
| `visao-de-fora` | Relatório do que a internet e os dados públicos mostram de um negócio local, sem nenhum acesso interno. |

## Duas coisas que economizam uma tarde

**A fonte é aqui, a cópia é gerada.** Edite em `.agents/skills/`. A pasta
`.claude/skills/` é espelho: o que se escreve lá é sobrescrito na próxima
sincronização, sem aviso.

**A `description` é o que faz a skill acordar** — não o corpo dela. Skill que
não dispara quase sempre tem descrição vaga, não conteúdo ruim. E a descrição
custa: ela entra no catálogo que toda sessão paga antes de trabalhar.
