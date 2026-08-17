# Configuração da casa

Onde ESTE repositório trabalha por issue. O arquivo é seu: a camada o
cria uma vez e a atualização nunca o sobrescreve — troque os
`${...}` pelos valores da sua casa. Sessão e corrente leem daqui antes
de criar issue; enquanto houver `${...}` sem valor, não se cria issue —
pergunta-se ao dono.

- **Repositório das issues:** `esopo-bot/atlas` — toda issue
  deste trabalho nasce lá, mesmo quando o código mora em outro
  repositório. Nunca criar issue em repositório de código.
- **Padrão de nome:** `semana_<número ISO da semana>_hist_<n>` — ex.:
  `semana_33_hist_1`.
- **Fluxo do backlog:** issue nova nasce no backlog, no fim da fila;
  achado novo durante a hist corrente entra na PRÓXIMA
  (`hist_<n+1>`), nunca fura; uma sessão termina um trabalho; épico
  vira pergunta ao dono antes de entrar.

O desenho e o porquê: `fluxos/historia-em-issue.md`. O que se executa:
skill `trabalho-por-issue`.
