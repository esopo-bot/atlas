# Módulo encadeador

O que ele é: o script que roda uma execução de etapas lendo um roteiro e
deixando uma evidência por etapa — o motor opcional de quem quer encadear
sessões de IA e scripts com prova em arquivo. Generaliza a receita local de rodar
`claude -p` com ambiente preparado e soma o
que ela não tinha: roteiro com dependências, fork/join de etapas
independentes, ensaio que lista tudo sem executar nada, e evidências escritos
só por código (o contrato mora na camada, em `.agents/evidencia/`).

O que ele instala: `.agents/encadeador/encadeador.py`. Ele exige a camada
no destino — usa `evidencia.py` e `verificar.py` como estão, nunca os copia.

Etapa `tipo: sessao` pode declarar `modelo` (texto) e `ferramentas-negadas`
(lista de nomes), que viram `--model` e `--disallowed-tools` na chamada.
Sem o campo na etapa, o motor procura `modelo_por_etapa.<nome-da-etapa>` em
`nucleo/configuracao.json` — assim um modelo escolhido para uma etapa vale
em todo roteiro que a tiver, sem editar cada arquivo. A etapa que declara o
próprio `modelo` sempre vence o valor central. `bare` (booleano) some com
a camada da sessão — mesmo uso de sempre, só que agora declarável no
roteiro em vez de só por variável de ambiente.

Por que é módulo e não camada: só serve a quem roda execuções de etapas;
para todo o resto seria peso morto na largada. E o nome é `encadeador` por
decisão do dono (16/08/2026): o motor daqui nunca tomou emprestada a
palavra que, nas regras da camada, nomeia a automação do repositório — hoje
chamada de integração contínua.

## O que a execução desliga: `--dangerously-skip-permissions`

Confissão, não justificativa.

**O que ele desliga:** a pergunta de permissão do Claude Code. Com ele, a
sessão não pede aprovação para nenhuma ferramenta — nem para editar arquivo,
nem para rodar comando de terminal. O que sobra de guarda são os ganchos, que
continuam valendo.

**Por que a execução exige:** cada etapa roda `claude -p` sem ninguém na
frente do terminal. Uma pergunta de permissão não teria quem a respondesse: a
etapa ficaria parada até estourar o tempo-limite.

**Onde ele está declarado:** `PADRAO_DAS_BANDEIRAS_DA_SESSAO`, em
`.agents/encadeador/encadeador.py` — a fonte é
`modulos/encadeador/.agents/encadeador/encadeador.py`. A variável de ambiente
`ENCADEADOR_SESSAO_BANDEIRAS` substitui a linha inteira.

Como a pergunta some, é o gancho que fica no lugar dela. O
`vetar-escrita-em-politica` recusa, durante a etapa, escrita nos arquivos que
decidem quais cercas existem — e só durante a etapa, porque quem levanta essa
cerca é a marca `ENCADEADOR_ETAPA` no ambiente, posta por este motor.
