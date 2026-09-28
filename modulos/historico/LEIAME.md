# historico

Quando uma issue fecha, o corpo final dela vira um `.md` local, numa pasta
por projeto, indexado para o trabalho seguinte achar. O mecanismo viaja; o
histórico fica na máquina de quem trabalha.

Um instrumento, `historico`, e uma página, `conhecimento/historico.md`, com o
que ele garante e o que se guarda onde. Vem ligado: a seção "Fechar" da
skill `trabalho-por-issue` o cita.

```bash
python <pasta do clone do atlas>/montar.py --modulo historico
python .agents/historico/historico.py --pendentes
python .agents/historico/historico.py --colher
```

**O que ele precisa:** `issues.repositorio` e `projetos` em
`nucleo/executor.json`, e o `gh` com a conta das issues. Sem o endereço ele
diz que não mediu, e não inventa zero.

**A pasta fica fora do git** pelo `.gitignore` que o módulo grava dentro
dela, uma vez só: o instalador não mexe no `.gitignore` da raiz de ninguém.
