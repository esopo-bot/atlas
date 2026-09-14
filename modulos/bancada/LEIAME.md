# bancada

Dá **nota** a uma versão do texto de abertura, em vez de opinião. Cada rodada
abre sessões de verdade, sem ninguém no terminal, em árvores isoladas, e mede
o que elas fizeram.

Existe porque o texto que toda sessão lê ao abrir é a peça mais cara da
camada, e a régua usual para ele é a intuição de quem o escreveu — que é a
pior régua possível. Prompt bem escrito parece bom; regra clara parece que vai
ser seguida. Só medindo se descobre que não.

```bash
python montar.py --modulo bancada
cp nucleo/bancada.exemplo.json nucleo/bancada.json   # e preencha
python .agents/bancada/bancada.py tudo --versao v1 --ref <commit>
```

A receita inteira — por que cada peça existe, como escolher um problema fixo e
as armadilhas medidas — está em
[medir o prompt de abertura](../../conhecimento/medir-o-prompt-de-abertura.md).
Este cartão é só o de operar.

## O que ela faz, em cinco passos

1. **`montar`** — clona a camada do commit que você declarou em `--ref` para
   uma árvore por braço, e o repositório vizinho de um espelho local, no
   commit onde o defeito ainda existe. Nada toca repositório de verdade.
2. **`rodar`** — abre uma sessão sem cabeça em cada árvore, com o pedido
   declarado e mais nada. Os ganchos e as cercas do repositório valem lá
   dentro.
3. **`medir`** — lê o que ficou no disco, no rastreador e no transcrito, e dá
   a nota dos itens que instrumento consegue medir.
4. **`placar`** — imprime a tabela da versão, item a item.
5. **`tudo`** — os quatro na sequência.

`julgar.py` aplica ao placar os três ou quatro itens que instrumento nenhum
mede — língua, ordem da explicação, receita seguida —, depois de um painel de
juízes ler o `resumo.md` de cada braço.

## Os casos são seus, e ficam fora do git

O instrumento não conhece projeto nenhum. Os braços moram em
`nucleo/bancada.json`, que **não entra em git**: ele nomeia repositório e
commit. O exemplo versionado ao lado explica cada campo.

Um braço declara o pedido, a prova e — quando o trabalho é num vizinho — a
pasta dele, o commit e a branch de integração. **A prova é um comando que sai
zero quando o problema está resolvido**, e é isso que mantém a nota honesta:
critério que começa pelo adjetivo não serve.

## O que ela nunca faz

- **Não escreve no rastreador.** O cliente de linha de comando é substituído
  por um dublê que deixa leitura passar e finge escrita, guardando o que a
  sessão tentou criar. A sessão de teste também roda com a configuração do
  cliente apontando para uma pasta vazia, então o binário de verdade não tem
  conta nenhuma — rede de segurança para o caso de o dublê falhar.
- **Não empurra para remoto de verdade.** O `push` cai no espelho local.
- **Não escreve na raiz da camada.** Ela só lê de lá para clonar.

## O preço

Cada rodada abre uma sessão por braço e **cobra por elas**. Três braços ficam
na casa de alguns dólares e vinte minutos. Instalar é ligar; não instalar é
desligar — quem não vai medir texto de abertura não deve pagar por isto.

Exige, no destino: um cliente de linha de comando do rastreador, o agente de
terminal que abre a sessão sem cabeça, e `git`.

## Uma medição não é medição

Diferença de poucos pontos entre duas rodadas é ruído. O que se lê é o piso
que mudou de categoria: um item que era zero de três e virou três de três.
