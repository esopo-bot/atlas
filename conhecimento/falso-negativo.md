# Falso negativo

"Não encontrei" e "não existe" são coisas diferentes, e o instrumento
raramente avisa qual das duas entregou. Vale para busca, consulta,
chamada de interface e verificação de permissão.

## O bolso: causa → hábito

| # | Causa | O hábito que resolve |
| --- | --- | --- |
| 1 | Filtro ligado sem você saber | Ancore a busca dentro do repositório; teste-a com termo que você sabe que existe. |
| 2 | Vocabulário errado | Olhe uma linha real e copie o vocabulário dela; fixe o ambiente na consulta. |
| 3 | O terminal reescreveu o argumento | Resposta sem sentido? Imprima o que o programa recebeu (`MSYS_NO_PATHCONV=1` no Git Bash). |
| 4 | O filtro espera um fim que não vem | Processo longo escreve em arquivo; para esperar, use sonda que termina. |
| 5 | A interface não está no arquivo | Presença em interface se prova com clique, não com busca no HTML. |
| 6 | O ambiente não tem o dado | Antes de navegar, pergunte "o dado existe aqui?" com consulta direta. |
| 7 | A medição saiu de outro lugar | Ancore no caminho absoluto; imprima o `pwd` na mesma chamada que mede. |
| 8 | O seu próprio filtro | Exclua por arquivo, não por conteúdo; rode uma vez sem o filtro. |
| 9 | Quem perguntou não foi você | Pergunte quem está logado com a chamada que **usa** o token; quem trocou de conta, devolve. |

## Os comandos de cada causa

- **1** — `.gitignore` esconde do git E da busca (não da leitura direta).
  Contraprovas: `rg --no-ignore` da raiz; `git log -S <termo>` dentro do
  repositório.
- **3** — imprima o recebido antes de acreditar na resposta:
  `MSYS_NO_PATHCONV=1 python -c "import sys; print(sys.argv[1])" /caminho`.
- **4** — `tail`, `sort` e `wc` só respondem quando a entrada fecha;
  `head -n N` e `grep -m N` saem quando a conta fecha. Para esperar
  serviço: `until curl -s -o /dev/null <endereço>; do sleep 2; done`.
- **6** — verificação que depende de evento não fecha em janela sem
  evento: provoque o evento ou ancore num que tem hora marcada. Massa
  semeada por fora morre na recriação do ambiente.
- **7** — quando o número importar: `pwd; <a medição>` na mesma chamada.
- **8** — exclua pelo campo do caminho (`grep -v "^caminho/"`,
  `rg -g '!pasta/**'`), nunca pelo conteúdo. Frase em prosa formatada dá
  zero falso: normalize antes (`tr '\n' ' ' | tr -s ' '`) ou procure um
  pedaço curto.
- **9** — `404` responde igual para "não existe" e "você não enxerga".
  Pergunte ao token, não ao rótulo: só a chamada autenticada prova a
  identidade em uso. Verificação de identidade: duas provas no mesmo token,
  várias tentativas por prova, e qual prova respondeu aparece na tela.
  Resultado intermitente se conta, não se conclui da primeira.

## A regra em uma linha

Antes de escrever "não existe", prove que o instrumento sabe achar: a
mesma consulta, na mesma janela, tem de trazer alguma coisa. Sem isso,
escreva "não medido".
