import { Link } from 'react-router-dom';

import DetailList from '../../components/DetailList.jsx';
import Modal from '../../components/Modal.jsx';
import { ConformityTag, RatePill, StatusTag } from '../../components/Tags.jsx';
import { formatDateTime } from '../../utils/format.js';

export default function AccessibilityDetailModal({ inspection, onClose }) {
  if (!inspection) return null;

  return (
    <Modal
      title={`无障碍检查详情 - ${inspection.restroom?.name ?? ''}`}
      onClose={onClose}
      width={820}
      footer={
        <button type="button" className="btn" onClick={onClose}>
          关闭
        </button>
      }
    >
      <DetailList
        items={[
          { label: '检查时间', value: formatDateTime(inspection.inspect_time) },
          { label: '检查人', value: inspection.inspector },
          { label: '总体判定', value: <ConformityTag conformity={inspection.conformity} /> },
          { label: '达标率', value: <RatePill rate={inspection.rate} /> },
          {
            label: '判定分布',
            value: `符合 ${inspection.compliant_count} 项 · 部分符合 ${inspection.partial_count} 项 · 不符合 ${inspection.non_compliant_count} 项`,
          },
          { label: '检查备注', value: inspection.remark || '无' },
        ]}
      />

      <div className="section-title">设施登记明细</div>
      <div className="facility-grid">
        {(inspection.items || []).map((item) => (
          <div
            className={`facility-card${item.conformity === '不符合' ? ' is-fail' : item.conformity === '部分符合' ? ' is-partial' : ''}`}
            key={item.key}
          >
            <div className="facility-head">
              <strong>{item.name}</strong>
              <ConformityTag conformity={item.conformity} />
            </div>
            <div className="facility-standard">检查标准：{item.standard}</div>
            <div className="facility-row">
              <span className="muted">配置情况</span>
              <span>{item.configured ? '已配置' : '未配置'}</span>
            </div>
            {item.configured ? (
              <div className="facility-row">
                <span className="muted">完好状态</span>
                <span>{item.condition}</span>
              </div>
            ) : null}
            {item.remark ? (
              <div className="muted" style={{ fontSize: 12 }}>
                备注：{item.remark}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      <div className="section-title">生成的待整改事项（{inspection.issues?.length || 0}）</div>
      {inspection.issues?.length ? (
        <div className="issue-link-list">
          {inspection.issues.map((issue) => (
            <div className="issue-link-row" key={issue.id}>
              <span className="muted">{issue.code}</span>
              <Link to={`/issues/${issue.id}`}>{issue.title}</Link>
              <StatusTag status={issue.status} />
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-block">本次检查无不符合项，未生成整改事项</div>
      )}
    </Modal>
  );
}
