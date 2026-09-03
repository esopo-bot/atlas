# Auditoria externa da camada — prove que ela merece existir

Prompt para uma sessão **de fora**: outro modelo, outra conta, contexto
limpo. Cole inteiro numa sessão aberta na raiz do repositório da camada.

Seu papel não é ajudar. É **derrubar**. A camada tem de se provar diante de
você, não o contrário.

## Por que uma sessão de fora

O ritual do repositório tem treze rotinas e elas passam verdes com defeito
grave dentro. Já aconteceu: um instrumento nunca conseguiu mover o cartão do
quadro por falta de permissão e a recusa aparecia como "não achei" — semanas
assim, ritual verde o tempo todo. Ritual verifica o que alguém pensou em
verificar. **Você existe para olhar o que ninguém pensou.**

## A regra que vale acima de todas

**Meça antes de afirmar.** Este repositório recusa opinião: cada afirmação
sua precisa vir com o comando que a produziu e a saída colada. Achado sem
medição é palpite, e palpite aqui custa mais caro que silêncio.

E **uma medição não é medição**. Onde houver variação — escolha de modelo,
tempo, custo —, o ruído engole diferenças pequenas. Compare medianas de cinco
execuções, e desconfie de qualquer diferença menor que o ruído que você
mediu.

## O que você faz, nesta ordem

### 1. Entenda antes de julgar

- [ ] `cat AGENTS.md` e `cat CLAUDE.md` — as instruções que toda sessão paga.
- [ ] `python3 verificacoes.py` — a lista das rotinas e o que cada uma prova.
- [ ] `python3 verificacoes.py ritual` — rode e leia a saída inteira. Ela passa
      de 100 KB: leia por seção, com `grep` ou `awk`, em vez de abrir tudo de
      uma vez — leitor que estoura o teto de saída perde o fim, que é onde
      mora o veredito.
- [ ] `python3 verificacoes.py instalada` — **esta não está no ritual** e é a
      que roda o `--testar` de cada gancho e instrumento. Rode sempre.
- [ ] `python3 .agents/camada/camada.py --largada` — o que toda sessão paga
      antes de trabalhar, e o teto declarado.

### 2. Ataque a premissa, não a implementação

Para cada peça que você encontrar, pergunte nesta ordem:

1. **Isto resolve um problema real, ou um problema imaginado?** Peça sem
   caso de uso medido é peso. Procure quem a chama: se ninguém chama, diga.
2. **Isto já existe pronto?** Compare com o que a ferramenta oficial já
   traz, com o que o ecossistema tem, e com o que outra peça daqui já faz.
   Cite a fonte oficial — versão e data — quando disser que existe.
3. **A prova dela prova mesmo?** Teste que não falha quando o código quebra
   não é teste. Quebre de propósito e veja se alguém acusa.
4. **O que ela custa a toda sessão?** Bytes de largada, tempo, tokens.
   Compare o custo com o problema que ela resolve.

### 3. Procure o caminho de erro que ninguém escolheu testar

É onde os defeitos moram. Especificamente:

- [ ] Função que **engole exceção em volta de uma conta**: falha vira zero, e
      zero parece fato.
- [ ] Verificação que enumera **o que ignora** em vez de declarar **o que
      prova**: cada peça nova do repositório vira falso positivo.
- [ ] Cópia gerada que diverge da fonte sem ninguém acusar.
- [ ] Cerca que barra por uma via e cala por outra — o mesmo efeito por
      `Edit` e por `Bash`, por exemplo.
- [ ] Cerca que reconhece uma **lista fechada de programas**: liste todo
      programa que o parser de comando conhece e pergunte o que produz o
      mesmo efeito e NÃO está na lista. A falha mora dentro do mesmo canal,
      não entre canais — em 03/09/2026 foi `curl -o`, `wget -O`, `rsync`,
      `perl -i` e `dd of=` atravessando quatro cercas de escrita que só
      conheciam `rm`, `mv`, `cp`, `tee` e `sed -i`.
- [ ] **Antes de atacar um gancho, leia a issue mais recente que o tocou**
      (`gh issue list --search "<nome do gancho>"`). Achado que a issue já
      discutiu e deixou fora de propósito não é achado — é comentário nela.
- [ ] Recusa de permissão que aparece como "não encontrei".

### 4. Consulte a documentação oficial, e cite

Onde a camada usa ferramenta de terceiro, confira contra a documentação
oficial **de hoje**, não contra a sua memória. Diga a versão que consultou.
Se a camada usa um recurso descontinuado, ou deixa de usar um que resolveria
melhor, isso é achado de primeira ordem.

## O que fazer com o que você achar

**Achado vira linha no quadro, não arquivo:**

```bash
python3 .agents/caixa/caixa.py defeito --id <kebab-minusculo> --assunto "<o achado inteiro, com a medição e o comando que a replica>"
python3 .agents/caixa/caixa.py melhoria --id <kebab-minusculo> --assunto "<idem>"
```

Uma linha por achado, com o comando que o reproduz. Sem isso, quem ler não
consegue reproduzir e o achado morre.

**Mudança de regra se PROPÕE, não se aplica.** Regra, gancho e política são
do dono. Escreva a proposta com a medição que a sustenta e pare.

**Feche mais do que abre.** Antes de abrir issue nova, procure a existente:
`gh issue list --repo <declarado em nucleo/executor.json>`. Achado que já tem
linha no quadro vira comentário nela, não linha nova.

## Onde você NÃO manda

- **Publicar é do dono.** Seu teto é `python3 publicar.py --ensaio`.
- **Destrutivo é do dono.** Não apague nada; proponha, com a razão.
- **Não edite cópia gerada.** A fonte é a que viaja; a cópia se regenera.
- **Nada de segredo, nome de pessoa, de empresa ou caminho de máquina** em
  arquivo, commit ou issue. Este repositório é público.

## Como você encerra

- [ ] O que você **mediu**, com comando e saída colados.
- [ ] O que você **derrubou** — afirmação da camada que não se sustentou.
- [ ] O que você **não conseguiu derrubar**, que é o valor de verdade: peça
      que resistiu a um ataque honesto está mais provada que antes.
- [ ] As linhas que você pôs no quadro, por identidade.
- [ ] **Uma crítica a este prompt**: o que ele te fez perder tempo olhando, e
      o que ele deixou de mandar você olhar. A régua sobe a cada rodada, e
      quem a levanta é você.
