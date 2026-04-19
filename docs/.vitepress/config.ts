import { defineConfig, type DefaultTheme } from 'vitepress'

const base = '/TeachDo/'

const guideGroup: DefaultTheme.SidebarItem = {
  text: '指南',
  items: [
    { text: '快速开始', link: '/guide/getting-started' },
    { text: '功能介绍', link: '/guide/features' },
    { text: '截图展示', link: '/guide/screenshots' }
  ]
}

const devGroup: DefaultTheme.SidebarItem = {
  text: '开发',
  items: [
    { text: '项目架构', link: '/dev/architecture' }
  ]
}

const docsGroup: DefaultTheme.SidebarItem = {
  text: '更多',
  items: [
    { text: '更新日志', link: '/changelog' },
    { text: '文档索引', link: '/about' }
  ]
}

export default defineConfig({
  title: 'TeachDo',
  description: '教师备课工作台',
  lang: 'zh-CN',
  base,
  head: [
    ['link', { rel: 'icon', type: 'image/svg+xml', href: `${base}teachdo-logo.svg` }]
  ],
  srcExclude: ['legacy/**', 'dev/history/**', 'dev/prototypes/**'],
  ignoreDeadLinks: [
    /^\.\/\.\.\/\.\.\/frontend\//,
    /^\.\/\.\.\/\.\.\/backend\//,
    /^\.\/\.\.\/\.\.\/\.kilocode\//,
    /^\.\/\.\.\/\.\.\/README(?:\.md)?$/,
    /^\.\/\.\.\/\.\.\/README_PRODUCTION(?:\.md)?$/,
    /^\.\/\.\.\/\.\.\/backend\/启动说明\.md$/
  ],
  appearance: 'dark',
  cleanUrls: true,
  lastUpdated: true,
  themeConfig: {
    siteTitle: 'TeachDo',
    logo: '/teachdo-logo.svg',
    nav: [
      { text: '首页', link: '/' },
      { text: '指南', link: '/guide/getting-started' },
      { text: '文档索引', link: '/about' },
      { text: '开发', link: '/dev/architecture' },
      { text: '更新日志', link: '/changelog' }
    ],
    sidebar: {
      '/': [guideGroup, devGroup, docsGroup]
    },
    socialLinks: [
      { icon: 'github', link: 'https://github.com/rbetree/TeachDo' }
    ],
    search: {
      provider: 'local'
    },
    docFooter: {
      prev: '上一页',
      next: '下一页'
    },
    outline: {
      level: [2, 3],
      label: '页面导航'
    },
    footer: {
      message: 'TeachDo 文档站点基于 VitePress 构建',
      copyright: 'Copyright © TeachDo Contributors'
    }
  }
})
