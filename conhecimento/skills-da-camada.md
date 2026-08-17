# O canivete

Tudo o que já existe, para você não escrever de novo: as skills que a camada
instala, os comandos que vêm de fábrica e os poucos plugins que se pagam.
**Abra esta página antes de escrever qualquer automação.**

## As skills da camada

O que vem instalado e **como cada uma entra na conversa**. A fonte da verdade
é a descrição dentro de cada `SKILL.md`, em `.agents/skills/<nome>/`.

| Skill | Para quê | Como entra |
| --- | --- | --- |
| `qualidade` | O padrão de código da casa: KISS, YAGNI, teste em três atos, erro tratado na fronteira | **Por gancho, onde houver gancho** — ver o aviso abaixo |
| `antes-de-criar` | Procurar e citar o que já existe antes de criar serviço, helper, contrato ou componente | Pelo pedido ("cria", "implementa") e pela regra no `AGENTS.md` |
| `wiki-de-projetos` | Gerar e atualizar a wiki local: um perfil por repositório e o mapa do conjunto | Quando você pede para indexar, gerar ou atualizar a wiki |
| `cetico` | Atacar uma conclusão antes de agir: separa provado de suposto e reemite o veredito | Ao fechar investigação, antes de escalar, ou pedindo "rode o cético" |
| `analise-de-promocao` | Ao dar por pronto, separar o que é genérico, o que é da casa e o que é descartável | No fechamento da sessão (o esfriamento chama) |
| `esfriamento` | Fechar a sessão colhendo o que o dia ensinou, do cético na conclusão à revisão das regras | "O trabalho terminou. Rode o esfriamento." |
| `documentar-processo` | Documentar um processo para outras pessoas: lê a fonte junto, escreve no padrão do repositório de documentação | Ao documentar, atualizar documentação ou explicar um fluxo a outro time |
| `trabalho-por-issue` | Conduzir o trabalho pela issue: padrão do corpo, verificação com evidência e o ponto de retomada da próxima sessão | Ao abrir, retomar, verificar ou encerrar trabalho que tem issue |

A camada tem também uma **parte opcional**, que não chega sem ser pedida — o
que ela oferece e como se instala está no
[mapa](mapa-do-repositorio.md#a-parte-opcional).

### Como uma skill entra na conversa

Três caminhos, do mais frágil ao mais firme:

1. **Pela descrição.** O agente compara o que você escreveu com a descrição de
   cada skill. Funciona para skill de método — e falha para skill de padrão,
   porque escrever código o agente resolve sem consultar ninguém; a medição
   está em [skills: criar e testar](skills-criar-e-testar.md).
2. **Pelo nome.** Você cita a skill no pedido. Simples e certeiro; depende de
   você lembrar.
3. **Por gancho.** Um programa injeta a skill no início da sessão, sem pedir
   licença — é assim que a `qualidade` entra, e é o único caminho que não
   depende nem do modelo nem da sua memória. O contrato está em
   [ganchos](ganchos.md).

**Gancho é de cada ferramenta, e nem toda ferramenta tem.** Medido com um
segundo agente: ele leu as skills de `.agents/skills/` e relatou **nenhum
gancho** — o `settings.json` do Claude Code não vale para ele. Onde não há
gancho, a `qualidade` volta a depender do caminho 1, e skill de padrão não
dispara por descrição. A saída é o caminho 2: **cite `qualidade` pelo nome
no pedido**, ou escreva o gancho equivalente na configuração daquela
ferramenta.

Quer escrever a sua? A peneira e os comandos de medição estão em
[skills: criar e testar](skills-criar-e-testar.md).

## O que vem de fábrica

Metade do trabalho já vem junto. Escrever skill ou prompt para isto é
reinventar.

| Comando | Para quê |
| --- | --- |
| `/code-review` | Revisar o que mudou, procurando erro de verdade |
| `/security-review` | Passar o diff atrás de vulnerabilidade |
| `/run` | Levantar o app para ver a mudança funcionando |
| `/simplify` | Sugerir simplificação no código |
| `/loop` | Repetir um pedido num intervalo |
| `/init` | Criar o arquivo de instruções do projeto |
| `/dataviz` | Gráfico e painel que se leem |
| `/claude-api` | Referência da API: modelos, preço, cache, ferramentas |

As revisões — `/code-review` e `/security-review` — **só rodam quando você
chama**. É de propósito: gastam tempo e dinheiro, então a decisão fica com
você.

**Esta tabela envelhece a cada versão.** A lista de fábrica muda sem aviso —
na conferência de 17/08/2026, quatro comandos antes citados aqui já não
existiam e saíram. A fonte é `/help` numa sessão interativa; o texto aqui é
o resumo.

## Os plugins que se pagam

Curadoria, não catálogo. O critério para ler o catálogo inteiro — e por que
estar nele não quer dizer ser oficial — está em
[plugins oficiais](plugins-oficiais-do-claude-code.md).

| Plugin | O que faz | Quando vale |
| --- | --- | --- |
| `skill-creator` | Cria skill, melhora skill existente e **mede o desempenho** dela com avaliações | Sempre que você for escrever uma skill |
| `feature-dev` | Conduz uma funcionalidade do início ao fim, com agentes para explorar, desenhar e revisar | Ao implementar algo maior num código que já existe |
| `code-simplifier` | Simplifica e refina preservando o comportamento; foca no que mudou há pouco | Depois de fazer funcionar, antes de entregar |
| `frontend-design` | Interface de qualidade de produção, fugindo da aparência genérica de IA | Ao construir tela que alguém vai ver |
| `pr-review-toolkit` | Revisores especializados por assunto: testes, tratamento de erro, tipos, qualidade | Quando a revisão genérica não basta |
| `claude-security` | Varredura profunda de vulnerabilidade, com cada achado desafiado antes de ser relatado | Auditoria de segurança sob demanda |
| `security-guidance` | Segurança contínua: aviso ao editar, revisão do diff ao parar, revisor de commit | Quando o agente edita de verdade e você quer rede |
| `hookify` | Cria gancho a partir do que deu errado na conversa, por regra em markdown | Quando um erro se repete e instrução não resolve |
| `claude-md-management` | Audita o arquivo de instruções, dá nota e registra o que a sessão aprendeu | Quando as instruções não batem mais com o código |
| `claude-code-setup` | Lê o repositório e recomenda quais automações valem a pena | Ao começar num projeto novo |

O `security-guidance` é o único desta lista que age sozinho — são só ganchos,
em quatro eventos.

## Ligar um plugin

Duas chaves no `.claude/settings.json` do projeto: de onde vem, e o que está
ativo. Quem clonar o repositório recebe a sugestão junto com o código.

```json
{
  "extraKnownMarketplaces": {
    "claude-plugins-official": {
      "source": { "source": "github", "repo": "anthropics/claude-plugins-official" }
    }
  },
  "enabledPlugins": {
    "code-review@claude-plugins-official": true
  }
}
```

**Ligue pouco.** Cada plugin ativo ocupa contexto da sessão inteira, e os que
dependem de programa externo **falham em silêncio** quando a dependência não
está instalada.
