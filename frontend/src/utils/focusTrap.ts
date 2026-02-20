/**
 * 简易 Focus Trap（无三方依赖）
 *
 * 设计目标：
 * - Dialog/Modal 打开时，Tab / Shift+Tab 不应逃逸到页面其他区域
 * - 不接管焦点管理的其它策略（打开时聚焦哪个元素由调用方决定）
 *
 * 使用方式：
 * - 在 document 的 keydown 监听里调用 trapTabKey(e, dialogEl)
 */

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'area[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[contenteditable="true"]',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

const isElementVisible = (el: HTMLElement) => {
  if (el.hasAttribute('hidden')) return false;
  const style = window.getComputedStyle(el);
  if (style.display === 'none' || style.visibility === 'hidden') return false;
  // 允许 opacity:0 的元素参与（例如动画过渡中），避免 Tab 断链
  return true;
};

export const getFocusableElements = (container: HTMLElement): HTMLElement[] => {
  const nodes = Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
  return nodes.filter((el) => isElementVisible(el));
};

export const trapTabKey = (event: KeyboardEvent, container: HTMLElement) => {
  if (event.key !== 'Tab') return;

  const focusables = getFocusableElements(container);
  if (!focusables.length) {
    event.preventDefault();
    container.focus();
    return;
  }

  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  const active = document.activeElement instanceof HTMLElement ? document.activeElement : null;

  // 如果焦点不在容器内，也强制拉回（防止意外点击/读屏导致失焦）
  if (!active || !container.contains(active)) {
    event.preventDefault();
    (event.shiftKey ? last : first).focus();
    return;
  }

  if (event.shiftKey) {
    if (active === first) {
      event.preventDefault();
      last.focus();
    }
    return;
  }

  if (active === last) {
    event.preventDefault();
    first.focus();
  }
};

