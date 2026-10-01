# Receitas do trabalho por issue

Os comandos que a skill cita pelo nome. Abra quando for rodar.

## A medição, antes de escrever

```bash
git rev-parse HEAD                              # o commit de partida: SHA, nunca HEAD
git status --porcelain                          # a árvore está limpa?
git worktree list                               # há alvo paralelo, e em que commit?
git branch --sort=-committerdate --format='%(refname:short) %(committerdate:relative)' | head
gh pr list --base <base da configuração> --json number,title,headRefName
```

O que essas cinco linhas respondem vai na issue: branch recente no mesmo
assunto, worktree parado num commit velho, PR aberto sobre a base — cada um é
motivo para o trabalho novo esperar, mudar de base, ou nascer em outro lugar.

## Na sessão na nuvem: a forma REST

A nuvem recusa GraphQL, e `gh issue` e `gh pr` usam GraphQL por baixo
(`conhecimento/estado-que-nao-viaja.md`). Cada forma curta tem a sua em
`gh api`, que funciona aqui e na máquina local:

```bash
R=repos/<dono>/<repo>
gh api $R/issues/<n> --jq .body                                  # issue view
gh api "$R/issues?state=open&per_page=50" --jq '.[] | select(.pull_request | not) | "\(.number) \(.title)"'  # issue list
gh api $R/issues -f title='<título>' -F body=@<rascunho>         # issue create
gh api -X PATCH $R/issues/<n> -F body=@<rascunho>                # issue edit
gh api $R/issues/<n>/comments -F body=@<rascunho>                # issue comment
gh api $R/issues/<n>/labels -f 'labels[]=<etiqueta>'             # --add-label
gh api "$R/pulls?base=<base>" --jq '.[] | "\(.number) \(.head.ref) \(.title)"'  # pr list
gh api $R/pulls -f title='<título>' -f head=<branch> -f base=<base> -F body=@<rascunho>  # pr create
```

O rascunho mora na pasta temporária, nunca no repositório. O quadro de
projetos não tem forma REST: na nuvem, o cartão se move à mão.

## Mescla com a integração aberta em outra árvore

O `git switch <integração>` recusa ("already used by worktree"). Mescle em
HEAD destacado:

```bash
git switch --detach origin/<integração>
git merge --no-ff -F <arquivo> <branch de trabalho>
git rev-parse HEAD^{tree}                       # igual ao da árvore que a bancada provou
git push origin HEAD:<integração>               # cabeça de pedido: pela conta de automação, abaixo
```

A mensagem vai por arquivo, porque o `git merge` não lê `-F -`.

## Mescla do pedido aprovado

Da pasta do repositório, pela conta de automação, nesta ordem: o push na
cabeça do pedido, a aprovação do dono, a mescla. Onde o servidor exige a
aprovação de outro, a de quem empurrou por último não conta, e push depois
da aprovação pede aprovação nova.

```bash
T=$(gh auth token --user <conta>) && [ -n "$T" ] && GH_TOKEN=$T git -c credential.helper= -c 'credential.helper=!gh auth git-credential' push origin HEAD:<integração>
T=$(gh auth token --user <conta>) && [ -n "$T" ] && GH_TOKEN=$T gh pr merge <número> --merge
```

Token vazio faria o `gh` cair na conta guardada; o `[ -n "$T" ]` para antes.
O `$(...)` vai sem aspas: é a forma que o gancho julga.
