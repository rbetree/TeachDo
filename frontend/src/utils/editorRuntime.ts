import type { App } from 'vue';

let installed = false;
let installing: Promise<void> | null = null;

/**
 * 按需安装 editor-runtime 的全局插件（IconPark 图标组件、指令等）。
 *
 * 目的：避免 editor-runtime 侵入首屏/工作台，仅在进入编辑器路由前加载。
 */
export async function ensureEditorRuntimePlugins(app: App): Promise<void> {
  if (installed) return;
  if (installing) return installing;

  installing = (async () => {
    const [{ default: iconPlugin }, { default: directivePlugin }] = await Promise.all([
      import('@editor/plugins/icon'),
      import('@editor/plugins/directive'),
    ]);

    app.use(iconPlugin);
    app.use(directivePlugin);

    installed = true;
  })();

  try {
    await installing;
  } finally {
    installing = null;
  }
}

