/**
 * 无障碍专项检查判定规则（与后端 accessibility_rules 保持一致）：
 * 未配置 -> 不符合；完好 -> 符合；轻微破损 -> 部分符合；严重损坏 -> 不符合。
 */

export const NOT_CONFIGURED = '未配置';

export function judgeItem(item) {
  if (!item.configured) return '不符合';
  if (item.condition === '完好') return '符合';
  if (item.condition === '轻微破损') return '部分符合';
  return '不符合';
}

const VERDICT_SCORES = { 符合: 1, 部分符合: 0.5, 不符合: 0 };

export function calcScore(items) {
  if (!items?.length) return 0;
  const total = items.reduce((sum, item) => sum + VERDICT_SCORES[judgeItem(item)], 0);
  return Math.round((total / items.length) * 1000) / 10;
}

export function resultOf(items) {
  const verdicts = (items || []).map(judgeItem);
  if (verdicts.includes('不符合')) return '不达标';
  if (verdicts.includes('部分符合')) return '部分达标';
  return '达标';
}

export function countByVerdict(items) {
  const verdicts = (items || []).map(judgeItem);
  return {
    compliant: verdicts.filter((item) => item === '符合').length,
    partial: verdicts.filter((item) => item === '部分符合').length,
    failed: verdicts.filter((item) => item === '不符合').length,
  };
}
