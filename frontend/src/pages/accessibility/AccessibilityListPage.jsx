import { useState } from 'react';
import { Link } from 'react-router-dom';

import { accessibilityApi } from '../../api/accessibility.js';
import { restroomApi } from '../../api/restrooms.js';
import DataTable from '../../components/DataTable.jsx';
import Field from '../../components/Field.jsx';
import PageHeader from '../../components/PageHeader.jsx';
import Pagination from '../../components/Pagination.jsx';
import { ConformityTag, RatePill } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useAsync } from '../../hooks/useAsync.js';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { useListQuery } from '../../hooks/useListQuery.js';
import { formatDateTime } from '../../utils/format.js';
import AccessibilityDetailModal from './AccessibilityDetailModal.jsx';
import AccessibilityFormModal from './AccessibilityFormModal.jsx';
import AccessibilitySummary from './AccessibilitySummary.jsx';

const DEFAULT_FILTERS = {
  keyword: '',
  district: '',
  conformity: '',
  date_from: '',
  date_to: '',
};

const TABS = [
  { key: 'records', label: '检查记录' },
  { key: 'summary', label: '达标率汇总' },
];

export default function AccessibilityListPage() {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [tab, setTab] = useState('records');
  const [showForm, setShowForm] = useState(false);
  const [active, setActive] = useState(null);

  const list = useListQuery((params) => accessibilityApi.list(params), DEFAULT_FILTERS, 10);
  const { data: districts } = useAsync(() => restroomApi.districts(), []);

  const remove = async (row) => {
    if (!window.confirm('确认删除该条无障碍检查记录？已生成的整改事项不会被删除。')) return;
    try {
      await accessibilityApi.remove(row.id);
      toast.success('删除成功');
      list.reload();
    } catch (err) {
      toast.error(err.message);
    }
  };

  return (
    <>
      <PageHeader
        title="无障碍设施专项检查"
        description="登记扶手、坡道、盲道、专用间的配置与完好状态，按检查标准判定符合性，不符合项自动生成待整改事项"
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
            + 登记无障碍检查
          </button>
        }
      />
      <div className="content">
        <div className="tab-bar">
          {TABS.map((item) => (
            <button
              key={item.key}
              type="button"
              className={`tab-item${tab === item.key ? ' active' : ''}`}
              onClick={() => setTab(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>

        {tab === 'summary' ? <AccessibilitySummary /> : null}

        {tab === 'records' ? (
          <>
            <section className="card">
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
                <Field label="总体判定">
                  <select
                    value={list.filters.conformity}
                    onChange={(event) => list.updateFilter('conformity', event.target.value)}
                  >
                    <option value="">全部</option>
                    {(dictionaries?.accessibility_conformity || ['符合', '部分符合', '不符合']).map(
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
            </section>

            <section className="card">
              <DataTable
                loading={list.loading}
                error={list.error}
                rows={list.items}
                emptyText="暂无无障碍检查记录"
                columns={[
                  {
                    key: 'inspect_time',
                    title: '检查时间',
                    render: (row) => formatDateTime(row.inspect_time),
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
                    key: 'counts',
                    title: '符合/部分/不符合',
                    render: (row) =>
                      `${row.compliant_count} / ${row.partial_count} / ${row.non_compliant_count}`,
                  },
                  {
                    key: 'rate',
                    title: '达标率',
                    render: (row) => <RatePill rate={row.rate} />,
                  },
                  {
                    key: 'conformity',
                    title: '总体判定',
                    render: (row) => <ConformityTag conformity={row.conformity} />,
                  },
                  {
                    key: 'issues',
                    title: '待整改事项',
                    render: (row) =>
                      row.issues?.length ? (
                        <span className="tag tag-danger">{row.issues.length} 条</span>
                      ) : (
                        <span className="muted">0</span>
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
                        <button
                          type="button"
                          className="btn-link danger"
                          onClick={() => remove(row)}
                        >
                          删除
                        </button>
                      </div>
                    ),
                  },
                ]}
              />
              <Pagination meta={list.meta} onPageChange={list.setPage} />
            </section>
          </>
        ) : null}
      </div>

      {showForm ? (
        <AccessibilityFormModal onClose={() => setShowForm(false)} onSaved={list.reload} />
      ) : null}

      {active ? (
        <AccessibilityDetailModal inspection={active} onClose={() => setActive(null)} />
      ) : null}
    </>
  );
}
