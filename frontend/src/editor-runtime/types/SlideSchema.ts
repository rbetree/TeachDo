/**
 * Slide JSON Schema 类型别名（TeachDo 对外口径）
 *
 * 说明：
 * - 为了避免文档/对接长期使用历史命名（如 AIPPT），这里提供更中性的类型别名；
 * - 底层实现仍复用 editor-runtime 内既有的类型定义，保持兼容与最小改动。
 */

import type { AIPPTChartType, AIPPTContentItem, AIPPTImage, AIPPTSlide } from './AIPPT';

export type SlideSchemaSlide = AIPPTSlide;
export type SlideSchemaContentItem = AIPPTContentItem;
export type SlideSchemaChartType = AIPPTChartType;
export type SlideSchemaImage = AIPPTImage;

