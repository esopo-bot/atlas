# O catalogador

O roteiro `catalogador.json`, ao lado, é a rotina fixa que reorganiza a
camada de conhecimento e as anotações do workspace.

O CATALOGADOR — a rotina fixa que reorganiza a camada de conhecimento e as anotações do workspace.

Roteiro da CAMADA: viaja com o módulo, não sabe nada de ninguém, e por isso todo endereço sai da configuração.

O dono a invoca quando quiser; ela NUNCA roda sozinha.

Ela não commita: deixa o diff para revisão.

O alcance é limitado por CÓDIGO — o gancho vetar-conhecimento-em-codigo.py barra escrita em diretório só de código, e a etapa de verificação acusa qualquer toque fora do permitido, inclusive em nucleo/.

## Como rodar

```bash
python .agents/encadeador/encadeador.py ensaio \
  --roteiro modulos/encadeador/execucoes/catalogador.json \
  --trabalho catalogador --dir tmp/evidencias
python .agents/encadeador/encadeador.py executar \
  --roteiro modulos/encadeador/execucoes/catalogador.json \
  --trabalho catalogador --dir tmp/evidencias --cwd .
```

O ensaio primeiro, sempre. E **o dono invoca**: esta rotina não tem
agendamento e não roda sozinha.
