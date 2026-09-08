# Sessão de pesquisa — a que não escreve no repositório

Prompt de abertura para a sessão que **pesquisa e não entrega em disco**:
ela lê a camada, conversa sobre ela, mede o que precisar, e o resultado do
trabalho vai para uma **issue**. Nenhum arquivo do repositório muda.

Cole inteiro numa sessão aberta na raiz, com a marca `ATLAS_SO_LEITURA` no
ambiente, e escreva o pedido no fim.

## Por que este modo existe

A camada cobra destino de tudo que a sessão faz: árvore suja, commit fora da
branch de entrega, pedido de incorporação aberto. É a regra 16, e ela está
certa — para quem entrega em disco.

Quem só pesquisa não entrega em disco, e a cobrança vira ruído: a sessão
gasta turno explicando que não tem o que commitar. Pior, em árvore
compartilhada ela é cobrada pelo trabalho das outras. Este modo desliga essa
cobrança e, em troca, fecha a porta da escrita.

## O trato

**Você pode:**

- Ler tudo: páginas, skills, instrumentos, ganchos, código dos projetos.
- Rodar instrumento que só mede — `--estado`, `--largada`, `--ensaio`,
  `--testar`, `git` de leitura, busca no acervo.
- Escrever **fora** do repositório: a pasta temporária da máquina serve, e o
  sistema a limpa sozinho. É onde vão rascunho, saída longa e script de
  medição.
- Criar issue, comentar, editar o corpo da issue.

**Você não pode:**

- Escrever, editar ou apagar **qualquer arquivo dentro do repositório** —
  nem em `tmp/`, nem arquivo temporário. A cerca
  `vetar-escrita-em-sessao-de-pesquisa` recusa, e a recusa não é negociável:
  se você precisa escrever, o modo é o errado.
- Gravar memória. O que valeria memória vira **comentário na issue do
  trabalho** — decisão do dono, para a sessão não deixar rastro na máquina.
- Commitar, empurrar, mesclar, abrir pedido de incorporação.

## O que você entrega

**A issue, e só ela.** Vale a skill `trabalho-por-issue`: a issue nasce onde
a configuração do repositório manda, com objetivo, escopo com o "fora",
critérios verificáveis e ponto de retomada.

Ao fechar, o que a sessão apurou tem de estar **no corpo ou num comentário**.
O que não estiver na issue não existe — aqui isso é literal, porque não sobra
arquivo nenhum.

## Como medir sem sujar

- Saída longa vai para arquivo na pasta temporária, e você lê de lá.
- Script de medição nasce na pasta temporária e roda de lá, com caminhos
  absolutos para o repositório.
- Contagem e comparação: prefira o comando que já existe no repositório a
  escrever um novo.
- Achou algo que exige mudar arquivo? **Não mude.** Escreva na issue o
  caminho, a linha e o conserto proposto, e diga que é de outra sessão.

## As regras que continuam valendo

Todas as da camada, menos a cobrança de destino. Em especial:

- **Regra 2**: só é pronto o que um instrumento provou — comando rodado com
  saída vista, colada na issue.
- **Regra 3**: antes de afirmar que algo não existe, procure e cite; "não
  achei" só vale com o comando de busca ao lado, e com a contraprova de que
  esse comando acha o que está lá.
- **Regra 8**: segredo não entra em texto rastreado, e issue é texto
  rastreado.
- **Regra 17**: explique na altura de quem lê, começando por júnior.

## Antes de abrir

Confirme que a marca está posta — sem ela a cerca não morde e você volta a
ser cobrado:

```bash
echo "$ATLAS_SO_LEITURA"
```

Vazio? Então esta sessão **não** está em modo de pesquisa: ou você põe a
marca e reabre, ou usa o prompt de abertura normal.

---

## O PEDIDO

<escreva aqui o que a sessão vai pesquisar, e em que issue o resultado mora>
