# Investigação de incidente

Algo quebrou em produção e a pergunta é "o que mudou?". Esta ordem existe
para você não gastar horas na hipótese errada: cada passo estreita o campo, e
nenhum deles depende de qual nuvem ou ferramenta você usa.

## A ordem

1. **Reproduza o sintoma.** Sem reprodução você está investigando um relato.
   Não reproduziu? O primeiro trabalho é descobrir para quem acontece.
2. **Ache no código a mensagem que o usuário vê.** É o fio mais curto entre a
   tela e a linha de código — e mostra qual caminho, dos vários possíveis,
   foi o percorrido.
3. **Extraia o identificador de rastreio.** O identificador de correlação
   liga a tela ao registro. Sem ele, você vai ler log por horário e vai ler
   o log errado.
4. **Ache a requisição exata.** Uma requisição real, inteira, com começo e
   fim. Uma requisição verdadeira vale mais que mil linhas filtradas por
   palavra-chave.
5. **Ancore a linha do tempo.** Não pergunte "está falhando?" — pergunte
   **"desde quando?"**, com contagem por período: antes e depois. O começo é
   o dado que separa causa de coincidência.
6. **Diferencie o que mudou**, e prefira artefato imutável a memória: versão
   ou identificador único do que está publicado, data da última implantação,
   trilha de auditoria de quem alterou o quê. Quatro suspeitos, sempre:
   código, configuração, infraestrutura, rede.
7. **Separe defeito nosso de dependência externa.** Se o erro nasce antes da
   sua aplicação responder, o dono do problema pode não ser você — e a
   evidência disso muda a quem você escala.
8. **Rode o cético** (skill `cetico`) antes de concluir. É o passo que separa
   a explicação que convence da explicação que resiste.
9. **Só então conclua** — e diga o que ficou sem prova.

## O raciocínio que fecha investigação

**Código idêntico + infraestrutura idêntica + horário exato de uma mudança de
configuração = a configuração é a variável.** Quando os artefatos publicados
não mudaram e o começo do problema tem hora marcada, a pergunta deixa de ser
"o que no sistema está errado?" e vira "quem mudou o quê naquele minuto?" — e
trilha de auditoria responde isso em minutos.

O contrário também vale: se você não consegue nomear o instante do começo,
ainda não investigou o suficiente para acusar nada.

## Duas armadilhas que custam horas

Busca que devolve zero e log que não fala a língua que você procura fazem
você concluir "não existe" quando existe. As duas estão em
[zero que mente](../conhecimento/zero-que-mente.md) — leia antes de confiar
num resultado vazio.
