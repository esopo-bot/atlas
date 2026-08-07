# Tipos de repositório: sinais, profundidade e templates

Classifique em cascata, do sinal mais barato ao mais caro, parando no
primeiro que decide. Antes de olhar qualquer coisa, exclua da conta:
`node_modules/`, `vendor/`, `dist/`, `build/`, `.terraform/`, `coverage/`,
arquivos `*.min.*` e lockfiles.

## A tabela de sinais

Procure as âncoras com `git -C <repo> ls-files` — sem abrir arquivo. A
primeira linha que casar decide o tipo.

| Âncora (precedência de cima para baixo)                                                                                               | Tipo           | Perfil                     |
| ------------------------------------------------------------------------------------------------------------------------------------- | -------------- | -------------------------- |
| `*.tf` na raiz ou `modules/`, `Chart.yaml`, `terragrunt.hcl`, `docker-compose.*`, `compose.yaml`, `kustomization.yaml`, `ansible.cfg` | infraestrutura | curto, ~40 linhas          |
| `dbt_project.yml`, `dags/`, muitos `*.ipynb`                                                                                          | dados          | médio, ~70 linhas          |
| `pubspec.yaml`, `*.xcodeproj`, gradle de app, `app.json`                                                                              | mobile         | médio, ~70 linhas          |
| `next.config.*`, `angular.json`, `vite.config.*`, `nuxt.*`                                                                            | frontend/ui    | médio, ~70 linhas          |
| Dockerfile + framework servidor, pasta de rotas, `openapi.*`                                                                          | api/serviço    | cheio, ~120 linhas         |
| manifesto de publicação sem servidor (`exports`, `*.nuspec`)                                                                          | biblioteca     | médio, ~70 linhas          |
| nenhuma âncora casou                                                                                                                  | indefinido     | 1 linha no mapa + pergunta |

Repositório misto: registre o tipo principal e cite o secundário no perfil.

## Arquivos-chave por tipo (vão para o índice)

- **infraestrutura**: `README.md`, `variables.tf`, `outputs.tf`,
  `versions.tf`, `Chart.yaml`, `values.yaml`, `terragrunt.hcl`
- **api/serviço**: `README.md`, manifesto de dependências, pastas de rotas ou
  controllers, contratos (`openapi.*`, DTOs), configuração de build
- **frontend/ui**: `README.md`, manifesto, configuração de build, pasta de
  rotas ou páginas
- **demais**: `README.md` + manifesto de dependências

## Perfil cheio (api/serviço) — o template completo

```markdown
# <nome do repositório>

Atualizado em <data>, commit <sha>. Perfil destilado — o código é a verdade.

## O que é
<uma frase: o papel deste repositório no conjunto>

## Stack e padrões
<linguagem, framework, organização de pastas, convenções de nome, como se
roda, como se testa. O que uma aplicação nova deveria imitar.>

## O que oferece
<a lista que evita reinvenção: serviços, helpers, contratos, endpoints —
cada um com o caminho onde vive>

## Como conversa com os irmãos
<quem chama, quem é chamado, contratos compartilhados — só o que você VIU>

## Armadilhas
<o que parece mas não é; o que quebra fácil; decisões com motivo>
```

O perfil médio usa as mesmas seções, na metade do tamanho: rotas e
componentes principais em vez de inventário completo.

## Perfil de infraestrutura — curto, pelo contrato

Nunca varra `templates/` nem leia HCL arquivo a arquivo; nunca rode
`terraform init/plan` para documentar (exige credenciais). Os degraus:

1. `terraform-docs` instalado? `terraform-docs markdown table --recursive .`
   e destile. Para charts, `helm-docs --dry-run`.
2. Sem a ferramenta, leia SÓ a lista fechada: `README.md`, `variables.tf`,
   `outputs.tf`, `versions.tf`, `Chart.yaml`, `values.yaml`,
   `terragrunt.hcl` — e `grep -c '^resource'` para o tamanho.

```markdown
# <nome do repositório>

Atualizado em <data>, commit <sha>. Perfil de infraestrutura — o contrato.

## O que provisiona
<recursos e providers, em linhas>

## Onde se aplica
<ambientes/regiões pela árvore de pastas, até 3 níveis>

## Entradas e saídas
<inputs com defaults e outputs — referenciados, nunca copiados à mão>

## Dependências e como se aplica
<módulos que consome; pipeline ou manual; onde vive o estado>
```
