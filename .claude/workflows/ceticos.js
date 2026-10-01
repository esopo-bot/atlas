export const meta = {
  name: 'ceticos',
  description: 'Rodada de céticos da verificação adversarial: lentes independentes acham, cada achado ganha um cético que tenta derrubá-lo, e sai provado, provável ou não provado com a medição',
  whenToUse: 'Pela skill verificacao-adversarial, na segunda forma: revisar uma mudança ou um conjunto de arquivos por várias lentes. Recebe em args o alvo e, quando houver, o texto da revisão do Codex.',
  phases: [
    { title: 'Lentes', detail: 'lentes independentes procuram defeito no alvo, cada uma por um ângulo' },
    { title: 'Céticos', detail: 'cada achado ganha um cético que tenta derrubá-lo medindo' },
  ],
}

const TETO_DE_AGENTES = 9
const ACHADOS_POR_LENTE = 5
const DISTANCIA_DE_LINHA_DO_MESMO_ACHADO = 1
const PRIORIDADE_MAIS_BAIXA_QUE_E_GRAVE = 1
const PESO_DA_GRAVIDADE = 10

const LENTES = [
  {
    nome: 'correcao',
    pede: 'a lógica faz o que o nome, o chamador e o teste esperam: condição invertida, limite e contagem fora por um, caso vazio, tipo ou unidade trocados.',
  },
  {
    nome: 'caminho-de-erro',
    pede: 'o caminho de erro que ninguém testou: exceção engolida em volta de conta, que faz a falha virar zero; código de saída que mente; verificação que enumera o que ignora; erro que não chega à fronteira com mensagem útil.',
  },
  {
    nome: 'usuario-final',
    pede: 'o que o usuário final veria: refaça a conta com os números reais do dado do repositório — exemplo, fixture, configuração —, nunca com exemplo inventado, e diga o valor que ele veria e o que deveria ver.',
  },
]

const ANGULOS_DO_CETICO = {
  reproduza: 'Rode a medição mais barata que mostraria o defeito: o teste que já existe, ou um roteiro curto na pasta temporária da máquina. Se a saída não mostrar o defeito, ele caiu.',
  contrato: 'Leia o contrato: quem chama, o teste, a documentação e a issue. Se o comportamento apontado é o pretendido, ou se o caminho nunca é alcançado, ele caiu.',
}

const VEREDITOS_DO_CETICO = ['derrubado', 'reproduzido', 'sustentado_sem_medicao', 'inconclusivo']

const ESQUEMA_DA_LENTE = {
  type: 'object',
  required: ['achados'],
  properties: {
    achados: {
      type: 'array',
      items: {
        type: 'object',
        required: ['titulo', 'arquivo', 'linha', 'gravidade', 'explicacao', 'como_medir'],
        properties: {
          titulo: { type: 'string' },
          arquivo: { type: 'string' },
          linha: { type: 'integer' },
          gravidade: { type: 'string', enum: ['grave', 'menor'] },
          explicacao: { type: 'string' },
          como_medir: { type: 'string' },
        },
      },
    },
  },
}

const ESQUEMA_DO_CETICO = {
  type: 'object',
  required: ['veredito', 'razao', 'comando', 'saida'],
  properties: {
    veredito: { type: 'string', enum: VEREDITOS_DO_CETICO },
    razao: { type: 'string' },
    comando: { type: 'string' },
    saida: { type: 'string' },
  },
}

const ITEM_DA_REVISAO_DO_CODEX = /^- \[P(\d)\] (.+?) — (.+):(\d+)-(\d+)\s*$/
const LINHA_COM_ITEM_DO_CODEX = /^\s*- \[P\d\]/
const MARCA_DE_ITEM_DO_CODEX = /\[P\d\]/
const MOTIVO_DO_AGENTE_SEM_RESPOSTA = 'o agente não devolveu resposta: foi pulado ou morreu por erro da API depois das novas tentativas'

function descricaoDoAlvo(alvo) {
  if (alvo && typeof alvo.base === 'string' && alvo.base) {
    const ponta = alvo.ponta || 'HEAD'
    return `a mudança entre \`${alvo.base}\` e \`${ponta}\`: leia \`git diff ${alvo.base}...${ponta}\` e o código em volta de cada trecho`
  }
  if (alvo && Array.isArray(alvo.arquivos) && alvo.arquivos.length) {
    return `estes arquivos: ${alvo.arquivos.join(', ')}`
  }
  throw new Error('args.alvo precisa de base (a ponta, por omissão, é HEAD) ou de uma lista não vazia em arquivos')
}

function leituraDaRevisaoDoCodex(texto) {
  const leitura = { achados: [], fora_do_formato: [] }
  if (!texto) return leitura
  let atual = null
  for (const linha of String(texto).split(/\r?\n/)) {
    const casou = ITEM_DA_REVISAO_DO_CODEX.exec(linha)
    if (casou) {
      atual = {
        titulo: casou[2],
        arquivo: casou[3],
        linha: Number(casou[4]),
        gravidade: Number(casou[1]) <= PRIORIDADE_MAIS_BAIXA_QUE_E_GRAVE ? 'grave' : 'menor',
        origens: ['codex'],
        alegacoes: [{ origem: 'codex', titulo: casou[2], explicacao: '', como_medir: '' }],
      }
      leitura.achados.push(atual)
    } else if (LINHA_COM_ITEM_DO_CODEX.test(linha)) {
      leitura.fora_do_formato.push(linha.trim())
      atual = null
    } else if (!linha.trim()) {
      atual = null
    } else if (atual) {
      const alegacao = atual.alegacoes[0]
      alegacao.explicacao = `${alegacao.explicacao} ${linha.trim()}`.trim()
    }
  }
  if (!leitura.achados.length && MARCA_DE_ITEM_DO_CODEX.test(texto)) {
    throw new Error('o texto da revisão do Codex tem item [P<n>], mas nenhum se leu no formato "- [P<n>] <título> — <arquivo>:<início>-<fim>": confira o formato antes de rodar, porque zero lido não é zero achado')
  }
  return leitura
}

function caminhoNormalizado(caminho) {
  return String(caminho).replace(/\\/g, '/').replace(/^\.\//, '').toLowerCase()
}

function mesmoArquivo(um, outro) {
  const a = caminhoNormalizado(um)
  const b = caminhoNormalizado(outro)
  return a === b || a.endsWith(`/${b}`) || b.endsWith(`/${a}`)
}

function tituloNormalizado(titulo) {
  return String(titulo).normalize('NFD').replace(/\p{M}/gu, '').toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ').trim()
}

function mesmoAchado(um, outro) {
  return mesmoArquivo(um.arquivo, outro.arquivo)
    && Math.abs(um.linha - outro.linha) <= DISTANCIA_DE_LINHA_DO_MESMO_ACHADO
    && tituloNormalizado(um.titulo) === tituloNormalizado(outro.titulo)
}

function juntarRepetidos(achados) {
  const juntos = []
  for (const achado of achados) {
    const igual = juntos.find(j => mesmoAchado(j, achado))
    if (!igual) {
      juntos.push({ ...achado, origens: [...achado.origens], alegacoes: [...achado.alegacoes] })
      continue
    }
    igual.origens.push(...achado.origens)
    igual.alegacoes.push(...achado.alegacoes)
    if (achado.gravidade === 'grave') igual.gravidade = 'grave'
  }
  return juntos
}

function peso(achado) {
  return (achado.gravidade === 'grave' ? PESO_DA_GRAVIDADE : 0) + achado.origens.length
}

function promptDaLente(lente, alvo, contexto) {
  return [
    `Você é uma lente de revisão e olha por um ângulo só: ${lente.pede}`,
    `O alvo é ${alvo}.`,
    contexto ? `O que a mudança diz fazer: ${contexto}` : '',
    `Procure defeito real, com arquivo e linha. No máximo ${ACHADOS_POR_LENTE}, os mais graves primeiro; lista vazia é resposta válida.`,
    'Grave é o que dá resultado errado, perde dado ou deixa passar o que devia barrar; o resto é menor.',
    'Para cada achado, diga a medição mais barata que o mostraria.',
    'Não conserte nada e não escreva no repositório: rascunho vai na pasta temporária da máquina.',
  ].filter(Boolean).join('\n\n')
}

async function rodarLente(lente, alvo, contexto) {
  try {
    const resposta = await agent(promptDaLente(lente, alvo, contexto), { label: `lente ${lente.nome}`, phase: 'Lentes', schema: ESQUEMA_DA_LENTE })
    if (!resposta) return { lente: lente.nome, motivo: MOTIVO_DO_AGENTE_SEM_RESPOSTA }
    if (resposta.achados.length > ACHADOS_POR_LENTE) {
      log(`lente ${lente.nome}: ${resposta.achados.length - ACHADOS_POR_LENTE} achado(s) além do limite de ${ACHADOS_POR_LENTE} ficaram de fora`)
    }
    return {
      lente: lente.nome,
      achados: resposta.achados.slice(0, ACHADOS_POR_LENTE).map(a => ({
        titulo: a.titulo,
        arquivo: a.arquivo,
        linha: a.linha,
        gravidade: a.gravidade,
        origens: [`lente ${lente.nome}`],
        alegacoes: [{ origem: `lente ${lente.nome}`, titulo: a.titulo, explicacao: a.explicacao, como_medir: a.como_medir }],
      })),
    }
  } catch (erro) {
    return { lente: lente.nome, motivo: `o agente lançou erro: ${erro && erro.message ? erro.message : String(erro)}` }
  }
}

function promptDoCetico(achado, angulo, alvo) {
  const alegacoes = achado.alegacoes.map(a =>
    `- [${a.origem}] ${a.titulo}: ${a.explicacao}${a.como_medir ? ` (como medir: ${a.como_medir})` : ''}`)
  return [
    'Você é um cético, e seu papel é DERRUBAR este achado. Parta da hipótese de que ele é falso.',
    `Achado: ${achado.titulo} — ${achado.arquivo}:${achado.linha}, gravidade ${achado.gravidade}.`,
    `O que se alegou:\n${alegacoes.join('\n')}`,
    `O alvo é ${alvo}.`,
    ANGULOS_DO_CETICO[angulo],
    'Zero e vazio não provam ausência: se a medição não mostrou nada, confira que ela mostraria o defeito caso ele existisse.',
    'Veredito: derrubado (a medição mostrou que é falso), reproduzido (a medição mostrou o defeito), sustentado_sem_medicao (a leitura sustenta, mas nenhum instrumento mostrou) ou inconclusivo. Traga o comando exato e as linhas da saída que decidem.',
    'Não conserte nada e não escreva no repositório: rascunho vai na pasta temporária da máquina.',
  ].join('\n\n')
}

function vereditoFinal(votos) {
  if (!votos.length) return 'sem_voto'
  const derrubaram = votos.filter(v => v.veredito === 'derrubado').length
  if (derrubaram * 2 > votos.length) return 'derrubado'
  if (derrubaram) return 'nao_provado'
  if (votos.some(v => v.veredito === 'reproduzido')) return 'provado'
  if (votos.some(v => v.veredito === 'sustentado_sem_medicao')) return 'provavel'
  return 'nao_provado'
}

const entrada = args && typeof args === 'object' ? args : {}
const alvo = descricaoDoAlvo(entrada.alvo)
const contexto = typeof entrada.contexto === 'string' ? entrada.contexto : ''
const leituraDoCodex = leituraDaRevisaoDoCodex(entrada.revisao_do_codex)
const doCodex = leituraDoCodex.achados
const revisaoDoCodex = entrada.revisao_do_codex
  ? { itens_no_texto: doCodex.length + leituraDoCodex.fora_do_formato.length, lidos: doCodex.length, fora_do_formato: leituraDoCodex.fora_do_formato }
  : null
if (revisaoDoCodex) {
  log(`revisão do Codex: ${revisaoDoCodex.lidos} de ${revisaoDoCodex.itens_no_texto} item(ns) [P<n>] lido(s), que entram como a primeira lista`)
  if (revisaoDoCodex.fora_do_formato.length) {
    log(`revisão do Codex: ${revisaoDoCodex.fora_do_formato.length} item(ns) fora do formato "- [P<n>] <título> — <arquivo>:<início>-<fim>" ficaram sem cético — ${revisaoDoCodex.fora_do_formato.join('; ')}`)
  }
}

phase('Lentes')
const respostas = (await parallel(LENTES.map(lente => () => rodarLente(lente, alvo, contexto))))
  .map((resposta, i) => resposta || { lente: LENTES[i].nome, motivo: MOTIVO_DO_AGENTE_SEM_RESPOSTA })
const lentesQueCairam = respostas.filter(r => !r.achados).map(r => ({ lente: r.lente, motivo: r.motivo }))
const lentesQueDevolveram = respostas.filter(r => r.achados)
lentesQueCairam.forEach(c => log(`a lente ${c.lente} caiu (${c.motivo}): o ângulo dela ficou sem medir`))

const resultado = {
  alvo: entrada.alvo,
  teto_de_agentes: TETO_DE_AGENTES,
  agentes: lentesQueDevolveram.length,
  lentes_que_cairam: lentesQueCairam,
}
if (revisaoDoCodex) resultado.revisao_do_codex = revisaoDoCodex
if (!lentesQueDevolveram.length) {
  const doCodexSemCetico = doCodex.length ? `, e os ${doCodex.length} achado(s) do Codex ficaram sem cético` : ''
  resultado.nao_mediu = `as ${LENTES.length} lentes caíram e a rodada não mediu${doCodexSemCetico}: rode de novo quando o agente voltar a responder`
  log(resultado.nao_mediu)
  return resultado
}
Object.assign(resultado, { provado: [], provavel: [], nao_provado: [], derrubado: [], sem_voto: [] })

const juntos = juntarRepetidos([...doCodex, ...lentesQueDevolveram.flatMap(r => r.achados)])
const ordenados = [...juntos].sort((a, b) => peso(b) - peso(a))
if (!ordenados.length) {
  log('nenhum achado, nem das lentes nem do Codex: zero não prova ausência, e a rodada termina sem cético')
  return resultado
}

const vagas = TETO_DE_AGENTES - LENTES.length
const comVoto = ordenados.slice(0, vagas)
const semVoto = ordenados.slice(vagas)
if (semVoto.length) {
  log(`teto de ${TETO_DE_AGENTES} agentes: ${semVoto.length} achado(s) ficaram sem cético, e sem voto não é derrubado — ${semVoto.map(a => a.titulo).join('; ')}`)
}
const tarefas = comVoto.map((_, indice) => ({ indice, angulo: 'reproduza' }))
const graves = comVoto.map((a, indice) => ({ a, indice })).filter(g => g.a.gravidade === 'grave')
const segundos = graves.slice(0, Math.max(0, vagas - comVoto.length))
tarefas.push(...segundos.map(g => ({ indice: g.indice, angulo: 'contrato' })))
if (graves.length > segundos.length) {
  log(`teto de ${TETO_DE_AGENTES} agentes: ${graves.length - segundos.length} achado(s) grave(s) ficaram com um cético só`)
}

phase('Céticos')
const votos = await parallel(tarefas.map(t => () =>
  agent(promptDoCetico(comVoto[t.indice], t.angulo, alvo), { label: `cético ${t.indice + 1} · ${t.angulo}`, phase: 'Céticos', schema: ESQUEMA_DO_CETICO })
    .then(v => v ? { ...v, indice: t.indice, angulo: t.angulo } : null)))
const lidos = votos.filter(Boolean)
if (lidos.length < tarefas.length) log(`${tarefas.length - lidos.length} cético(s) caíram: o achado deles pode ter ficado sem voto`)

resultado.agentes += lidos.length
comVoto.forEach((achado, i) => {
  const dele = lidos.filter(v => v.indice === i).map(({ indice, ...voto }) => voto)
  resultado[vereditoFinal(dele)].push({ ...achado, votos: dele })
})
semVoto.forEach(achado => resultado.sem_voto.push({ ...achado, votos: [] }))
log(`provado ${resultado.provado.length}, provável ${resultado.provavel.length}, não provado ${resultado.nao_provado.length}, derrubado ${resultado.derrubado.length}, sem voto ${resultado.sem_voto.length}; ${resultado.agentes} agente(s)`)
return resultado
