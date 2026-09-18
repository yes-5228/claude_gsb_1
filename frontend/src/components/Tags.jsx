import { isOverdue, scoreTone, severityTone, statusTone } from '../utils/format.js';

export function StatusTag({ status }) {
  return <span className={`tag ${statusTone(status)}`}>{status}</span>;
}

export function SeverityTag({ severity }) {
  return <span className={`tag ${severityTone(severity)}`}>{severity}</span>;
}

export function ScorePill({ score }) {
  return <span className={`score-pill ${scoreTone(score)}`}>{Number(score).toFixed(1)}</span>;
}

export function OverdueTag({ deadline, status }) {
  if (!isOverdue(deadline, status)) return null;
  return <span className="tag tag-danger">已超期</span>;
}

export function GradeTag({ grade }) {
  const tone =
    grade === '优秀'
      ? 'tag-success'
      : grade === '良好'
        ? 'tag-primary'
        : grade === '合格'
          ? 'tag-warning'
          : 'tag-danger';
  return <span className={`tag ${tone}`}>{grade || '未评级'}</span>;
}

export function ConformityTag({ conformity }) {
  return <span className={`tag ${statusTone(conformity)}`}>{conformity || '未检查'}</span>;
}

export function RatePill({ rate }) {
  if (rate === null || rate === undefined) return <span className="muted">-</span>;
  return <span className={`score-pill ${scoreTone(rate)}`}>{Number(rate).toFixed(1)}%</span>;
}
