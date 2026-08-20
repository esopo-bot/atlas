# Revisar a camada

O roteiro `revisar-a-camada.json`, ao lado, mede a camada de IA **deste**
repositório e diz se ela ainda paga o que cobra.

Ela responde três perguntas, nesta ordem, e nenhuma delas por opinião:

1. **Quanto a camada cobra?** Quantos bytes toda sessão paga antes de fazer
   qualquer coisa — as instruções mais o catálogo de skills. O corpo de cada
   skill não entra nessa conta: ele só é cobrado quando a skill dispara.
2. **A camada se prova?** Todo gancho e todo instrumento roda o próprio
   `--testar`, e o instalador verifica se o que ele carrega embutido bate com
   o disco. Gancho sem teste é acusado pelo nome.
3. **Uma sessão de verdade lê e aplica as regras?** Uma sessão sem dono por
   perto abre neste repositório, lê a camada e responde seis perguntas sobre
   as regras dela — onde abrir a sessão, quantas regras existem, se pode
   commitar, o que fazer com segredo, o que fazer com branch de longa
   duração, o que é pronto. Depois escreve um script pequeno, e duas
   checagens medem se o teste que ela escreveu passa e se ele exercita o
   próprio código. A correção é programática: comparação com
   `nucleo/regras.json` e leitura de AST. Não há juiz de IA.

## O que ela NÃO faz

Não commita, não empurra, não publica e não conserta nada. Ela mede e
relata; o que fazer com o número é de quem lê.

## Como rodar

```bash
python .agents/encadeador/encadeador.py ensaio \
  --roteiro modulos/encadeador/execucoes/revisar-a-camada.json \
  --trabalho revisar-a-camada --dir tmp/evidencias
python .agents/encadeador/encadeador.py executar \
  --roteiro modulos/encadeador/execucoes/revisar-a-camada.json \
  --trabalho revisar-a-camada --dir tmp/evidencias --cwd .
```

O ensaio lista os estágios sem executar nada. A etapa `sessao-simulada` gasta
uma sessão de verdade: é a única que custa dinheiro, e a única cujo número
varia sozinho. Acurácia que cai pede uma segunda rodada antes de virar
achado.

## Onde os números moram

Cada etapa grava uma evidência em `<dir>/<trabalho>/`. As provas são
comandos re-executáveis que imprimem um número só — o `--numero` do
`camada.py` existe para isso, e é o que a etapa de verificação re-roda.
