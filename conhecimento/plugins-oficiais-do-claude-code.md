# Plugins oficiais do Claude Code

O que a Anthropic escreveu, para você não escrever de novo. Esta página não é
o catálogo: é o critério para ler o catálogo, mais os poucos plugins que
resolvem dor que se repete.

## Antes de instalar qualquer coisa

Metade do trabalho já vem de fábrica. Instalar plugin para isso é reinventar.

| O que vem junto      | Para quê                                              |
| -------------------- | ----------------------------------------------------- |
| `/code-review`       | Revisar o que mudou, procurando erro de verdade       |
| `/security-review`   | Passar o diff atrás de vulnerabilidade                |
| `/verify`            | Subir o app e confirmar que a mudança faz o que devia |
| `/run`               | Levantar o app para ver a mudança funcionando         |
| `/simplify`          | Sugerir simplificação no código                       |
| `/debug`             | Ligar registro de depuração e investigar              |
| `/batch`             | Mudança grande espalhada pelo código, em paralelo     |
| `/loop`              | Repetir um pedido num intervalo                       |
| `/init`              | Criar o arquivo de instruções do projeto              |
| `/dataviz`           | Gráfico e painel que se leem                          |
| `/claude-api`        | Referência da API: modelos, preço, cache, ferramentas |
| `/deep-research`     | Pesquisa na web com fontes cruzadas e relatório       |

Duas delas — `/verify` e `/code-review` — **só rodam quando você chama**. É de
propósito: gastam tempo e dinheiro, então a decisão fica com você.

**Esta tabela envelhece a cada versão.** A lista de fábrica muda sem aviso, e
quem cita comando que sumiu manda o leitor para o vazio. A fonte é `/help`
numa sessão interativa; o texto aqui é o resumo.

## Como separar o oficial do resto

O catálogo `anthropics/claude-plugins-official` tem centenas de plugins, e a
minoria é da Anthropic. O resto é de terceiros — quase tudo integração de
fornecedor, que serve à API de uma empresa, não ao seu jeito de trabalhar.

O corte é medível, não é gosto: **`author.name == "Anthropic"` no manifesto.**
Bate com o outro sinal — só esses moram em `./plugins/` dentro do próprio
repositório; os demais apontam para repositórios de fora.

**Estar no catálogo oficial não quer dizer ser da Anthropic.** O caso a
conhecer é o `superpowers`: ele é distribuído pelo catálogo oficial, mas o
código vem de `github.com/obra/superpowers` e não tem autor Anthropic no
manifesto. É bom e é muito usado — só não é primeira-parte. Se o seu critério é
"me prender no oficial", ele fica de fora do corte.

O comando que responde quantos são, hoje, na sua máquina — com o catálogo
sincronizado:

```bash
python -c "
import json,io,os
p=os.path.expanduser('~/.claude/plugins/marketplaces/claude-plugins-official/.claude-plugin/marketplace.json')
d=json.load(io.open(p,encoding='utf-8'))
a=lambda q:(q.get('author') or {}).get('name','') if isinstance(q.get('author'),dict) else ''
n=[q['name'] for q in d['plugins'] if a(q)=='Anthropic']
print(len(n),'da Anthropic de',len(d['plugins']),'no total')
print(', '.join(sorted(n)))
"
```

O comando é a fonte; o que vem abaixo é curadoria — os que se pagam.

## Escrever código

| Plugin            | O que faz                                                                                         | Quando usar                                         |
| ----------------- | ------------------------------------------------------------------------------------------------- | --------------------------------------------------- |
| `feature-dev`     | Conduz uma funcionalidade do início ao fim, com agentes para explorar, desenhar a arquitetura e revisar. | Ao implementar algo maior num código que já existe. |
| `code-simplifier` | Simplifica e refina, preservando o comportamento. Foca no que mudou há pouco.                     | Depois de fazer funcionar, antes de entregar.       |
| `frontend-design` | Interface de qualidade de produção, fugindo da aparência genérica de IA.                          | Ao construir tela que alguém vai ver.               |

## Revisar e proteger

| Plugin              | O que faz                                                                                          | Quando usar                                        |
| ------------------- | ---------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| `pr-review-toolkit` | Revisores especializados por assunto: testes, tratamento de erro, tipos, qualidade.                | Quando a revisão genérica não basta.               |
| `claude-security`   | Varredura profunda de vulnerabilidade, com cada achado desafiado antes de ser relatado.            | Auditoria de segurança sob demanda.                |
| `security-guidance` | Segurança contínua: aviso no momento da edição, revisão do diff ao parar, revisor de commit.       | Quando o agente edita de verdade e você quer rede. |

O `security-guidance` é o único desta página que age sozinho — são só ganchos,
em quatro eventos.

## Fazer o Claude Code render mais

| Plugin                 | O que faz                                                                   | Quando usar                                       |
| ---------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------- |
| `skill-creator`        | Cria skill, melhora skill existente e **mede o desempenho** dela com avaliações. | Sempre que você for escrever uma skill.           |
| `hookify`              | Cria gancho a partir do que deu errado na conversa, por regra em markdown.  | Quando um erro se repete e instrução não resolve. |
| `claude-md-management` | Audita o arquivo de instruções, dá nota e registra o que a sessão aprendeu. | Quando as instruções não batem mais com o código. |
| `claude-code-setup`    | Lê o repositório e recomenda quais automações valem a pena.                 | Ao começar num projeto novo.                      |

O `skill-creator` é o antídoto da roda reinventada: existe plugin oficial até
para escrever skill.

## O que existe e não coube aqui

Há também, no corte oficial: um plugin por linguagem para entender código com
precisão de IDE (todos exigem o servidor da linguagem instalado, e **falham em
silêncio** sem ele); kits para construir com a plataforma da Anthropic
(SDK de agentes, servidor MCP, túnel); relatórios de sessão e de impacto; e
estilos de resposta. Rode o comando acima para ver a lista de hoje — repetir
os nomes aqui só cria uma lista para envelhecer.

## Como ligar

As duas chaves no `settings.json` estão nos
[templates](../fluxos/templates.md), na seção "Ligar um plugin" — junto com o
motivo de ligar pouco: cada plugin ativo ocupa contexto da sessão inteira.
