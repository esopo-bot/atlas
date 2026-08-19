# modulos

A parte **opcional** da camada: uma pasta por módulo, e nenhum viaja sozinho.
Módulo só chega onde alguém pedir pelo nome; os três comandos (`--modulos`,
`--modulo <nome>`, `--atualizar`) estão no
[mapa do repositório](../conhecimento/mapa-do-repositorio.md).

## Como se escreve um módulo

**A pasta dele espelha a árvore de destino.** O caminho do arquivo dentro de
`modulos/<nome>/` é o caminho onde ele vai parar no repositório de destino —
não existe roteiro, porque duas listas dessincronizam e um caminho não.

```
modulos/<nome>/
├── LEIAME.md                    o cartão do módulo — NÃO é instalado
├── conhecimento/<nome>.md       vai para conhecimento/<nome>.md
└── .agents/skills/<skill>/      vai para .agents/skills/<skill>/
```

Três regras que o mecanismo cobra:

- **O `LEIAME.md` da raiz do módulo fica.** Instalado, ele iria parar na raiz
  do repositório de destino e sobrescreveria arquivo alheio. LEIAME de
  subpasta é conteúdo e viaja normal.
- **Arquivo destinado a subpasta de `conhecimento/` é escrito uma vez e nunca
  mais.** É molde: o que nasce ali é a memória de quem usa, e a atualização
  não a sobrescreve. A fronteira é a mesma do mapa do repositório — primeiro
  nível é da camada, subpasta é do repositório.
- **O nome da pasta é o nome do módulo, e ele não se renomeia.** Renomear
  deixa órfão eterno em toda máquina que já instalou. Módulo nasce com nome
  largo o bastante para caber a segunda ferramenta dentro dele.
