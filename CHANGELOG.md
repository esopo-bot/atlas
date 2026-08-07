# Mudanças da camada

Cada versão, pelo efeito que você vê. O número aparece em todo comando
(`python montar.py --versao`); máquina com número menor está atrasada.

## 0.46 — 2026-08-06

Branch de longa duração deixa de depender de boa vontade: vira regra e vira
trava. E o que um segundo agente enxergou da camada.

### Adicionado

- **Regra 12: branch de longa duração e configuração de esteira não se
  tocam.** Integração, homologação, produção — quaisquer que sejam os nomes —
  não se apagam, não se renomeiam, não recebem push forçado e não têm a
  história reescrita; e a automação não se altera de passagem. É
  infraestrutura de outras pessoas: desfazer é público e caro. **Na dúvida se
  uma branch é dessas, ela é.** Os nomes ficam no perfil do repositório.
- **Gancho `vetar-branch-protegida.py`**, a regra 12 virando trava. Um
  `PreToolUse` que lê o comando e recusa apagar, renomear e forçar — porque
  padrão de texto erra dos dois lados: `git push origin +x` é forçado e
  `git push origin x` não é. Ele carrega o próprio teste (`--testar`) com as
  duas listas: 16 casos que barra e 13 que deixa passar, incluindo a forma
  escondida depois de `&&` e a bandeira antes do verbo.
  **Limite declarado:** push normal para branch protegida passa — quem decide
  isso é a regra 9 e o perfil. Veto largo demais é desligado na primeira
  semana.
- **`.claude/branches-protegidas.txt`**, a lista que o gancho lê. É da casa:
  nasce uma vez e a atualização nunca a reescreve. Chega tanto na montagem
  quanto pelo `--atualizar`, porque este não escreve `ARQUIVOS` — sem a
  segunda porta, quem já tinha a camada receberia o gancho e ficaria sem a
  lista.
- **O verificador cobra o veto**: que ele esteja ligado, que passe nos 29
  casos, e que o caminho de passagem seja silencioso.
- **A skill `wiki-de-projetos` preserva a seção `## Declarado pelo dono`.** O
  perfil tem duas metades: o destilado do código, que se regenera, e o que só
  uma pessoa sabe — política de branch, o que a sessão pode empurrar, se o
  repositório é somente leitura. Regeneração que apaga o declarado ensina o
  dono a não declarar nada.
- **Template "conferir o trabalho de outra sessão"**: a conferência vale mais
  numa sessão limpa, que não tem apego à conclusão. O prompt manda rodar os
  instrumentos de novo em vez de crer na saída colada, proíbe consertar (senão
  a auditoria vira mais mudança não revisada) e exige, para cada afirmação
  numérica, que o conferente diga **o que contou** — número sem definição não
  se confere, e duas medições honestas de coisas ligeiramente diferentes
  discordam sem que ninguém tenha errado.

### Corrigido

- **O gancho é de cada ferramenta, e o guia dizia que a `qualidade` entra
  "sozinha, no início de toda sessão".** Medido: outro agente listou as sete
  skills e relatou **nenhum gancho** — a configuração do Claude Code não vale
  para ele. Onde não há gancho, a skill de padrão volta a depender do disparo
  por descrição, que é zero em 160. O guia agora diz isso e dá a saída.
- **A declaração de MCP não viaja entre ferramentas.** Medido: workspace com
  três servidores declarados na raiz, outro agente aberto na mesma raiz
  listou zero servidores e zero ferramentas. A página de MCP passa a separar
  o programa (neutro, em `.agents/mcp/`) da declaração (de cada ferramenta), e
  a avisar que **caminho declarado não é validado por ninguém** — arquivo que
  sumiu continua declarado e vira servidor que não sobe sem dizer por quê.
- **A regra 1 era ambígua e foi lida errado.** "Skill e regra não carregam de
  subpasta" fez um leitor entender que o problema era o lugar do arquivo. O
  que decide é **onde você abre a sessão**. Reescrita nos três lugares onde
  aparece, incluindo o modelo de `AGENTS.md`.
- **A regra 11 estava escrita por extenso dentro da skill `trabalho-por-issue`**
  — quarta cópia do mesmo enunciado. Virou ponteiro: nome, número e endereço,
  sem repetir o texto nem o motivo. A regra tem uma casa (a lista numerada) e
  o reforço nos dois `AGENTS.md`, que é o que vale em toda sessão.
- **A regra 9 dizia "push é do dono" e isso era falso na prática.** Há casa em
  que a sessão empurra o dia inteiro até a branch de homologação. A linha
  divisória não é *push*, é **"isso aciona automação?"**: a permissão é de
  cada repositório e se grava no perfil; sem registro, a sessão não empurra
  nada; e o que aciona esteira, implantação ou aviso a outras pessoas é sempre
  do dono. **Sincronizar não é entregar.**
- **Instrução que não rodava no terminal de quem lê.** Três lugares mandavam
  `cd site && npm install && npm run build`; `&&` é erro de sintaxe no Windows
  PowerShell 5.1. Agora é um comando por linha.

## 0.40 — 2026-08-06

O script confere o que criou, e dois prompts novos para arrumar a casa e
medir o que o agente de fato recebeu.

### Adicionado

- **O `montar.py` confere se o git enxerga o que ele escreveu.** Criar o
  arquivo não bastava: uma linha de ignore sem barra inicial esconde em
  qualquer profundidade, e o que a camada criou não chegava ao clone nem à
  sessão na nuvem — em silêncio, com o repositório parecendo montado. A
  conferência nomeia o arquivo e a regra culpada, com arquivo e linha.
  **Avisa e não conserta**, por dois motivos: as regras de ignore são do
  repositório, não da camada; e o git não reinclui arquivo cujo diretório-pai
  está excluído, então a exceção automática mentiria em parte dos casos.
- **Template "auditar a arrumação do repositório"**: manda a sessão ler a
  regra que vale hoje antes de opinar, exige a citação da regra em cada
  achado, protege a camada multi-fornecedor (a fonte é `.agents/skills/`; o
  espelho do Claude não se edita à mão) e proíbe apagar — o que está fora do
  lugar se move com `git mv`, e destino ocupado vira pergunta.
- **Template "pedir um diagnóstico a outro agente"**: o agente responde o que
  carregou **antes** de poder ler o disco, e só depois compara. A distância
  entre as duas respostas é o relatório — com leitura liberada desde o
  começo, ele responde certo sobre o que nunca recebeu.

### Corrigido

- **Instrução que não rodava no terminal de quem lê.** Três lugares mandavam
  `cd site && npm install && npm run build`; `&&` é erro de sintaxe no
  Windows PowerShell 5.1. Agora é um comando por linha.

## 0.39 — 2026-08-06

Revisão do guia inteiro, corte de contexto e a regra que impede a sessão de
improvisar procedimento.

### Adicionado

- **Regra 11: não invente passo onde já existe receita.** Antes de propor como
  se faz algo que a casa já faz — subir uma peça, publicar, liberar acesso —, a
  sessão procura o procedimento na documentação dela e cita a origem de cada
  passo; não achando, pede o endereço em vez de improvisar. Entrou em dois
  lugares: a lista numerada e o modelo de `AGENTS.md` — porque skill dispara em
  metade dos pedidos e linha no `AGENTS.md` vale em toda sessão.
- **A skill `trabalho-por-issue` virou executável**: o bloco que a casa
  preenche uma vez e grava no perfil do repositório, as três recusas na
  abertura, a régua de critério verificável, os quatro tipos de comentário e a
  sequência da sessão com os buracos da casa marcados.

### Corrigido

- **O gancho local não viaja mais dentro do script.** As páginas embutidas
  vinham de um glob `.claude/hooks/*.py`, que varria também o gancho pessoal de
  quem trabalha no repositório da camada — arquivo fora do git, que lê um
  arquivo de uma máquina só. Agora o gancho da camada entra nomeado.
- **Contagens escritas à mão saíram da prosa**: o README dizia "três skills"
  e a página de entrada dizia "seis"; são sete. Número em prosa mente na
  próxima skill — quem conta agora é o índice.
- **`zero-que-mente` anunciava duas causas** e listava cinco.
- **A lista do que vem de fábrica envelheceu**: entraram os comandos novos,
  saíram os que não se confirmam mais, e a página passou a dizer que a lista
  muda entre versões e onde conferir.
- **A coluna do Codex em `subagentes` saiu**: o endereço não foi conferido em
  máquina nenhuma, e afirmação sem instrumento não entra.

### Mudado

- **A camada custa menos em toda sessão**: 7 861 → 6 589 caracteres no
  repositório da camada. O gancho da qualidade parou de injetar o frontmatter
  (nome e descrição já chegam pelo catálogo de skills), e `AGENTS.md` e
  `CLAUDE.md` pararam de repetir a árvore do mapa do repositório.
  A conta é `AGENTS.md` + `CLAUDE.md` + o nome e a descrição de cada skill +
  o que o gancho **de fato imprime** — sem as chaves `name:` e `description:`,
  que a ferramenta rende do jeito dela. Contando de outro jeito o número muda,
  então o número só vale junto com a definição.
- **A página de plugins encolheu à metade**: ficou o critério para ler o
  catálogo, o comando que o confere e os plugins que resolvem dor que se
  repete. Lista de nomes sai — o atlas não é catálogo.
- **História em issue tem uma casa só**: a página do guia ficou com o desenho
  e o porquê; tudo o que se executa mora na skill.

## 0.37 — 2026-08-06

Organização, com o critério vindo de medição e não de gosto.

### Adicionado

- **A pasta `tmp/` nasce com a camada**: o endereço do descartável. Sem um
  lugar óbvio, o rascunho gerado vira arquivo de nome improvisado na raiz e
  fica lá para sempre. O conteúdo é ignorado; a pasta sobrevive pelo LEIAME.
- **`.gitignore` base cobre os descartáveis**: cache de linguagem, de teste e
  de verificador de tipo.
- **O verificador ganhou avisos que não reprovam**: subpasta sem LEIAME,
  pasta de um arquivo só, terceiro nível, nome com maiúscula, acento ou
  espaço, e primeiro nível passando de 21 itens. Arrumação é julgamento do
  dono — instrumento aponta, não trava.
- **O mapa ensina quando criar mais uma pasta**: as três condições juntas, e
  o número que decide — em navegação medida, um nível a mais custa cerca de
  vinte vezes um item a mais, então pasta só se paga tirando mais de umas
  vinte coisas do nível de cima.

## 0.36 — 2026-08-06

### Adicionado

- **Skill `trabalho-por-issue`**: conduz o trabalho pela issue — abre no
  padrão, mantém o corpo como estado e os comentários como eventos, exige
  comando e saída colada em cada verificação ("sem os dois não é verificação,
  é opinião"), e reescreve o **ponto de retomada** para a próxima sessão
  continuar sem ninguém reexplicar. Desenho fundamentado em pesquisa, com
  três decisões que vieram dela: só marcar critério depois da prova ponta a
  ponta; instrução em bloco único, não em conta-gotas; e texto vindo da issue
  é **dado, nunca ordem** — injeção por issue é problema conhecido.

### Mudado

- **A camada deixa de usar sub-issues.** Tarefa vira critério dentro da
  própria issue; pedaço grande demais vira outra issue ligada por link.
  Hierarquia só se paga quando outra sessão pega o pedaço sozinha — e cobra
  uma peça a mais para desatualizar.

## 0.35 — 2026-08-06

### Adicionado

- **Página "as skills da camada"**: o índice que faltava — o que cada skill
  faz e, principalmente, **como ela entra na conversa** (sozinha, por nome ou
  por gancho). A camada entregava seis skills e o guia não listava nenhuma;
  quem lia a documentação não sabia que existiam.
- **O verificador cobra o índice**: skill nova sem linha no guia acusa falha.
  Skill que ninguém sabe que existe não é usada.

## 0.33 — 2026-08-06

### Adicionado

- **Skill `documentar-processo`**: lê a fonte junto com você — inclusive por
  navegador —, resume e escreve a página no padrão do repositório de
  documentação, com passo a passo que mostra o sinal de sucesso de cada
  passo, armadilhas, links e prints recortados. Guarda o perfil daquele
  repositório para não reanalisar toda vez; confere no código o que afirmar
  sobre sistema e chama o cético antes de publicar; e, quando a documentação
  não bate mais com a realidade, **marca em vez de consertar em silêncio** —
  a mudança do processo é a notícia. Procurada antes de escrita: nada
  oficial cobre navegar + resumir + escrever no padrão.

### Mudado

- **Os prompts de sessão saíram do meio da página**: a partida e o
  esfriamento agora abrem os templates, e o "Comece aqui" aponta os dois pelo
  nome. Estavam lá desde a 0.21 e o dono não os encontrou — página longa
  esconde o que se usa todo dia.
- O esfriamento ganhou um item: o que a sessão descobriu sobre o repositório
  **atualiza o perfil dele na wiki**, em vez de virar arquivo novo. Um
  arquivo por repositório envelhece junto com ele; uma pilha de anotações de
  sessão envelhece sem ninguém perceber.

## 0.30 — 2026-08-06

### Mudado

- **Tamanho de linha sai da régua.** Ela cobrava 80 colunas de tudo — e caía
  onde não paga: anotação da casa, perfil gerado, registro de incidente.
  Ninguém requebra aquilo, e aviso que ninguém atende ensina a ignorar aviso.
  As páginas da camada seguem em 80 colunas por hábito de quem escreve. Quem
  quiser a disciplina de volta liga na sua pasta, com um `.markdownlint.jsonc`
  próprio — configuração de pasta vence a da raiz.

## 0.29 — 2026-08-06

Dois falsos negativos, achados rodando o ritual num repositório que **recebeu**
a camada — nenhum dos dois aparecia no repositório de origem.

### Corrigido

- **A sonda de instruções não se aplica em toda casa.** Ela pergunta pelas
  pastas da camada; num repositório com `AGENTS.md` próprio, a resposta certa
  é outra e a checagem acusava falha que não era defeito. Agora ela confere se
  a pergunta cabe naquele `AGENTS.md` e, quando não cabe, pula dizendo por quê.
- **A régua prometia um conserto que não existe.** A regra de alinhamento de
  tabela não tem correção automática: o comando que o guia manda rodar não a
  resolve, e o aviso ficava lá para sempre. A regra saiu da régua — o site
  renderiza igual, e cobrar o que a ferramenta não conserta faz gente ignorar
  aviso de verdade.

## 0.28 — 2026-08-06

### Adicionado

- **Mais duas causas de zero que mente**, vindas de uso e verificadas aqui:
  o filtro que espera um fim que nunca chega (`tail` de processo que não
  termina devolve nada, para sempre — e o nada parece "não subiu"), e a
  interface que não está no arquivo buscado (item dentro de componente
  colapsado não nasce no HTML; a rota existe e a busca diz que não).

## 0.27 — 2026-08-06

### Mudado

- **O site passa a publicar as subpastas de `conhecimento/`** — a wiki que a
  skill gera e as notas da casa deixam de ser invisíveis. Um nível só: o site
  enxerga a raiz, e mais alcance arrastaria os repositórios de código.
- **O menu descobre a casa sozinho**: as páginas da camada seguem escritas à
  mão, na ordem de leitura, e depois entra uma categoria por subpasta,
  encontrada na construção — nome livre, rótulo vindo do título do `LEIAME`.
- **`.md` é lido como markdown comum, não como MDX.** Era a razão de a
  subpasta ficar de fora: um `<coisa/assim>` fora de bloco de código derrubava
  a construção com um erro que não dizia onde consertar. Reproduzido e
  corrigido na raiz — quem precisar de componente escreve `.mdx`.
- O `LEIAME` de subpasta passa a ser página: nela ele costuma ser conteúdo (o
  mapa da wiki), não recado de pasta. No primeiro nível continua fora.

## 0.26 — 2026-08-06

### Adicionado

- **A ordem de atualizar**: repositório com remoto traz o que já foi
  empurrado **antes** de rodar a camada — senão a versão nova cai sobre uma
  árvore velha e o conflito aparece com a camada no meio.
- **Terceira causa de zero que mente**: o terminal que reescreve o argumento.
  No Windows, o Bash do Git converte argumento começando com barra em caminho
  do sistema, sem avisar — e o programa responde honestamente sobre a coisa
  errada. Medido, com o conserto.

## 0.23 — 2026-08-06

Verificação adversarial de conclusão, e o fluxo que leva do sintoma à causa.

### Adicionado

- **Skill `cetico`**: verificação adversarial de uma conclusão — separa
  provado de suposto, desenha a medição que derrubaria cada suposição, e
  reemite o veredito em provado / provável / não provado.
- **Fluxo de investigação de incidente**: do sintoma à conclusão, em nove
  passos, sem depender de ferramenta. Fecha com o raciocínio que resolve —
  artefato imutável igual + hora exata de mudança = a configuração é a
  variável.
- **Página "zero que mente"**: por que uma busca devolve vazio e o vazio
  engana. Duas causas medidas: o filtro que você não sabia que estava ligado
  (busca respeita o `.gitignore` e some com pastas inteiras, sem avisar) e o
  vocabulário errado (o nome que o código escreve não é o que fica gravado).
- **Template de escalação para outro time**: escopo medido e não amostrado,
  identificadores que o receptor consegue procurar, e o pedido acionável —
  evidência sem pedido é escalação pela metade.

### Mudado

- O esfriamento da sessão passa a pedir o cético antes da promoção, e a
  apontar o atrito do dia: o que atrapalhou e o que o dono poderia ter feito
  diferente.
- A skill de promoção exige conclusão auditada antes de promover: lição
  errada promovida sai de uma casa e entra em todas.
- A página de MCP ganhou o gatilho de "quando vale escrever o seu": ritual
  repetido, parâmetro que causa erro silencioso vira obrigatório.
- O mapa corrige uma meia-verdade: `.gitignore` esconde do git **e da
  busca** — só a leitura direta continua funcionando.

## 0.21 — 2026-08-05

### Adicionado

- **As regras da camada**, numeradas de 1 a 10, com o rito de propor
  mudança citando o número.
- **Dois templates de sessão**: a partida (regras, estrutura e como não
  varrer repositório grande inteiro) e o esfriamento (promoção do genérico,
  candidatos a automação, crítica às regras).
- **Análise de promoção** como skill e como regra: ao dar por pronto, três
  pilhas — genérico, da casa, descartável.
- Skills novas de conhecimento do conjunto: **wiki de projetos** (agora
  incremental: consulta o índice, tipa o repositório, poucos por rodada) e
  **antes de criar** (procurar e citar antes de implementar).

### Mudado

- O script ficou enxuto: a versão é a primeira linha dele; a instrução mora
  no guia.
- Regra econômica para os agentes: repositório grande não se varre inteiro;
  rede e MCP só quando a tarefa exigir, com pausa entre chamadas.
- A varredura de markdown respeita as fronteiras do que não é da camada.

## 0.9 — 2026-08-05

### Mudado

- A skill `wiki-de-projetos` deixa os perfis **na régua sozinha**: roda o
  conserto do markdownlint ao terminar de gerar.
- O mapa ensina o conserto manual (`npx markdownlint-cli2 --fix ...`) e a
  régua entrou na árvore do repositório.

## 0.7 — 2026-08-05

### Corrigido

- **A estrutura do workspace agora viaja no git.** As pastas do esqueleto
  eram ignoradas inteiras e não chegavam num clone; agora só o conteúdo fica
  de fora — o LEIAME segura cada pasta, e o publicador de tokens viaja na
  `.credenciais/`. Segredo e projeto pessoal continuam sem entrar em git
  nenhum (provado com clone real).

## 0.6 — 2026-08-05

### Mudado

- O atlas entrega **um script só**: o `montar.py`. A verificação de agentes
  virou ferramenta local do autor — nem toda máquina tem todos os agentes
  instalados para medir, e a falta dela não pode sujar quem recebe a camada.

## 0.5 — 2026-08-05

### Adicionado

- **Régua de markdown** (`.markdownlint.jsonc`) nasce com a camada — o editor
  e o verificador leem a mesma; o verificador acusa markdown fora dela e diz
  o comando que conserta.

### Corrigido

- Todos os markdowns da camada entram na régua: tabelas realinhadas, linhas
  requebradas em 80 colunas — os avisos do editor somem.

## 0.4 — 2026-08-05

### Adicionado

- O modelo de `AGENTS.md` nasce com as regras da casa completas: abrir na
  raiz, credencial não se abre, destrutivo é do dono, pronto só com prova de
  instrumento.
- O esqueleto traz o **publicador de tokens**: valores em
  `.credenciais/mcp.env`, `publicar-mcp-env.py` os publica como variáveis —
  e o `.mcp.json` fica só com `${NOME}`, nunca com segredo.

## 0.3 — 2026-08-05

### Adicionado

- Página **Comece aqui** abrindo o guia: o que a camada instala, como usar,
  as três regras que não mudam.
- **CHANGELOG** (este arquivo) e `--versao` nos comandos.

### Mudado

- README reescrito: cada passo diz o que aparece quando dá certo.
- Menu do guia na ordem da jornada: comece aqui → mapa → templates → o resto.
- O mapa ganhou os casos de borda da atualização ("editei uma página da
  camada", "apaguei uma página").

## 0.2 — 2026-08-05

### Adicionado

- **O site do guia viaja com a camada**: montar em qualquer máquina traz o
  `site/` pronto para `npm install && npm run build`.
- **Versão da camada**: sobe sozinha quando o conteúdo muda; todo comando a
  imprime.
- O contrato da atualização no mapa: o que a camada sobrescreve, o que é seu.
- O modelo de `AGENTS.md` nasce com a regra "procure antes de criar" — skill
  sozinha dispara em só metade dos pedidos (medido).

## 0.1 — 2026-08-05

Linha de base do dia:

- O montador passou a levar **tudo**: páginas, skills, ganchos — antes as
  skills ficavam para trás em silêncio.
- Esqueleto do workspace virou opção (`--esqueleto`), com `.gitignore`
  ancorado na raiz.
- Padrão de qualidade entra sozinho por **gancho** em toda sessão (medido:
  três em três; sem gancho, zero).
- Espelho de skills entra no git — sessão na nuvem passa a ter skills.
- Ponte do Devin desligada: skill uma vez só, negações de credencial próprias.
- Skills novas: **wiki de projetos** e **antes de criar**.
- Verificador ganhou `--camada`, a prova do gancho e a caça a arquivo órfão.
