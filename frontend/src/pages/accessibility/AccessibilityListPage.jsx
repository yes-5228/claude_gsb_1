import { useState } from 'react';
import { Link } from 'react-router-dom';

import { accessibilityApi } from '../../api/accessibility.js';
import { restroomApi } from '../../api/restrooms.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import StatCard from '../../components/StatCard.jsx';
import { ScorePill, StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDateTime } from '../../utils/format.js';
import AccessibilityDetailModal from './AccessibilityDetailModal.jsx';
import AccessibilityFormModal from './AccessibilityFormModal.jsx';

const DEFAULT_FILTERS = {
  keyword: '',
  district: '',
  result: '',
  date_from: '',
  date_to: '',
};

export default function AccessibilityListPage() {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [showForm, setShowForm] = useState(false);
  const [active, setActive] = useState(null);

  const list = useListQuery((params) => accessibilityApi.list(params), DEFAULT_FILTERS, 10);
  const summary = useAsync(() => accessibilityApi.summary(), []);
  const { data: districts } = useAsync(() => restroomApi.districts(), []);

  const reloadAll = () => {
    list.reload();
    summary.reload();
  };

  const remove = async (row) => {
    if (!window.confirm('确认删除该条检查记录？已生成的整改事项会保留并解除关联。')) return;
    try {
      await accessibilityApi.remove(row.id);
      toast.success('删除成功');
      reloadAll();
    } catch (err) {
      toast.error(err.message);
    }
  };

  const overview = summary.data;

  return (
    <>
      <PageHeader
        title="无障碍设施专项检查"
        description="登记扶手、坡道、盲道、专用间的配置与完好状态，自动判定达标情况并生成整改事项"
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
            + 新增专项检查
          </button>
        }
      />
      <div className="content">
        <div className="stat-grid">
          <StatCard
            label="累计检查次数"
            value={overview?.total_checks ?? '-'}
            unit="次"
            foot={`覆盖 ${overview?.checked_restrooms ?? 0}/${overview?.total_restrooms ?? 0} 座公厕`}
          />
          <StatCard
            label="平均达标率"
            value={overview ? overview.avg_score.toFixed(1) : '-'}
            unit="%"
            tone="info"
            foot={`达标 ${overview?.pass_checks ?? 0} · 部分达标 ${overview?.partial_checks ?? 0} · 不达标 ${overview?.failed_checks ?? 0}`}
          />
          <StatCard
            label="累计不符合项"
            value={overview?.failed_items ?? '-'}
            unit="项"
            tone="warning"
            foot={`符合 ${overview?.compliant_items ?? 0} · 部分符合 ${overview?.partial_items ?? 0}`}
          />
          <StatCard
            label="待整改事项"
            value={overview?.open_issue_count ?? '-'}
            unit="项"
            tone="danger"
            foot="不符合项自动生成，闭环后不计入"
          />
        </div>

        <section className="card">
          <div className="card-title">
            <h3>区域达标率汇总</h3>
            <span className="hint">按各公厕最近一次检查结论统计，达标率 = 达标公厕数 / 区域公厕总数</span>
          </div>
          <DataTable
            loading={summary.loading}
            error={summary.error}
            rows={overview?.districts ?? []}
            emptyText="暂无区域数据"
            rowKey={(row) => row.district}
            columns={[
              { key: 'district', title: '区域' },
              { key: 'restroom_count', title: '公厕数' },
              { key: 'inspected_count', title: '已检查' },
              { key: 'uninspected_count', title: '未检查' },
              {
                key: 'compliant_count',
                title: '达标 / 部分 / 不达标',
                render: (row) => (
                  <span className="inline">
                    <span className="tag tag-success">{row.compliant_count}</span>
                    <span className="tag tag-warning">{row.partial_count}</span>
                    <span className="tag tag-danger">{row.failed_count}</span>
                  </span>
                ),
              },
              {
                key: 'pass_rate',
                title: '达标率',
                render: (row) => (
                  <div className="rate-cell">
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${row.pass_rate}%` }} />
                    </div>
                    <span className="bar-value">{row.pass_rate.toFixed(1)}%</span>
                  </div>
                ),
              },
              { key: 'avg_score', title: '平均达标率', render: (row) => `${row.avg_score.toFixed(1)}%` },
              { key: 'open_issue_count', title: '待整改事项' },
            ]}
          />
        </section>

        <section className="card">
          <div className="card-title">
            <h3>公厕达标情况</h3>
            <span className="hint">取每座公厕最近一次专项检查结论</span>
          </div>
          <DataTable
            loading={summary.loading}
            error={summary.error}
            rows={overview?.restrooms ?? []}
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
              {
                key: 'last_check_time',
                title: '最近检查',
                render: (row) => (row.last_check_time ? formatDateTime(row.last_check_time) : '-'),
              },
              {
                key: 'last_result',
                title: '最近结论',
                render: (row) => <StatusTag status={row.last_result} />,
              },
              {
                key: 'last_score',
                title: '达标率',
                render: (row) =>
                  row.last_score === null || row.last_score === undefined ? (
                    '-'
                  ) : (
                    <ScorePill score={row.last_score} />
                  ),
              },
              { key: 'check_count', title: '检查次数' },
              {
                key: 'open_issue_count',
                title: '待整改事项',
                render: (row) =>
                  row.open_issue_count > 0 ? (
                    <span className="tag tag-danger">{row.open_issue_count}</span>
                  ) : (
                    0
                  ),
              },
            ]}
          />
        </section>

        <section className="card">
          <div className="card-title">
            <h3>检查记录</h3>
          </div>
          <div className="filter-bar">
            <Field label="关键字" full>
              <input
                value={list.filters.keyword}
                placeholder="公厕名称 / 检查人 / 备注"
                onChange={(event) => list.updateFilter('keyword', event.target.value)}
              />
            </Field>
            <Field label="所属区域">
              <select
                value={list.filters.district}
                onChange={(event) => list.updateFilter('district', event.target.value)}
              >
                <option value="">全部</option>
                {(districts || []).map((item) => (
                  <option key={item}>{item}</option>
                ))}
              </select>
            </Field>
            <Field label="检查结论">
              <select
                value={list.filters.result}
                onChange={(event) => list.updateFilter('result', event.target.value)}
              >
                <option value="">全部</option>
                {(dictionaries?.accessibility_results || ['达标', '部分达标', '不达标']).map(
                  (item) => (
                    <option key={item}>{item}</option>
                  ),
                )}
              </select>
            </Field>
            <Field label="开始日期">
              <input
                type="date"
                value={list.filters.date_from}
                onChange={(event) => list.updateFilter('date_from', event.target.value)}
              />
            </Field>
            <Field label="结束日期">
              <input
                type="date"
                value={list.filters.date_to}
                onChange={(event) => list.updateFilter('date_to', event.target.value)}
              />
            </Field>
            <button type="button" className="btn" onClick={list.resetFilters}>
              重置
            </button>
          </div>

          <DataTable
            loading={list.loading}
            error={list.error}
            rows={list.items}
            emptyText="暂无检查记录"
            columns={[
              {
                key: 'check_time',
                title: '检查时间',
                render: (row) => formatDateTime(row.check_time),
              },
              {
                key: 'restroom',
                title: '公厕',
                render: (row) =>
                  row.restroom ? (
                    <Link to={`/restrooms/${row.restroom.id}`}>{row.restroom.name}</Link>
                  ) : (
                    '-'
                  ),
              },
              { key: 'district', title: '区域', render: (row) => row.restroom?.district ?? '-' },
              { key: 'inspector', title: '检查人' },
              {
                key: 'verdicts',
                title: '判定（符合/部分/不符合）',
                render: (row) => (
                  <span className="inline">
                    <span className="tag tag-success">{row.compliant_count}</span>
                    <span className="tag tag-warning">{row.partial_count}</span>
                    <span className="tag tag-danger">{row.failed_count}</span>
                  </span>
                ),
              },
              { key: 'score', title: '达标率', render: (row) => <ScorePill score={row.score} /> },
              { key: 'result', title: '结论', render: (row) => <StatusTag status={row.result} /> },
              {
                key: 'issues',
                title: '整改事项',
                render: (row) =>
                  row.issues?.length ? (
                    <span className="tag tag-warning">{row.issues.length} 项</span>
                  ) : (
                    '-'
                  ),
              },
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <div className="inline">
                    <button type="button" className="btn-link" onClick={() => setActive(row)}>
                      详情
                    </button>
                    <button type="button" className="btn-link danger" onClick={() => remove(row)}>
                      删除
                    </button>
                  </div>
                ),
              },
            ]}
          />
          <Pagination meta={list.meta} onPageChange={list.setPage} />
        </section>
      </div>

      {showForm ? (
        <AccessibilityFormModal onClose={() => setShowForm(false)} onSaved={reloadAll} />
      ) : null}

      {active ? (
        <AccessibilityDetailModal check={active} onClose={() => setActive(null)} />
      ) : null}
    </>
  );
}
