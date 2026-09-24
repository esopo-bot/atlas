# bancada

Dá **nota** a uma versão do texto de abertura, em vez de opinião. Cada rodada
abre sessões de verdade, sem ninguém no terminal, em árvores isoladas, e mede
o que elas fizeram.

Existe porque o texto que toda sessão lê ao abrir é a peça mais cara da
camada, e a régua usual para ele é a intuição de quem o escreveu — que é a
pior régua possível. Prompt bem escrito parece bom; regra clara parece que vai
ser seguida. Só medindo se descobre que não.

```bash
python <pasta do clone do atlas>/montar.py --modulo bancada
cp nucleo/bancada.exemplo.json nucleo/bancada.json   # e preencha
python .agents/bancada/bancada.py tudo --versao v1 --ref <commit>
```

Este cartão é o de operar e a receita inteira: por que cada peça existe, como
escolher um problema fixo e as armadilhas medidas. Ela nasceu de seis rodadas
sobre o próprio prompt de abertura desta camada, e o que está aqui é o que
sobreviveu à medição.

## O que ela faz, em cinco passos

1. **`montar`** — clona a camada do commit que você declarou em `--ref` para
   uma árvore por braço, e o repositório vizinho de um espelho local, no
   commit onde o defeito ainda existe. Nada toca repositório de verdade.
2. **`rodar`** — abre uma sessão sem cabeça em cada árvore, com o pedido
   declarado e mais nada. Os ganchos e as cercas do repositório valem lá
   dentro — provado: uma cerca recusou um comando numa sessão sem cabeça, com
   a mensagem inteira no transcrito.
3. **`medir`** — lê o que ficou no disco, no rastreador e no transcrito, e dá
   a nota dos itens que instrumento consegue medir.
4. **`placar`** — imprime a tabela da versão, item a item.
5. **`tudo`** — os quatro na sequência.

`julgar.py` aplica ao placar os três ou quatro itens que instrumento nenhum
mede — língua, ordem da explicação, receita seguida —, depois de um painel de
juízes ler o `resumo.md` de cada braço.

## A regra da rodada

- **A versão sob teste é um commit.** Escreva ou corrija o prompt, commite, e
  é esse commit que a rodada mede. Sem commit não há versão, e sem versão não
  há comparação.
- **O que muda de uma rodada para a outra é só o prompt.** Mesmo problema,
  mesmo commit, mesmo modelo. É isso que torna a diferença atribuível ao
  texto.
- **Cada erro vira uma correção do prompt**, e a correção vira a versão
  seguinte.
- **A leitura do briefing só conta inteira.** O item que a mede exige a
  leitura do arquivo todo antes de abrir outro arquivo; `grep`, `head` e
  leitura com limite não contam.

## Os casos são seus, e ficam fora do git

O instrumento não conhece projeto nenhum. Os braços moram em
`nucleo/bancada.json`, que **não entra em git**: ele nomeia repositório e
commit. O exemplo versionado ao lado explica cada campo.

Um braço declara o pedido, a prova e — quando o trabalho é num vizinho — a
pasta dele, o commit e a branch de integração. **A prova é um comando que sai
zero quando o problema está resolvido**, e é isso que mantém a nota honesta:
critério que começa pelo adjetivo não serve.

## Os problemas fixos: pequenos, reais e prováveis por comando

O problema de cada braço se escolhe por três propriedades, nesta ordem:

- **Existe de verdade no commit declarado.** Problema inventado mede a
  obediência da sessão, não o trabalho dela.
- **Cabe numa sessão** — poucas dezenas de linhas, sem depender de serviço
  externo, login ou dado de gente.
- **Tem um comando que diz sim ou não**, sem adjetivo: uma contagem que era
  quatro e passa a ser zero, uma suíte que passa.

Três armadilhas medidas, todas caras:

- **Problema que já foi resolvido na vida real contamina a rodada.** Uma
  sessão leu o rastreador, viu o trabalho mesclado em produção e parou antes
  de duplicar. A conduta estava certa e a medição, perdida. Prefira problema
  sem história pública, ou esconda essa história do dublê.
- **Problema que nasce vazio dá nota falsa.** A contagem inicial foi feita
  numa cópia atrasada do repositório; na ponta, o defeito já não existia. As
  sessões disseram "nada a trocar", estavam certas, e o instrumento as
  reprovou por quatro rodadas.
- **O dublê precisa de memória.** Um cliente falso que inventa identificador
  e esquece o que criou faz a sessão gastar turnos investigando um registro
  que não existe. Guarde o que ele cria e devolva na leitura seguinte.

## A régua: o que instrumento mede e o que juiz julga

Separe os dois na hora de escrever a régua, porque misturar produz nota que
ninguém consegue reproduzir.

**Instrumento mede fato do disco e do rastreador**, e a armadilha é olhar o
estado final. Um medidor que lia a branch no fim da sessão reprovou justamente
quem fez tudo certo: criou a branch, empurrou, mesclou e podou o rastro — e
terminou na branch de integração, com a branch de trabalho já apagada. Meça o
**ato**, não o resíduo: a criação da branch nos comandos, o trabalho chegando
ao espelho, o commit da ponta sendo mescla.

**Juiz julga o que não tem instrumento**: língua, ordem da explicação, receita
seguida. Use mais de uma lente, exija trecho literal como evidência, e ponha
um cético por achado — mede-se que a maioria dos achados de painel não
sobrevive a quem tenta derrubá-los.

**Juiz também erra, e a bancada é quem o corrige.** Duas vezes um painel
propôs frase que contrariava a regra declarada do repositório, e as duas foram
descartadas por isso. Quando o juiz e o contrato divergem, o contrato ganha.

## O achado que paga a bancada inteira

**Regra escrita não muda o jeito de falar; exemplo copiável muda.**

Foi medido assim: quatro rodadas seguidas acrescentaram frases de regra sobre
como escrever — a língua, a ordem, o tamanho da frase. O item de conversa
ficou parado em zero de três nas quatro. Na rodada seguinte, as mesmas
intenções entraram como **três moldes prontos** — a linha entre duas
ferramentas, a primeira resposta, a resposta final — e o item foi de zero para
três de três na primeira tentativa.

A leitura que sobra: para **mecânica** (o que rodar, em que ordem, o que não
fazer), regra funciona. Para **forma** (como escrever, como explicar), só
exemplo funciona.

E há um irmão desse achado, medido no mesmo laço: **prompt que ninguém abre
não corrige nada.** Nas duas primeiras rodadas o briefing estava pronto e só
uma sessão o leu, porque o ponteiro para ele morava no meio do arquivo de
instruções. Movido para a primeira seção, a leitura foi a três de três, e
junto com ela o primeiro comando da abertura. **Ponteiro no topo vale mais que
capítulo bem escrito no fim.**

## O que ela nunca faz

- **Não escreve no rastreador.** O cliente de linha de comando é substituído
  por um dublê que deixa leitura passar e finge escrita, guardando o que a
  sessão tentou criar. A sessão de teste também roda com a configuração do
  cliente apontando para uma pasta vazia, então o binário de verdade não tem
  conta nenhuma — rede de segurança para o caso de o dublê falhar.
- **Não empurra para remoto de verdade.** O `push` cai no espelho local.
- **Não escreve na raiz da camada.** Ela só lê de lá para clonar.

## Quando vale a pena, e o preço

Não vale para texto que uma pessoa lê uma vez. Vale para o texto que **toda
sessão paga**: o prompt de abertura, as instruções da raiz, a descrição de uma
skill. Ali, meio ponto de nota se multiplica por todas as sessões de todo
mundo, e a opinião de quem escreveu custa mais caro que a medição.

Cada rodada abre uma sessão por braço e **cobra por elas**. Três braços ficam
na casa de alguns dólares e vinte minutos; seis rodadas cabem numa madrugada.
Instalar é ligar; não instalar é desligar — quem não vai medir texto de
abertura não deve pagar por isto.

Exige, no destino: um cliente de linha de comando do rastreador, o agente de
terminal que abre a sessão sem cabeça, e `git`.

## Uma medição não é medição

Diferença de poucos pontos entre duas rodadas é ruído. O que se lê é o piso
que mudou de categoria: um item que era zero de três e virou três de três.
