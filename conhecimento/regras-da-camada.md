<!-- GERADA de conhecimento/regras.json pelo `montar.py --sincronizar`. Edite lá: o que for escrito aqui se perde na próxima sincronização. -->

# As regras da camada

A lista numerada do que não muda sem decisão do dono. **Proponha; não
aplique**: o protocolo de proposta está no fim da página.

Cada regra é a ordem, direta. A procedência mora nas páginas linkadas — leitura
de consulta, não de sessão.

1. **Abra a sessão na raiz — a pasta que tem o `AGENTS.md`.**
    - O que decide é onde você abre, não onde o arquivo mora: numa subpasta, a
      sessão roda sem as skills da raiz, e nada avisa.
    - Procedência: [mapa do repositório](mapa-do-repositorio.md).

2. **Só é pronto o que um instrumento provou.**
    - Prova é build, teste ou listagem — "o modelo disse" não é prova, e saída
      colada de outra sessão é citação, não prova.
    - Fluxo que ninguém executou nem tem fonte citada é hipótese — grava-se
      marcado como hipótese, nunca como instrução.
    - Resultado negativo pede contraprova: zero, vazio e "sem permissão" viram
      prova só quando o mesmo instrumento, na mesma janela, achar alguma coisa.
      Sem isso, escreva "não medido", nunca "não existe".
    - Procedência: [zero que mente](zero-que-mente.md).

3. **Antes de criar, procure e cite.**
    - O que o conjunto já oferece não se reimplementa; aplicação nova imita a
      irmã mais parecida.

4. **A memória mora no disco, não no contexto.**
    - O que vale amanhã se escreve — wiki, nota, decisão — nas subpastas de
      `conhecimento/`.

5. **Ao dar por pronto, faça a análise de promoção.**
    - Três pilhas: genérico, da casa, descartável. Na dúvida se é genérico: é
      pessoal, e fica.

6. **Trabalhe econômico.**
    - Repositório grande não se varre inteiro: índice, wiki e busca dirigida
      primeiro.
    - Identifique a linguagem pelo manifesto e leia LEIAME e pontos de entrada
      antes do resto.

7. **Rede com cortesia.**
    - Chamada externa e MCP só quando a tarefa exigir, espaçadas.
    - No primeiro `403`/`429`, recue — não insista em rajada.

8. **Segredo não entra em git nenhum — e ler credencial localmente é livre.**
    - Ler é reversível; publicar não é. Em texto rastreado — arquivo, commit,
      issue — vai `${VARIAVEL}`, nunca o valor. Vale para git público E
      privado.
    - O exemplo canônico: ler credencial para montar a camada MCP read-only do
      banco de produção, pode; o valor num `.mcp.json` rastreado, não.
    - Depois de usar credencial para configurar algo, avise o dono para tirá-la
      de vista — o backup é dele.
    - O que aparece na tela entra na sessão: print e janela compartilhada
      carregam segredo sem passar por instrumento nenhum. Feche o que tem
      segredo antes de mandar imagem.
    - Procedência: [ganchos](ganchos.md).

9. **Destrutivo é do dono; commit e push seguem o que a casa autorizou.**
    - A permissão é de cada repositório e se grava no perfil dele; sem
      registro, a sessão não grava e não empurra.
    - O que aciona automação — esteira, implantação, aviso a outras pessoas — é
      sempre do dono, mesmo onde o resto é liberado: sincronizar não é
      entregar.
    - Antes de empurrar para branch compartilhada, olhe os PRs abertos dela:
      push em branch com PR aberto entra na entrega em rota, e o corpo do PR
      precisa cobrir o que entrou — corpo que não cobre o diff é revisão
      aprovando sem ver.
    - Decisão do dono vira pergunta — uma por vez, com a recomendação primeiro;
      o agente prepara e executa o não-destrutivo.
    - Redesenho de experiência pede esboço e pergunta fechada antes do código;
      conserto de defeito não pede.

10. **Texto na régua.**
    - Markdown validado, conclusão primeiro, frases curtas, pt-BR.

11. **Não invente passo onde já existe receita.**
    - Antes de propor como se faz algo que a casa já faz — subir uma peça de
      infraestrutura, publicar, abrir acesso —, procure o procedimento na
      documentação dela e cite de onde saiu cada passo.
    - Não achou? Peça o endereço, não improvise: esteira improvisada parece
      pronta, e quebra longe de onde nasceu.

12. **Branch de longa duração e configuração de esteira não se tocam.**
    - As branches que a casa mantém — integração, homologação, produção,
      quaisquer que sejam os nomes — não se apagam, não se renomeiam, não
      recebem push forçado e não têm a história reescrita; e a configuração da
      automação não se altera de passagem. As duas são infraestrutura de outras
      pessoas.
    - Os nomes estão em `.claude/branches-protegidas.txt` — e na dúvida se uma
      branch é dessas, ela é.

13. **Publicar exige revisão semântica, não só varredura.**
    - Releia exemplo, fixture e caso de teste perguntando: um colega
      reconheceria a casa nisto? E releia o texto perguntando: isto conta algo
      sobre quem escreveu?
    - Varredura por padrão acha nome e segredo; jeito de trabalhar e
      procedência não têm padrão — passam inteiros.
    - Publicação não se desfaz: reescrever a história tira das listagens, não
      do alcance de quem já copiou.

## Como propor mudança — e como consultar por código

No fechamento da sessão (o prompt de esfriamento pede): *"regra N atrapalhou
neste caso porque X; proponho trocar por Y"* — ou *"faltou uma regra para Z"*.
A proposta fica no relatório; o dono aceita, adapta ou recusa.

Regra nova ou mudada se edita em `conhecimento/regras.json` — esta página é
gerada dali e qualquer edição aqui se perde na sincronização.

Sessão ou script que precise das regras como dado lê a fonte direto:
`conhecimento/regras.json`, campo `regras` — cada item tem `id`, `regra` (a
frase imperativa) e `faca` (os itens). É o que o encadeador injeta em toda
etapa de sessão; não há servidor nem API — o arquivo é o contrato.
