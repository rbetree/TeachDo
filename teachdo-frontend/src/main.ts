import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import './style.css';
import { setupAppStore } from './stores/appStore';
import { createAppRouter } from './router';
import { i18n } from './i18n';
import { toast } from './utils/toast';
import { ensureEditorRuntimePlugins } from './utils/editorRuntime';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
setupAppStore(pinia);
const router = createAppRouter(pinia);

router.beforeEach(async (to) => {
  if (to.name !== 'course-unit-ppt-editor') return true;
  try {
    await ensureEditorRuntimePlugins(app);
    return true;
  } catch (err) {
    console.error('[Editor Runtime Init Failed]', err);
    toast.error(i18n.global.t('common.error'));
    return { name: 'workspace' };
  }
});
app.use(router);
app.use(i18n);

app.config.errorHandler = (err, instance, info) => {
  console.error('[Vue Error]', err, info);
  toast.error(i18n.global.t('common.error'));
};

window.addEventListener('unhandledrejection', (event) => {
  console.error('[Unhandled Promise]', event.reason);
  toast.error(i18n.global.t('common.error'));
});

void router.isReady().then(() => app.mount('#app'));
