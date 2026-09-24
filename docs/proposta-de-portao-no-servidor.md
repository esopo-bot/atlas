# Proposta: o portão no servidor

Isto é uma proposta, não uma configuração. A regra 12 da camada proíbe a
sessão de escrever automação, e configurar o repositório no servidor é do
dono. O texto abaixo existe para ele copiar, adaptar ou recusar.

## O problema que o portão resolve

Regra escrita em prompt orienta o modelo; não impede a ação. Gancho local só
vale para o agente que carrega os ganchos do cliente, na máquina onde eles
estão. O servidor é a única camada que vale igual para qualquer agente, para
gente e em qualquer máquina.

Hoje a sessão faz à mão, em série, o que um pipeline faz sozinho: roda o
ritual inteiro antes de cada entrega e cobra, na parada, o que ainda não tem
destino. O portão tira esse trabalho da sessão.

## Primeiro, medir se o plano permite

Proteção de branch em repositório privado depende do plano da conta. Se a
conta que a sessão usa não administra o repositório, a resposta dela não
decide nada: para quem não administra, a consulta devolve 404 nos dois casos.

Com uma conta que administra:

```bash
gh api "repos/${DONO}/${REPOSITORIO}/branches/${BRANCH_DE_PUBLICACAO}/protection"
```

- 404 com "Branch not protected": o plano permite, e a regra ainda não existe.
- 403 pedindo mudança de plano ou repositório público: o plano não permite.
- 200: já existe regra, e a saída diz qual.

Se o plano não permitir, restam três caminhos: mudar o plano, tornar o
repositório público, ou aceitar o pipeline como aviso sem trava. O terceiro
ainda vale a pena: tira a bancada da sessão, só não segura a mescla.

## A regra de proteção da branch de publicação

Pela tela de configuração do repositório, em regras de branch, ou pela API:

- exigir pedido de incorporação para entrar na branch de publicação;
- exigir que o check do pipeline abaixo passe antes da mescla;
- exigir a branch atualizada com a base antes da mescla;
- incluir administradores na regra, senão a conta do dono passa por cima sem
  perceber;
- proibir empurrão forçado e proibir apagar a branch.

Revisão obrigatória por outra pessoa só entra onde há outra pessoa para
revisar. Onde quem abre o pedido é o único que pode aprová-lo, a plataforma
não aceita aprovação de si mesmo, e a regra travaria toda mescla.

A branch de integração segue o que `autorizacoes` declara: onde a sessão
pode mesclar nela, ela fica sem proteção; onde não pode, recebe a mesma
regra da branch de publicação.

## O pipeline, um só

Um arquivo, em `.github/workflows/`, escrito pelo dono. Dispara em pedido de
incorporação para a branch de publicação e em empurrão para a integração.

```yaml
name: portao
on:
  pull_request:
    branches: ["${BRANCH_DE_PUBLICACAO}"]
  push:
    branches: ["${BRANCH_DE_INTEGRACAO}"]
permissions:
  contents: read
jobs:
  ritual:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: sincronia das cópias com a fonte
        run: python montar.py --verificar
      - name: rotinas deterministicas
        run: |
          python verificacoes.py sincronia
          python verificacoes.py matricula
          python verificacoes.py codificacao
          python verificacoes.py manual
          python verificacoes.py markdown
          python verificacoes.py camada
      - name: bancadas
        run: python verificacoes.py instalada
  segredo:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
```

O que este rascunho escolhe, e por quê:

- **Permissão só de leitura.** O pipeline mede; não escreve, não comenta,
  não mescla.
- **Rotinas nomeadas, não o `ritual` inteiro.** Parte do ritual mede a
  máquina de quem trabalha: o índice, a ronda, o rascunho, a conta das
  execuções, a entrega. No servidor essas rotinas não têm o que medir.
- **`instalada` entra aqui.** É a rotina que roda o `--testar` de cada gancho
  e instrumento, e hoje fica fora do ritual porque custa minutos. No servidor
  o custo não é da sessão.
- **Varredura de segredo em job separado.** Falha dela não se confunde com
  falha de bancada.

## O que não está provado

Nada aqui rodou. Antes de virar check obrigatório, o pipeline roda algumas
vezes como aviso, e estas perguntas se respondem com a saída dele:

- As rotinas passam em Linux limpo, sem os arquivos locais que ficam fora do
  git? A rotina `camada` e as bancadas nasceram em Windows, e o cadastro
  local não existe no servidor.
- A rotina `markdown` acha a ferramenta de régua que ela espera, só com o
  Node instalado?
- Quanto tempo leva `instalada` inteira? O teto de 30 minutos é palpite.
- A varredura de segredo acusa falso positivo nos casos de teste dos ganchos
  de credencial, que carregam segredo de mentira de propósito? Se acusar, a
  saída é uma lista de exceções por caminho, versionada.

## O que sai da sessão quando o portão entrar

Decisão do dono, peça por peça, depois de o pipeline provar que segura:

- o ritual inteiro antes de cada entrega vira o ritual do que a sessão tocou;
- a cobrança de destino na parada perde a parte que o servidor passa a
  cobrir, que é a integração à frente da publicação sem pedido aberto;
- o gancho local de branch protegida fica com o que o servidor não vê:
  operação em branch local e as autorizações por ação.

## Fora desta proposta

- Os repositórios vizinhos. Cada um tem o próprio servidor, as próprias
  regras e o próprio dono da decisão.
- O escopo do token da conta de automação. É configuração de conta, e a
  proteção de branch já impede a mescla direta mesmo com o escopo atual.
