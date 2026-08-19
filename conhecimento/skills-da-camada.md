# O catálogo

Tudo o que já existe, para você não escrever de novo. **Abra esta página antes
de escrever qualquer automação.**

## As skills da camada

A fonte da verdade é a descrição de cada `SKILL.md`, em `.agents/skills/<nome>/`.

| Skill | Para quê | Como entra |
| --- | --- | --- |
| `qualidade` | KISS, YAGNI, teste em três atos, erro na fronteira | por gancho, onde houver gancho |
| `antes-de-criar` | procurar e citar o que já existe antes de criar | pelo pedido ("cria", "implementa") |
| `wiki-de-projetos` | um perfil por repositório e o mapa do conjunto | quando você pede a wiki |
| `cetico` | atacar uma conclusão antes de agir sobre ela | ao fechar investigação; "rode o cético" |
| `analise-de-promocao` | separar genérico, do workspace e descartável | no fechamento (o esfriamento chama) |
| `esfriamento` | fechar a sessão colhendo o que o dia ensinou | "O trabalho terminou. Rode o esfriamento." |
| `documentar-processo` | documentar processo no padrão do repositório de docs | ao documentar ou atualizar documentação |
| `trabalho-por-issue` | conduzir o trabalho pela issue, com evidência e retomada | ao abrir, retomar ou encerrar issue |
| `iniciar-pedido` | pedido cru vira issue que uma sessão sem cabeça executa | ao começar trabalho novo; "abre uma issue disso" |

A parte opcional não chega sem ser pedida:
[mapa](mapa-do-repositorio.md#os-comandos).

Três caminhos de entrada, do mais frágil ao mais firme: pela **descrição**
(falha para skill de padrão), pelo **nome** no pedido, por **gancho** (único que
não depende de ninguém lembrar). Gancho é de cada ferramenta: onde não há, cite
`qualidade` pelo nome. Criar a sua:
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
| `/dataviz` | gráfico e painel de controle que se leem |
| `/claude-api` | referência da API: modelos, preço, cache |

`/code-review` pode ser iniciado pelo próprio Claude; para deixá-lo só manual,
`skillOverrides {"code-review": "user-invocable-only"}`. A tabela envelhece a
cada versão — a fonte é `/help` numa sessão interativa.

## Os plugins que se pagam

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

Curadoria, não catálogo. **Estar no catálogo oficial não quer dizer ser da
Anthropic** — o corte é medível, `author.name == "Anthropic"` no manifesto, e
o caso a conhecer é o `superpowers`: distribuído pelo catálogo, código de
terceiro. Quantos são hoje, na sua máquina:

```bash
python -c "
import json,io,os
p=os.path.expanduser('~/.claude/plugins/marketplaces/claude-plugins-official/.claude-plugin/marketplace.json')
d=json.load(io.open(p,encoding='utf-8'))
a=lambda q:(q.get('author') or {}).get('name','') if isinstance(q.get('author'),dict) else ''
n=[q['name'] for q in d['plugins'] if a(q)=='Anthropic']
print(len(n),'da Anthropic de',len(d['plugins']),'no total'); print(', '.join(sorted(n)))
"
```

**O comando é a fonte; lista escrita é foto velha.** No corte oficial há
também um plugin por linguagem (exigem o servidor da linguagem, e sem ele não
sobem), kits da plataforma, relatórios e estilos de resposta.

## Ligar um plugin

```json
{
  "extraKnownMarketplaces": {
    "claude-plugins-official": {
      "source": { "source": "github", "repo": "anthropics/claude-plugins-official" }
    }
  },
  "enabledPlugins": { "code-review@claude-plugins-official": true }
}
```

**Ligue por projeto, não por máquina.** O mesmo bloco vale em três escopos, e o
de baixo vence o de cima:

| Escopo | Arquivo | Vale onde |
| --- | --- | --- |
| usuário | `~/.claude/settings.json` | em toda pasta da máquina |
| projeto | `.claude/settings.json` | só naquele repositório |
| local | `.claude/settings.local.json` | naquele repositório, fora do git |

Plugin de uma tecnologia só mora no repositório que a usa. No escopo de
usuário ele cobra contexto em toda sessão de todo projeto — inclusive nos que
nunca vão chamá-lo.

**Ligue pouco.** Plugin que depende de programa externo falha sem barulho
quando a dependência falta; o erro fica na aba Errors do `/plugin`. Sem depender
da aba:

```bash
python -c "
import json,glob,os,shutil
s=os.path.expanduser('~/.claude/settings.json')
lig={k.split('@')[0] for k,v in json.load(open(s)).get('enabledPlugins',{}).items() if v}
for f in glob.glob(os.path.expanduser('~/.claude/plugins/cache/*/*/*/.mcp.json')):
    p=f.split(os.sep)[-3]
    if p in lig:
        for _,c in (json.load(open(f)).get('mcpServers') or {}).items():
            d=c.get('command')
            print('falta' if d and not shutil.which(d) else 'http' if not d else 'ok', d or c.get('url'), '<-', p)
"
```

`falta` = o servidor não sobe e você paga a descrição sem receber ferramenta.
`http` = servidor remoto, ainda pode exigir autorização.
