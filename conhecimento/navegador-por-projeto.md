# Um navegador por projeto

Para a sessão ler uma tela que só existe depois do login. A camada **manda
usar** navegador — a skill `documentar-processo` pede para ler a fonte junto,
com a ferramenta de navegador disponível — e nunca ensinou a montar uma.
Esta página é a receita que faltava.

O que ela entrega: um servidor de navegador por projeto, com a sessão já
autenticada, que o agente aciona como qualquer outra ferramenta.

**O servidor em si não viaja.** Ele é da sua máquina e do seu projeto, e a
declaração dele fica fora do git. O que viaja é esta receita.

## Um servidor por projeto, não um só para tudo

Cada projeto tem seu endereço, seu login e sua sessão. Um servidor
compartilhado entre projetos mistura os três: o agente entra com a sessão
errada, lê a tela de outro sistema e conclui em cima dela — sem erro nenhum
aparecer. Separar custa uma pasta a mais; descobrir isso depois custa a
conclusão inteira.

A separação é uma pasta de perfil por projeto, e um servidor declarado por
projeto apontando para a sua.

## O perfil persistente, num cofre local

O navegador guarda o que prova quem você é: cookie, armazenamento local e,
às vezes, o banco de dados do navegador. Servidor sem perfil persistente
começa cada execução do zero — e do zero quer dizer deslogado.

A receita, uma vez por projeto:

1. **Escolha a pasta do cofre local** — fora da árvore rastreada, ignorada
   pelo `.gitignore`. Ali dentro vai estado de sessão, que é credencial.
2. **Declare a pasta como perfil do servidor**, na configuração de
   servidores do seu agente.
3. **Suba com janela visível e faça o login à mão.** É a única vez que
   alguém digita senha.
4. **Feche.** O perfil ficou gravado na pasta, e a próxima execução já entra
   logada.

Segredo não entra em texto rastreado: onde a configuração pedir senha ou
token, vai `${VARIAVEL}`, nunca o valor. O caminho da pasta é da sua máquina
— declare-o por nome em `nucleo/ambiente.json` e verifique por instrumento.
O porquê e a receita de repor estão em
[o estado que não viaja](estado-que-nao-viaja.md).

## Quando o perfil não serve: o estado de armazenamento

São duas formas de guardar a sessão, as duas dentro do cofre local, e a
escolha muda o que você tem de levar junto:

- **perfil persistente** é a pasta inteira do navegador. É o padrão, e é o
  mais simples.
- **estado de armazenamento** é um arquivo com os cookies e o armazenamento
  da página, gravado depois do login e recarregado antes de cada uso. Use
  quando o navegador precisa nascer limpo a cada execução, ou quando a mesma
  sessão vale em mais de uma máquina: arquivo se copia, pasta de perfil
  quase nunca.

**O que o estado de armazenamento tem de incluir.** Cookie e armazenamento
local costumam bastar. Não bastam quando a autenticação guarda o token no
**banco de dados do navegador** — aí o estado que só leva cookie devolve uma
sessão que parece gravada e volta deslogada. O sinal é este: o login
sobrevive a recarregar a página e não sobrevive ao estado gravado. Inclua o
banco do navegador no estado de armazenamento.

## Janela visível quando há plateia

Sem janela é o padrão: mais rápido, mais barato, e é assim que a rotina
roda. Ligue a janela visível em três situações:

- **no login à mão da primeira vez** — não se digita senha em janela que não
  existe;
- **quando alguém lê junto.** Documentar processo é a dois: quem tem o
  acesso vê a mesma tela que o agente e corrige na hora, em vez de
  descobrir o engano na revisão;
- **quando a leitura não bate com o esperado** e você precisa ver o que o
  agente está vendo.

## A armadilha: sessão gravada expira calada

A sessão que você gravou vai expirar. Quando expirar, **nada quebra**: o
servidor pede a página, uma resposta chega, o agente lê — e o que ele leu é
a tela de login. A leitura sai limpa, sem erro nenhum, e a conclusão sai
errada. Não há aviso porque, do ponto de vista do navegador, nada falhou.

O que fazer, nesta ordem:

- **Verifique uma marca que só existe depois do login** antes de confiar em
  qualquer leitura: um elemento da tela interna, o nome da conta no canto,
  uma rota que só responde autenticada. Sem essa verificação, a receita
  inteira é aposta.
- **Trate "voltou a tela de login" como falha**, nunca como conteúdo. É a
  disciplina do resultado negativo: sem contraprova, escreva "não medido".
- **Regrave a sessão** quando ela expirar — é o login à mão de novo, com a
  janela visível. Não dá para automatizar sem pôr a senha em algum lugar, e
  esse lugar nunca é texto rastreado (regra 8).

## Quando dá errado

| O sinal | O que costuma ser |
| --- | --- |
| toda leitura devolve a tela de login | sessão expirada — regrave à mão |
| a sessão some a cada execução | perfil não persistente, ou pasta errada |
| loga na tela, mas o estado gravado volta deslogado | falta o banco do navegador no estado de armazenamento |
| o agente lê o sistema errado | um servidor só servindo vários projetos |
| o servidor nem sobe | variável declarada sem valor no ambiente |
