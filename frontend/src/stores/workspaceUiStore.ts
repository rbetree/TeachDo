import { defineStore } from 'pinia';

export type WorkspaceRightPanelTab = 'kb' | 'assistant';

interface WorkspaceUiState {
  rightPanelCollapsed: boolean;
  rightPanelTab: WorkspaceRightPanelTab;
}

export const useWorkspaceUiStore = defineStore('workspace_ui', {
  state: (): WorkspaceUiState => ({
    rightPanelCollapsed: false,
    rightPanelTab: 'kb',
  }),
  actions: {
    setRightPanelTab(tab: WorkspaceRightPanelTab) {
      this.rightPanelTab = tab;
      this.rightPanelCollapsed = false;
    },
    toggleRightPanelCollapsed() {
      this.rightPanelCollapsed = !this.rightPanelCollapsed;
    },
    expandRightPanel() {
      this.rightPanelCollapsed = false;
    },
    collapseRightPanel() {
      this.rightPanelCollapsed = true;
    },
  },
});
