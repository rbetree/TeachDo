import type { InjectionKey, Ref } from 'vue';

/**
 * TeachDo 外层业务（PPTEditorRuntime）与 editor-runtime 内部组件的桥接上下文。
 *
 * 说明：
 * - editor-runtime 可能被复用在非 TeachDo 场景，因此这里用可选注入的方式做“能力探测”。
 * - 目前用于：在编辑器原生顶部（EditorHeader）触发“返回工作台”，并展示保存中状态。
 */
export interface TeachdoEditorBridge {
  backToWorkspace: () => void | Promise<void>;
  saving: Ref<boolean>;
}

export const TEACHDO_EDITOR_BRIDGE_KEY: InjectionKey<TeachdoEditorBridge> = Symbol('TEACHDO_EDITOR_BRIDGE');

