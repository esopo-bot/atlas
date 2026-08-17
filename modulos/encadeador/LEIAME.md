# Módulo encadeador

O que ele é: o script que roda uma corrente de etapas lendo um manifesto e
deixando um recibo por etapa — o motor opcional de quem quer encadear
sessões de IA e scripts com prova em arquivo. Generaliza a receita de
`rotinas/executar.sh` (rodar `claude -p` com ambiente preparado) e soma o
que ela não tinha: manifesto com dependências, fork/join de etapas
independentes, ensaio que lista tudo sem executar nada, e recibos escritos
só por código (o contrato mora na camada, em `.agents/recibo/`).

O que ele instala: `.agents/encadeador/encadeador.py`. Ele exige a camada
no destino — usa `recibo.py` e `conferir.py` como estão, nunca os copia.

Por que é módulo e não camada: só serve a quem roda correntes de etapas;
para todo o resto seria peso morto na largada. E o nome é `encadeador` por
decisão do dono (16/08/2026): "esteira", nas regras da camada, é a
automação da casa (CI) — palavra que este módulo não usa.
