<template>
  <div class="editor-wrapper">
    <!-- 原编辑器完整结构（使用独立浅色主题） -->
    <div class="pptist-editor editor-container-light-theme">
      <EditorHeader class="layout-header" />
      <div class="layout-content">
          <Thumbnails class="layout-content-left" />
          <div class="layout-content-center">
            <CanvasTool class="center-top" />
            <Canvas class="center-body" :style="{ height: `calc(100% - ${remarkHeight + 40}px)` }" />
            <Remark
              class="center-bottom"
              v-model:height="remarkHeight"
              :style="{ height: `${remarkHeight}px` }"
            />
          </div>
          <Toolbar class="layout-content-right" />
        </div>
    </div>
  </div>

  <SelectPanel v-if="showSelectPanel" />
  <SearchPanel v-if="showSearchPanel" />
  <NotesPanel v-if="showNotesPanel" />
  <MarkupPanel v-if="showMarkupPanel" />
  <SymbolPanel v-if="showSymbolPanel" />

  <Modal
    :visible="!!dialogForExport" 
    :width="680"
    @closed="closeExportDialog()"
  >
    <ExportDialog />
  </Modal>
  <div v-if="isGenerating" class="bottom-loading">
    <span>AI 生成中，请耐心等待…</span>
  </div>
  
</template>

<script lang="ts" setup>
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useMainStore } from '@editor/store'
import useGlobalHotkey from '@editor/hooks/useGlobalHotkey'
import usePasteEvent from '@editor/hooks/usePasteEvent'

import EditorHeader from './EditorHeader/index.vue'
import Canvas from './Canvas/index.vue'
import CanvasTool from './CanvasTool/index.vue'
import Thumbnails from './Thumbnails/index.vue'
import Toolbar from './Toolbar/index.vue'
import Remark from './Remark/index.vue'
import ExportDialog from './ExportDialog/index.vue'
import SelectPanel from './SelectPanel.vue'
import SearchPanel from './SearchPanel.vue'
import NotesPanel from './NotesPanel.vue'
import SymbolPanel from './SymbolPanel.vue'
import MarkupPanel from './MarkupPanel.vue'
import Modal from '@editor/components/Modal.vue'


const mainStore = useMainStore()
const { dialogForExport, showSelectPanel, showSearchPanel, showNotesPanel, showSymbolPanel, showMarkupPanel, isGenerating } = storeToRefs(mainStore)

const closeExportDialog = () => mainStore.setDialogForExport('')

const remarkHeight = ref(40)

useGlobalHotkey()
usePasteEvent()
</script>

<style lang="scss" scoped>
.editor-wrapper {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pptist-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.editor-container-light-theme {
  /* 编辑器整体强制使用浅色主题，完全隔离暗黑主题影响 */
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  
  /* 使用 !important 强制覆盖所有CSS变量，确保不受全局主题影响 */
  --bg-surface: #ffffff !important;
  --bg-surface-hover: #f4f4f4 !important;
  --bg-surface-secondary: #f4f4f4 !important;
  --text-primary: #111111 !important;
  --text-secondary: #666666 !important;
  --text-tertiary: #888888 !important;
  --border-color: #e0e0e0 !important;
  --primary-color: #000000 !important;
  --primary-light: rgba(0, 0, 0, 0.08) !important;
  --spacing-sm: 8px !important;
  --spacing-md: 12px !important;
  --spacing-lg: 16px !important;
  --radius-md: 2px !important;
  --transition-base: 0.2s !important;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace !important;
  
  background-color: #f4f4f4 !important;
  color: #111111 !important;
  
  /* 强制所有子元素继承浅色主题 */
  * {
    --bg-surface: #ffffff !important;
    --bg-surface-hover: #f4f4f4 !important;
    --text-primary: #111111 !important;
    --text-secondary: #666666 !important;
    --border-color: #e0e0e0 !important;
  }
}

.layout-header {
  height: 40px;
  flex-shrink: 0;
}

.layout-content {
  flex: 1;
  height: 100%;
  display: flex;
  overflow: hidden;
}
.layout-content-left {
  width: 160px;
  height: 100%;
  flex-shrink: 0;
}
.layout-content-center {
  width: calc(100% - 160px - 260px);

  .center-top {
    height: 40px;
  }
}
.layout-content-right {
  width: 260px;
  height: 100%;
}

.bottom-loading {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 20px;
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  border-radius: 8px;
  z-index: 1000;
}
</style>
