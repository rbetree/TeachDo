import { defineStore } from 'pinia';

export type WorkspaceRightPanelTab = 'kb' | 'assistant';

interface WorkspaceUiState {
  rightPanelCollapsed: boolean;
  rightPanelTab: WorkspaceRightPanelTab;
  outputPanelCollapsed: boolean;
}

export const useWorkspaceUiStore = defineStore('workspace_ui', {
  state: (): WorkspaceUiState => ({
    rightPanelCollapsed: false,
    rightPanelTab: 'kb',
    outputPanelCollapsed: false,
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
    toggleOutputPanelCollapsed() {
      this.outputPanelCollapsed = !this.outputPanelCollapsed;
    },
    expandOutputPanel() {
      this.outputPanelCollapsed = false;
    },
    collapseOutputPanel() {
      this.outputPanelCollapsed = true;
    },
  },
});
