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

## Mescla com a integração aberta em outra árvore

O `git switch <integração>` recusa ("already used by worktree"). Mescle em
HEAD destacado:

```bash
git switch --detach origin/<integração>
git merge --no-ff -F <arquivo> <branch de trabalho>
git rev-parse HEAD^{tree}                       # igual ao da árvore que a bancada provou
git push origin HEAD:<integração>
```

A mensagem vai por arquivo, porque o `git merge` não lê `-F -`.
