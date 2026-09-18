import { Link } from 'react-router-dom';

import DetailList from '../../components/DetailList.jsx';
import Modal from '../../components/Modal.jsx';
import { SeverityTag, StatusTag } from '../../components/Tags.jsx';
import { formatDateTime } from '../../utils/format.js';

export default function AccessibilityDetailModal({ check, onClose }) {
  if (!check) return null;
  return (
    <Modal title={`无障碍专项检查详情 #${check.id}`} onClose={onClose} width={860}>
      <DetailList
        items={[
          { label: '公厕', value: check.restroom ? check.restroom.name : `#${check.restroom_id}` },
          { label: '所属区域', value: check.restroom?.district ?? '-' },
          { label: '检查人', value: check.inspector },
          { label: '检查时间', value: formatDateTime(check.check_time) },
          {
            label: '检查结论',
            value: (
              <span className="inline">
                <StatusTag status={check.result} />
                <span className="muted">达标率 {Number(check.score).toFixed(1)}%</span>
              </span>
            ),
          },
          {
            label: '判定统计',
            value: `符合 ${check.compliant_count} / 部分符合 ${check.partial_count} / 不符合 ${check.failed_count}`,
          },
        ]}
      />

      <div className="section-title" style={{ marginTop: 16 }}>
        设施登记与判定
      </div>
      <div className="table-wrap">
        <table className="data-table">
          <thead>
            <tr>
              <th>设施</th>
              <th>配置情况</th>
              <th>完好状态</th>
              <th>判定</th>
              <th>备注</th>
            </tr>
          </thead>
          <tbody>
            {check.items.map((item) => (
              <tr key={item.facility}>
                <td>{item.facility}</td>
                <td>{item.configured ? '已配置' : '未配置'}</td>
                <td>
                  <StatusTag status={item.condition} />
                </td>
                <td>
                  <StatusTag status={item.verdict} />
                </td>
                <td className="wrap">{item.remark || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="section-title" style={{ marginTop: 16 }}>
        生成的整改事项（{check.issues?.length || 0}）
      </div>
      {check.issues?.length ? (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>问题编号</th>
                <th>标题</th>
                <th>严重程度</th>
                <th>整改状态</th>
                <th>整改期限</th>
              </tr>
            </thead>
            <tbody>
              {check.issues.map((issue) => (
                <tr key={issue.id}>
                  <td>
                    <Link to={`/issues/${issue.id}`} onClick={onClose}>
                      {issue.code}
                    </Link>
                  </td>
                  <td className="wrap">{issue.title}</td>
                  <td>
                    <SeverityTag severity={issue.severity} />
                  </td>
                  <td>
                    <StatusTag status={issue.status} />
                  </td>
                  <td>{formatDateTime(issue.deadline)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-block">本次检查无不符合项，未生成整改事项</div>
      )}

      {check.remark ? (
        <>
          <div className="section-title" style={{ marginTop: 16 }}>
            检查备注
          </div>
          <p className="muted" style={{ margin: '4px 0 0' }}>
            {check.remark}
          </p>
        </>
      ) : null}
    </Modal>
  );
}
