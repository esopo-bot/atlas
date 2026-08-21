# auditor

Lê a pasta de evidências de um trabalho e conta o que aconteceu: quais etapas
seguiram, quais pararam, quais repetiram ciclo, e se a prova de cada uma
**ainda reproduz**.

Ele **não espia sessão**. Não lê transcrição e não julga comportamento —
sessão narrando sessão produz prosa plausível, e a regra 2 diz que "o modelo
disse" não é prova. O auditor lê o que ficou no disco.

O relatório sai em duas partes, e a separação é o ponto:

- **PROVADO** — o que está na evidência e o que o verificador conseguiu
  re-executar.
- **SUPOSTO** — a leitura disso. Rotulada, para ninguém confundir com fato.

```bash
python montar.py --modulo auditor
python .agents/auditor/auditor.py <pasta-de-evidências>/<trabalho>
```

Instalar é ligar. Não instalar é desligar: ele é auditoria, não guarda — o que
precisa valer sempre mora no ritual e nos ganchos, onde não dá para pular.

Exige a camada no destino: usa o verificador que já existe, e não reimplementa
re-execução de prova.
