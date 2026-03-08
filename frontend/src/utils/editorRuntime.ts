import type { App, Plugin } from 'vue';

let installed = false;
let installing: Promise<void> | null = null;
let modulesLoading: Promise<[Plugin, Plugin]> | null = null;
let modulesLoaded: [Plugin, Plugin] | null = null;

const loadPluginModules = async (): Promise<[Plugin, Plugin]> => {
  if (modulesLoaded) return modulesLoaded;
  if (!modulesLoading) {
    modulesLoading = Promise.all([import('@editor/plugins/icon'), import('@editor/plugins/directive')]).then(
      ([icon, directive]) => [icon.default as Plugin, directive.default as Plugin],
    );
  }

  try {
    modulesLoaded = await modulesLoading;
    return modulesLoaded;
  } finally {
    modulesLoading = null;
  }
};

/**
 * 仅预加载 editor-runtime 插件依赖的模块（不执行 app.use）。
 * 用于 hover / idle 期间提前拉取与解析，减少“点击进入编辑器”时的主线程压力。
 */
export async function prefetchEditorRuntimePluginModules(): Promise<void> {
  try {
    await loadPluginModules();
  } catch {
    // ignore
  }
}

/**
 * 按需安装 editor-runtime 的全局插件（IconPark 图标组件、指令等）。
 *
 * 目的：避免 editor-runtime 侵入首屏/工作台，仅在进入编辑器路由前加载。
 */
export async function ensureEditorRuntimePlugins(app: App): Promise<void> {
  if (installed) return;
  if (installing) return installing;

  installing = (async () => {
    const [iconPlugin, directivePlugin] = await loadPluginModules();

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
