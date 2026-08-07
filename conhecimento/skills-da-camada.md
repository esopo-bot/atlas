# As skills da camada

O que vem instalado, o que cada uma faz e **como ela entra na conversa**. A
fonte da verdade é a descrição dentro de cada `SKILL.md`, em
`.agents/skills/<nome>/`; esta página é o índice.

| Skill | Para quê | Como entra |
| --- | --- | --- |
| `qualidade` | O padrão de código da casa: KISS, YAGNI, teste em três atos, erro tratado na fronteira | **Por gancho, onde houver gancho** — ver o aviso abaixo |
| `antes-de-criar` | Procurar e citar o que já existe antes de criar serviço, helper, contrato ou componente | Pelo pedido ("cria", "implementa") e pela regra no `AGENTS.md` |
| `wiki-de-projetos` | Gerar e atualizar a wiki local: um perfil por repositório e o mapa do conjunto | Quando você pede para indexar, gerar ou atualizar a wiki |
| `cetico` | Atacar uma conclusão antes de agir: separa provado de suposto e reemite o veredito | Ao fechar investigação, antes de escalar, ou pedindo "rode o cético" |
| `analise-de-promocao` | Ao dar por pronto, separar o que é genérico, o que é da casa e o que é descartável | No fechamento da sessão (o esfriamento chama) |
| `esfriamento` | Fechar a sessão colhendo: cético na conclusão, promoção, automação, wiki, atrito e revisão das regras | "O trabalho terminou. Rode o esfriamento." |
| `documentar-processo` | Documentar um processo para outras pessoas: lê a fonte junto, escreve no padrão do repositório de documentação | Ao documentar, atualizar documentação ou explicar um fluxo a outro time |
| `trabalho-por-issue` | Conduzir o trabalho pela issue: padrão do corpo, verificação com evidência e o ponto de retomada da próxima sessão | Ao abrir, retomar, verificar ou encerrar trabalho que tem issue |

## Como uma skill entra na conversa

Três caminhos, do mais frágil ao mais firme:

1. **Pela descrição.** O agente compara o que você escreveu com a descrição de
   cada skill. Funciona para skill de método — e falha para skill de padrão:
   medido, uma skill de padrão de código dispara zero vez em 160 tentativas,
   porque escrever código o agente resolve sem consultar ninguém.
2. **Pelo nome.** Você cita a skill no pedido. Simples e certeiro; depende de
   você lembrar.
3. **Por gancho.** Um programa injeta a skill no início da sessão, sem pedir
   licença — é assim que a `qualidade` entra, e é o único caminho que não
   depende nem do modelo nem da sua memória. O contrato está em
   [ganchos](ganchos.md).

**Gancho é de cada ferramenta, e nem toda ferramenta tem.** Medido: um agente
que lê as skills de `.agents/skills/` normalmente listou as sete e relatou
**nenhum gancho** — o `settings.json` do Claude Code não vale para ele. Onde
não há gancho, a `qualidade` volta a depender do caminho 1, e skill de padrão
não dispara por descrição (zero em 160). A saída é o caminho 2: **cite
`qualidade` pelo nome no pedido**, ou escreva o gancho equivalente na
configuração daquela ferramenta.

Quer escrever a sua? A peneira e os comandos de medição estão em
[skills: criar e testar](skills-criar-e-testar.md).
