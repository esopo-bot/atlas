# Plugins oficiais do Claude Code

Esta página não é o catálogo nem a curadoria — é **o critério para ler o
catálogo**. Quais plugins se pagam está no
[canivete](skills-da-camada.md#os-plugins-que-se-pagam).

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

## Quantos são hoje, na sua máquina

Com o catálogo sincronizado:

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

**O comando é a fonte; qualquer lista escrita é foto velha.** Por isso esta
página não repete nomes: há também, no corte oficial, um plugin por linguagem
para entender código com precisão de IDE (todos exigem o servidor da linguagem
instalado, e **falham em silêncio** sem ele); kits para construir com a
plataforma da Anthropic (SDK de agentes, servidor MCP, túnel); relatórios de
sessão e de impacto; e estilos de resposta. Rode o comando para ver a lista de
hoje.

## Como ligar

As duas chaves do `settings.json` estão no
[canivete](skills-da-camada.md#ligar-um-plugin), junto com o motivo de ligar
pouco.
