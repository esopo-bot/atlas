# As regras da camada

A lista numerada do que não muda sem decisão do dono. As sessões leem esta
página no fechamento e podem propor mudanças — citando o número, o texto novo
e o porquê. **Proponha; não aplique**: quem decide é o dono do repositório.

1. **Abra a sessão na raiz** — a pasta que tem o `AGENTS.md`. O que decide é
   **onde você abre**, não onde o arquivo mora: aberta numa subpasta, a
   sessão não enxerga as skills da raiz, e nada avisa.
2. **Só é pronto o que um instrumento provou.** Build, teste, listagem — "o
   modelo disse" não é prova.
3. **Antes de criar, procure e cite.** O que o conjunto já oferece não se
   reimplementa; aplicação nova imita a irmã mais parecida.
4. **A memória mora no disco, não no contexto.** O que vale amanhã se escreve
   — wiki, nota, decisão — nas subpastas de `conhecimento/`.
5. **Ao dar por pronto, faça a análise de promoção.** Três pilhas: genérico,
   da casa, descartável. Na dúvida se é genérico: é pessoal, e fica.
6. **Trabalhe econômico.** Repositório grande não se varre inteiro: índice,
   wiki e busca dirigida primeiro; identifique a linguagem pelo manifesto e
   leia LEIAME e pontos de entrada antes do resto.
7. **Rede com cortesia.** Chamada externa e MCP só quando a tarefa exigir,
   espaçadas; no primeiro `403`/`429`, recue — não insista em rajada.
8. **Segredo não entra em git nenhum.** Credencial não se abre; configuração
   carrega `${VARIAVEL}`, nunca o valor.
9. **Destrutivo é do dono; push segue o que a casa autorizou** — a permissão
   é de cada repositório e se grava no perfil dele; sem registro, a sessão
   não empurra nada. O que **aciona automação** (esteira, implantação, aviso
   a outras pessoas) é sempre do dono, mesmo onde o resto é liberado:
   **sincronizar não é entregar.** Decisão dele vira pergunta com
   recomendação; o agente prepara e executa o não-destrutivo.
10. **Texto na régua.** Markdown validado, conclusão primeiro, frases curtas,
    pt-BR.
11. **Não invente passo onde já existe receita.** Antes de propor como se faz
    algo que a casa já faz — subir uma peça de infraestrutura, publicar, abrir
    acesso —, procure o procedimento na documentação dela e cite de onde saiu
    cada passo. Não achou? **Peça o endereço**, não improvise. É a irmã da
    regra 3: uma cobre código, esta cobre procedimento. O motivo é o mesmo —
    esteira improvisada parece pronta, e quebra longe de onde nasceu.
12. **Branch de longa duração e configuração de esteira não se tocam.** As
    branches que a casa mantém — integração, homologação, produção, quaisquer
    que sejam os nomes — não se apagam, não se renomeiam, não recebem push
    forçado e não têm a história reescrita; e a configuração da automação não
    se altera de passagem. As duas são infraestrutura de outras pessoas:
    desfazer é público, caro, e às vezes impossível. Os nomes estão no perfil
    do repositório — e **na dúvida se uma branch é dessas, ela é.**

## Como propor mudança

No fechamento da sessão (o prompt de esfriamento pede): *"regra N atrapalhou
neste caso porque X; proponho trocar por Y"* — ou *"faltou uma regra para Z"*.
A proposta fica no relatório; o dono aceita, adapta ou recusa.
