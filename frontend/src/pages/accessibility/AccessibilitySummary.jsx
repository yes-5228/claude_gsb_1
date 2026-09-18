import { Link } from 'react-router-dom';

import { accessibilityApi } from '../../api/accessibility.js';
import DataTable from '../../components/DataTable.jsx';
import StatCard from '../../components/StatCard.jsx';
import { ConformityTag, RatePill } from '../../components/Tags.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { formatDateTime } from '../../utils/format.js';

export default function AccessibilitySummary() {
  const { data, loading, error } = useAsync(() => accessibilityApi.summary(), []);
  const overall = data?.overall;

  return (
    <>
      {error ? <div className="alert alert-error">{error.message}</div> : null}
      {loading && !data ? <div className="loading-block">汇总数据加载中…</div> : null}

      {overall ? (
        <>
          <div className="stat-grid">
            <StatCard
              label="累计检查"
              value={overall.inspection_total}
              unit="次"
              foot={`覆盖 ${overall.restroom_covered} 座公厕`}
            />
            <StatCard
              label="平均达标率"
              value={overall.avg_rate.toFixed(1)}
              unit="%"
              tone={overall.avg_rate >= 80 ? 'primary' : overall.avg_rate >= 60 ? 'warning' : 'danger'}
              foot="符合计 1、部分符合计 0.5 折算"
            />
            <StatCard
              label="登记设施项"
              value={overall.item_total}
              unit="项"
              tone="info"
              foot={`符合 ${overall.compliant_items} · 部分符合 ${overall.partial_items} · 不符合 ${overall.non_compliant_items}`}
            />
            <StatCard
              label="未闭环整改事项"
              value={overall.open_issue_count}
              unit="条"
              tone={overall.open_issue_count > 0 ? 'danger' : 'primary'}
              foot="由不符合项自动生成"
            />
          </div>

          <section className="card">
            <div className="card-title">
              <h3>按区域汇总</h3>
              <span className="hint">达标率取区域内各公厕最近一次检查的平均，低达标率优先展示</span>
            </div>
            <DataTable
              loading={false}
              rows={data.districts}
              emptyText="暂无区域数据"
              rowKey={(row) => row.district}
              columns={[
                { key: 'district', title: '区域' },
                { key: 'restroom_count', title: '公厕数' },
                { key: 'inspected_count', title: '已检查' },
                {
                  key: 'compliant_count',
                  title: '符合 / 部分 / 不符合',
                  render: (row) =>
                    `${row.compliant_count} / ${row.partial_count} / ${row.non_compliant_count}`,
                },
                {
                  key: 'avg_rate',
                  title: '区域达标率',
                  render: (row) => <RatePill rate={row.avg_rate} />,
                },
                {
                  key: 'open_issue_count',
                  title: '未闭环整改',
                  render: (row) =>
                    row.open_issue_count > 0 ? (
                      <span className="tag tag-danger">{row.open_issue_count} 条</span>
                    ) : (
                      <span className="muted">0</span>
                    ),
                },
              ]}
            />
          </section>

          <section className="card">
            <div className="card-title">
              <h3>按公厕汇总</h3>
              <span className="hint">按最近一次检查达标率升序，未检查的排在最后</span>
            </div>
            <DataTable
              loading={false}
              rows={data.restrooms}
              emptyText="暂无公厕数据"
              rowKey={(row) => row.restroom_id}
              columns={[
                {
                  key: 'name',
                  title: '公厕',
                  render: (row) => (
                    <Link to={`/restrooms/${row.restroom_id}`}>
                      {row.code} {row.name}
                    </Link>
                  ),
                },
                { key: 'district', title: '区域' },
                { key: 'inspection_count', title: '检查次数' },
                {
                  key: 'latest_inspect_time',
                  title: '最近检查',
                  render: (row) =>
                    row.latest_inspect_time ? formatDateTime(row.latest_inspect_time) : '未检查',
                },
                {
                  key: 'latest_conformity',
                  title: '最新判定',
                  render: (row) =>
                    row.latest_conformity ? (
                      <ConformityTag conformity={row.latest_conformity} />
                    ) : (
                      <span className="muted">-</span>
                    ),
                },
                {
                  key: 'latest_rate',
                  title: '最新达标率',
                  render: (row) => <RatePill rate={row.latest_rate} />,
                },
                {
                  key: 'avg_rate',
                  title: '平均达标率',
                  render: (row) => <RatePill rate={row.avg_rate} />,
                },
                {
                  key: 'open_issue_count',
                  title: '未闭环整改',
                  render: (row) =>
                    row.open_issue_count > 0 ? (
                      <span className="tag tag-danger">{row.open_issue_count} 条</span>
                    ) : (
                      <span className="muted">0</span>
                    ),
                },
              ]}
            />
          </section>
        </>
      ) : null}
    </>
  );
}
