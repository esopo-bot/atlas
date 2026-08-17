# O canivete

Tudo o que já existe, para você não escrever de novo. **Abra esta página
antes de escrever qualquer automação.**

## As skills da camada

A fonte da verdade é a descrição de cada `SKILL.md`, em
`.agents/skills/<nome>/`.

| Skill | Para quê | Como entra |
| --- | --- | --- |
| `qualidade` | KISS, YAGNI, teste em três atos, erro na fronteira | por gancho, onde houver gancho |
| `antes-de-criar` | procurar e citar o que já existe antes de criar | pelo pedido ("cria", "implementa") |
| `wiki-de-projetos` | um perfil por repositório e o mapa do conjunto | quando você pede a wiki |
| `cetico` | atacar uma conclusão antes de agir sobre ela | ao fechar investigação; "rode o cético" |
| `analise-de-promocao` | separar genérico, da casa e descartável | no fechamento (o esfriamento chama) |
| `esfriamento` | fechar a sessão colhendo o que o dia ensinou | "O trabalho terminou. Rode o esfriamento." |
| `documentar-processo` | documentar processo no padrão do repositório de docs | ao documentar ou atualizar documentação |
| `trabalho-por-issue` | conduzir o trabalho pela issue, com recibo e retomada | ao abrir, retomar ou encerrar issue |

A parte opcional não chega sem ser pedida:
[mapa](mapa-do-repositorio.md#a-parte-opcional).

Três caminhos de entrada, do mais frágil ao mais firme: pela **descrição**
(falha para skill de padrão), pelo **nome** no pedido, por **gancho**
(único que não depende de ninguém lembrar). Gancho é de cada ferramenta:
onde não há, cite `qualidade` pelo nome. Criar a sua:
[skills: criar e testar](skills-criar-e-testar.md).

## O que vem de fábrica

| Comando | Para quê |
| --- | --- |
| `/code-review` | revisar o que mudou, procurando erro de verdade |
| `/security-review` | passar o diff atrás de vulnerabilidade |
| `/run` | levantar o app para ver a mudança funcionando |
| `/simplify` | sugerir simplificação no código |
| `/loop` | repetir um pedido num intervalo |
| `/init` | criar o arquivo de instruções do projeto |
| `/dataviz` | gráfico e painel que se leem |
| `/claude-api` | referência da API: modelos, preço, cache |

- O `/code-review` pode ser iniciado pelo próprio Claude; para deixá-lo só
  manual: `skillOverrides {"code-review": "user-invocable-only"}` nas
  settings.
- Esta tabela envelhece a cada versão — a fonte é `/help` numa sessão
  interativa.

## Os plugins que se pagam

Curadoria, não catálogo — o critério para ler o catálogo:
[plugins oficiais](plugins-oficiais-do-claude-code.md).

| Plugin | Quando vale |
| --- | --- |
| `skill-creator` | sempre que for escrever ou medir uma skill |
| `feature-dev` | funcionalidade maior num código que já existe |
| `code-simplifier` | depois de funcionar, antes de entregar |
| `frontend-design` | tela que alguém vai ver |
| `pr-review-toolkit` | revisores especializados por assunto |
| `claude-security` | auditoria de segurança sob demanda |
| `security-guidance` | rede contínua (só ganchos — o único que age sozinho) |
| `hookify` | criar gancho a partir do que deu errado na conversa |
| `claude-md-management` | quando as instruções não batem mais com o código |
| `claude-code-setup` | começar num projeto novo |

## Ligar um plugin

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

**Ligue pouco**: plugin ativo ocupa contexto, e o que depende de programa
externo falha sem barulho quando a dependência falta — o erro fica na aba
Errors do `/plugin`.
