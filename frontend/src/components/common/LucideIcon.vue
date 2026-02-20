<script setup lang="ts">
/* eslint-env browser */
/* global console */
import { computed } from 'vue';
import { useAttrs } from 'vue';

type IconElement = 'path' | 'rect' | 'circle' | 'line' | 'polyline' | 'ellipse';

interface IconNode {
  tag: IconElement;
  attrs: Record<string, string>;
}

export type IconName =
  | 'mail'
  | 'lock'
  | 'user'
  | 'loader'
  | 'loader-2'
  | 'arrow-left'
  | 'arrow-right'
  | 'arrow-left-right'
  | 'layout-grid'
  | 'layout-list'
  | 'info'
  | 'globe'
  | 'moon'
  | 'sun'
  | 'menu'
  | 'wifi'
  | 'wifi-off'
  | 'refresh-cw'
  | 'settings'
  | 'log-out'
  | 'chevron-down'
  | 'plus'
  | 'book-open'
  | 'layers'
  | 'file-text'
  | 'presentation'
  | 'database'
  | 'message-square'
  | 'panel-left-close'
  | 'panel-left-open'
  | 'x'
  | 'eye'
  | 'edit-3'
  | 'save'
  | 'check'
  | 'history'
  | 'download'
  | 'sparkles'
  | 'send'
  | 'bot'
  | 'file-down'
  | 'upload-cloud'
  | 'file-text'
  | 'trash-2'
  | 'database'
  | 'check-circle'
  | 'check-circle-2'
  | 'alert-circle'
  | 'alert-triangle'
  | 'search'
  | 'file'
  | 'server'
  | 'code'
  | 'activity'
  | 'x-circle'
  | 'cpu'
  | 'network'
  | 'terminal'
  | 'copy'
  | 'settings-2'
  | 'shield'
  | 'rotate-ccw'
  | 'eye-off';

const ICONS: Record<IconName, IconNode[]> = {
  mail: [
    { tag: 'path', attrs: { d: 'm22 7-8.991 5.727a2 2 0 0 1-2.009 0L2 7' } },
    { tag: 'rect', attrs: { x: '2', y: '4', width: '20', height: '16', rx: '2' } },
  ],
  lock: [
    { tag: 'rect', attrs: { width: '18', height: '11', x: '3', y: '11', rx: '2', ry: '2' } },
    { tag: 'path', attrs: { d: 'M7 11V7a5 5 0 0 1 10 0v4' } },
  ],
  user: [
    { tag: 'path', attrs: { d: 'M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2' } },
    { tag: 'circle', attrs: { cx: '12', cy: '7', r: '4' } },
  ],
  loader: [
    { tag: 'path', attrs: { d: 'M12 2v4' } },
    { tag: 'path', attrs: { d: 'm16.2 7.8 2.9-2.9' } },
    { tag: 'path', attrs: { d: 'M18 12h4' } },
    { tag: 'path', attrs: { d: 'm16.2 16.2 2.9 2.9' } },
    { tag: 'path', attrs: { d: 'M12 18v4' } },
    { tag: 'path', attrs: { d: 'm4.9 19.1 2.9-2.9' } },
    { tag: 'path', attrs: { d: 'M2 12h4' } },
    { tag: 'path', attrs: { d: 'm4.9 4.9 2.9 2.9' } },
  ],
  'arrow-left': [
    { tag: 'path', attrs: { d: 'm12 19-7-7 7-7' } },
    { tag: 'path', attrs: { d: 'M19 12H5' } },
  ],
  'arrow-right': [
    { tag: 'path', attrs: { d: 'M5 12h14' } },
    { tag: 'path', attrs: { d: 'm12 5 7 7-7 7' } },
  ],
  'layout-grid': [
    { tag: 'rect', attrs: { width: '7', height: '7', x: '3', y: '3', rx: '1' } },
    { tag: 'rect', attrs: { width: '7', height: '7', x: '14', y: '3', rx: '1' } },
    { tag: 'rect', attrs: { width: '7', height: '7', x: '14', y: '14', rx: '1' } },
    { tag: 'rect', attrs: { width: '7', height: '7', x: '3', y: '14', rx: '1' } },
  ],
  'layout-list': [
    { tag: 'rect', attrs: { width: '7', height: '7', x: '3', y: '3', rx: '1' } },
    { tag: 'rect', attrs: { width: '7', height: '7', x: '3', y: '14', rx: '1' } },
    { tag: 'path', attrs: { d: 'M14 4h7' } },
    { tag: 'path', attrs: { d: 'M14 9h7' } },
    { tag: 'path', attrs: { d: 'M14 15h7' } },
    { tag: 'path', attrs: { d: 'M14 20h7' } },
  ],
  info: [
    { tag: 'circle', attrs: { cx: '12', cy: '12', r: '10' } },
    { tag: 'path', attrs: { d: 'M12 16v-4' } },
    { tag: 'path', attrs: { d: 'M12 8h.01' } },
  ],
  globe: [
    { tag: 'circle', attrs: { cx: '12', cy: '12', r: '10' } },
    { tag: 'path', attrs: { d: 'M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20' } },
    { tag: 'path', attrs: { d: 'M2 12h20' } },
  ],
  moon: [
    {
      tag: 'path',
      attrs: {
        d: 'M20.985 12.486a9 9 0 1 1-9.473-9.472c.405-.022.617.46.402.803a6 6 0 0 0 8.268 8.268c.344-.215.825-.004.803.401',
      },
    },
  ],
  sun: [
    { tag: 'circle', attrs: { cx: '12', cy: '12', r: '4' } },
    { tag: 'path', attrs: { d: 'M12 2v2' } },
    { tag: 'path', attrs: { d: 'M12 20v2' } },
    { tag: 'path', attrs: { d: 'm4.93 4.93 1.41 1.41' } },
    { tag: 'path', attrs: { d: 'm17.66 17.66 1.41 1.41' } },
    { tag: 'path', attrs: { d: 'M2 12h2' } },
    { tag: 'path', attrs: { d: 'M20 12h2' } },
    { tag: 'path', attrs: { d: 'm6.34 17.66-1.41 1.41' } },
    { tag: 'path', attrs: { d: 'm19.07 4.93-1.41 1.41' } },
  ],
  menu: [
    { tag: 'path', attrs: { d: 'M4 5h16' } },
    { tag: 'path', attrs: { d: 'M4 12h16' } },
    { tag: 'path', attrs: { d: 'M4 19h16' } },
  ],
  wifi: [
    { tag: 'path', attrs: { d: 'M12 20h.01' } },
    { tag: 'path', attrs: { d: 'M2 8.82a15 15 0 0 1 20 0' } },
    { tag: 'path', attrs: { d: 'M5 12.859a10 10 0 0 1 14 0' } },
    { tag: 'path', attrs: { d: 'M8.5 16.429a5 5 0 0 1 7 0' } },
  ],
  plus: [
    { tag: 'path', attrs: { d: 'M5 12h14' } },
    { tag: 'path', attrs: { d: 'M12 5v14' } },
  ],
  'book-open': [
    { tag: 'path', attrs: { d: 'M12 7v14' } },
    {
      tag: 'path',
      attrs: {
        d: 'M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z',
      },
    },
  ],
  layers: [
    {
      tag: 'path',
      attrs: {
        d: 'M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z',
      },
    },
    {
      tag: 'path',
      attrs: {
        d: 'M2 12a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 12',
      },
    },
    {
      tag: 'path',
      attrs: {
        d: 'M2 17a1 1 0 0 0 .58.91l8.6 3.91a2 2 0 0 0 1.65 0l8.58-3.9A1 1 0 0 0 22 17',
      },
    },
  ],
  'file-text': [
    {
      tag: 'path',
      attrs: {
        d: 'M6 22a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.704.706l3.588 3.588A2.4 2.4 0 0 1 20 8v12a2 2 0 0 1-2 2z',
      },
    },
    { tag: 'path', attrs: { d: 'M14 2v5a1 1 0 0 0 1 1h5' } },
    { tag: 'path', attrs: { d: 'M10 9H8' } },
    { tag: 'path', attrs: { d: 'M16 13H8' } },
    { tag: 'path', attrs: { d: 'M16 17H8' } },
  ],
  presentation: [
    { tag: 'path', attrs: { d: 'M2 3h20' } },
    { tag: 'path', attrs: { d: 'M21 3v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V3' } },
    { tag: 'path', attrs: { d: 'm7 21 5-5 5 5' } },
  ],
  database: [
    { tag: 'ellipse', attrs: { cx: '12', cy: '5', rx: '9', ry: '3' } },
    { tag: 'path', attrs: { d: 'M3 5V19A9 3 0 0 0 21 19V5' } },
    { tag: 'path', attrs: { d: 'M3 12A9 3 0 0 0 21 12' } },
  ],
  'message-square': [
    {
      tag: 'path',
      attrs: {
        d: 'M22 17a2 2 0 0 1-2 2H6.828a2 2 0 0 0-1.414.586l-2.202 2.202A.71.71 0 0 1 2 21.286V5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2z',
      },
    },
  ],
  'panel-left-close': [
    { tag: 'rect', attrs: { width: '18', height: '18', x: '3', y: '3', rx: '2' } },
    { tag: 'path', attrs: { d: 'M9 3v18' } },
    { tag: 'path', attrs: { d: 'm16 15-3-3 3-3' } },
  ],
  'panel-left-open': [
    { tag: 'rect', attrs: { width: '18', height: '18', x: '3', y: '3', rx: '2' } },
    { tag: 'path', attrs: { d: 'M9 3v18' } },
    { tag: 'path', attrs: { d: 'm14 9 3 3-3 3' } },
  ],
  x: [
    { tag: 'path', attrs: { d: 'M18 6 6 18' } },
    { tag: 'path', attrs: { d: 'm6 6 12 12' } },
  ],
  'wifi-off': [
    { tag: 'path', attrs: { d: 'M12 20h.01' } },
    { tag: 'path', attrs: { d: 'M8.5 16.429a5 5 0 0 1 7 0' } },
    { tag: 'path', attrs: { d: 'M5 12.859a10 10 0 0 1 5.17-2.69' } },
    { tag: 'path', attrs: { d: 'M19 12.859a10 10 0 0 0-2.007-1.523' } },
    { tag: 'path', attrs: { d: 'M2 8.82a15 15 0 0 1 4.177-2.643' } },
    { tag: 'path', attrs: { d: 'M22 8.82a15 15 0 0 0-11.288-3.764' } },
    { tag: 'path', attrs: { d: 'm2 2 20 20' } },
  ],
  'refresh-cw': [
    { tag: 'path', attrs: { d: 'M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8' } },
    { tag: 'path', attrs: { d: 'M21 3v5h-5' } },
    { tag: 'path', attrs: { d: 'M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16' } },
    { tag: 'path', attrs: { d: 'M8 16H3v5' } },
  ],
  settings: [
    {
      tag: 'path',
      attrs: {
        d: 'M9.671 4.136a2.34 2.34 0 0 1 4.659 0 2.34 2.34 0 0 0 3.319 1.915 2.34 2.34 0 0 1 2.33 4.033 2.34 2.34 0 0 0 0 3.831 2.34 2.34 0 0 1-2.33 4.033 2.34 2.34 0 0 0-3.319 1.915 2.34 2.34 0 0 1-4.659 0 2.34 2.34 0 0 0-3.32-1.915 2.34 2.34 0 0 1-2.33-4.033 2.34 2.34 0 0 0 0-3.831A2.34 2.34 0 0 1 6.35 6.051a2.34 2.34 0 0 0 3.319-1.915',
      },
    },
    { tag: 'circle', attrs: { cx: '12', cy: '12', r: '3' } },
  ],
  'log-out': [
    { tag: 'path', attrs: { d: 'm16 17 5-5-5-5' } },
    { tag: 'path', attrs: { d: 'M21 12H9' } },
    { tag: 'path', attrs: { d: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4' } },
  ],
  'chevron-down': [{ tag: 'path', attrs: { d: 'm6 9 6 6 6-6' } }],
  'loader-2': [
    { tag: 'path', attrs: { d: 'M12 2v4' } },
    { tag: 'path', attrs: { d: 'm16.2 7.8 2.9-2.9' } },
    { tag: 'path', attrs: { d: 'M18 12h4' } },
    { tag: 'path', attrs: { d: 'm16.2 16.2 2.9 2.9' } },
    { tag: 'path', attrs: { d: 'M12 18v4' } },
    { tag: 'path', attrs: { d: 'm4.9 19.1 2.9-2.9' } },
    { tag: 'path', attrs: { d: 'M2 12h4' } },
    { tag: 'path', attrs: { d: 'm4.9 4.9 2.9 2.9' } },
  ],
  'arrow-left-right': [
    { tag: 'path', attrs: { d: 'M8 3 4 7l4 4' } },
    { tag: 'path', attrs: { d: 'M4 7h16' } },
    { tag: 'path', attrs: { d: 'm16 21 4-4-4-4' } },
    { tag: 'path', attrs: { d: 'M20 17H4' } },
  ],
  eye: [
    { tag: 'path', attrs: { d: 'M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0' } },
    { tag: 'circle', attrs: { cx: '12', cy: '12', r: '3' } },
  ],
  'edit-3': [
    { tag: 'path', attrs: { d: 'M12 20h9' } },
    { tag: 'path', attrs: { d: 'M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z' } },
  ],
  save: [
    { tag: 'path', attrs: { d: 'M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z' } },
    { tag: 'path', attrs: { d: 'M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7' } },
    { tag: 'path', attrs: { d: 'M7 3v4a1 1 0 0 0 1 1h7' } },
  ],
  check: [
    { tag: 'path', attrs: { d: 'M20 6 9 17l-5-5' } },
  ],
  history: [
    { tag: 'path', attrs: { d: 'M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8' } },
    { tag: 'path', attrs: { d: 'M3 3v5h5' } },
    { tag: 'path', attrs: { d: 'M12 7v5l4 2' } },
  ],
  download: [
    { tag: 'path', attrs: { d: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' } },
    { tag: 'polyline', attrs: { points: '7 10 12 15 17 10' } },
    { tag: 'line', attrs: { x1: '12', x2: '12', y1: '15', y2: '3' } },
  ],
  sparkles: [
    { tag: 'path', attrs: { d: 'm12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275z' } },
    { tag: 'path', attrs: { d: 'M5 3v4' } },
    { tag: 'path', attrs: { d: 'M19 17v4' } },
    { tag: 'path', attrs: { d: 'M3 5h4' } },
    { tag: 'path', attrs: { d: 'M17 19h4' } },
  ],
  send: [
    { tag: 'path', attrs: { d: 'm22 2-7 20-4-9-9-4Z' } },
    { tag: 'path', attrs: { d: 'M22 2 11 13' } },
  ],
  bot: [
    { tag: 'path', attrs: { d: 'M12 8V4' } },
    { tag: 'rect', attrs: { x: '4', y: '8', width: '16', height: '12', rx: '2' } },
    { tag: 'path', attrs: { d: 'M2 14h2' } },
    { tag: 'path', attrs: { d: 'M20 14h2' } },
    { tag: 'path', attrs: { d: 'M9 14h.01' } },
    { tag: 'path', attrs: { d: 'M15 14h.01' } },
    { tag: 'path', attrs: { d: 'M12 2h4' } },
    { tag: 'path', attrs: { d: 'M12 20v4' } },
  ],
  'file-down': [
    { tag: 'path', attrs: { d: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' } },
    { tag: 'path', attrs: { d: 'M14 2v6h6' } },
    { tag: 'path', attrs: { d: 'M12 18v-6' } },
    { tag: 'path', attrs: { d: 'm9 15 3 3 3-3' } },
  ],
  'upload-cloud': [
    { tag: 'path', attrs: { d: 'M4 14.89a4.5 4.5 0 0 1 2.5-8.39 5 5 0 0 1 9 1.1 4 4 0 0 1 2.5 7.29' } },
    { tag: 'path', attrs: { d: 'M12 12v9' } },
    { tag: 'path', attrs: { d: 'm16 16-4-4-4 4' } },
  ],
  'trash-2': [
    { tag: 'path', attrs: { d: 'M3 6h18' } },
    { tag: 'path', attrs: { d: 'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6' } },
    { tag: 'path', attrs: { d: 'M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2' } },
    { tag: 'path', attrs: { d: 'M10 11v6' } },
    { tag: 'path', attrs: { d: 'M14 11v6' } },
  ],
  'check-circle': [
    { tag: 'path', attrs: { d: 'M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z' } },
    { tag: 'path', attrs: { d: 'm9 12 2 2 4-4' } },
  ],
  'alert-circle': [
    { tag: 'circle', attrs: { cx: '12', cy: '12', r: '10' } },
    { tag: 'path', attrs: { d: 'M12 8v4' } },
    { tag: 'path', attrs: { d: 'M12 16h.01' } },
  ],
  'alert-triangle': [
    { tag: 'path', attrs: { d: 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z' } },
    { tag: 'path', attrs: { d: 'M12 9v4' } },
    { tag: 'path', attrs: { d: 'M12 17h.01' } },
  ],
  search: [
    { tag: 'circle', attrs: { cx: '11', cy: '11', r: '8' } },
    { tag: 'path', attrs: { d: 'm21 21-4.3-4.3' } },
  ],
  file: [
    { tag: 'path', attrs: { d: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' } },
    { tag: 'path', attrs: { d: 'M14 2v6h6' } },
  ],
  server: [
    { tag: 'rect', attrs: { x: '2', y: '2', width: '20', height: '8', rx: '2' } },
    { tag: 'rect', attrs: { x: '2', y: '14', width: '20', height: '8', rx: '2' } },
    { tag: 'path', attrs: { d: 'M6 6h.01' } },
    { tag: 'path', attrs: { d: 'M6 18h.01' } },
  ],
  code: [
    { tag: 'polyline', attrs: { points: '16 18 22 12 16 6' } },
    { tag: 'polyline', attrs: { points: '8 6 2 12 8 18' } },
  ],
  activity: [
    { tag: 'path', attrs: { d: 'M22 12h-4l-3 9L9 3l-3 9H2' } },
  ],
  'x-circle': [
    { tag: 'circle', attrs: { cx: '12', cy: '12', r: '10' } },
    { tag: 'path', attrs: { d: 'm15 9-6 6' } },
    { tag: 'path', attrs: { d: 'm9 9 6 6' } },
  ],
  cpu: [
    { tag: 'rect', attrs: { x: '4', y: '4', width: '16', height: '16', rx: '2' } },
    { tag: 'rect', attrs: { x: '9', y: '9', width: '6', height: '6' } },
    { tag: 'path', attrs: { d: 'M15 2v2' } },
    { tag: 'path', attrs: { d: 'M15 20v2' } },
    { tag: 'path', attrs: { d: 'M2 15h2' } },
    { tag: 'path', attrs: { d: 'M2 9h2' } },
    { tag: 'path', attrs: { d: 'M20 15h2' } },
    { tag: 'path', attrs: { d: 'M20 9h2' } },
    { tag: 'path', attrs: { d: 'M9 2v2' } },
    { tag: 'path', attrs: { d: 'M9 20v2' } },
  ],
  network: [
    { tag: 'rect', attrs: { x: '9', y: '2', width: '6', height: '6', rx: '1' } },
    { tag: 'rect', attrs: { x: '16', y: '16', width: '6', height: '6', rx: '1' } },
    { tag: 'rect', attrs: { x: '2', y: '16', width: '6', height: '6', rx: '1' } },
    { tag: 'path', attrs: { d: 'm5 16 4-4' } },
    { tag: 'path', attrs: { d: 'm15 12 4 4' } },
    { tag: 'path', attrs: { d: 'm12 8 0 4' } },
  ],
  terminal: [
    { tag: 'path', attrs: { d: 'm4 17 6-6-6-6' } },
    { tag: 'path', attrs: { d: 'M12 19h8' } },
  ],
  copy: [
    { tag: 'rect', attrs: { x: '9', y: '9', width: '13', height: '13', rx: '2', ry: '2' } },
    { tag: 'path', attrs: { d: 'M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1' } },
  ],
  'settings-2': [
    { tag: 'path', attrs: { d: 'M20 7h-9' } },
    { tag: 'path', attrs: { d: 'M14 17H5' } },
    { tag: 'circle', attrs: { cx: '17', cy: '17', r: '3' } },
    { tag: 'circle', attrs: { cx: '7', cy: '7', r: '3' } },
  ],
  shield: [
    { tag: 'path', attrs: { d: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10' } },
  ],
  'rotate-ccw': [
    { tag: 'polyline', attrs: { points: '1 4 1 10 7 10' } },
    { tag: 'path', attrs: { d: 'M3.51 15a9 9 0 1 0 .49-9' } },
  ],
  'eye-off': [
    { tag: 'path', attrs: { d: 'M9.88 9.88a3 3 0 0 0 4.24 4.24' } },
    { tag: 'path', attrs: { d: 'M10.73 5.08A9.12 9.12 0 0 1 12 5c5 0 9 4 9 7a9.12 9.12 0 0 1-1.67 3.45' } },
    { tag: 'path', attrs: { d: 'm6.11 6.11-1.9 1.43C2.51 9.05 2 10.21 2 12c0 .5.08.97.22 1.41C3.45 16.9 7 19 12 19a9.24 9.24 0 0 0 3.25-.6' } },
    { tag: 'line', attrs: { x1: '2', y1: '2', x2: '22', y2: '22' } },
  ],
  'check-circle-2': [
    { tag: 'path', attrs: { d: 'M12 22a10 10 0 1 1 0-20 10 10 0 0 1 0 20z' } },
    { tag: 'path', attrs: { d: 'm9 12 2 2 4-4' } },
  ],
};

const props = withDefaults(
  defineProps<{
    name: IconName;
    size?: number | string;
    strokeWidth?: number;
  }>(),
  {
    size: 20,
    strokeWidth: 2,
  },
);

const attrs = useAttrs();

const iconNodes = computed(() => {
  const nodes = ICONS[props.name];
  if (!nodes) {
    console.warn(`[LucideIcon] 未找到图标：${props.name}`);
    return [];
  }
  return nodes;
});

const sizeValue = computed(() => (typeof props.size === 'number' ? `${props.size}` : props.size || '20'));

const ariaHidden = computed(() => {
  if ('aria-label' in attrs || 'aria-labelledby' in attrs) {
    return undefined;
  }
  return 'true';
});
</script>

<template>
  <svg
    v-bind="attrs"
    :width="sizeValue"
    :height="sizeValue"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="props.strokeWidth"
    stroke-linecap="round"
    stroke-linejoin="round"
    role="img"
    :aria-hidden="ariaHidden"
  >
    <component :is="node.tag" v-for="(node, index) in iconNodes" :key="index" v-bind="node.attrs" />
  </svg>
</template>
