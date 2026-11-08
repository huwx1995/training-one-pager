// One-pager preview rendering and editing controls.
function renderIncludedAnswers() {
  const items = currentOnePager.qa_items || [];
  if (!items.length) return "";
  return `<section class="knowledge-section qa-paper-section"><header class="knowledge-section-head"><div><h4>材料问答</h4></div>${knowledgeSectionTools("qa_items")}</header><div class="qa-paper-list">${items.map((item, index) => `<p><strong>问：${escapeHtml(item.question)}</strong><br>答：${escapeHtml(item.answer)} ${sourceControl(item)} <button class="editor-only" type="button" data-remove-qa="${index}">移除</button></p>`).join("")}</div></section>`;
}

function setupAnswerEditing() {
  paper.querySelectorAll("[data-remove-qa]").forEach((button) => button.addEventListener("click", () => {
    markOnePagerDeletion();
    currentOnePager.qa_items.splice(Number(button.dataset.removeQa), 1);
    currentOnePager.status = "待确认";
    renderOnePager();
  }));
}

function editable(value, module, index, field, className = "") {
  return `<span class="editable-text ${className}" contenteditable="true" data-module="${module}" data-index="${index}" data-field="${field}">${escapeHtml(value || "")}</span>`;
}

function sourceControl(item) {
  return `<button class="source-link editor-only" type="button" data-source-ids="${escapeHtml((item.source_ids || []).join(","))}">出处</button>
    ${item.needs_confirmation ? '<span class="confirm-chip editor-only">需核对</span>' : ""}`;
}

function itemControls(module, index) {
  return `<span class="item-edit-controls editor-only">
    <button type="button" data-item-action="up" data-module="${module}" data-index="${index}" title="上移">↑</button>
    <button type="button" data-item-action="down" data-module="${module}" data-index="${index}" title="下移">↓</button>
    <button type="button" data-item-action="delete" data-module="${module}" data-index="${index}" title="删除">×</button>
  </span>`;
}

function moduleItems(module) {
  if (module === "logic") return currentOnePager.logic?.nodes || [];
  return currentOnePager[module] || [];
}

function renderModuleBody(module) {
  const items = moduleItems(module);
  if (module === "conclusions") {
    return `<ol class="conclusion-list">${items.map((item, index) => `<li class="one-item" draggable="true" data-module="${module}" data-index="${index}">
      <span class="conclusion-number">${index + 1}</span>${editable(item.text, module, index, "text")}${sourceControl(item)}${itemControls(module, index)}</li>`).join("")}</ol>`;
  }
  if (module === "metrics") {
    return `<div class="metric-grid">${items.map((item, index) => `<article class="metric-card one-item" draggable="true" data-module="${module}" data-index="${index}">
      ${editable(item.value, module, index, "value", "metric-value")}
      ${editable(item.label, module, index, "label", "metric-label")}
      ${editable(item.comparison, module, index, "comparison", "metric-comparison")}
      <span class="metric-tools">${sourceControl(item)}${itemControls(module, index)}</span></article>`).join("")}</div>`;
  }
  if (module === "logic") {
    return `<div class="logic-type editor-only">结构：${editable(currentOnePager.logic?.type || "总分总", "logic", -1, "type")}</div>
      <div class="logic-flow">${items.map((item, index) => `<article class="logic-node one-item" draggable="true" data-module="${module}" data-index="${index}">
        <span class="logic-dot">${index + 1}</span>${editable(item.title, module, index, "title", "logic-title")}${editable(item.text, module, index, "text", "logic-text")}
        <span class="logic-tools">${sourceControl(item)}${itemControls(module, index)}</span></article>`).join('<span class="logic-arrow">→</span>')}</div>`;
  }
  if (module === "actions") {
    const priorityText = { high: "高", medium: "中", low: "低" };
    return `<div class="action-list">${items.map((item, index) => `<article class="action-row one-item priority-${escapeHtml(item.priority || "medium")}" draggable="true" data-module="${module}" data-index="${index}">
      <span class="priority-badge">${priorityText[item.priority] || "中"} · ${escapeHtml(item.kind || "待办")}</span>
      ${editable(item.text, module, index, "text", "action-text")}
      <span class="action-meta">${editable(item.owner || "负责人待定", module, index, "owner")} · ${editable(item.due || "时间待定", module, index, "due")}</span>
      <span class="action-tools">${sourceControl(item)}${itemControls(module, index)}</span></article>`).join("")}</div>`;
  }
  return `<div class="supplement-list">${items.map((item, index) => `<article class="supplement-row one-item" draggable="true" data-module="${module}" data-index="${index}">
    ${editable(item.term, module, index, "term", "supplement-term")}<span>：</span>${editable(item.explanation, module, index, "explanation")}${sourceControl(item)}${itemControls(module, index)}</article>`).join("")}</div>`;
}

function moduleSection(module, orderIndex) {
  const hidden = (currentOnePager.hidden_modules || []).includes(module);
  return `<section class="one-module module-${module} ${hidden ? "module-hidden" : ""}" data-module="${module}">
    <header class="one-module-head">
      <h4>${escapeHtml(moduleLabels[module] || module)}${module === "logic" ? ` <small>${escapeHtml(currentOnePager.logic?.type || "")}</small>` : ""}</h4>
      <span class="module-controls editor-only">
        <button type="button" data-module-action="up" data-module="${module}" title="模块上移">↑</button>
        <button type="button" data-module-action="down" data-module="${module}" title="模块下移">↓</button>
        <button type="button" data-module-action="toggle" data-module="${module}">${hidden ? "显示" : "隐藏"}</button>
        <button type="button" data-module-action="add" data-module="${module}">添加</button>
      </span>
    </header>
    <div class="module-content">${hidden ? '<p class="hidden-note editor-only">该模块已从成品中隐藏。</p>' : renderModuleBody(module)}</div>
  </section>`;
}

const architectureTypeLabels = {
  module: "模块型",
  process: "流程型",
  hierarchy: "层级型",
  mixed: "混合型",
  grouped: "分组型",
};

const trainingTypeLabels = {
  product: "产品培训",
  policy: "制度培训",
  operation: "操作培训",
  general: "综合培训",
};

function knowledgeGroupFor(moduleId) {
  return (currentOnePager.knowledge_modules || []).find((group) => group.architecture_id === moduleId);
}

function deleteArchitectureNode(index) {
  const removed = currentOnePager.knowledge_architecture.modules.splice(index, 1)[0];
  if (!removed) return;
  const group = knowledgeGroupFor(removed.id);
  const removedSources = new Set([...(removed.source_ids || []), ...(group?.points || []).flatMap((point) => point.source_ids || [])]);
  currentOnePager.knowledge_modules = (currentOnePager.knowledge_modules || []).filter((group) => group.architecture_id !== removed.id);
  currentOnePager.original_structure = (currentOnePager.original_structure || []).filter((item) => item.architecture_id !== removed.id);
  const belongsOnlyToRemoved = (item) => item.source_ids?.length && item.source_ids.every((id) => removedSources.has(id));
  currentOnePager.key_reminders = (currentOnePager.key_reminders || []).filter((item) => !belongsOnlyToRemoved(item));
  currentOnePager.practical_application = (currentOnePager.practical_application || []).map((section) => ({
    ...section, items: (section.items || []).filter((item) => !belongsOnlyToRemoved(item)),
  })).filter((section) => section.items.length);
}

function syncKnowledgeOrder() {
  const modules = currentOnePager.knowledge_architecture?.modules || [];
  if (currentOnePager.generation_requirements?.include_knowledge_modules === false) {
    modules.forEach((module, index) => { module.order = index; });
    return;
  }
  const existing = new Map((currentOnePager.knowledge_modules || []).map((group) => [group.architecture_id, group]));
  currentOnePager.knowledge_modules = modules.map((module, index) => {
    const group = existing.get(module.id) || { architecture_id: module.id, title: module.title, points: [] };
    group.title = module.title;
    group.order = index;
    return group;
  });
  modules.forEach((module, index) => { module.order = index; });
}

function knowledgeSectionTools(moduleKey) {
  return `<span class="module-controls editor-only"><button type="button" data-delete-section="${moduleKey}">删除板块</button></span>`;
}

function renderFrameworkMap() {
  const architecture = currentOnePager.knowledge_architecture || {};
  const modules = architecture.modules || [];
  const groups = new Map((currentOnePager.generation_requirements?.include_knowledge_modules === false ? [] : currentOnePager.knowledge_modules || []).map((group) => [group.architecture_id, group]));
  if (!modules.length || currentOnePager.generation_requirements?.include_architecture === false) return "";
  const split = Math.ceil(modules.length / 2);
  const branch = (module, index) => {
    const points = groups.get(module.id)?.points || [];
    return `<article class="framework-branch">
      <h5 contenteditable="true" data-framework-module="${index}">${escapeHtml(module.title || "知识主题")}</h5>
      ${module.description ? `<p>${escapeHtml(module.description)}</p>` : ""}
      ${sourceControl(module)}
      ${points.length ? `<ul>${points.map((point, pointIndex) => `<li><span contenteditable="true" data-framework-point="${index}:${pointIndex}">${escapeHtml(point.text || "")}</span>${sourceControl(point)}<button class="editor-only inline-delete" type="button" data-framework-point-delete="${index}:${pointIndex}" aria-label="删除该知识点">×</button></li>`).join("")}</ul>` : ""}
      <button class="editor-only inline-delete" type="button" data-framework-delete="${index}">删除此部分</button>
    </article>`;
  };
  return `<div class="framework-layout-picker editor-only"><label>框架形式 <select id="frameworkTypeSelect">${Object.entries(architectureTypeLabels).map(([value, label]) => `<option value="${value}" ${architecture.type === value ? "selected" : ""}>${label}</option>`).join("")}</select></label></div>
  <section class="framework-map framework-${escapeHtml(architecture.type || "grouped")}" aria-label="材料框架图">
    ${architecture.type === "module" ? `<div class="framework-side framework-left">${modules.slice(0, split).map((module, index) => branch(module, index)).join("")}</div>
      <div class="framework-center">${escapeHtml(architecture.central_topic || currentOnePager.meta?.title || "中心主题")}</div>
      <div class="framework-side framework-right">${modules.slice(split).map((module, index) => branch(module, index + split)).join("")}</div>` :
      `<div class="framework-center">${escapeHtml(architecture.central_topic || currentOnePager.meta?.title || "中心主题")}</div>
       <div class="framework-branches">${modules.map((module, index) => branch(module, index)).join(architecture.type === "process" ? '<span class="framework-flow-arrow" aria-hidden="true">→</span>' : "")}</div>`}
  </section>`;
}

function renderOriginalStructure() {
  const items = currentOnePager.original_structure || [];
  if (currentOnePager.generation_requirements?.include_full_structure === false || !items.length) return "";
  return `<section class="knowledge-section original-structure-section"><header class="knowledge-section-head"><div><span class="section-number">全文</span><h4>全文架构</h4></div>${knowledgeSectionTools("original_structure")}</header>
    <ol class="original-structure-list">${items.map((item, index) => `<li><span class="structure-number">${index + 1}.</span> ${editable(item.title, "original_structure", index, "title")}${sourceControl(item)}${itemControls("original_structure", index)}</li>`).join("")}</ol></section>`;
}

function renderKnowledgeModules() {
  const groups = currentOnePager.knowledge_modules || [];
  return `<section class="knowledge-section knowledge-points-section">
    <header class="knowledge-section-head"><div><span class="section-number">要点</span><h4>${escapeHtml({policy: "关键规定", operation: "办理步骤", product: "产品要点", general: "核心知识"}[currentOnePager.meta?.training_type] || "核心知识")}</h4></div>${knowledgeSectionTools("knowledge_modules")}</header>
    <div class="knowledge-card-grid">
      ${groups.map((group, groupIndex) => `<article class="knowledge-card" data-group-index="${groupIndex}">
        <h5><span>${String(groupIndex + 1).padStart(2, "0")}</span>${escapeHtml(group.title || "知识模块")}</h5>
        <ul>${(group.points || []).map((point, pointIndex) => `<li class="knowledge-point knowledge-draggable" draggable="true" data-knowledge-kind="point" data-group-index="${groupIndex}" data-index="${pointIndex}">
          ${editable(point.text, "knowledge_point", pointIndex, "text")}${sourceControl(point)}${itemControls("knowledge_point", pointIndex)}
        </li>`).join("")}</ul>
        <button class="inline-add editor-only" type="button" data-add-point="${groupIndex}">＋ 添加知识点</button>
      </article>`).join("")}
    </div>
  </section>`;
}

function renderPracticalApplication() {
  const groups = currentOnePager.practical_application || [];
  return `<section class="knowledge-section practice-section">
    <header class="knowledge-section-head"><div><span class="section-number">行动</span><h4>工作中怎么做</h4></div>${knowledgeSectionTools("practical_application")}</header>
    <div class="practice-grid">${groups.map((group, groupIndex) => `<article class="practice-card" data-group-index="${groupIndex}">
      <h5>${editable(group.title, "practice_group", groupIndex, "title")}</h5>
      <ul>${(group.items || []).map((item, itemIndex) => `<li>${editable(item.text, "practice_item", itemIndex, "text")}${sourceControl(item)}${itemControls("practice_item", itemIndex)}</li>`).join("")}</ul>
      <button class="inline-add editor-only" type="button" data-add-practice-item="${groupIndex}">＋ 添加事项</button>
      <button class="inline-delete editor-only" type="button" data-delete-practice-group="${groupIndex}">删除分组</button>
    </article>`).join("")}</div>
  </section>`;
}

function renderKeyReminders() {
  const reminders = currentOnePager.key_reminders || [];
  return `<section class="knowledge-section reminder-section">
    <header class="knowledge-section-head"><div><span class="section-number">注意</span><h4>风险与例外</h4></div>${knowledgeSectionTools("key_reminders")}</header>
    <div class="reminder-list">${reminders.map((item, index) => `<article class="reminder-item level-${escapeHtml(item.level || "medium")}">
      <span class="reminder-mark">!</span>${editable(item.text, "key_reminders", index, "text")}${sourceControl(item)}${itemControls("key_reminders", index)}
    </article>`).join("")}</div>
  </section>`;
}

function renderCoverageReview() {
  const items = currentOnePager?.coverage_review || [];
  coverageReview.hidden = !items.length || Boolean(currentOnePager?.user_deleted_content);
  if (!items.length || currentOnePager?.user_deleted_content) return;
  const covered = items.filter((item) => item.status === "covered").length;
  const needsCheck = items.filter((item) => item.status === "check").length;
  coverageReview.innerHTML = `<div class="coverage-review-head"><strong>内容覆盖线索</strong><span>成稿已提及 ${covered} 项${needsCheck ? ` · 建议核对 ${needsCheck} 项` : ""}</span></div>
    <div class="coverage-chips">${items.map((item) => `<span class="coverage-chip status-${escapeHtml(item.status)}">${escapeHtml(item.topic)} · ${{covered: "已提及", check: "建议核对", absent: "原文未提及"}[item.status] || "建议核对"}</span>`).join("")}</div>
    <p>这是关键词线索检查，不代表事实已完整覆盖；请结合原文和你填写的问题核对成稿。</p>`;
}

function renderKnowledgeOnePager() {
  const meta = currentOnePager.meta || {};
  const compactClass = currentOnePager.layout?.compact ? "compact-layout" : "";
  const limit = currentOnePager.generation_requirements?.max_chars;
  const lengthClass = limit && limit <= 200 ? "length-brief" : limit && limit <= 500 ? "length-standard" : "length-detailed";
  const framework = currentOnePager.generation_requirements?.presentation_mode === "framework";
  document.querySelector("#printPageStyle").textContent = framework ? "@media print { @page { size: A4 landscape; margin: 0; } }" : "";
  paper.className = `paper one-pager-sheet knowledge-sheet ${framework ? "framework-sheet" : ""} template-${escapeHtml(meta.template || "knowledge-auto")} training-${escapeHtml(meta.training_type || "general")} ${lengthClass} ${compactClass}`;
  paper.innerHTML = `
    <header class="knowledge-header">
      <div class="knowledge-kicker"><span>培训一纸通</span><span>${escapeHtml(trainingTypeLabels[meta.training_type] || "培训材料")} · ${escapeHtml(meta.audience || audienceSelect.value)}</span></div>
      <h3 id="paperTitle" contenteditable="true">${escapeHtml(meta.title || "培训一纸通")}</h3>
      <p class="document-meta">${escapeHtml(meta.file_name || "")} · ${escapeHtml(meta.page_count || 1)}页 · ${escapeHtml(meta.generated_at || "")}</p>
      ${contactMarkup()}
    </header>
    ${currentOnePager.generation_requirements?.include_overview === false || !meta.overview ? "" : `<section class="knowledge-section overview-section">
      <header class="knowledge-section-head"><div><span class="section-number">结论</span><h4>核心结论</h4></div>${knowledgeSectionTools("overview")}</header>
      <p id="paperOverview" contenteditable="true">${escapeHtml(meta.overview || "")}</p>${meta.overview_source_ids?.length ? sourceControl({ source_ids: meta.overview_source_ids, needs_confirmation: meta.overview_needs_confirmation }) : ""}
    </section>`}
    ${currentOnePager.model_note ? `<p class="model-note editor-only">${escapeHtml(currentOnePager.model_note)}</p>` : ""}
    ${(currentOnePager.quality_warnings || []).length ? `<details class="quality-warnings editor-only"><summary>${currentOnePager.quality_warnings.length} 项质量提醒</summary><ul>${currentOnePager.quality_warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></details>` : ""}
    ${renderOriginalStructure()}
    <div class="knowledge-body">
      ${framework ? renderFrameworkMap() : ""}
      ${framework || currentOnePager.generation_requirements?.include_knowledge_modules === false ? "" : renderKnowledgeModules()}
      <div class="knowledge-lower-grid">${currentOnePager.generation_requirements?.include_practice === false || !currentOnePager.practical_application?.length ? "" : renderPracticalApplication()}${currentOnePager.key_reminders?.length ? renderKeyReminders() : ""}</div>
      ${renderIncludedAnswers()}
    </div>
    <footer class="one-pager-footer"><span>内容依据脱敏原文提炼；点击“出处”可在线核对，出处不进入导出文件</span><span>AI-2 培训一纸通</span></footer>`;
  setupKnowledgeEditing();
  paper.querySelectorAll("[data-framework-module]").forEach((node) => node.addEventListener("blur", () => {
    const index = Number(node.dataset.frameworkModule);
    const module = currentOnePager.knowledge_architecture?.modules?.[index];
    if (module) { module.title = node.textContent.trim(); module.needs_confirmation = true; currentOnePager.status = "待确认"; checkPageOverflow(); }
  }));
  paper.querySelector("#frameworkTypeSelect")?.addEventListener("change", (event) => {
    currentOnePager.knowledge_architecture.type = event.target.value;
    currentOnePager.status = "待确认";
    renderOnePager();
  });
  paper.querySelectorAll("[data-framework-delete]").forEach((button) => button.addEventListener("click", () => {
    markOnePagerDeletion();
    const index = Number(button.dataset.frameworkDelete);
    deleteArchitectureNode(index);
    currentOnePager.status = "待确认";
    renderOnePager();
  }));
  paper.querySelectorAll("[data-framework-point-delete]").forEach((button) => button.addEventListener("click", () => {
    const [moduleIndex, pointIndex] = button.dataset.frameworkPointDelete.split(":").map(Number);
    const moduleId = currentOnePager.knowledge_architecture.modules[moduleIndex]?.id;
    const points = knowledgeGroupFor(moduleId)?.points;
    if (!points?.[pointIndex]) return;
    markOnePagerDeletion();
    points.splice(pointIndex, 1);
    currentOnePager.status = "待确认";
    renderOnePager();
  }));
  paper.querySelectorAll("[data-framework-point]").forEach((node) => node.addEventListener("blur", () => {
    const [index, pointIndex] = node.dataset.frameworkPoint.split(":").map(Number);
    const moduleId = currentOnePager.knowledge_architecture?.modules?.[index]?.id;
    const point = (currentOnePager.knowledge_modules || []).find((group) => group.architecture_id === moduleId)?.points?.[pointIndex];
    if (point) { point.text = node.textContent.trim(); point.needs_confirmation = true; currentOnePager.status = "待确认"; checkPageOverflow(); }
  }));
  setupAnswerEditing();
  renderCoverageReview();
  updateExportButtons();
  requestAnimationFrame(checkPageOverflow);
}

function renderOnePager() {
  if (!currentOnePager) {
    document.querySelector("#printPageStyle").textContent = "";
    coverageReview.hidden = true;
    paper.innerHTML = `
      <header class="paper-header">
        <div>
          <p id="paperBadge">待生成</p>
          <h3 id="paperTitle">一纸通预览</h3>
        </div>
        <span id="reviewStatus">待确认</span>
      </header>
      <div class="empty-state">
        <p>生成后，这里会以一页 A4 展示核心结论、关键数据、逻辑结构和重点事项。</p>
      </div>
    `;
    updateExportButtons();
    return;
  }
  if (currentOnePager.schema_version === "3.0") {
    renderKnowledgeOnePager();
    return;
  }
  coverageReview.hidden = true;
  const meta = currentOnePager.meta || {};
  const order = currentOnePager.module_order || ["conclusions", "metrics", "logic", "actions", "supplements"];
  paper.className = `paper one-pager-sheet template-${escapeHtml(meta.template || templateSelect.value || "report")} ${currentOnePager.layout?.compact ? "compact-layout" : ""}`;
  paper.innerHTML = `
    <header class="one-pager-header">
      <div class="title-copy">
        <p id="paperBadge">${escapeHtml(meta.document_type || "材料")} · ${escapeHtml(meta.audience || audienceSelect.value)}</p>
        <h3 id="paperTitle" contenteditable="true">${escapeHtml(meta.title || "一纸通")}</h3>
        ${contactMarkup()}
        <p id="paperSubtitle" contenteditable="true">${escapeHtml(meta.subtitle || "一分钟读懂材料核心信息")}</p>
      </div>
      <span id="reviewStatus" class="${currentOnePager.status === "已确认" ? "approved" : ""}">${escapeHtml(currentOnePager.status || "待确认")}</span>
      <p class="document-meta">${escapeHtml(meta.file_name || "")} · ${escapeHtml(meta.page_count || 1)}页 · ${escapeHtml(meta.generated_at || "")}</p>
    </header>
    ${currentOnePager.model_note ? `<p class="model-note editor-only">${escapeHtml(currentOnePager.model_note)}</p>` : ""}
    ${(currentOnePager.quality_warnings || []).length ? `<details class="quality-warnings editor-only"><summary>${currentOnePager.quality_warnings.length} 项质量提醒</summary><ul>${currentOnePager.quality_warnings.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></details>` : ""}
    <div class="one-pager-body">
      ${order.map((module, index) => moduleSection(module, index)).join("")}
      ${renderIncludedAnswers()}
    </div>
    <footer class="one-pager-footer"><span>内容由原文提炼，请通过工作台“出处”按钮核对</span><span>AI-2 培训一纸通</span></footer>
  `;
  setupOnePagerEditing();
  setupAnswerEditing();
  updateExportButtons();
  requestAnimationFrame(checkPageOverflow);
}

function setOnePagerField(module, index, field, value) {
  if (module === "logic" && index === -1) currentOnePager.logic.type = value;
  else {
    const items = moduleItems(module);
    if (items[index]) items[index][field] = value;
  }
  currentOnePager.status = "待确认";
}

function defaultModuleItem(module) {
  const common = { id: `${module}-${Date.now()}`, source_ids: [], sources: [], needs_confirmation: true };
  if (module === "metrics") return { ...common, label: "指标名称", value: "待填写", comparison: "" };
  if (module === "logic") return { ...common, title: "新节点", text: "补充逻辑说明" };
  if (module === "actions") return { ...common, kind: "待办", priority: "medium", text: "补充重点事项", owner: "", due: "" };
  if (module === "supplements") return { ...common, term: "补充信息", explanation: "填写说明" };
  return { ...common, text: "补充核心结论" };
}

function moveArrayItem(items, from, to) {
  if (to < 0 || to >= items.length || from === to) return false;
  const [item] = items.splice(from, 1);
  items.splice(to, 0, item);
  items.forEach((value, index) => { if (value && typeof value === "object") value.order = index; });
  return true;
}

function setupOnePagerEditing() {
  const title = paper.querySelector("#paperTitle");
  const subtitle = paper.querySelector("#paperSubtitle");
  title?.addEventListener("input", (event) => { currentOnePager.meta.title = event.target.textContent.trim(); checkPageOverflow(); });
  subtitle?.addEventListener("input", (event) => { currentOnePager.meta.subtitle = event.target.textContent.trim(); checkPageOverflow(); });
  paper.querySelectorAll(".editable-text").forEach((node) => {
    node.addEventListener("input", (event) => {
      setOnePagerField(event.target.dataset.module, Number(event.target.dataset.index), event.target.dataset.field, event.target.textContent.trim());
      checkPageOverflow();
    });
  });
  paper.querySelectorAll(".source-link").forEach((button) => button.addEventListener("click", () => {
    showSources((button.dataset.sourceIds || "").split(",").filter(Boolean));
  }));
  paper.querySelectorAll("[data-item-action]").forEach((button) => button.addEventListener("click", () => {
    const items = moduleItems(button.dataset.module);
    const index = Number(button.dataset.index);
    if (button.dataset.itemAction === "delete") items.splice(index, 1);
    if (button.dataset.itemAction === "up") moveArrayItem(items, index, index - 1);
    if (button.dataset.itemAction === "down") moveArrayItem(items, index, index + 1);
    currentOnePager.status = "待确认";
    renderOnePager();
  }));
  paper.querySelectorAll("[data-module-action]").forEach((button) => button.addEventListener("click", () => {
    const module = button.dataset.module;
    const action = button.dataset.moduleAction;
    if (action === "toggle") {
      currentOnePager.hidden_modules ||= [];
      if (currentOnePager.hidden_modules.includes(module)) currentOnePager.hidden_modules = currentOnePager.hidden_modules.filter((key) => key !== module);
      else currentOnePager.hidden_modules.push(module);
      renderOnePager();
    }
    if (action === "add") {
      const maximums = { conclusions: 5, metrics: 8, logic: 5, actions: 6, supplements: 4 };
      if (moduleItems(module).length >= maximums[module]) {
        layoutStatus.textContent = `${moduleLabels[module]}最多保留 ${maximums[module]} 项。`;
        return;
      }
      moduleItems(module).push(defaultModuleItem(module));
      renderOnePager();
    }
    if (action === "up" || action === "down") {
      const order = currentOnePager.module_order;
      const index = order.indexOf(module);
      moveArrayItem(order, index, index + (action === "up" ? -1 : 1));
      renderOnePager();
    }
  }));
  let dragged = null;
  paper.querySelectorAll(".one-item[draggable]").forEach((node) => {
    node.addEventListener("dragstart", () => { dragged = { module: node.dataset.module, index: Number(node.dataset.index) }; node.classList.add("dragging"); });
    node.addEventListener("dragend", () => node.classList.remove("dragging"));
    node.addEventListener("dragover", (event) => event.preventDefault());
    node.addEventListener("drop", (event) => {
      event.preventDefault();
      const targetModule = node.dataset.module;
      if (!dragged || dragged.module !== targetModule) return;
      moveArrayItem(moduleItems(targetModule), dragged.index, Number(node.dataset.index));
      renderOnePager();
    });
  });
}

function setupKnowledgeEditing() {
  const markEdited = () => {
    currentOnePager.status = "待确认";
    checkPageOverflow();
  };
  paper.querySelector("#paperTitle")?.addEventListener("input", (event) => {
    currentOnePager.meta.title = event.target.textContent.trim();
    markEdited();
  });
  paper.querySelector("#paperOverview")?.addEventListener("input", (event) => {
    currentOnePager.meta.overview = event.target.textContent.trim();
    currentOnePager.meta.overview_needs_confirmation = true;
    markEdited();
  });
  paper.querySelectorAll(".editable-text").forEach((node) => node.addEventListener("input", (event) => {
    const target = event.target;
    const module = target.dataset.module;
    const index = Number(target.dataset.index);
    const field = target.dataset.field;
    const value = target.textContent.trim();
    if (module === "knowledge_architecture") {
      if (index === -1) currentOnePager.knowledge_architecture.central_topic = value;
      else {
        const item = currentOnePager.knowledge_architecture.modules[index];
        if (item) {
          item[field] = value;
          if (field === "title") {
            const group = knowledgeGroupFor(item.id);
            if (group) group.title = value;
          }
        }
      }
    } else if (module === "original_structure") {
      if (currentOnePager.original_structure[index]) currentOnePager.original_structure[index][field] = value;
    } else if (module === "knowledge_point") {
      const groupIndex = Number(target.closest("[data-group-index]")?.dataset.groupIndex);
      const item = currentOnePager.knowledge_modules[groupIndex]?.points[index];
      if (item) item[field] = value;
    } else if (module === "practice_group") {
      if (currentOnePager.practical_application[index]) currentOnePager.practical_application[index][field] = value;
    } else if (module === "practice_item") {
      const groupIndex = Number(target.closest("[data-group-index]")?.dataset.groupIndex);
      const item = currentOnePager.practical_application[groupIndex]?.items[index];
      if (item) item[field] = value;
    } else if (module === "key_reminders") {
      if (currentOnePager.key_reminders[index]) currentOnePager.key_reminders[index][field] = value;
    }
    markEdited();
  }));
  paper.querySelectorAll(".source-link").forEach((button) => button.addEventListener("click", () => {
    showSources((button.dataset.sourceIds || "").split(",").filter(Boolean));
  }));
  paper.querySelectorAll("[data-item-action]").forEach((button) => button.addEventListener("click", () => {
    const module = button.dataset.module;
    const index = Number(button.dataset.index);
    const action = button.dataset.itemAction;
    let items = [];
    if (module === "knowledge_architecture") items = currentOnePager.knowledge_architecture.modules;
    if (module === "original_structure") items = currentOnePager.original_structure;
    if (module === "knowledge_point") {
      const groupIndex = Number(button.closest("[data-group-index]")?.dataset.groupIndex);
      items = currentOnePager.knowledge_modules[groupIndex]?.points || [];
    }
    if (module === "practice_item") {
      const groupIndex = Number(button.closest("[data-group-index]")?.dataset.groupIndex);
      items = currentOnePager.practical_application[groupIndex]?.items || [];
    }
    if (module === "key_reminders") items = currentOnePager.key_reminders;
    if (action === "delete") {
      markOnePagerDeletion();
      if (module === "knowledge_architecture") deleteArchitectureNode(index);
      else {
        const removed = items.splice(index, 1)[0];
        if (module === "original_structure" && removed?.architecture_id) {
          const linkedIndex = currentOnePager.knowledge_architecture.modules.findIndex((node) => node.id === removed.architecture_id);
          if (linkedIndex >= 0) deleteArchitectureNode(linkedIndex);
        }
      }
    }
    if (action === "up") moveArrayItem(items, index, index - 1);
    if (action === "down") moveArrayItem(items, index, index + 1);
    if (module === "knowledge_architecture") syncKnowledgeOrder();
    currentOnePager.status = "待确认";
    renderOnePager();
  }));
  paper.querySelectorAll("[data-delete-section]").forEach((button) => button.addEventListener("click", () => {
    markOnePagerDeletion();
    const key = button.dataset.deleteSection;
    const requirements = currentOnePager.generation_requirements ||= guidanceValues();
    if (key === "overview") { requirements.include_overview = false; currentOnePager.meta.overview = ""; }
    if (key === "original_structure") { requirements.include_full_structure = false; currentOnePager.original_structure = []; }
    if (key === "knowledge_architecture") { requirements.include_architecture = false; currentOnePager.knowledge_architecture.show_diagram = false; }
    if (key === "knowledge_modules") { requirements.include_knowledge_modules = false; currentOnePager.knowledge_modules = []; }
    if (key === "practical_application") { requirements.include_practice = false; currentOnePager.practical_application = []; }
    if (key === "key_reminders") currentOnePager.key_reminders = [];
    if (key === "qa_items") currentOnePager.qa_items = [];
    currentOnePager.removed_sections ||= [];
    if (!currentOnePager.removed_sections.includes(key)) currentOnePager.removed_sections.push(key);
    currentOnePager.status = "待确认";
    renderOnePager();
  }));
  paper.querySelectorAll("[data-add-point]").forEach((button) => button.addEventListener("click", () => {
    const points = currentOnePager.knowledge_modules[Number(button.dataset.addPoint)]?.points;
    if (!points || points.length >= 4) { layoutStatus.textContent = "每个知识模块最多保留4条要点。"; return; }
    points.push({ id: `point-${Date.now()}`, text: "补充核心知识点", source_ids: [], sources: [], needs_confirmation: true });
    renderOnePager();
  }));
  paper.querySelectorAll("[data-add-practice-item]").forEach((button) => button.addEventListener("click", () => {
    const items = currentOnePager.practical_application[Number(button.dataset.addPracticeItem)]?.items;
    if (!items || items.length >= 4) { layoutStatus.textContent = "每个实务分组最多保留4项。"; return; }
    items.push({ id: `practice-${Date.now()}`, text: "补充实务内容", source_ids: [], sources: [], needs_confirmation: true });
    renderOnePager();
  }));
  paper.querySelectorAll("[data-delete-practice-group]").forEach((button) => button.addEventListener("click", () => {
    markOnePagerDeletion();
    currentOnePager.practical_application.splice(Number(button.dataset.deletePracticeGroup), 1);
    renderOnePager();
  }));
  let dragged = null;
  paper.querySelectorAll(".knowledge-draggable").forEach((node) => {
    node.addEventListener("dragstart", () => {
      dragged = { kind: node.dataset.knowledgeKind, index: Number(node.dataset.index), groupIndex: Number(node.dataset.groupIndex) };
      node.classList.add("dragging");
    });
    node.addEventListener("dragend", () => node.classList.remove("dragging"));
    node.addEventListener("dragover", (event) => event.preventDefault());
    node.addEventListener("drop", (event) => {
      event.preventDefault();
      if (!dragged || dragged.kind !== node.dataset.knowledgeKind) return;
      if (dragged.kind === "architecture") {
        moveArrayItem(currentOnePager.knowledge_architecture.modules, dragged.index, Number(node.dataset.index));
        syncKnowledgeOrder();
      } else {
        const targetGroup = Number(node.dataset.groupIndex);
        if (dragged.groupIndex !== targetGroup) return;
        moveArrayItem(currentOnePager.knowledge_modules[targetGroup].points, dragged.index, Number(node.dataset.index));
      }
      renderOnePager();
    });
  });
}

