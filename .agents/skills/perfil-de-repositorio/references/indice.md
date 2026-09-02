# Template do índice (`indice.json`)

Abra só para criar o índice do zero ou migrar `versao_do_template` — nas
rodadas normais lê-se o `indice.json` real do disco. O template atual é a
versão 2. Uma entrada por repositório:

```json
{
  "versao_do_template": 2,
  "repositorios": {
    "nome-do-repo": {
      "sha_indexado": "a1b2c3d",
      "data": "2026-08-05",
      "tipo": "infraestrutura",
      "tipo_declarado_pelo_dono": false,
      "arquivos_chave": ["README.md", "variables.tf", "outputs.tf"],
      "versao_do_template": 2,
      "pendente": false
    }
  }
}
```
