import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import './style.css';
import { setupAppStore } from './stores/appStore';
import { createAppRouter } from './router';
import { i18n } from './i18n';
import { toast } from './utils/toast';

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
setupAppStore(pinia);
const router = createAppRouter(pinia);
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

app.mount('#app');
