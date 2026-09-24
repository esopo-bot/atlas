# observabilidade

Copiloto de investigação em ferramenta de observabilidade. Ele **consulta por
rota autorizada** — servidor declarado no workspace ou navegador do dono —, e
onde não houver rota, ensina a investigar e entrega a consulta pronta. Em
qualquer caso guarda o que cada incidente ensinou, e vai compondo consulta
melhor à medida que conhece as aplicações do workspace.

O módulo não traz servidor de consulta nenhum: ele usa o que o workspace já
declarou. Quem quer a rota pronta para o serviço de log da nuvem instala o
módulo `insights`, que traz a dele.

Primeira ferramenta hospedada: **Datadog**. O módulo foi desenhado para
receber uma segunda sem renomear nada — o que é método mora no nível do
módulo, o que é sintaxe mora identificado por ferramenta.

```bash
python <pasta do clone do atlas>/montar.py --modulo observabilidade
```

## O que ele instala

| Destino | O que é |
| --- | --- |
| `conhecimento/observabilidade.md` | a página da camada: método, sintaxe, formato da memória |
| `conhecimento/observabilidade/` | o **molde vazio** da memória — o conteúdo nasce na máquina de quem usa |
| `.agents/skills/observabilidade/` | a skill que conduz, ingere e encerra |
| `.agents/observabilidade/` | o emissor e o batimento, instrumentos avulsos que a camada usa para medir a si mesma |

## Os instrumentos avulsos

Nenhum dos dois roda sozinho: não há gancho nem executor que os chame. Sem
`DD_API_KEY` no ambiente, os dois dizem não medido e saem zero.

```bash
python .agents/observabilidade/emissor.py --execucao <pasta de evidências>
python .agents/observabilidade/emissor.py --motores
python .agents/observabilidade/batimento.py
```

- `--execucao` lê os recibos de UMA execução e manda span e métrica. Rode
  logo depois de ela fechar: a API de métrica descarta ponto com mais de uma
  hora, e emitir de novo uma execução já emitida dobra o span no painel.
- `--motores` manda o crédito de cada motor auxiliar cadastrado e o gasto do
  Codex, lido do registro de sessão dele. Motor sem fonte local de crédito
  fica ausente da métrica, nunca zero; a cobertura diz 0 para ele. Registro do
  Codex mais velho que a janela da API fica de fora e é contado.
- `--ensaio`, nos dois modos, mostra o que sairia sem emitir.
- O emissor tem prazo duro: o processo não vive além dele.

## Por que ele não viaja com a camada

Quem não usa observabilidade não deveria pagar contexto por ela — e quem usa
outra ferramenta receberia sintaxe errada. É a barreira do custo aplicada
literalmente: o que entra tem que valer o que cobra, e aqui só vale para
quem instalou.

## A linha que não se apaga na revisão

O objetivo deste módulo é **acumular nome de aplicação, de serviço e de
incidente** — exatamente o que nunca pode entrar num repositório público.
Por isso a fronteira é física: a camada entrega molde vazio, e todo exemplo
usa nome inventado que ninguém confunde com workspace real. Se um exemplo aqui
começar a parecer plausível, ele está errado.
