/**
 * 无障碍专项检查的前端预判规则，与后端 accessibility_service 保持一致：
 * 未配置 -> 不符合；完好 -> 符合；轻微破损 -> 部分符合；严重损坏 -> 不符合。
 */
export function judgeItem(item) {
  if (!item.configured) return '不符合';
  if (item.condition === '完好') return '符合';
  if (item.condition === '轻微破损') return '部分符合';
  return '不符合';
}

const WEIGHTS = { 符合: 1, 部分符合: 0.5, 不符合: 0 };

export function summarizeItems(items) {
  const judged = (items || []).map((item) => ({ ...item, conformity: judgeItem(item) }));
  const compliant = judged.filter((item) => item.conformity === '符合').length;
  const partial = judged.filter((item) => item.conformity === '部分符合').length;
  const nonCompliant = judged.length - compliant - partial;
  const rate = judged.length
    ? Math.round(
        (judged.reduce((sum, item) => sum + WEIGHTS[item.conformity], 0) / judged.length) * 1000,
      ) / 10
    : 0;
  const conformity = nonCompliant ? '不符合' : partial ? '部分符合' : '符合';
  return { judged, compliant, partial, nonCompliant, rate, conformity };
}
