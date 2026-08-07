// Site mínimo: só renderiza a documentação que já existe na raiz.
// Nada é copiado — as páginas são lidas de onde estão.

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: 'Camada de IA',
  tagline: 'Skills, fluxos e conhecimento genéricos para sessões de IA',
  url: 'http://localhost',
  baseUrl: '/',

  // Link quebrado derruba a construção: erro de documentação é erro.
  onBrokenLinks: 'throw',
  markdown: {
    hooks: { onBrokenMarkdownLinks: 'throw' },
    // `.md` é lido como markdown comum, não como MDX. Sem isso, um
    // `<coisa/assim>` fora de bloco de código — coisa que texto gerado e nota
    // pessoal escrevem o tempo todo — derruba a construção com um erro que
    // não diz onde consertar. Quem quiser JSX escreve `.mdx`.
    format: 'detect',
  },

  i18n: { defaultLocale: 'pt-BR', locales: ['pt-BR'] },

  presets: [
    [
      'classic',
      /** @type {import('@docusaurus/preset-classic').Options} */
      ({
        docs: {
          // As páginas ficam na raiz do repositório, um nível acima daqui.
          path: '..',
          routeBasePath: '/',
          sidebarPath: './sidebars.js',
          // Lista de permissão, não de exclusão: só entra o que está aqui.
          // As páginas da camada, e um nível de subpasta de conhecimento/ —
          // onde moram a wiki e as notas da casa. O caminho do preset é a
          // raiz do repositório, então um `**` arrastaria os repositórios de
          // código e o material de terceiro junto: por isso, um nível só.
          include: ['fluxos/*.md', 'conhecimento/*.md', 'conhecimento/*/*.md'],
          // O LEIAME do primeiro nível diz ao repositório o que entra na
          // pasta — não é página. O de uma subpasta costuma ser conteúdo (o
          // mapa da wiki, por exemplo), e esse entra.
          exclude: ['fluxos/LEIAME.md', 'conhecimento/LEIAME.md'],
        },
        blog: false,
        theme: { customCss: './src/css/custom.css' },
      }),
    ],
  ],

  themeConfig: {
    navbar: {
      title: 'Camada de IA',
      items: [{ type: 'docSidebar', sidebarId: 'documentacao', label: 'Documentação' }],
    },
    footer: { style: 'dark', copyright: 'Camada abstrata e compartilhável.' },
  },
};

export default config;
