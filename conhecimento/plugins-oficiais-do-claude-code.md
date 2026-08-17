# Plugins oficiais do Claude Code

Esta página é o critério para ler o catálogo. Quais se pagam:
[canivete](skills-da-camada.md#os-plugins-que-se-pagam).

## Como separar o oficial do resto

- O catálogo `anthropics/claude-plugins-official` tem centenas de plugins;
  a minoria é da Anthropic. O corte é medível:
  **`author.name == "Anthropic"` no manifesto.**
- Só os da Anthropic moram em `./plugins/` do próprio repositório; os
  demais apontam para repositórios de fora ou moram em
  `./external_plugins/` — estar dentro do repositório não prova autoria.
- Estar no catálogo não quer dizer ser da Anthropic — o caso a conhecer é o
  `superpowers`: distribuído pelo catálogo, código de terceiro, sem autor
  Anthropic no manifesto.

## Quantos são hoje, na sua máquina

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

**O comando é a fonte; lista escrita é foto velha.** No corte oficial há
também: um plugin por linguagem para entender código com precisão de IDE
(exigem o servidor da linguagem — sem ele, o erro fica na aba Errors do
`/plugin`, e a sessão segue sem avisar em voz alta); kits da plataforma
Anthropic; relatórios; estilos de resposta.

## Como ligar

As duas chaves do `settings.json`:
[canivete](skills-da-camada.md#ligar-um-plugin).
