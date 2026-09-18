import { useEffect, useMemo, useState } from 'react';

import { accessibilityApi } from '../../api/accessibility.js';
import { metaApi } from '../../api/meta.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { ConformityTag, RatePill } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { summarizeItems } from '../../utils/accessibility.js';
import { toDateTimeInput } from '../../utils/format.js';

const CONDITIONS = ['完好', '轻微破损', '严重损坏'];

export default function AccessibilityFormModal({ defaultRestroomId, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [options, setOptions] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    restroom_id: defaultRestroomId ? Number(defaultRestroomId) : '',
    inspector: '',
    inspect_time: toDateTimeInput(),
    remark: '',
  });
  const [items, setItems] = useState([]);

  useEffect(() => {
    metaApi
      .restroomOptions()
      .then(setOptions)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    const template = dictionaries?.accessibility_check_items || [];
    setItems(
      template.map((spec) => ({
        key: spec.key,
        name: spec.name,
        standard: spec.standard,
        configured: true,
        condition: '完好',
        remark: '',
      })),
    );
  }, [dictionaries]);

  const summary = useMemo(() => summarizeItems(items), [items]);

  const patchItem = (index, patch) => {
    setItems((prev) => prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item)));
  };

  const fillAll = (configured, condition) =>
    setItems((prev) => prev.map((item) => ({ ...item, configured, condition })));

  const submit = async (event) => {
    event.preventDefault();
    if (!form.restroom_id) {
      setError('请选择被检查的公厕');
      return;
    }
    if (!form.inspector.trim()) {
      setError('请填写检查人');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await accessibilityApi.create({
        restroom_id: Number(form.restroom_id),
        inspector: form.inspector.trim(),
        inspect_time: form.inspect_time ? new Date(form.inspect_time).toISOString() : null,
        remark: form.remark || null,
        items: items.map((item) => ({
          key: item.key,
          configured: item.configured,
          condition: item.configured ? item.condition : null,
          remark: item.remark || null,
        })),
      });
      const issueCount = created.issues?.length || 0;
      toast.success(
        issueCount ? `检查已登记，自动生成 ${issueCount} 条待整改事项` : '检查已登记，全部符合',
      );
      onSaved();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      title="登记无障碍设施专项检查"
      onClose={onClose}
      width={920}
      footer={
        <>
          <button type="button" className="btn" onClick={onClose}>
            取消
          </button>
          <button
            type="submit"
            form="accessibility-form"
            className="btn btn-primary"
            disabled={saving}
          >
            {saving ? '提交中…' : '提交检查'}
          </button>
        </>
      }
    >
      {error ? <div className="alert alert-error">{error}</div> : null}
      <form id="accessibility-form" onSubmit={submit} className="form-grid">
        <Field label="被检查公厕 *">
          <select
            value={form.restroom_id}
            onChange={(event) => setForm((prev) => ({ ...prev, restroom_id: event.target.value }))}
          >
            <option value="">请选择公厕</option>
            {options.map((option) => (
              <option key={option.id} value={option.id}>
                {option.code} {option.name}（{option.district}）
              </option>
            ))}
          </select>
        </Field>
        <Field label="检查人 *">
          <input
            value={form.inspector}
            onChange={(event) => setForm((prev) => ({ ...prev, inspector: event.target.value }))}
            placeholder="请输入检查人姓名"
          />
        </Field>
        <Field label="检查时间">
          <input
            type="datetime-local"
            value={form.inspect_time}
            onChange={(event) => setForm((prev) => ({ ...prev, inspect_time: event.target.value }))}
          />
        </Field>
      </form>

      <div className="card-title">
        <div className="inline">
          <h3>设施登记（按检查标准判定）</h3>
          <span className="muted" style={{ fontSize: 12.5 }}>
            达标率
          </span>
          <RatePill rate={summary.rate} />
          <ConformityTag conformity={summary.conformity} />
          {summary.nonCompliant ? (
            <span className="tag tag-danger">{summary.nonCompliant} 项将生成待整改事项</span>
          ) : null}
        </div>
        <div className="inline">
          <button type="button" className="btn btn-sm" onClick={() => fillAll(true, '完好')}>
            全部完好
          </button>
        </div>
      </div>

      <div className="facility-grid">
        {items.map((item, index) => {
          const conformity = summary.judged[index]?.conformity;
          return (
            <div
              className={`facility-card${conformity === '不符合' ? ' is-fail' : conformity === '部分符合' ? ' is-partial' : ''}`}
              key={item.key}
            >
              <div className="facility-head">
                <strong>{item.name}</strong>
                <ConformityTag conformity={conformity} />
              </div>
              <div className="facility-standard">检查标准：{item.standard}</div>
              <div className="facility-row">
                <span className="muted">配置情况</span>
                <div className="inline">
                  <label className="checkbox-row">
                    <input
                      type="radio"
                      name={`configured-${item.key}`}
                      checked={item.configured}
                      onChange={() =>
                        patchItem(index, { configured: true, condition: item.condition || '完好' })
                      }
                    />
                    已配置
                  </label>
                  <label className="checkbox-row">
                    <input
                      type="radio"
                      name={`configured-${item.key}`}
                      checked={!item.configured}
                      onChange={() => patchItem(index, { configured: false })}
                    />
                    未配置
                  </label>
                </div>
              </div>
              <div className="facility-row">
                <span className="muted">完好状态</span>
                <select
                  value={item.condition || '完好'}
                  disabled={!item.configured}
                  onChange={(event) => patchItem(index, { condition: event.target.value })}
                >
                  {(dictionaries?.accessibility_conditions || CONDITIONS).map((condition) => (
                    <option key={condition}>{condition}</option>
                  ))}
                </select>
              </div>
              <input
                className="field-input facility-remark"
                placeholder="单项备注（可选）"
                value={item.remark || ''}
                onChange={(event) => patchItem(index, { remark: event.target.value })}
              />
            </div>
          );
        })}
      </div>

      <Field label="检查备注" full>
        <textarea
          rows="2"
          value={form.remark}
          onChange={(event) => setForm((prev) => ({ ...prev, remark: event.target.value }))}
          placeholder="整体情况说明，不符合项的整改建议可在此描述"
        />
      </Field>
    </Modal>
  );
}
