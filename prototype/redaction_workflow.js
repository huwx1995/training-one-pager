// Redaction decisions, review, and custom term controls.
function deepClone(value) {
  return JSON.parse(JSON.stringify(value));
}

function redactionSnapshot() {
  return { candidates: deepClone(sensitiveCandidates), imageRegions: deepClone(imageRegions) };
}

function updateHistoryButtons() {
  undoBtn.disabled = !undoStack.length;
  redoBtn.disabled = !redoStack.length;
}

function logRedactionAction(action, details = {}) {
  const entry = {
    id: `action-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`,
    action, timestamp: Math.floor(Date.now() / 1000),
    operator: redactionOperator?.value.trim() || "未填写",
    ...details,
  };
  redactionActionLog.push(entry);
  if (redactionActionLog.length > 200) redactionActionLog.shift();
  return entry.id;
}

function recordHistory(action = "修改脱敏项") {
  undoStack.push(redactionSnapshot());
  if (undoStack.length > 100) undoStack.shift();
  redoStack = [];
  logRedactionAction(action);
  updateHistoryButtons();
}

function restoreSnapshot(snapshot, message) {
  sensitiveCandidates = deepClone(snapshot.candidates);
  imageRegions = deepClone(snapshot.imageRegions);
  invalidateRedaction(message);
  renderCandidates();
  updateRedactionStats();
}

function undoRedaction() {
  if (!undoStack.length) return;
  const relatedActionId = redactionActionLog.at(-1)?.id || "";
  redoStack.push(redactionSnapshot());
  restoreSnapshot(undoStack.pop(), "已撤销上一步操作，请重新确认脱敏。");
  logRedactionAction("撤销操作", { related_action_id: relatedActionId });
  updateHistoryButtons();
}

function redoRedaction() {
  if (!redoStack.length) return;
  const relatedActionId = redactionActionLog.at(-1)?.id || "";
  undoStack.push(redactionSnapshot());
  restoreSnapshot(redoStack.pop(), "已重做上一步操作，请重新确认脱敏。");
  logRedactionAction("重做操作", { related_action_id: relatedActionId });
  updateHistoryButtons();
}

function occurrenceStatus(occurrence) {
  if (occurrence.status) return occurrence.status;
  return occurrence.selected === false ? "cancelled" : "pending";
}

function setOccurrenceStatus(occurrence, status) {
  occurrence.status = status;
  occurrence.selected = status !== "cancelled";
  occurrence.updated_at = Math.floor(Date.now() / 1000);
}

function refreshCandidateState(candidate) {
  candidate.selected = candidate.occurrences.some((item) => occurrenceStatus(item) !== "cancelled");
  const statuses = new Set(candidate.occurrences.map(occurrenceStatus));
  candidate.status = statuses.size === 1 ? [...statuses][0] : "mixed";
  candidate.group_state = statuses.size > 1 ? "mixed"
    : statuses.has("cancelled") ? "excluded_all"
      : statuses.has("confirmed") ? "confirmed_all" : "pending";
}

function allImageAssets() {
  return [...(currentDocument?.image_assets || []), ...(currentDocument?.supplemental_image_assets || [])];
}

function visibleCandidates() {
  const type = redactionFilter.value;
  const sensitivity = confidenceFilter.value;
  const status = statusFilter.value;
  const file = fileFilter.value;
  return sensitiveCandidates.filter((candidate) => {
    const matchingOccurrences = candidate.occurrences.filter((occurrence) =>
      (status === "all" || occurrenceStatus(occurrence) === status)
      && (file === "all" || occurrence.file_name === file));
    return (type === "all" || candidate.category === type)
      && (sensitivity === "all" || candidate.sensitivity === sensitivity)
      && Boolean(matchingOccurrences.length);
  });
}

function updateFileFilter() {
  const selected = fileFilter.value;
  const files = [...new Set(allOriginalSegments().map((item) => item.file_name).filter(Boolean))];
  fileFilter.innerHTML = '<option value="all">全部文件</option>'
    + files.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
  if (files.includes(selected)) fileFilter.value = selected;
}

function updateRedactionStats() {
  const markedOccurrences = sensitiveCandidates.reduce(
    (sum, candidate) => sum + candidate.occurrences.filter((item) => occurrenceStatus(item) !== "cancelled").length,
    0,
  );
  const activeImageRegions = imageRegions.filter((region) => region.status !== "cancelled").length;
  const summary = `已标记文字 ${markedOccurrences} 处 · 图片框 ${activeImageRegions} 个`;
  redactionStats.textContent = summary;
  workspaceRedactionCount.textContent = summary;
  const enabled = Boolean(currentDocument);
  const hasVisible = enabled && visibleCandidates().length > 0;
  confirmVisibleBtn.disabled = !hasVisible;
  cancelVisibleBtn.disabled = !hasVisible;
  restoreVisibleBtn.disabled = !enabled;
  confirmRedactionBtn.disabled = !enabled;
  confirmRedactionBtn.title = enabled ? "所有黄色文字和红色图片框都会被脱敏" : "请先抽取材料";
}

function allOriginalSegments() {
  return [...(currentDocument?.segments || []), ...supplementalOriginalSegments];
}

function allMaskedSegments() {
  return [...(currentDocument?.masked_segments || []), ...supplementalMaskedSegments];
}

function splitMaskedSegments(segments) {
  const primaryIds = new Set((currentDocument?.segments || []).map((item) => item.id));
  currentDocument.masked_segments = segments.filter((item) => primaryIds.has(item.id));
  supplementalMaskedSegments = segments.filter((item) => !primaryIds.has(item.id));
  qaExtraSources = supplementalMaskedSegments;
}

function invalidateRedaction(message = "脱敏选择已修改，请重新确认。") {
  redactionConfirmed = false;
  confirmationToken = "";
  showMaskedPreview = false;
  if (currentDocument) currentDocument.masked_segments = [];
  supplementalMaskedSegments = [];
  qaExtraSources = [];
  currentOnePager = null;
  contactCandidates = [];
  editContactBtn.disabled = true;
  decisionManifest = null;
  exportDecisionCsvBtn.disabled = true;
  exportDecisionJsonBtn.disabled = true;
  generateBtn.disabled = true;
  downloadRedactedBtn.disabled = true;
  togglePreviewBtn.textContent = "查看脱敏效果";
  redactionStatus.textContent = message;
  generateStatus.textContent = "请先确认脱敏结果。";
  renderOnePager();
  renderSources();
  updateRedactionStats();
}

function preserveCandidateSelections(nextCandidates) {
  const oldCandidates = new Map(sensitiveCandidates.map((item) => [item.id, item]));
  return nextCandidates.map((candidate) => {
    const old = oldCandidates.get(candidate.id);
    if (!old) return candidate;
    const oldOccurrences = new Map((old.occurrences || []).map((item) => [item.id, item.selected]));
    const oldStatuses = new Map((old.occurrences || []).map((item) => [item.id, occurrenceStatus(item)]));
    candidate.occurrences.forEach((item) => {
      if (oldOccurrences.has(item.id)) item.selected = oldOccurrences.get(item.id);
      if (oldStatuses.has(item.id)) item.status = oldStatuses.get(item.id);
      else item.status = item.status || "pending";
    });
    refreshCandidateState(candidate);
    return candidate;
  });
}

async function detectSensitive(manualValue = "", manualType = "custom") {
  const manualEntries = sensitiveCandidates
    .filter((item) => item.manual && !managedCustomTerms.has(item.value))
    .map((item) => ({ value: item.value, type: item.type }));
  for (const value of [...savedCustomTerms, ...sessionCustomTerms]) {
    manualEntries.push({ value, type: "custom" });
  }
  if (manualValue) manualEntries.push({ value: manualValue, type: manualType });
  const response = await fetch("/api/detect-sensitive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segments: allOriginalSegments(), manual_entries: manualEntries }),
  });
  const payload = await response.json();
  if (!payload.ok) throw new Error(payload.error || "敏感信息识别失败");
  sensitiveCandidates = preserveCandidateSelections(payload.candidates || []);
  sensitiveCandidates.forEach((candidate) => {
    candidate.occurrences.forEach((occurrence) => {
      occurrence.status = occurrence.selected === false || occurrence.status === "cancelled" ? "cancelled" : "confirmed";
      occurrence.selected = occurrence.status !== "cancelled";
    });
    refreshCandidateState(candidate);
  });
  renderCandidates();
}

function readSavedCustomTerms() {
  try {
    const values = JSON.parse(localStorage.getItem(customTermsStorageKey) || "[]");
    return Array.isArray(values) ? values.filter((value) => typeof value === "string") : [];
  } catch { return []; }
}

function renderCustomTerms() {
  const terms = [...new Set([...savedCustomTerms, ...sessionCustomTerms])];
  customTermsList.innerHTML = terms.map((value) => `<span class="custom-redaction-term">${escapeHtml(value)} <button type="button" data-custom-term="${escapeHtml(value)}" aria-label="删除 ${escapeHtml(value)}">×</button></span>`).join("") || "<span>尚未添加词语</span>";
}

async function refreshCustomTerms(message) {
  if (currentDocument && parsingConfirmed) {
    await detectSensitive();
    invalidateRedaction("常用脱敏词语已更改，请重新确认。");
    renderSources();
  }
  renderCustomTerms();
  customTermsStatus.textContent = message;
}

async function addCustomTerms() {
  const values = [...new Set(customTermsInput.value.split(/[\n;；]+/).map((value) => value.trim()).filter(Boolean))];
  if (!values.length) { customTermsStatus.textContent = "请先输入词语，每行一个。"; return; }
  if (values.some((value) => value.length < 2 || value.length > 50)) { customTermsStatus.textContent = "每个词语应为 2—50 个字符。"; return; }
  if (values.some((value) => ["银行", "客户", "产品", "业务", "贷款", "机构", "公司", "经理"].includes(value))) { customTermsStatus.textContent = "包含过于通用的词语，请输入更具体的名称。"; return; }
  if (new Set([...savedCustomTerms, ...sessionCustomTerms, ...values]).size > 100) { customTermsStatus.textContent = "最多保存 100 个词语。"; return; }
  const target = saveCustomTerms.checked ? savedCustomTerms : sessionCustomTerms;
  for (const value of values) if (!target.includes(value)) target.push(value);
  for (const value of values) managedCustomTerms.add(value);
  if (saveCustomTerms.checked) localStorage.setItem(customTermsStorageKey, JSON.stringify(savedCustomTerms));
  customTermsInput.value = "";
  try { await refreshCustomTerms(`已添加 ${values.length} 个词语。`); }
  catch (error) { customTermsStatus.textContent = friendlyError(error); }
}

function candidateSelectionState(candidate) {
  const selected = candidate.occurrences.filter((item) => occurrenceStatus(item) !== "cancelled").length;
  return { selected, total: candidate.occurrences.length };
}

function candidateReviewState(candidate) {
  const statuses = new Set(candidate.occurrences.map(occurrenceStatus));
  if (statuses.has("pending")) return "pending";
  if (statuses.size > 1) return "mixed";
  return statuses.has("confirmed") ? "confirmed" : "cancelled";
}

function reviewStateLabel(status) {
  return ({ pending: "待处理", confirmed: "已脱敏", cancelled: "已保留", mixed: "逐处处理" })[status] || "待处理";
}

function maskedSegmentPlain(segment) {
  const ranges = [];
  sensitiveCandidates.forEach((candidate) => {
    candidate.occurrences.forEach((occurrence) => {
      if (occurrence.target === "text" && occurrence.segment_id === segment.id && occurrenceStatus(occurrence) !== "cancelled") {
        ranges.push({ start: occurrence.start, end: occurrence.end, replacement: candidate.replacement });
      }
    });
  });
  ranges.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));
  const chosen = [];
  let lastEnd = -1;
  ranges.forEach((item) => {
    if (item.start >= lastEnd) {
      chosen.push(item);
      lastEnd = item.end;
    }
  });
  let output = "";
  let position = 0;
  chosen.forEach((item) => {
    output += segment.text.slice(position, item.start) + item.replacement;
    position = item.end;
  });
  return output + segment.text.slice(position);
}

function occurrenceContext(candidate, occurrence, masked = false) {
  const segment = allOriginalSegments().find((item) => item.id === occurrence.segment_id);
  if (!segment) return escapeHtml(candidate.type === "secret" ? "敏感值不在界面中显示" : occurrence.context || candidateDisplayValue(candidate));
  const radius = 150;
  const start = Math.max(0, Number(occurrence.start || 0) - radius);
  const end = Math.min(segment.text.length, Number(occurrence.end || 0) + radius);
  const prefix = start > 0 ? "…" : "";
  const suffix = end < segment.text.length ? "…" : "";
  if (masked) {
    const text = maskedSegmentPlain(segment);
    return escapeHtml(`${prefix}${text.slice(Math.max(0, start - 20), Math.min(text.length, end + 40))}${suffix}`);
  }
  const localStart = Number(occurrence.start || 0) - start;
  const localEnd = Number(occurrence.end || 0) - start;
  const excerpt = segment.text.slice(start, end);
  const value = candidate.type === "secret" ? "••••••••" : excerpt.slice(localStart, localEnd);
  return `${prefix}${escapeHtml(excerpt.slice(0, localStart))}<mark class="context-sensitive-value">${escapeHtml(value)}</mark>${escapeHtml(excerpt.slice(localEnd))}${suffix}`;
}

function renderContextReview() {
  if (!currentDocument || !sensitiveCandidates.length) {
    contextReviewView.innerHTML = '<div class="empty-state">未识别到需要检查的敏感信息。仍可在“完整材料”中手动补充。</div>';
    return;
  }
  let candidate = sensitiveCandidates.find((item) => item.id === activeCandidateId);
  if (!candidate) candidate = visibleCandidates()[0] || sensitiveCandidates[0];
  activeCandidateId = candidate.id;
  let occurrence = candidate.occurrences.find((item) => item.id === activeOccurrenceId) || candidate.occurrences[0];
  activeOccurrenceId = occurrence?.id || "";
  const state = candidateReviewState(candidate);
  contextReviewView.innerHTML = `
    <header class="context-review-head">
      <div>
        <span class="candidate-type">${escapeHtml(candidate.type_label || "敏感信息")}</span>
        <h3>${escapeHtml(candidateDisplayValue(candidate))}</h3>
        <p>${escapeHtml(candidate.category_label || "")}${candidate.reason ? ` · ${escapeHtml(candidate.reason)}` : ""}</p>
      </div>
      <span class="review-state ${state}">${reviewStateLabel(state)}</span>
    </header>
    <div class="replacement-summary">
      <span>原值</span><strong>${escapeHtml(candidateDisplayValue(candidate))}</strong>
      <b>→</b>
      <span>外发替换</span><strong>${escapeHtml(candidate.replacement)}</strong>
    </div>
    <div class="group-decision-actions">
      <button class="primary" type="button" data-group-decision="confirmed" data-candidate-id="${escapeHtml(candidate.id)}">全部脱敏</button>
      <button class="ghost" type="button" data-group-decision="cancelled" data-candidate-id="${escapeHtml(candidate.id)}">全部保留</button>
      <span>共 ${candidate.occurrences.length} 处，可在下方逐处调整</span>
    </div>
    ${occurrence ? `
      <section class="context-comparison">
        <div class="context-location">
          <strong>${escapeHtml(occurrence.file_name || currentDocument.file_name || "当前材料")}</strong>
          <span>${escapeHtml(occurrence.target === "file_name" ? "文件名" : occurrence.sheet ? `${occurrence.segment_id || ""} · 工作表「${occurrence.sheet}」第${occurrence.index}行` : `${occurrence.segment_id || ""} · 第${occurrence.page || 1}页`)}</span>
        </div>
        <article><span>原文</span><p>${occurrenceContext(candidate, occurrence, false)}</p></article>
        <article class="masked-context"><span>发送给模型</span><p>${occurrenceContext(candidate, occurrence, true)}</p></article>
      </section>` : ""}
    <section class="occurrence-review-list">
      <h4>出现位置</h4>
      ${candidate.occurrences.map((item) => {
        const itemStatus = occurrenceStatus(item);
        return `<button class="occurrence-review-item ${item.id === activeOccurrenceId ? "active" : ""}" type="button"
          data-occurrence-review="${escapeHtml(item.id)}" data-candidate-id="${escapeHtml(candidate.id)}">
          <span><strong>${escapeHtml(item.target === "file_name" ? "文件名" : item.sheet ? `工作表「${item.sheet}」第${item.index}行` : item.segment_id || `第${item.page}页`)}</strong><small>${escapeHtml(item.file_name || "")}</small></span>
          <i class="status-chip ${itemStatus}">${reviewStateLabel(itemStatus)}</i>
          <span class="instance-actions">
            <b data-instance-decision="confirmed" data-occurrence-id="${escapeHtml(item.id)}">脱敏</b>
            <b data-instance-decision="cancelled" data-occurrence-id="${escapeHtml(item.id)}">保留</b>
          </span>
        </button>`;
      }).join("")}
    </section>`;

  contextReviewView.querySelectorAll("[data-group-decision]").forEach((button) => button.addEventListener("click", () => {
    applyGroupDecision(candidate, button.dataset.groupDecision, "context_group",
      button.dataset.groupDecision === "confirmed" ? `已将“${candidate.value}”全部设为脱敏` : `已将“${candidate.value}”全部设为保留`);
  }));
  contextReviewView.querySelectorAll("[data-occurrence-review]").forEach((button) => button.addEventListener("click", (event) => {
    if (event.target.closest("[data-instance-decision]")) return;
    activeCandidateId = button.dataset.candidateId;
    activeOccurrenceId = button.dataset.occurrenceReview;
    renderContextReview();
  }));
  contextReviewView.querySelectorAll("[data-instance-decision]").forEach((button) => button.addEventListener("click", (event) => {
    event.stopPropagation();
    const item = candidate.occurrences.find((entry) => entry.id === button.dataset.occurrenceId);
    if (!item) return;
    recordHistory("逐处修改脱敏决定");
    setOccurrenceStatus(item, button.dataset.instanceDecision);
    item.decision_origin = "context_instance";
    refreshCandidateState(candidate);
    invalidateRedaction("脱敏决定已修改，请重新确认。");
    renderCandidates();
  }));
}

function renderOutboundPreview() {
  if (!currentDocument) return;
  const segments = allOriginalSegments();
  const pending = sensitiveCandidates.reduce((sum, candidate) => sum + candidate.occurrences.filter((item) => occurrenceStatus(item) === "pending").length, 0);
  const replacementCount = sensitiveCandidates.reduce((sum, candidate) => sum + candidate.occurrences.filter((item) => occurrenceStatus(item) !== "cancelled").length, 0);
  outboundSummary.textContent = `${segments.length} 段文字 · ${replacementCount} 处替换 · 0 张图片`;
  outboundSegments.innerHTML = `${pending ? `<div class="outbound-pending-warning">还有 ${pending} 处待处理；下方暂按脱敏建议预览，完成处理后才能确认。</div>` : ""}
    ${segments.map((segment) => `<article><strong>${escapeHtml(segment.file_name)} · ${escapeHtml(segment.id)} · ${segment.sheet ? `工作表「${escapeHtml(segment.sheet)}」第${segment.index}行` : `第${segment.page}页`}</strong><p>${escapeHtml(maskedSegmentPlain(segment))}</p></article>`).join("")}`;
}

function setRedactionView(view) {
  activeRedactionView = view;
  redactionViewTabs.forEach((button) => button.classList.toggle("active", button.dataset.redactionView === view));
  contextReviewView.hidden = view !== "context";
  documentReviewView.hidden = view !== "document";
  outboundReviewView.hidden = view !== "outbound";
  if (view === "context") renderContextReview();
  if (view === "document") renderSources();
  if (view === "outbound") renderOutboundPreview();
}

function renderCandidates() {
  if (!currentDocument) {
    redactionCount.textContent = "请先抽取材料";
    workspaceRedactionCount.textContent = "请先抽取材料";
    candidateList.innerHTML = '<div class="empty-state small">抽取原文后，这里会显示需要处理的敏感信息。</div>';
    renderContextReview();
    return;
  }
  const visible = visibleCandidates();
  const pendingGroups = sensitiveCandidates.filter((item) => candidateReviewState(item) === "pending").length;
  const summary = `${sensitiveCandidates.length} 组敏感信息 · ${pendingGroups} 组待处理`;
  redactionCount.textContent = summary;
  workspaceRedactionCount.textContent = summary;
  if (!visible.length) {
    candidateList.innerHTML = '<div class="empty-state small">当前筛选下没有项目。可切换到“全部”查看已处理内容，或在完整材料中手动补充。</div>';
    renderContextReview();
    updateRedactionStats();
    return;
  }
  candidateList.innerHTML = visible
    .map((candidate) => {
      const state = candidateSelectionState(candidate);
      const reviewState = candidateReviewState(candidate);
      return `
        <article class="candidate-card ${activeCandidateId === candidate.id ? "active" : ""}" data-candidate-id="${escapeHtml(candidate.id)}" tabindex="0">
          <div class="candidate-card-top">
            <span class="candidate-type">${escapeHtml(candidate.type_label || "敏感信息")}</span>
            <span class="confidence-chip ${escapeHtml(candidate.sensitivity || "high")}">${candidate.manual ? "手动" : candidate.sensitivity === "high" ? "高敏" : candidate.sensitivity === "medium" ? "中敏" : "低敏"}</span>
            <span class="review-state ${reviewState}">${reviewStateLabel(reviewState)}</span>
          </div>
          <strong class="candidate-value">${escapeHtml(candidateDisplayValue(candidate))}</strong>
          <div class="candidate-replacement">→ ${escapeHtml(candidate.replacement)} <span>${state.total} 处</span></div>
          <div class="candidate-card-actions">
            <button class="candidate-decision mask" type="button" data-decision="confirmed" data-candidate-id="${escapeHtml(candidate.id)}">全部脱敏</button>
            <button class="candidate-decision keep" type="button" data-decision="cancelled" data-candidate-id="${escapeHtml(candidate.id)}">全部保留</button>
          </div>
        </article>
      `;
    })
    .join("");

  candidateList.querySelectorAll(".candidate-card").forEach((card) => {
    const select = () => {
      activeCandidateId = card.dataset.candidateId;
      activeOccurrenceId = "";
      setRedactionView("context");
      renderCandidates();
    };
    card.addEventListener("click", (event) => { if (!event.target.closest(".candidate-decision")) select(); });
    card.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); select(); } });
  });
  candidateList.querySelectorAll(".candidate-decision").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      const candidate = sensitiveCandidates.find((item) => item.id === button.dataset.candidateId);
      activeCandidateId = candidate.id;
      applyGroupDecision(candidate, button.dataset.decision, "task_group",
        button.dataset.decision === "confirmed" ? `已将“${candidate.value}”全部设为脱敏` : `已将“${candidate.value}”全部设为保留`);
    });
  });
  renderContextReview();
  if (activeRedactionView === "outbound") renderOutboundPreview();
  updateRedactionStats();
}

