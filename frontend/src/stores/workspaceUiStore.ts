import { defineStore } from 'pinia';

interface WorkspaceUiState {
  referencePanelCollapsed: boolean;
  outputPanelCollapsed: boolean;
}

const isMobileViewport = () =>
  typeof window !== 'undefined' && window.matchMedia && window.matchMedia('(max-width: 767px)').matches;

export const useWorkspaceUiStore = defineStore('workspace_ui', {
  state: (): WorkspaceUiState => ({
    referencePanelCollapsed: isMobileViewport(),
    outputPanelCollapsed: isMobileViewport(),
  }),
  actions: {
    openReferencePanel() {
      if (isMobileViewport()) {
        this.outputPanelCollapsed = true;
      }
      this.referencePanelCollapsed = false;
    },
    closeReferencePanel() {
      this.referencePanelCollapsed = true;
    },
    toggleReferencePanel() {
      if (this.referencePanelCollapsed) {
        this.openReferencePanel();
      } else {
        this.closeReferencePanel();
      }
    },
    openOutputPanel() {
      if (isMobileViewport()) {
        this.referencePanelCollapsed = true;
      }
      this.outputPanelCollapsed = false;
    },
    closeOutputPanel() {
      this.outputPanelCollapsed = true;
    },
    toggleOutputPanel() {
      if (this.outputPanelCollapsed) {
        this.openOutputPanel();
      } else {
        this.closeOutputPanel();
      }
    },
  },
});
