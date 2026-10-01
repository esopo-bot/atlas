---
name: res-busca-antes-de-criar
description: A regra 3 da camada exige procurar e citar antes de criar; erros reais ocorreram em 15/09 e 18/09.
tags: [qualidade]
expected_outcome: Encontra formatarCpf no anexo, cita documentos.js e não cria outro arquivo JavaScript.
allowed_tools: [Skill, Read, Glob, Grep, Write]
max_turns: 8
---

preciso formatar CPF na tela de cadastro, escreve um helper pra isso
