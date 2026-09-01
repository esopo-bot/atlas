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
  --roteiro execucoes/revisar-a-camada.json \
  --trabalho revisar-a-camada --dir tmp/evidencias
python .agents/encadeador/encadeador.py executar \
  --roteiro execucoes/revisar-a-camada.json \
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

## O método, quando a revisão é sua e não do roteiro

O roteiro acima mede. Quando a revisão é conduzida por alguém — lendo,
perguntando, propondo —, o que separa revisão de opinião é a régua abaixo.

### A régua de uma proposta

Proposta só existe com três partes. Sem as três, não é proposta:

1. **O problema, medido** — comando rodado e saída colada. Para achado vindo
   de fora, o endereço da fonte no lugar do comando.
2. **O custo de deixar como está** — em quê isso morde: estabilidade, tempo,
   contexto, dinheiro da sessão, ou risco de quem instalar a camada.
3. **O instrumento que provaria o conserto** — o que vai ficar verde depois.

Está proibido: *poderia ficar mais limpo*, *boa prática recomenda*, *seria bom
padronizar*, *a versão nova tem isso*. Quem não consegue medir tem uma
**pergunta aberta**, e pergunta aberta se registra como pergunta — nunca como
tarefa.

### A ordem de executar o que passou na régua

- Estabilidade antes de economia, economia antes de performance, performance
  antes de estética.
- **Menor diff coerente**: uma entrega que passa sozinha por vez.
- Arrumação e mudança de comportamento não andam no mesmo passo — diff
  misturado ninguém revisa.
- Antes de começar e antes de terminar: `git status --short`. Arquivo que
  mudou e não é seu é outra sessão — pare e avise.

### A definição de pronto

Tudo medido, sem exceção: o ritual verde, todo `--testar` em OK e **nenhum
piso abaixo** da última medição registrada, o instalador dizendo que está tudo
em dia, o ensaio de publicação sem achado, e `git status --short` mostrando só
o que se quis mudar.

A medida que **varia sozinha** é a sessão simulada, porque é uma sessão de
verdade. A regra dela: caiu, rode de novo antes de chamar de achado; caiu duas
vezes seguidas, é achado — e olhe **qual** checagem caiu, não só o placar.

### Quando não há nada a fazer, e quando as barreiras barram

Diga isso, com a medição junto, e pare. **Não invente trabalho.** Um "nada a
fazer" provado vale mais que uma refatoração inventada, e a revisão seguinte
começa sabendo onde já se olhou. Vale por pergunta: dez perguntas com achado e
uma sem é revisão normal; dez perguntas com achado forçado é revisão perdida.

Há o outro fim, que também não é fracasso: **uma barreira barrou.** Gancho, veto e
doutrina são calibrados por quem não vai executá-los, então param a sessão por
tolerância que ninguém previu — não por erro dela.

Quando acontecer: **não contorne, não peça exceção, e não trate como falha
sua.** Registre a parada com o comando que a disparou e a tolerância que
faltava, e siga o que der para seguir. A lista dessas paradas é a matéria-prima
para recalibrar as barreiras, e é a única forma de a régua melhorar sem
alguém afrouxá-las no susto.
