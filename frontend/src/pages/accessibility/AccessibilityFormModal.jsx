import { useEffect, useMemo, useState } from 'react';

import { accessibilityApi } from '../../api/accessibility.js';
import { metaApi } from '../../api/meta.js';
import Field from '../../components/Field.jsx';
import Modal from '../../components/Modal.jsx';
import { StatusTag } from '../../components/Tags.jsx';
import { useToast } from '../../components/Toast.jsx';
import { useDictionaries } from '../../hooks/useDictionaries.js';
import { calcScore, countByVerdict, judgeItem, resultOf } from '../../utils/accessibility.js';
import { toDateTimeInput } from '../../utils/format.js';

const DEFAULT_FACILITIES = ['扶手', '坡道', '盲道', '专用间'];
const DEFAULT_CONDITIONS = ['完好', '轻微破损', '严重损坏'];

export default function AccessibilityFormModal({ defaultRestroomId, onClose, onSaved }) {
  const { dictionaries } = useDictionaries();
  const toast = useToast();
  const [options, setOptions] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    restroom_id: defaultRestroomId ? Number(defaultRestroomId) : '',
    inspector: '',
    check_time: toDateTimeInput(),
    remark: '',
  });
  const [items, setItems] = useState([]);

  const facilities = dictionaries?.accessibility_facilities || DEFAULT_FACILITIES;
  const conditions = dictionaries?.accessibility_conditions || DEFAULT_CONDITIONS;

  useEffect(() => {
    metaApi
      .restroomOptions()
      .then(setOptions)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    setItems(facilities.map((facility) => ({ facility, configured: true, condition: '完好', remark: '' })));
  }, [dictionaries]); // eslint-disable-line react-hooks/exhaustive-deps

  const score = useMemo(() => calcScore(items), [items]);
  const result = resultOf(items);
  const counts = countByVerdict(items);

  const updateItem = (index, patch) => {
    setItems((prev) => prev.map((item, idx) => (idx === index ? { ...item, ...patch } : item)));
  };

  const markAll = (configured, condition) => {
    setItems((prev) => prev.map((item) => ({ ...item, configured, condition })));
  };

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
        check_time: form.check_time ? new Date(form.check_time).toISOString() : null,
        remark: form.remark || null,
        items: items.map((item) => ({
          facility: item.facility,
          configured: item.configured,
          condition: item.configured ? item.condition : null,
          remark: item.remark || null,
        })),
      });
      const generated = created.issues?.length || 0;
      toast.success(
        generated > 0
          ? `检查已登记（${created.result}），不符合项已生成 ${generated} 项待整改事项`
          : `检查已登记（${created.result}），无需整改`,
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
      title="新增无障碍专项检查"
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
            value={form.check_time}
            onChange={(event) => setForm((prev) => ({ ...prev, check_time: event.target.value }))}
          />
        </Field>
      </form>

      <div className="card-title">
        <div className="inline">
          <h3>设施登记（按检查标准自动判定）</h3>
          <span className="tag tag-primary">达标率 {score.toFixed(1)}%</span>
          <StatusTag status={result} />
          <span className="muted">
            符合 {counts.compliant} / 部分符合 {counts.partial} / 不符合 {counts.failed}
          </span>
        </div>
        <div className="inline">
          <button type="button" className="btn btn-sm" onClick={() => markAll(true, '完好')}>
            全部完好
          </button>
        </div>
      </div>

      <div className="facility-grid">
        {items.map((item, index) => {
          const verdict = judgeItem(item);
          return (
            <div className={`facility-item${verdict === '不符合' ? ' is-failed' : ''}`} key={item.facility}>
              <div className="head">
                <strong>{item.facility}</strong>
                <StatusTag status={verdict} />
              </div>
              <div className="line">
                <span className="muted">配置情况</span>
                <select
                  value={item.configured ? '1' : '0'}
                  onChange={(event) =>
                    updateItem(index, { configured: event.target.value === '1' })
                  }
                >
                  <option value="1">已配置</option>
                  <option value="0">未配置</option>
                </select>
              </div>
              <div className="line">
                <span className="muted">完好状态</span>
                <select
                  value={item.condition}
                  disabled={!item.configured}
                  onChange={(event) => updateItem(index, { condition: event.target.value })}
                >
                  {conditions.map((condition) => (
                    <option key={condition}>{condition}</option>
                  ))}
                </select>
              </div>
              <input
                className="field-input"
                placeholder="备注（可选）"
                value={item.remark || ''}
                onChange={(event) => updateItem(index, { remark: event.target.value })}
              />
            </div>
          );
        })}
      </div>

      <div className="alert alert-info" style={{ marginTop: 12 }}>
        判定标准：未配置或严重损坏 → 不符合；轻微破损 → 部分符合；完好 → 符合。不符合项提交后将自动生成待整改事项。
      </div>

      <Field label="检查备注" full>
        <textarea
          rows="2"
          value={form.remark}
          onChange={(event) => setForm((prev) => ({ ...prev, remark: event.target.value }))}
          placeholder="整体情况说明，可记录现场照片编号、遗留问题等"
        />
      </Field>
    </Modal>
  );
}
