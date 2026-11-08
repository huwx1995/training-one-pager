let currentDocument = null;
let activeAudioJob = "";
let boundedPlayback = null;
let showingAllImages = false;
const previewPageBatch = 15;
const previewFlowBatch = 100;
let visiblePreviewItems = new Map();
let currentOnePager = null;
function markOnePagerDeletion() {
  if (!currentOnePager) return;
  currentOnePager.user_deleted_content = true;
}
let qaExtraSources = [];
let supplementalOriginalSegments = [];
let supplementalMaskedSegments = [];
let sensitiveCandidates = [];
const customTermsStorageKey = "one-pager-custom-redaction-terms-v1";
let savedCustomTerms = [];
let sessionCustomTerms = [];
let managedCustomTerms = new Set();
let imageRegions = [];
let parsingConfirmed = false;
let redactionConfirmed = false;
let confirmationToken = "";
let showMaskedPreview = false;
let selectedSourceText = "";
let apiKey = "";
let activeModelSettings = {};
let undoStack = [];
let redoStack = [];
let activeCanvasInteraction = null;
let redactionActionLog = [];
let decisionManifest = null;
let supplementalDocumentPreviews = [];
let pendingMixedCandidate = null;
let activeCandidateId = "";
let activeOccurrenceId = "";
let activeRedactionView = "context";
const markClickTimers = new Map();

const apiKeyInput = document.querySelector("#apiKeyInput");
const toggleApiKeyBtn = document.querySelector("#toggleApiKeyBtn");
const testApiBtn = document.querySelector("#testApiBtn");
const clearApiBtn = document.querySelector("#clearApiBtn");
const apiStatus = document.querySelector("#apiStatus");
const modelProvider = document.querySelector("#modelProvider");
const modelBaseUrl = document.querySelector("#modelBaseUrl");
const modelName = document.querySelector("#modelName");
const refreshModelsBtn = document.querySelector("#refreshModelsBtn");
const customModelName = document.querySelector("#customModelName");
const modelReasoning = document.querySelector("#modelReasoning");
const presetManualModel = document.querySelector("#presetManualModel");
const modelAdvancedSettings = document.querySelector("#modelAdvancedSettings");
const modelRecommendation = document.querySelector("#modelRecommendation");
const modelConnectionSummary = document.querySelector("#modelConnectionSummary");
const modelSettingsBody = document.querySelector("#modelSettingsBody");
const modelToggleBtn = document.querySelector("#modelToggleBtn");
let modelSelectionManual = false;
const onlineReasoningChoices = {};
const modelDiscoveryCache = new Map();
const modelChoices = {
  deepseek: [["deepseek-flash", "Flash（默认）"], ["deepseek-v4-pro", "V4 Pro"]],
  kimi: [["kimi-k2.6", "Kimi K2.6（轻量默认）"], ["kimi-k3", "Kimi K3（旗舰）"]],
  qwen: [["qwen3.8-flash", "千问 3.8 Flash（默认）"], ["qwen3.8-max", "千问 3.8 Max（旗舰）"]],
  doubao: [["doubao-seed-2-1-turbo-260628", "豆包 Seed 2.1 Turbo（快速默认）"],
    ["doubao-seed-2-1-pro-260915", "豆包 Seed 2.1 Pro（旗舰）"]],
};
const reasoningChoices = {
  "deepseek-flash": [["none", "无思考（默认）"], ["low", "低"], ["high", "高"], ["max", "最高"]],
  "deepseek-v4-pro": [["none", "无思考（默认）"], ["low", "低"], ["high", "高"], ["max", "最高"]],
  "kimi-k3": [["low", "低（默认）"], ["high", "高"], ["max", "最高"]],
  "kimi-k2.6": [["none", "无思考（默认）"], ["low", "开启思考"]],
  "qwen3.8-max": [["none", "无思考（默认）"], ["low", "低"], ["medium", "中"], ["xhigh", "高"]],
  "qwen3.8-flash": [["none", "无思考（默认）"], ["low", "低"], ["medium", "中"], ["xhigh", "高"]],
  "doubao-seed-2-1-pro-260915": [["none", "无思考（默认）"], ["minimal", "最低"], ["low", "低"],
    ["medium", "中"], ["high", "高"]],
  "doubao-seed-2-1-turbo-260628": [["none", "无思考（默认）"], ["minimal", "最低"], ["low", "低"],
    ["medium", "中"], ["high", "高"]],
  "doubao-seed-2-0-pro-260215": [["none", "无思考（默认）"], ["minimal", "最低"], ["low", "低"],
    ["medium", "中"], ["high", "高"]],
};

const fileInput = document.querySelector("#fileInput");
const audioModelRow = document.querySelector("#audioModelRow");
const audioTermsRow = document.querySelector("#audioTermsRow");
const audioTermsInput = document.querySelector("#audioTermsInput");
const audioModelStatus = document.querySelector("#audioModelStatus");
const downloadAudioModelBtn = document.querySelector("#downloadAudioModelBtn");
const extractBtn = document.querySelector("#extractBtn");
const clearBtn = document.querySelector("#clearBtn");
const generateBtn = document.querySelector("#generateBtn");
const cancelGenerateBtn = document.querySelector("#cancelGenerateBtn");
let activeGeneration = null;
const audienceSelect = document.querySelector("#audience");
const templateSelect = document.querySelector("#templateType");
const presentationModeSelect = document.querySelector("#presentationMode");
const documentTypeSelect = document.querySelector("#documentType");
const focusInput = document.querySelector("#focusInput");
const excludeSectionsInput = document.querySelector("#excludeSectionsInput");
const explainTerms = document.querySelector("#explainTerms");
const audienceCustom = document.querySelector("#audienceCustom");
const maxCharsSelect = document.querySelector("#maxChars");
const customMaxField = document.querySelector("#customMaxField");
const customMaxChars = document.querySelector("#customMaxChars");
const detailDepth = document.querySelector("#detailDepth");
const writingTone = document.querySelector("#writingTone");
const includeOverview = document.querySelector("#includeOverview");
const includeFullStructure = document.querySelector("#includeFullStructure");
const includeArchitecture = document.querySelector("#includeArchitecture");
const includePractice = document.querySelector("#includePractice");
const mustKeepInput = document.querySelector("#mustKeepInput");
const extraRequirements = document.querySelector("#extraRequirements");
const requirementsPreview = document.querySelector("#requirementsPreview");
const guidanceAdvice = document.querySelector("#guidanceAdvice");
const coverageReview = document.querySelector("#coverageReview");
const documentTypeStatus = document.querySelector("#documentTypeStatus");
const fileMeta = document.querySelector("#fileMeta");
const extractStatus = document.querySelector("#extractStatus");
const generateStatus = document.querySelector("#generateStatus");
const questionInput = document.querySelector("#questionInput");
const supplementInput = document.querySelector("#supplementInput");
const extractSupplementBtn = document.querySelector("#extractSupplementBtn");
const askBtn = document.querySelector("#askBtn");
const askStatus = document.querySelector("#askStatus");
const qaAnswer = document.querySelector("#qaAnswer");
const qaPanel = document.querySelector("#qaPanel");
const qaInclude = document.querySelector("#qaInclude");
const includeAnswer = document.querySelector("#includeAnswer");
const applyAnswerBtn = document.querySelector("#applyAnswerBtn");
let pendingAnswer = null;
const sourceCount = document.querySelector("#sourceCount");
const sourceList = document.querySelector("#sourceList");
const paper = document.querySelector("#paper");
const sourceDialog = document.querySelector("#sourceDialog");
const dialogBody = document.querySelector("#dialogBody");
const closeDialogBtn = document.querySelector("#closeDialogBtn");
const redactionFilter = document.querySelector("#redactionFilter");
const confidenceFilter = document.querySelector("#confidenceFilter");
const statusFilter = document.querySelector("#statusFilter");
const fileFilter = document.querySelector("#fileFilter");
const manualSensitiveType = document.querySelector("#manualSensitiveType");
const imageRegionType = document.querySelector("#imageRegionType");
const addSelectionBtn = document.querySelector("#addSelectionBtn");
const customTermsInput = document.querySelector("#customRedactionTermsInput");
const saveCustomTerms = document.querySelector("#saveCustomRedactionTerms");
const addCustomTermsBtn = document.querySelector("#addCustomRedactionTermsBtn");
const customTermsList = document.querySelector("#customRedactionTermsList");
const customTermsStatus = document.querySelector("#customRedactionTermsStatus");
const togglePreviewBtn = document.querySelector("#togglePreviewBtn");
const candidateList = document.querySelector("#candidateList");
const redactionCount = document.querySelector("#redactionCount");
const selectionStatus = document.querySelector("#selectionStatus");
const confirmRedactionBtn = document.querySelector("#confirmRedactionBtn");
const redactionStatus = document.querySelector("#redactionStatus");
const redactionStats = document.querySelector("#redactionStats");
const confirmVisibleBtn = document.querySelector("#confirmVisibleBtn");
const cancelVisibleBtn = document.querySelector("#cancelVisibleBtn");
const restoreVisibleBtn = document.querySelector("#restoreVisibleBtn");
const undoBtn = document.querySelector("#undoBtn");
const redoBtn = document.querySelector("#redoBtn");
const textRedactionToolbar = document.querySelector("#textRedactionToolbar");
const textRedactionBatchbar = document.querySelector("#textRedactionBatchbar");
const imageRegionControls = document.querySelector("#imageRegionControls");
const candidateSummary = document.querySelector("#candidateSummary");
const redactionWorkspace = document.querySelector("#redactionWorkspace");
const parseWorkspace = document.querySelector("#parseWorkspace");
const openParseWorkspaceBtn = document.querySelector("#openParseWorkspaceBtn");
const downloadParsedBtn = document.querySelector("#downloadParsedBtn");
const closeParseWorkspaceBtn = document.querySelector("#closeParseWorkspaceBtn");
const confirmParseBtn = document.querySelector("#confirmParseBtn");
const parseCount = document.querySelector("#parseCount");
const parseStatus = document.querySelector("#parseStatus");
const showAllImagesBtn = document.querySelector("#showAllImagesBtn");
const parseWorkspaceCount = document.querySelector("#parseWorkspaceCount");
const parseSourceCount = document.querySelector("#parseSourceCount");
const parsePreviewPageNav = document.querySelector("#parsePreviewPageNav");
const parseSourceList = document.querySelector("#parseSourceList");
const parseLegacyPreviewWarning = document.querySelector("#parseLegacyPreviewWarning");
const openRedactionWorkspaceBtn = document.querySelector("#openRedactionWorkspaceBtn");
const downloadRedactedBtn = document.querySelector("#downloadRedactedBtn");
const closeRedactionWorkspaceBtn = document.querySelector("#closeRedactionWorkspaceBtn");
const workspaceRedactionCount = document.querySelector("#workspaceRedactionCount");
const redactionOperator = document.querySelector("#redactionOperator");
const exportDecisionCsvBtn = document.querySelector("#exportDecisionCsvBtn");
const exportDecisionJsonBtn = document.querySelector("#exportDecisionJsonBtn");
const legacyPreviewWarning = document.querySelector("#legacyPreviewWarning");
const previewPageNav = document.querySelector("#previewPageNav");
const mixedGroupDialog = document.querySelector("#mixedGroupDialog");
const mixedGroupMessage = document.querySelector("#mixedGroupMessage");
const keepMixedBtn = document.querySelector("#keepMixedBtn");
const confirmWholeGroupBtn = document.querySelector("#confirmWholeGroupBtn");
const contextReviewView = document.querySelector("#contextReviewView");
const documentReviewView = document.querySelector("#documentReviewView");
const outboundReviewView = document.querySelector("#outboundReviewView");
const outboundSummary = document.querySelector("#outboundSummary");
const outboundSegments = document.querySelector("#outboundSegments");
const redactionViewTabs = [...document.querySelectorAll("[data-redaction-view]")];
const layoutStatus = document.querySelector("#layoutStatus");
const compactBtn = document.querySelector("#compactBtn");
const pngBtn = document.querySelector("#pngBtn");
const docxBtn = document.querySelector("#docxBtn");
const markdownBtn = document.querySelector("#markdownBtn");
const jsonBtn = document.querySelector("#jsonBtn");
const pdfBtn = document.querySelector("#pdfBtn");
const contactDialog = document.querySelector("#contactDialog");
const contactCandidatesPanel = document.querySelector("#contactCandidates");
const contactNameInput = document.querySelector("#contactName");
const contactMethodInput = document.querySelector("#contactMethod");
const contactValidation = document.querySelector("#contactValidation");
const editContactBtn = document.querySelector("#editContactBtn");
let contactCandidates = [];
let selectedContactSourceIds = [];

function contactText(contact = currentOnePager?.business_contact) {
  return [contact?.name, contact?.method].filter(Boolean).join(" · ");
}

function contactMarkup() {
  const value = contactText();
  return value ? `<p class="business-contact"><strong>业务联系：</strong>${escapeHtml(value)}</p>` : "";
}

function showContactCandidates() {
  contactCandidatesPanel.innerHTML = contactCandidates.length ? contactCandidates.map((candidate, index) => {
    const sources = (candidate.source_ids || []).map((id) => (currentDocument?.segments || []).find((item) => item.id === id)).filter(Boolean);
    const sourceText = sources.map((source) => `${source.file_name} · 第 ${source.page} 页第 ${source.index} 段：${source.text}`).join("；");
    return `<button type="button" class="contact-candidate" data-contact-index="${index}">${escapeHtml(contactText(candidate) || "候选信息")}${candidate.ambiguous ? " · 关联待核对" : ""}<small>${escapeHtml(sourceText || "出处不可用")}</small></button>`;
  }).join("") : '<p class="hint">原始材料中未识别到明确标注的业务联系人或联系方式，请按需填写。</p>';
  contactCandidatesPanel.querySelectorAll("[data-contact-index]").forEach((button) => button.addEventListener("click", () => {
    const candidate = contactCandidates[Number(button.dataset.contactIndex)];
    contactNameInput.value = candidate.name || "";
    contactMethodInput.value = candidate.method || "";
    selectedContactSourceIds = candidate.source_ids || [];
    contactValidation.textContent = candidate.ambiguous ? "该材料存在多项姓名或联系方式，请核对后再加入。" : "";
  }));
}

async function openContactDialog(loadCandidates = false) {
  if (loadCandidates) {
    try {
      const response = await fetch("/api/contact-candidates", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: currentDocument.id, confirmation_token: confirmationToken }) });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || "联系人提取失败");
      contactCandidates = payload.candidates || [];
    } catch (_) { contactCandidates = []; }
  }
  const saved = currentOnePager?.business_contact || {};
  const first = saved.name || saved.method ? saved : contactCandidates.find((item) => !item.ambiguous) || contactCandidates[0] || {};
  contactNameInput.value = first.name || "";
  contactMethodInput.value = first.method || "";
  selectedContactSourceIds = first.source_ids || [];
  contactValidation.textContent = contactCandidates.length > 1 ? "找到多组信息，请核对姓名与联系方式是否属于同一人。" : "";
  showContactCandidates();
  contactDialog.showModal();
}

function setStep(step) {
  document.querySelectorAll(".step").forEach((node) => {
    node.classList.toggle("active", node.dataset.step === step);
  });
}
const exportHint = document.querySelector("#exportHint");

function guidanceValues() {
  const maxChars = maxCharsSelect.value === "custom" ? Number(customMaxChars.value) : Number(maxCharsSelect.value || 0);
  return {
    version: 1, max_chars: maxChars || null, detail_target: focusInput.value.trim(), detail_depth: detailDepth.value,
    presentation_mode: presentationModeSelect.value,
    tone: writingTone.value, include_overview: includeOverview.checked,
    include_full_structure: includeFullStructure.checked,
    include_architecture: includeArchitecture.checked, include_practice: includePractice.checked,
    must_keep: mustKeepInput.value.trim(),
    exclude_sections: excludeSectionsInput.value.trim(),
    explain_terms: explainTerms.checked,
    other_requirements: extraRequirements.value.trim(),
  };
}

function updateRequirementsPreview() {
  if (presentationModeSelect.value === "framework") {
    if (!["knowledge-auto", "knowledge-product", "knowledge-policy", "knowledge-operation"].includes(templateSelect.value)) templateSelect.value = "knowledge-auto";
    includeArchitecture.checked = true;
  }
  customMaxField.hidden = maxCharsSelect.value !== "custom";
  const r = guidanceValues();
  const role = audienceCustom.value.trim() || audienceSelect.value;
  requirementsPreview.textContent = `我是${role}，请将这份${documentTypeSelect.selectedOptions[0].text}整理为${templateSelect.selectedOptions[0].text}一纸通。` +
    `${r.max_chars ? `控制在 ${r.max_chars} 字以内。` : "按模板默认篇幅。"}` +
    `${r.detail_target ? `重点覆盖“${r.detail_target}”，${{ normal: "正常说明", detailed: "详细解释", brief: "简要提及" }[r.detail_depth]}。` : ""}` +
    `${r.exclude_sections ? `不呈现章节：${r.exclude_sections}。` : ""}` +
    `${r.include_overview ? "开头概括核心结论。" : "无需概括段。"}${r.include_full_structure ? "概括全文架构。" : "不展示全文架构。"}` +
    `${r.include_practice ? "突出实际工作要点。" : "不单列实际工作要点。"}${r.must_keep ? `必须保留：${r.must_keep}。` : ""}` +
    `${r.explain_terms ? "解释专业术语。" : ""}${r.presentation_mode === "framework" ? "采用横向框架图呈现。" : "采用纯文字版呈现。"}${r.other_requirements ? `其他要求：${r.other_requirements}。` : ""}`;
  const selectedSections = [r.include_overview, r.include_full_structure, r.include_practice].filter(Boolean).length;
  guidanceAdvice.textContent = r.max_chars && r.max_chars <= 200 && (selectedSections >= 2 || r.detail_depth === "detailed")
      ? "200 字版适合速读：建议聚焦一个重点主题，并减少概括、架构图或实务栏目。系统会优先保留关键事实。"
      : "成稿将按材料类型组织内容；原文没有依据的栏目不会用套话填满。";
  guidanceAdvice.classList.toggle("warning", Boolean(r.max_chars && r.max_chars <= 200 && selectedSections >= 2));
}

async function maskGuidanceText(value) {
  if (!value) return "";
  const request = async (confirmed) => {
    const response = await fetch("/api/desensitize", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: currentDocument.id, confirmation_token: confirmationToken, free_text: value, confirm_free_text: confirmed }) });
    const data = await response.json();
    if (!data.ok) throw new Error(data.error || "生成要求脱敏检查失败");
    return data;
  };
  let result = await request(false);
  if (result.free_text_candidates?.length) {
    const labels = result.free_text_candidates.map((item) => item.type_label).join("、");
    if (!window.confirm(`生成要求中发现${labels}，是否脱敏后继续？`)) throw new Error("已取消发送，请修改生成要求。");
    result = await request(true);
  }
  return result.masked_free_text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function candidateDisplayValue(candidate) {
  if (candidate?.type !== "secret") return candidate?.value || "";
  const value = String(candidate.value || "");
  return value.length <= 4 ? "••••" : `${value.slice(0, 2)}••••••${value.slice(-2)}`;
}

function friendlyError(error) {
  const message = error?.message || String(error);
  if (/load failed|failed to fetch|networkerror/i.test(message)) {
    return "上传或请求失败。常见原因是文件过大、服务刚重启、浏览器中断了上传，或本地服务未运行。请刷新页面后重试。";
  }
  return message;
}

function apiConnectionError(error) {
  const message = error?.message || String(error);
  if (/load failed|failed to fetch|networkerror|type\s*error|^typeerror/i.test(message)) {
    return "无法连接本地服务。请双击项目文件夹里的“启动一纸通.command”，看到浏览器自动打开后再试。";
  }
  return message;
}

function waitMilliseconds(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function normalizeApiKey(value) {
  return String(value || "")
    .trim()
    .replace(/^bearer\s+/i, "")
    .replace(/^(["'])(.*)\1$/, "$2")
    .replace(/\s+/g, "");
}

function reasoningChoicesForModel(model) {
  return onlineReasoningChoices[model] || reasoningChoices[model] || [];
}

function effectivePresetModel() {
  return presetManualModel.value.trim() || modelName.value;
}

function lastVerifiedModel(provider) {
  try { return JSON.parse(localStorage.getItem(`onepager_verified_model_${provider}`) || "null"); }
  catch (_) { return null; }
}

function selectedModelSettings() {
  if (modelProvider.value === "local") return { "X-Generation-Mode": "local" };
  if (modelProvider.value !== "custom") {
    const model = effectivePresetModel();
    const reasoning = modelReasoning.value;
    if (!/^[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}$/.test(model)) throw new Error("模型 ID 包含无效字符。");
    const levels = reasoningChoicesForModel(model);
    if (levels.length && !levels.some(([id]) => id === reasoning)) throw new Error("请选择当前模型支持的思考程度。");
    return { "X-LLM-Provider": modelProvider.value, "X-LLM-Model": model,
      "X-LLM-Reasoning": reasoning || "platform" };
  }
  const baseUrl = modelBaseUrl.value.trim().replace(/\/+$/, "");
  const model = customModelName.value.trim();
  let url;
  try { url = new URL(baseUrl); } catch (_) { throw new Error("请填写有效的 API Base URL。"); }
  if (url.protocol !== "https:" && !(url.protocol === "http:" && ["localhost", "127.0.0.1"].includes(url.hostname))) {
    throw new Error("API Base URL 应使用 HTTPS；本机服务可以使用 HTTP。");
  }
  if (!model) throw new Error("请填写模型名称。");
  return { "X-LLM-Base-URL": baseUrl, "X-LLM-Model": model };
}

function modelRequestHeaders() {
  if (modelProvider.value === "local") return { "X-Generation-Mode": "local" };
  if (!apiKey || !activeModelSettings["X-LLM-Model"]) return { "X-Generation-Mode": "local" };
  return { ...(apiKey ? { "X-LLM-API-Key": apiKey } : {}), ...activeModelSettings };
}

function setModelSettingsCollapsed(collapsed) {
  modelSettingsBody.hidden = collapsed;
  modelToggleBtn.setAttribute("aria-expanded", String(!collapsed));
  modelToggleBtn.textContent = collapsed ? "更换模型 / 展开设置" : "收起设置";
}

function updateModelConnectionSummary() {
  if (modelProvider.value === "local") {
    modelConnectionSummary.textContent = "本地规则 · 无需模型";
    return;
  }
  const provider = modelProvider.selectedOptions[0]?.textContent || "模型服务";
  const activeModel = activeModelSettings["X-LLM-Model"] ||
    (modelProvider.value === "custom" ? customModelName.value.trim() : effectivePresetModel());
  const reasoning = activeModelSettings["X-LLM-Reasoning"] || modelReasoning.value;
  modelConnectionSummary.textContent = apiKey
    ? `${provider} · ${activeModel} · ${reasoning === "none" ? "无思考" : reasoning === "platform" || !reasoning ? "思考由平台决定" : `思考 ${reasoning}`} · 已连接`
    : `${activeModel || provider} · 未连接；生成时使用本地规则`;
}

function invalidateModelConnection() {
  if (!apiKey) return;
  apiKey = "";
  modelDiscoveryCache.clear();
  activeModelSettings = {};
  clearApiBtn.disabled = true;
  apiKeyInput.placeholder = "在这里粘贴 API Key";
  apiStatus.textContent = "模型设置已更改；请重新输入密钥并测试连接。";
  modelRecommendation.textContent = "连接后会显示实际选用的模型。";
  updateModelConnectionSummary();
  setModelSettingsCollapsed(false);
}

function updateModelProvider() {
  invalidateModelConnection();
  apiKeyInput.value = "";
  modelDiscoveryCache.clear();
  modelSelectionManual = false;
  const local = modelProvider.value === "local";
  const custom = modelProvider.value === "custom";
  document.querySelectorAll(".custom-model-field").forEach((field) => { field.hidden = !custom; });
  document.querySelectorAll(".preset-model-field").forEach((field) => { field.hidden = local || custom; });
  document.querySelectorAll(".remote-model-field").forEach((field) => { field.hidden = local; });
  modelAdvancedSettings.hidden = local || custom;
  modelBaseUrl.value = "";
  presetManualModel.value = "";
  modelName.replaceChildren(...(modelChoices[modelProvider.value] || []).map(([id, label]) => new Option(label, id)));
  const lastVerified = lastVerifiedModel(modelProvider.value);
  if (lastVerified?.model) {
    if (modelChoices[modelProvider.value]?.some(([id]) => id === lastVerified.model)) modelName.value = lastVerified.model;
    else if (!local && !custom) presetManualModel.value = lastVerified.model;
  }
  updateReasoningChoices();
  modelRecommendation.textContent = local ? "本地规则整理草稿，不发送材料给模型服务。" : custom
    ? "其他服务需填写兼容接口地址和模型 ID；思考程度由该服务决定。"
    : lastVerified?.model ? `上次验证可用：${lastVerified.model}；请重新输入密钥并测试。`
      : "选好模型后点击“测试并使用”；实际使用的模型会显示在上方。";
  apiStatus.textContent = local ? "已选择本地规则，无需 API Key。" : "请连接所选模型。";
  updateModelConnectionSummary();
}

function updateReasoningChoices() {
  const previous = modelReasoning.value;
  const choices = [...reasoningChoicesForModel(effectivePresetModel())];
  if (!choices.length) choices.push(["platform", "由平台决定（新模型默认）"]);
  modelReasoning.replaceChildren(...choices.map(([id, label]) => new Option(label, id)));
  if (choices.some(([id]) => id === previous)) modelReasoning.value = previous;
  modelAdvancedSettings.hidden = modelProvider.value === "local" || modelProvider.value === "custom";
}

async function refreshModelChoices(candidate = normalizeApiKey(apiKeyInput.value) || apiKey, force = false) {
  const provider = modelProvider.value;
  if (!modelChoices[provider]) return;
  if (!candidate) {
    modelRecommendation.textContent = "输入 API Key 后可尝试更新模型列表；部分平台需在高级设置中手动填写新模型 ID。";
    return;
  }
  if (!/^[\x21-\x7E]+$/.test(candidate)) return;
  const lastQuery = modelDiscoveryCache.get(provider);
  if (!force && lastQuery?.key === candidate && Date.now() - lastQuery.at < 5 * 60 * 1000) return;
  refreshModelsBtn.disabled = true;
  modelRecommendation.textContent = "正在查询模型列表...";
  try {
    const response = await fetch("/api/model-choices", {
      method: "POST", headers: { "X-LLM-Provider": provider, "X-LLM-API-Key": candidate },
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "模型列表查询失败");
    if (modelProvider.value !== provider) return;
    modelDiscoveryCache.set(provider, {key: candidate, at: Date.now()});
    if (!payload.refreshed) {
      modelRecommendation.textContent = "模型列表未更新；可使用内置两款候选，或在高级设置中填写平台提供的新模型 ID 并测试。";
      return;
    }
    const oldModel = modelName.value;
    const oldRole = modelChoices[provider][1]?.[0] === oldModel ? 1 : 0;
    modelChoices[provider] = payload.models.map((id, index) => [id,
      `${index === 0 ? (id.includes("flash") ? "Flash / 快速" : provider === "kimi" ? "轻量" : "快速") : "旗舰"} · ${id}`]);
    for (const [model, levels] of Object.entries(payload.reasoning_levels || {})) {
      onlineReasoningChoices[model] = levels.map((id) => [id,
        ({ none: "无思考", minimal: "最低", low: "低", medium: "中", high: "高", xhigh: "高", max: "最高" })[id] || id]);
    }
    modelName.replaceChildren(...modelChoices[provider].map(([id, label]) => new Option(label, id)));
    if (modelSelectionManual) modelName.value = modelChoices[provider].some(([id]) => id === oldModel)
      ? oldModel : modelChoices[provider][oldRole][0];
    updateReasoningChoices();
    modelRecommendation.textContent = "已从平台更新可识别的快速模型与旗舰模型；请测试后使用。";
    if (apiKey) updateModelName();
  } catch (error) {
    modelRecommendation.textContent = `模型列表暂未更新：${apiConnectionError(error)}；仍可选择内置模型。`;
  } finally {
    refreshModelsBtn.disabled = false;
  }
}

function updateModelName() {
  if (apiKey && activeModelSettings["X-LLM-Model"]) {
    const activeModel = activeModelSettings["X-LLM-Model"];
    modelRecommendation.textContent = `当前仍使用：${activeModel}；新设置测试成功后才会切换。`;
    apiStatus.textContent = "设置已修改；点击“测试并使用”后才会切换，无需重复输入当前页面的密钥。";
  } else if (!apiKey) {
    modelRecommendation.textContent = "点击“测试并使用”后生效。";
  }
  updateModelConnectionSummary();
}

async function testApiConnection() {
  if (modelProvider.value === "local") return;
  const candidate = normalizeApiKey(apiKeyInput.value) || apiKey;
  if (!candidate) {
    apiStatus.textContent = "请先输入模型 API Key。";
    apiKeyInput.focus();
    return;
  }
  if (!/^[\x21-\x7E]+$/.test(candidate)) {
    apiStatus.textContent = "密钥中含有无法识别的字符。请从模型服务控制台重新复制 API Key。";
    apiKeyInput.focus();
    return;
  }
  if (modelProvider.value !== "custom") await refreshModelChoices(candidate);
  let settings;
  try { settings = selectedModelSettings(); } catch (error) {
    apiStatus.textContent = error.message;
    return;
  }
  const settingSnapshot = JSON.stringify([modelProvider.value, settings]);
  testApiBtn.disabled = true;
  apiStatus.textContent = "正在测试连接...";
  try {
    const requestOptions = { method: "POST", headers: { "X-LLM-API-Key": candidate, ...settings } };
    let response;
    try {
      response = await fetch("/api/test-llm", requestOptions);
    } catch (firstError) {
      await waitMilliseconds(500);
      try {
        response = await fetch("/api/test-llm", requestOptions);
      } catch (secondError) {
        let localServiceAvailable = false;
        try {
          const healthResponse = await fetch(`/?health_check=${Date.now()}`, { cache: "no-store" });
          localServiceAvailable = healthResponse.ok;
        } catch (_) { /* local service is not reachable */ }
        if (localServiceAvailable) {
          throw new Error("本地服务运行正常，但连接大模型服务的请求被中断。请检查网络和模型服务配置后重新点击“测试并使用”。");
        }
        throw secondError || firstError;
      }
    }
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "连接失败");
    if (settingSnapshot !== JSON.stringify([modelProvider.value, selectedModelSettings()])) {
      throw new Error("模型设置已更改，请重新点击“测试并使用”。");
    }
    apiKey = candidate;
    activeModelSettings = payload.model && payload.base_url
      ? { "X-LLM-Base-URL": payload.base_url, "X-LLM-Model": payload.model,
        ...(payload.reasoning ? { "X-LLM-Reasoning": payload.reasoning } : {}),
        ...(payload.json_mode === "prompt" ? { "X-LLM-JSON-Mode": "prompt" } : {}) }
      : settings;
    if (payload.model && modelProvider.value !== "custom" && !presetManualModel.value.trim()) modelName.value = payload.model;
    if (payload.model && modelProvider.value === "custom") customModelName.value = payload.model;
    if (payload.model && modelProvider.value !== "custom") {
      try { localStorage.setItem(`onepager_verified_model_${modelProvider.value}`,
        JSON.stringify({ model: payload.model, verified_at: Date.now() })); } catch (_) { /* optional cache */ }
    }
    apiKeyInput.value = "";
    apiKeyInput.placeholder = "已连接；如需更换，请输入新密钥";
    clearApiBtn.disabled = false;
    modelRecommendation.textContent = payload.model ? `当前使用：${payload.model}` : "使用服务端配置的模型。";
    apiStatus.textContent = payload.message || "大模型服务已连接。现在可以生成一纸通和提问。";
    updateModelConnectionSummary();
    setModelSettingsCollapsed(true);
  } catch (error) {
    apiStatus.textContent = `页面密钥连接失败：${apiConnectionError(error)}`;
  } finally {
    testApiBtn.disabled = false;
  }
}

function getSourceMap() {
  const map = new Map();
  allMaskedSegments().forEach((segment) => map.set(segment.id, segment));
  return map;
}

function highlightedSourceText(segment) {
  const ranges = [];
  sensitiveCandidates.forEach((candidate) => {
    candidate.occurrences.forEach((occurrence) => {
      if (occurrence.target === "text" && occurrence.segment_id === segment.id) {
        ranges.push({
          start: occurrence.start,
          end: occurrence.end,
          label: candidate.replacement,
          candidateId: candidate.id,
          occurrenceId: occurrence.id,
          selected: occurrenceStatus(occurrence) !== "cancelled",
          status: occurrenceStatus(occurrence),
          confidence: occurrence.confidence || candidate.confidence || "high",
          sensitivity: occurrence.sensitivity || candidate.sensitivity || "high",
          kind: candidate.type,
          manual: Boolean(candidate.manual),
          reason: occurrence.reason || candidate.reason || "",
        });
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
    output += escapeHtml(segment.text.slice(position, item.start));
    const highlighted = item.status !== "cancelled";
    const tag = highlighted ? "mark" : "span";
    const stateClass = highlighted ? "selected" : "excluded";
    const action = highlighted ? `将替换为 ${item.label}；单击取消全文相同标记，双击只切换当前一处` : "当前保留原文；单击恢复全文相同标记，双击只切换当前一处";
    output += `<${tag} class="sensitive-mark ${stateClass}" tabindex="0" role="button"
      data-candidate-id="${escapeHtml(item.candidateId)}" data-occurrence-id="${escapeHtml(item.occurrenceId)}"
      data-sensitivity="${escapeHtml(item.sensitivity)}" title="${escapeHtml(action)}">${escapeHtml(item.kind === "secret" ? "••••••••" : segment.text.slice(item.start, item.end))}</${tag}>`;
    position = item.end;
  });
  return output + escapeHtml(segment.text.slice(position));
}

function maskedPreviewText(segment) {
  const ranges = [];
  sensitiveCandidates.forEach((candidate) => {
    candidate.occurrences.forEach((occurrence) => {
      if (occurrenceStatus(occurrence) !== "cancelled" && occurrence.target === "text" && occurrence.segment_id === segment.id) {
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
    output += escapeHtml(segment.text.slice(position, item.start));
    output += `<span class="preview-replacement">${escapeHtml(item.replacement)}</span>`;
    position = item.end;
  });
  return output + escapeHtml(segment.text.slice(position));
}

function regionTypeLabel(type) {
  return "脱敏区域";
}

function pushHistorySnapshot(snapshot, action = "修改图片脱敏区域") {
  undoStack.push(snapshot);
  if (undoStack.length > 100) undoStack.shift();
  redoStack = [];
  logRedactionAction(action);
  updateHistoryButtons();
}

function drawImageCanvas(canvas) {
  const stage = canvas.closest(".image-stage");
  const image = stage?.querySelector("img");
  if (!image || !image.complete || !image.clientWidth) return;
  canvas.width = Math.max(1, Math.round(image.clientWidth));
  canvas.height = Math.max(1, Math.round(image.clientHeight));
  canvas.style.width = `${image.clientWidth}px`;
  canvas.style.height = `${image.clientHeight}px`;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  const regions = imageRegions.filter((region) => region.asset_id === canvas.dataset.assetId);
  regions.forEach((region) => {
    const x = region.x * canvas.width;
    const y = region.y * canvas.height;
    const width = region.width * canvas.width;
    const height = region.height * canvas.height;
    if (showMaskedPreview && region.status !== "cancelled") {
      const tiny = document.createElement("canvas");
      tiny.width = Math.max(2, Math.min(18, Math.round(width / 8)));
      tiny.height = Math.max(2, Math.min(18, Math.round(height / 8)));
      const tinyContext = tiny.getContext("2d");
      tinyContext.drawImage(image, region.x * image.naturalWidth, region.y * image.naturalHeight,
        region.width * image.naturalWidth, region.height * image.naturalHeight, 0, 0, tiny.width, tiny.height);
      context.imageSmoothingEnabled = false;
      context.drawImage(tiny, 0, 0, tiny.width, tiny.height, x, y, width, height);
      context.imageSmoothingEnabled = true;
    } else {
      context.fillStyle = "rgba(214, 58, 58, .16)";
      context.fillRect(x, y, width, height);
    }
    context.strokeStyle = "#d63a3a";
    context.lineWidth = 2;
    context.setLineDash([]);
    context.strokeRect(x, y, width, height);
    context.setLineDash([]);
    context.fillStyle = context.strokeStyle;
    context.fillRect(x + width - 5, y + height - 5, 10, 10);
  });
}

function redrawImageCanvases() {
  sourceList.querySelectorAll(".redaction-canvas").forEach(drawImageCanvas);
}

function setupImageEditors() {
  sourceList.querySelectorAll("[data-add-image-region]").forEach((button) => button.addEventListener("click", () => {
    recordHistory();
    imageRegions.push({ id: `region-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
      asset_id: button.dataset.addImageRegion, type: "custom", status: "confirmed",
      x: .3, y: .3, width: .4, height: .4, created_at: Math.floor(Date.now() / 1000) });
    invalidateRedaction("图片脱敏区域已修改，请重新确认。");
  }));
  sourceList.querySelectorAll("[data-region-field]").forEach((input) => input.addEventListener("change", () => {
    const region = imageRegions.find((item) => item.id === input.closest("[data-region-id]")?.dataset.regionId);
    if (!region) return;
    const value = Number(input.value) / 100;
    if (!Number.isFinite(value) || value < 0 || value > 1) { input.value = Math.round(region[input.dataset.regionField] * 100); return; }
    const next = { ...region, [input.dataset.regionField]: value };
    if (next.x + next.width > 1 || next.y + next.height > 1 || next.width < .01 || next.height < .01) {
      input.value = Math.round(region[input.dataset.regionField] * 100);
      return;
    }
    recordHistory();
    region[input.dataset.regionField] = value;
    invalidateRedaction("图片脱敏区域已修改，请重新确认。");
  }));
  sourceList.querySelectorAll(".image-stage img").forEach((image) => {
    const canvas = image.parentElement.querySelector("canvas");
    if (image.complete) drawImageCanvas(canvas);
    else image.addEventListener("load", () => drawImageCanvas(canvas), { once: true });
  });
  sourceList.querySelectorAll(".redaction-canvas").forEach((canvas) => {
    canvas.addEventListener("pointerdown", (event) => {
      if (showMaskedPreview) return;
      const rect = canvas.getBoundingClientRect();
      const point = { x: (event.clientX - rect.left) / rect.width, y: (event.clientY - rect.top) / rect.height };
      const regions = imageRegions.filter((region) => region.asset_id === canvas.dataset.assetId);
      const hit = [...regions].reverse().find((region) => point.x >= region.x && point.x <= region.x + region.width
        && point.y >= region.y && point.y <= region.y + region.height);
      const snapshot = redactionSnapshot();
      let mode = "draw";
      let region = hit;
      if (hit) {
        const handleDistance = Math.hypot(point.x - (hit.x + hit.width), point.y - (hit.y + hit.height));
        mode = handleDistance < 0.035 ? "resize" : "move";
      } else {
        region = {
          id: `region-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
          asset_id: canvas.dataset.assetId,
          type: "custom",
          status: "confirmed",
          x: point.x, y: point.y, width: 0, height: 0,
          created_at: Math.floor(Date.now() / 1000),
        };
        imageRegions.push(region);
      }
      activeCanvasInteraction = { canvas, region, mode, start: point, original: deepClone(region), snapshot, moved: false };
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      const action = activeCanvasInteraction;
      if (!action || action.canvas !== canvas) return;
      const rect = canvas.getBoundingClientRect();
      const point = { x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)), y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)) };
      const dx = point.x - action.start.x;
      const dy = point.y - action.start.y;
      action.moved = action.moved || Math.abs(dx) + Math.abs(dy) > 0.004;
      if (action.mode === "draw") {
        action.region.x = Math.min(action.start.x, point.x);
        action.region.y = Math.min(action.start.y, point.y);
        action.region.width = Math.abs(dx);
        action.region.height = Math.abs(dy);
      } else if (action.mode === "move") {
        action.region.x = Math.max(0, Math.min(1 - action.region.width, action.original.x + dx));
        action.region.y = Math.max(0, Math.min(1 - action.region.height, action.original.y + dy));
        action.region.status = "confirmed";
      } else {
        action.region.width = Math.max(0.002, Math.min(1 - action.original.x, action.original.width + dx));
        action.region.height = Math.max(0.002, Math.min(1 - action.original.y, action.original.height + dy));
        action.region.status = "confirmed";
      }
      drawImageCanvas(canvas);
    });
    canvas.addEventListener("pointerup", () => {
      const action = activeCanvasInteraction;
      if (!action || action.canvas !== canvas) return;
      activeCanvasInteraction = null;
      if (action.mode === "draw" && (action.region.width < 0.002 || action.region.height < 0.002)) {
        imageRegions = imageRegions.filter((item) => item.id !== action.region.id);
        renderSources();
        return;
      }
      pushHistorySnapshot(action.snapshot);
      invalidateRedaction("图片脱敏区域已修改，请重新确认。");
      renderCandidates();
    });
  });
  sourceList.querySelectorAll(".region-delete").forEach((button) => button.addEventListener("click", () => {
    recordHistory();
    imageRegions = imageRegions.filter((item) => item.id !== button.dataset.regionId);
    invalidateRedaction("图片脱敏区域已删除，请重新确认。");
    renderCandidates();
  }));
}

function openRedactionWorkspace() {
  if (!currentDocument || !parsingConfirmed) {
    parseStatus.textContent = "请先确认本地解析结果，再进入信息脱敏。";
    return;
  }
  redactionWorkspace.hidden = false;
  document.body.classList.add("redaction-workspace-open");
  selectionStatus.textContent = "如有遗漏，请在同一段材料中选中文字，再点击“将选中文字设为脱敏”。";
  renderSources();
  renderCandidates();
  requestAnimationFrame(() => sourceList.focus());
}

function closeRedactionWorkspace() {
  redactionWorkspace.hidden = true;
  document.body.classList.remove("redaction-workspace-open");
}

function allDocumentPreviews() {
  return [currentDocument?.document_preview, ...supplementalDocumentPreviews].filter(Boolean);
}

function parseSegment(segmentId) {
  const segment = allOriginalSegments().find((item) => item.id === segmentId);
  if (!segment) return "";
  if (segment.source_type === "audio") {
    const seekPoints = [Number(segment.start_ms), ...audioSeekPoints(segment)];
    return `<div class="audio-transcript-row" data-segment-id="${escapeHtml(segment.id)}">
    <span class="audio-range">${formatAudioTime(segment.start_ms)}–${formatAudioTime(segment.end_ms)}</span>
    <input class="audio-speaker" aria-label="说话人" maxlength="40" placeholder="说话人（可选）" value="${escapeHtml(segment.speaker || "")}">
    <textarea class="audio-text" aria-label="转写文字" rows="5" maxlength="2000">${escapeHtml(segment.text)}</textarea>
    <div class="audio-seek-points"><span>片段回放 · 点击可重听</span>${seekPoints.map((point, index) =>
      `<button type="button" class="audio-seek audio-seek-point" data-seek="${point}" data-end="${seekPoints[index + 1] || segment.end_ms}" title="播放 ${formatAudioTime(point)} 至 ${formatAudioTime(seekPoints[index + 1] || segment.end_ms)}">${formatAudioTime(point)}</button>`).join("")}</div>
  </div>`;
  }
  return `<div class="source-text parse-text-block" data-segment-id="${escapeHtml(segment.id)}">${escapeHtml(segment.text)}</div>`;
}

function formatAudioTime(ms) {
  const seconds = Math.floor(Number(ms || 0) / 1000);
  return `${String(Math.floor(seconds / 3600)).padStart(2, "0")}:${String(Math.floor(seconds % 3600 / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function audioSeekPoints(segment) {
  const points = [];
  let last = Number(segment.start_ms || 0);
  const end = Number(segment.end_ms || 0);
  for (const fragment of (segment.fragments || []).slice(1)) {
    const start = Number(fragment.start_ms || 0);
    if (start - last >= 12000 && end - start >= 4000) {
      points.push(start);
      last = start;
    }
  }
  return points;
}

function audioPlayer() {
  return currentDocument?.source_type === "audio" ? `<audio controls preload="metadata" src="${escapeHtml(currentDocument.audio_url)}"></audio>` : "";
}

function clearBoundedPlayback() {
  if (!boundedPlayback) return;
  const { player, button, onTimeUpdate, onPause } = boundedPlayback;
  player.removeEventListener("timeupdate", onTimeUpdate);
  player.removeEventListener("pause", onPause);
  button?.classList.remove("is-playing");
  boundedPlayback = null;
}

function seekAudio(ms, endMs, button) {
  const player = !parseWorkspace.hidden ? parseWorkspace.querySelector("audio") : document.querySelector("#sourceDialog audio");
  if (!player) return;
  clearBoundedPlayback();
  const start = Number(ms || 0) / 1000;
  const end = Number(endMs || 0) / 1000;
  player.currentTime = start;
  const onTimeUpdate = () => {
    if (end > start && player.currentTime >= end - 0.05) {
      player.pause();
      clearBoundedPlayback();
    }
  };
  const onPause = () => clearBoundedPlayback();
  boundedPlayback = { player, button, onTimeUpdate, onPause };
  player.addEventListener("timeupdate", onTimeUpdate);
  player.addEventListener("pause", onPause);
  button?.classList.add("is-playing");
  player.play().catch(() => clearBoundedPlayback());
}

function parseImage(assetId) {
  const asset = allImageAssets().find((item) => item.id === assetId);
  if (!asset) return "";
  const isChart = asset.source?.kind === "pptx_chart";
  const label = isChart ? "图表" : "图片";
  return `<figure class="parse-image-block">
    <img src="${escapeHtml(asset.preview_url)}" alt="${escapeHtml(asset.file_name)} 第${asset.page}页${label}">
    <figcaption>${label} · ${asset.original_width}×${asset.original_height}${isChart ? " · 数据已提取" : ""}</figcaption>
  </figure>`;
}

function renderParseSources() {
  clearBoundedPlayback();
  if (!currentDocument) {
    parseCount.textContent = "请先上传并解析材料";
    parseWorkspaceCount.textContent = "请先解析材料";
    parseSourceCount.textContent = "0 段文字 · 0 张图片/图表";
    parsePreviewPageNav.innerHTML = "";
    parseSourceList.innerHTML = '<div class="empty-state small">解析后这里会按文件和页码顺序显示文字与图片。</div>';
    return;
  }
  const previews = allDocumentPreviews();
  const isAudio = currentDocument.source_type === "audio";
  const pages = previews.reduce((sum, preview) => sum + (preview.pages || []).length, 0);
  const summary = isAudio ? `${allOriginalSegments().length} 段转写文字 · 请核对并修正` : `${allOriginalSegments().length} 段文字 · ${allImageAssets().length} 张图片/图表 · ${pages || currentDocument.page_count || 1} 页`;
  parseCount.textContent = summary;
  parseWorkspaceCount.textContent = currentDocument.file_name;
  parseSourceCount.textContent = summary;
  parseLegacyPreviewWarning.hidden = !previews.some((preview) => preview.legacy_layout_warning);
  parsePreviewPageNav.innerHTML = previews.flatMap((preview, previewIndex) => (preview.pages || []).map((page, pageIndex) =>
    `<button type="button" data-parse-target="parse-preview-${previewIndex}-page-${page.number}" data-preview-index="${previewIndex}" data-page-index="${pageIndex}">${preview.format === "pptx" ? "幻灯片" : "第"}${page.number}${preview.format === "pptx" ? "" : "页"}</button>`)).join("");
  parseSourceList.innerHTML = (isAudio ? audioPlayer() : "") + (previews.length ? previews.map((preview, index) => `
    <section class="preview-document-group">
      ${preview.legacy_layout_warning ? '<p class="legacy-inline-note">旧版格式内容顺序预览</p>' : ""}
      ${preview.mode === "paged" ? renderParsePagedPreview(preview, index) : renderParseFlowPreview(preview, index)}
      ${previewMoreButton(preview, index, true)}
    </section>`).join("") : '<div class="empty-state small">当前材料没有可显示的文字或图片。</div>');
  parseSourceList.querySelectorAll(".audio-seek").forEach((button) => button.addEventListener("click", () => seekAudio(button.dataset.seek, button.dataset.end, button)));
  parsePreviewPageNav.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
    const key = `page-${button.dataset.previewIndex}`;
    visiblePreviewItems.set(key, Math.max(visiblePreviewItems.get(key) || previewPageBatch, Number(button.dataset.pageIndex) + 1));
    renderParseSources();
    document.getElementById(button.dataset.parseTarget)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }));
  setupPreviewMore(parseSourceList, true);
}

function openParseWorkspace() {
  if (!currentDocument) return;
  renderParseSources();
  parseWorkspace.hidden = false;
  document.body.classList.add("redaction-workspace-open");
}

function closeParseWorkspace() {
  parseWorkspace.querySelector("audio")?.pause();
  clearBoundedPlayback();
  parseWorkspace.hidden = true;
  if (redactionWorkspace.hidden) document.body.classList.remove("redaction-workspace-open");
}

async function confirmParsing() {
  if (!currentDocument) return;
  if (currentDocument.source_type === "audio") {
    confirmParseBtn.disabled = true;
    try {
      const segments = [...parseSourceList.querySelectorAll(".audio-transcript-row")].map((row) => ({
        id: row.dataset.segmentId, text: row.querySelector(".audio-text").value,
        speaker: row.querySelector(".audio-speaker").value,
      }));
      const response = await fetch("/api/audio/confirm-transcript", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: currentDocument.id, document_version: currentDocument.document_version, segments }) });
      const result = await response.json();
      if (!result.ok) throw new Error(result.error);
      currentDocument.segments = result.segments;
      currentDocument.document_version = result.document_version;
      sensitiveCandidates = result.sensitive_candidates;
      sensitiveCandidates.forEach((candidate) => candidate.occurrences.forEach((occurrence) => setOccurrenceStatus(occurrence,
        candidate.default_highlight === false || occurrence.selected === false ? "cancelled" : "confirmed")));
      renderSources(); renderCandidates();
    } catch (error) { parseStatus.textContent = friendlyError(error); confirmParseBtn.disabled = false; return; }
    confirmParseBtn.disabled = false;
  }
  parsingConfirmed = true;
  if (savedCustomTerms.length || sessionCustomTerms.length) {
    try { await detectSensitive(); }
    catch (error) { parseStatus.textContent = friendlyError(error); parsingConfirmed = false; return; }
  }
  parseStatus.textContent = "本地解析结果已确认，可以进入信息脱敏。";
  openParseWorkspaceBtn.textContent = "重新查看解析结果";
  openRedactionWorkspaceBtn.disabled = false;
  closeParseWorkspace();
  openRedactionWorkspace();
}

function renderSources() {
  if (!currentDocument) {
    sourceCount.textContent = "0 段 · 0 张图片";
    sourceList.innerHTML = '<div class="empty-state small">抽取后这里会完整显示上传的文档。</div>';
    previewPageNav.innerHTML = "";
    return;
  }
  const previews = allDocumentPreviews();
  const pages = previews.reduce((sum, preview) => sum + (preview.pages || []).length, 0);
  sourceCount.textContent = `${allOriginalSegments().length} 段 · ${pages || currentDocument.page_count || 1} 页 · ${allImageAssets().length} 张图片/图表`;
  legacyPreviewWarning.hidden = !previews.some((preview) => preview.legacy_layout_warning);
  previewPageNav.innerHTML = previews.flatMap((preview, previewIndex) => (preview.pages || []).map((page, pageIndex) =>
    `<button type="button" data-preview-target="preview-${previewIndex}-page-${page.number}" data-preview-index="${previewIndex}" data-page-index="${pageIndex}">${preview.format === "pptx" ? "幻灯片" : "第"}${page.number}${preview.format === "pptx" ? "" : "页"}</button>`)).join("");
  sourceList.innerHTML = previews.length ? previews.map((preview, index) => `
    <section class="preview-document-group">
      ${preview.legacy_layout_warning ? '<p class="legacy-inline-note">旧版格式内容顺序预览</p>' : ""}
      ${preview.mode === "paged" ? renderPagedPreview(preview, index) : renderFlowPreview(preview, index)}
      ${previewMoreButton(preview, index)}
    </section>`).join("") : '<div class="empty-state small">当前材料没有可显示的内容。</div>';
  previewPageNav.querySelectorAll("button").forEach((button) => button.addEventListener("click", () => {
    const key = `page-${button.dataset.previewIndex}`;
    visiblePreviewItems.set(key, Math.max(visiblePreviewItems.get(key) || previewPageBatch, Number(button.dataset.pageIndex) + 1));
    renderSources();
    document.getElementById(button.dataset.previewTarget)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }));
  setupPreviewMore(sourceList, false);
  setupImageEditors();
}


function sourceSummary(item) {
  const sources = item.sources || [];
  if (!sources.length) return "无出处";
  if (sources.some((source) => source.source_type === "audio")) return `来源：录音 ${sources.map((source) => `${formatAudioTime(source.start_ms)}–${formatAudioTime(source.end_ms)}`).join("、")}`;
  const locations = [...new Set(sources.map((source) => source.sheet ? `「${source.sheet}」第${source.index}行` : `第${source.page}页`))];
  return `来源：${locations.join("、")}`;
}

function showSources(sourceIds) {
  const sourceMap = getSourceMap();
  const sources = sourceIds.map((id) => sourceMap.get(id)).filter(Boolean);
  dialogBody.innerHTML = (sources.some((source) => source.source_type === "audio") ? audioPlayer() : "") + (sources.length
    ? sources
        .map(
          (source) => `
            <article class="dialog-source">
              <strong>${escapeHtml(source.file_name)} · ${escapeHtml(source.id)} · ${source.source_type === "audio" ? `${formatAudioTime(source.start_ms)}–${formatAudioTime(source.end_ms)}` : source.sheet ? `工作表「${escapeHtml(source.sheet)}」第 ${source.index} 行` : `第 ${source.page} 页第 ${source.index} 段`}</strong>
              ${source.source_type === "audio" ? `<button class="ghost audio-seek" data-seek="${source.start_ms}" data-end="${source.end_ms}">播放这段</button>` : ""}
              <p>${escapeHtml(source.text)}</p>
            </article>
          `,
        )
        .join("")
    : '<p class="hint">这条内容没有可用出处，需要人工确认依据。</p>');
  sourceDialog.showModal();
  dialogBody.querySelectorAll(".audio-seek").forEach((button) => button.addEventListener("click", () => seekAudio(button.dataset.seek, button.dataset.end, button)));
}

const moduleLabels = {
  conclusions: "核心结论",
  metrics: "关键数据",
  logic: "逻辑结构",
  actions: "重点事项",
  supplements: "补充信息",
  overview: "培训内容概览",
  knowledge_architecture: "知识架构图",
  knowledge_modules: "核心知识要点",
  practical_application: "实际工作应用",
  key_reminders: "关键提醒",
};

function checkPageOverflow() {
  if (!currentOnePager || !paper.isConnected) return false;
  const body = paper.querySelector(".knowledge-body, .one-pager-body");
  const footer = paper.querySelector(".one-pager-footer");
  const overflowPixels = () => {
    const contentBottom = body ? Math.max(body.getBoundingClientRect().bottom,
      ...Array.from(body.children, (child) => child.getBoundingClientRect().bottom)) : 0;
    return Math.max(
      0,
      paper.scrollHeight - paper.clientHeight,
      paper.scrollWidth - paper.clientWidth,
      body ? body.scrollHeight - body.clientHeight : 0,
      body ? body.scrollWidth - body.clientWidth : 0,
      footer && body ? contentBottom - footer.getBoundingClientRect().top + 5 : 0,
    );
  };
  paper.classList.remove("preview-expanded");
  paper.classList.add("measuring-layout");
  const exportExtra = overflowPixels();
  const overflow = exportExtra > 3;
  paper.classList.remove("measuring-layout");
  const previewExtra = overflowPixels();
  const previewExpanded = overflow || previewExtra > 3;
  paper.classList.toggle("preview-expanded", previewExpanded);
  paper.classList.toggle("page-overflow", overflow);
  layoutStatus.textContent = overflow
    ? `内容超出一页约 ${Math.ceil(exportExtra)}px；预览已展开，请压缩或删减后导出`
    : previewExpanded ? "导出版面符合一页要求；编辑预览已展开显示全部内容" : "已通过一页版面检查";
  layoutStatus.classList.toggle("error", overflow);
  const limit = currentOnePager.generation_requirements?.max_chars;
  const count = visibleContentChars(currentOnePager);
  const lengthExceeded = Number.isInteger(limit) && count > limit;
  if (lengthExceeded) layoutStatus.textContent += `；当前 ${count} 字，超出 ${limit} 字上限，请调整要求或内容`;
  const hasIncludedAnswer = Boolean(currentOnePager.qa_items?.length);
  const hasContact = Boolean(contactText());
  const framework = currentOnePager.generation_requirements?.presentation_mode === "framework";
  const diagramHidden = currentOnePager.schema_version === "3.0" && !framework;
  const allExportsBlocked = overflow || lengthExceeded;
  let exportMessage = "";
  if (allExportsBlocked) {
    const reasons = [];
    if (overflow) reasons.push("内容超出 A4 单页");
    if (lengthExceeded) reasons.push(`正文 ${count} 字，超出 ${limit} 字上限`);
    exportMessage = `${reasons.join("；")}。请精简内容后再导出。`;
  }
  exportHint.textContent = exportMessage;
  exportHint.hidden = !exportMessage;
  exportHint.classList.toggle("error", allExportsBlocked);
  layoutStatus.classList.toggle("error", allExportsBlocked);
  [pngBtn, docxBtn, markdownBtn, jsonBtn, pdfBtn].forEach((button) => { button.disabled = !currentOnePager || allExportsBlocked; });
  compactBtn.disabled = !currentOnePager;
  compactBtn.textContent = currentOnePager?.complete_result ? "恢复完整内容" : "一键压缩";
  return allExportsBlocked;
}

function visibleContentChars(result) {
  const clone = JSON.parse(JSON.stringify(result));
  if (clone.generation_requirements?.include_overview === false) clone.meta.overview = "";
  if (clone.generation_requirements?.include_full_structure === false) clone.original_structure = [];
  if (clone.generation_requirements?.include_architecture === false || clone.knowledge_architecture?.show_diagram === false || !(clone.knowledge_architecture?.modules || []).length) clone.knowledge_architecture = { modules: [] };
  if (clone.generation_requirements?.include_knowledge_modules === false) clone.knowledge_modules = [];
  if (clone.generation_requirements?.include_practice === false) clone.practical_application = [];
  const fields = (clone.qa_items || []).flatMap((item) => [item.question, item.answer]);
  if (clone.business_contact?.name || clone.business_contact?.method) fields.push("业务联系", clone.business_contact.name, clone.business_contact.method);
  if (clone.schema_version === "3.0") {
    const meta = clone.meta || {};
    fields.push(meta.title, meta.overview);
    (clone.original_structure || []).forEach((item) => fields.push(item.title));
    fields.push(clone.knowledge_architecture?.central_topic);
    (clone.knowledge_architecture?.modules || []).forEach((item) => fields.push(item.title, item.description));
    (clone.knowledge_modules || []).forEach((group) => { fields.push(group.title); (group.points || []).forEach((item) => fields.push(item.text)); });
    (clone.practical_application || []).forEach((group) => { fields.push(group.title); (group.items || []).forEach((item) => fields.push(item.text)); });
    (clone.key_reminders || []).forEach((item) => fields.push(item.text));
  } else {
    fields.push(clone.meta?.title, clone.meta?.subtitle);
    (clone.conclusions || []).forEach((item) => fields.push(item.text));
    (clone.metrics || []).forEach((item) => fields.push(item.label, item.value, item.comparison));
    (clone.logic?.nodes || []).forEach((item) => fields.push(item.title, item.text));
    (clone.actions || []).forEach((item) => fields.push(item.text, item.owner, item.due));
    (clone.supplements || []).forEach((item) => fields.push(item.term, item.explanation));
  }
  return fields.reduce((sum, item) => sum + String(item || "").length, 0);
}

function updateExportButtons() {
  const disabled = !currentOnePager;
  [compactBtn, pngBtn, docxBtn, markdownBtn, jsonBtn, pdfBtn].forEach((button) => { button.disabled = disabled; });
  if (disabled) {
    layoutStatus.textContent = "生成后自动检查是否超出一页";
    exportHint.textContent = "";
    exportHint.hidden = true;
  }
}

function decisionManifestCsv() {
  if (!decisionManifest) return "";
  const headers = ["规则版本", "文档版本", "词形", "规范词形", "类别", "敏感级别", "规则来源", "组状态", "实例编号", "文件", "页码", "片段", "起始偏移", "结束偏移", "上下文", "判定结果", "操作来源", "操作人", "操作时间", "确认时间", "替换代号"];
  const quote = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
  const rows = (decisionManifest.text_decisions || []).map((item) => [item.rule_version || decisionManifest.rule_version,
    decisionManifest.document_version, item.term, item.normalized_term, item.category || item.type,
    item.sensitivity, (item.rule_ids || []).join("|"), item.group_state, item.occurrence_id, item.file_name, item.page,
    item.segment_id, item.start, item.end, item.context, item.decision, item.decision_origin, item.operator,
    item.operation_time, item.confirmed_at, item.replacement]);
  return `\uFEFF${[headers, ...rows].map((row) => row.map(quote).join(",")).join("\r\n")}`;
}

function exportDecisionManifest(format) {
  if (!decisionManifest) return;
  const base = (currentDocument?.file_name || "脱敏判定清单").replace(/\.[^.]+$/, "");
  if (format === "csv") downloadBlob(new Blob([decisionManifestCsv()], { type: "text/csv;charset=utf-8" }), `${base}-脱敏判定清单.csv`);
  else downloadBlob(new Blob([JSON.stringify(decisionManifest, null, 2)], { type: "application/json;charset=utf-8" }), `${base}-脱敏判定清单.json`);
}

async function clearServerDocument(documentId) {
  const response = await fetch("/api/document/clear", { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ document_id: documentId }) });
  const payload = await response.json();
  if (!payload.ok) throw new Error(payload.error || "本地材料清理失败，请重试。");
}

async function extractFile(includeAllImages = false) {
  const file = fileInput.files?.[0];
  if (!file) {
    extractStatus.textContent = "请先选择文件。";
    return;
  }

  const formData = new FormData();
  formData.append("file", file);
  if (includeAllImages) formData.append("include_all_images", "1");
  extractBtn.disabled = true;
  clearBtn.disabled = true;
  showAllImagesBtn.disabled = true;
  generateBtn.disabled = true;
  const extractionStarted = Date.now();
  extractStatus.textContent = "正在上传并解析材料，请保持页面打开。";
  extractStatus.classList.remove("error");
  const extractionTimer = setInterval(() => {
    const seconds = Math.floor((Date.now() - extractionStarted) / 1000);
    extractStatus.textContent = `正在本机处理材料 · 已等待 ${seconds} 秒。大文件和图片识别可能需要更久，请勿重复提交。`;
  }, 5000);

  try {
    let documentResult;
    if (isAudioFile(file)) {
      if (file.size > 200 * 1024 * 1024) throw new Error("录音超过 200MB 上限。");
      const upload = await fetch("/api/audio/upload", { method: "POST", headers: {
        "X-Audio-File-Name": encodeURIComponent(file.name), "X-Audio-Terms": encodeURIComponent(audioTermsInput.value),
      }, body: file });
      const started = await upload.json();
      if (!started.ok) throw new Error(started.error || "录音上传失败");
      activeAudioJob = started.job_id;
      while (true) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        const response = await fetch(`/api/audio/status/${started.job_id}`);
        const progress = await response.json();
        if (activeAudioJob !== started.job_id) throw new Error("转写已取消。");
        if (!progress.ok) throw new Error(progress.error);
        extractStatus.textContent = progress.message;
        if (progress.status === "error") throw new Error(progress.message);
        if (progress.status === "done") { documentResult = progress.document; activeAudioJob = ""; break; }
      }
    } else {
      const response = await fetch("/api/extract", { method: "POST", body: formData });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || "抽取失败");
      documentResult = payload.document;
    }
    const previousDocumentId = currentDocument?.id;
    if (previousDocumentId && previousDocumentId !== documentResult.id) {
      try {
        await clearServerDocument(previousDocumentId);
      } catch (cleanupError) {
        let newCopyCleaned = true;
        try { await clearServerDocument(documentResult.id); } catch (_) { newCopyCleaned = false; }
        throw new Error(`上一份材料未能删除，已保留当前页面：${friendlyError(cleanupError)}${newCopyCleaned ? "" : "；新上传副本也未确认清理，请关闭并重启本地服务。"}`);
      }
    }
    initializeDocument(documentResult, includeAllImages);
  } catch (error) {
    extractStatus.textContent = friendlyError(error);
    extractStatus.classList.add("error");
  } finally {
    clearInterval(extractionTimer);
    extractBtn.disabled = false;
    clearBtn.disabled = false;
    showAllImagesBtn.disabled = false;
  }
}

function initializeDocument(documentResult, includeAllImages = false) {
    visiblePreviewItems = new Map();
    if (currentDocument && currentDocument.file_name !== documentResult.file_name) {
      sessionCustomTerms = [];
      managedCustomTerms = new Set(savedCustomTerms);
      renderCustomTerms();
    }
    currentDocument = documentResult;
    currentDocument.masked_segments = [];
    currentDocument.supplemental_blocks = [];
    currentDocument.supplemental_image_assets = [];
    currentDocument.supplemental_previews = [];
    supplementalOriginalSegments = [];
    supplementalMaskedSegments = [];
    supplementalDocumentPreviews = [];
    decisionManifest = null;
    sensitiveCandidates = currentDocument.sensitive_candidates || [];
    sensitiveCandidates.forEach((candidate) => {
      candidate.occurrences.forEach((occurrence) => setOccurrenceStatus(
        occurrence,
        candidate.default_highlight === false || occurrence.selected === false ? "cancelled" : "confirmed",
      ));
      refreshCandidateState(candidate);
    });
    imageRegions = [];
    parsingConfirmed = false;
    redactionConfirmed = false;
    confirmationToken = "";
    showMaskedPreview = false;
    undoStack = [];
    redoStack = [];
    redactionActionLog = [];
    activeCandidateId = sensitiveCandidates[0]?.id || "";
    activeOccurrenceId = "";
    activeRedactionView = "document";
    statusFilter.value = "all";
    updateHistoryButtons();
    currentOnePager = null;
    qaPanel.hidden = true;
    qaInclude.hidden = true;
    fileMeta.textContent = currentDocument.source_type === "audio" ? `${currentDocument.file_name} · ${currentDocument.segment_count} 段转写` : `${currentDocument.file_name} · ${currentDocument.page_count} 页 · ${currentDocument.segment_count} 段`;
    const parsedSummary = currentDocument.source_type === "audio" ? `${currentDocument.segment_count} 段转写文字` : `${currentDocument.segment_count} 段文字、${(currentDocument.image_assets || []).length} 张图片`;
    const imageFilter = currentDocument.image_filter || {};
    showingAllImages = currentDocument.source_type !== "audio" && includeAllImages;
    showAllImagesBtn.hidden = currentDocument.source_type === "audio" || (!showingAllImages && !imageFilter.ignored_count);
    showAllImagesBtn.textContent = showingAllImages ? "恢复筛选后的状态" : "显示全部图片";
    const filterSummary = showingAllImages
      ? "当前显示全部可提取图片，可一键恢复筛选后的状态。"
      : imageFilter.ignored_count ? `已略过 ${imageFilter.ignored_count} 张明显装饰图片。` : "";
    const positioningWarning = currentDocument.pdf_positioning_available === false
      ? "当前 Python 缺少 PyMuPDF，PDF 图片无定位信息；请按 requirements.txt 安装完整依赖后重启。"
      : "";
    const ocrSummary = imageFilter.ocr_available === false ? "本机文字识别不可用，图片已保守保留，请检查截图内容。" : "";
    extractStatus.textContent = `本地解析完成：${parsedSummary}。${filterSummary}${positioningWarning}${ocrSummary}请先确认解析结果。`;
    parseStatus.textContent = currentDocument.source_type === "audio" ? "已在本机合并短片段并补充标点。请回放核对文字、数字和断句，确认后进入脱敏。" : "请检查文字、图片、页码和顺序，确认后再进入脱敏。";
    confirmParseBtn.textContent = currentDocument.source_type === "audio" ? "确认转写并进入脱敏" : "确认解析并进入脱敏";
    openParseWorkspaceBtn.disabled = false;
    downloadParsedBtn.disabled = false;
    downloadRedactedBtn.disabled = true;
    openParseWorkspaceBtn.textContent = "查看本地解析结果";
    confirmParseBtn.disabled = false;
    selectionStatus.textContent = "黄色文字会被脱敏。单击切换全文相同内容，双击只切换当前位置；遗漏内容可选中文字后补充。";
    redactionStatus.textContent = "请检查黄色文字和红色图片框；确认前不会向大模型服务发送材料。";
    confirmRedactionBtn.disabled = false;
    openRedactionWorkspaceBtn.disabled = true;
    addSelectionBtn.disabled = false;
    togglePreviewBtn.disabled = false;
    generateBtn.disabled = true;
    updateFileFilter();
    updateRedactionStats();
    renderParseSources();
    renderSources();
    renderCandidates();
    renderOnePager();
    openParseWorkspace();
}

function isAudioFile(file) { return /\.(mp3|m4a|wav|flac|aac|ogg|opus|webm|mp4)$/i.test(file?.name || ""); }

async function refreshAudioModel() {
  audioModelRow.hidden = !isAudioFile(fileInput.files?.[0]);
  audioTermsRow.hidden = audioModelRow.hidden;
  if (audioModelRow.hidden) return;
  const response = await fetch("/api/audio/model-status");
  const result = await response.json();
  audioModelStatus.textContent = result.message;
  downloadAudioModelBtn.hidden = result.status === "ready";
  if (result.status === "downloading") setTimeout(refreshAudioModel, 1000);
}

fileInput.addEventListener("change", () => refreshAudioModel().catch((error) => { audioModelStatus.textContent = friendlyError(error); }));
downloadAudioModelBtn.addEventListener("click", async () => {
  downloadAudioModelBtn.disabled = true;
  try {
    const response = await fetch("/api/audio/model-download", { method: "POST" });
    const result = await response.json();
    if (!result.ok) throw new Error(result.error);
    refreshAudioModel();
  } catch (error) { audioModelStatus.textContent = friendlyError(error); }
  finally { downloadAudioModelBtn.disabled = false; }
});

async function confirmRedaction() {
  if (!currentDocument) return;
  confirmRedactionBtn.disabled = true;
  redactionStatus.textContent = "正在生成脱敏版本...";
  try {
    const confirmedCandidates = deepClone(sensitiveCandidates);
    confirmedCandidates.forEach((candidate) => {
      candidate.occurrences.forEach((occurrence) => {
        if (occurrenceStatus(occurrence) !== "cancelled") setOccurrenceStatus(occurrence, "confirmed");
      });
      refreshCandidateState(candidate);
    });
    const confirmedRegions = deepClone(imageRegions).map((region) => ({
      ...region,
      status: region.status === "cancelled" ? "cancelled" : "confirmed",
    }));
    const response = await fetch("/api/desensitize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: currentDocument.id,
        document_version: currentDocument.document_version,
        candidates: confirmedCandidates,
        image_regions: confirmedRegions,
        action_log: redactionActionLog,
        operator: "本地使用人",
        confirmed: true,
      }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "脱敏失败");
    splitMaskedSegments(payload.segments || []);
    sensitiveCandidates = confirmedCandidates;
    imageRegions = confirmedRegions;
    redactionConfirmed = true;
    confirmationToken = payload.confirmation_token;
    decisionManifest = payload.decision_manifest || null;
    exportDecisionCsvBtn.disabled = true;
    exportDecisionJsonBtn.disabled = true;
    togglePreviewBtn.disabled = false;
    generateBtn.disabled = false;
    downloadRedactedBtn.disabled = false;
    redactionStatus.textContent = payload.summary.occurrence_count || payload.summary.image_region_count
      ? `脱敏已确认：${payload.summary.occurrence_count} 处黄色文字、${payload.summary.image_region_count} 个图片框已记录。`
      : "已确认当前材料无需脱敏。";
    generateStatus.textContent = "脱敏已确认，可以生成一纸通。";
    renderSources();
    renderCandidates();
    closeRedactionWorkspace();
  } catch (error) {
    redactionStatus.textContent = friendlyError(error);
  } finally {
    updateRedactionStats();
  }
}

async function addManualSelection() {
  const value = selectedSourceText.trim();
  if (!value) {
    selectionStatus.textContent = "请先在原文材料库中选中需要脱敏的文字。";
    return;
  }
  try {
    const snapshot = redactionSnapshot();
    await detectSensitive(value, manualSensitiveType.value);
    pushHistorySnapshot(snapshot, "手动添加敏感文字");
    selectedSourceText = "";
    selectionStatus.textContent = `已将全文 ${value} 的相同内容标为黄色；如只需当前一处，可双击其中一处调整。`;
    invalidateRedaction("已添加手动脱敏内容，请重新确认。 ");
    renderCandidates();
  } catch (error) {
    selectionStatus.textContent = friendlyError(error);
  }
}

async function extractSupplements() {
  const files = [...(supplementInput.files || [])];
  if (!files.length) {
    askStatus.textContent = "请先选择补充材料。";
    return;
  }
  const formData = new FormData();
  formData.append("document_id", currentDocument?.id || "");
  files.forEach((file) => formData.append("supplement", file));
  extractSupplementBtn.disabled = true;
  askStatus.textContent = "正在抽取补充材料...";
  try {
    const response = await fetch("/api/extract-supplements", { method: "POST", body: formData });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "补充材料抽取失败");
    supplementalOriginalSegments.push(...(payload.segments || []));
    currentDocument.supplemental_blocks.push(...(payload.blocks || []));
    currentDocument.supplemental_image_assets.push(...(payload.image_assets || []));
    supplementalDocumentPreviews.push(...(payload.document_previews || []));
    currentDocument.document_version = payload.document_version;
    await detectSensitive();
    invalidateRedaction("补充材料已加入，请检查新增候选项并重新确认脱敏。 ");
    askStatus.textContent = `已抽取补充材料 ${payload.segment_count} 段，请先重新确认脱敏。`;
    renderSources();
    updateFileFilter();
  } catch (error) {
    askStatus.textContent = friendlyError(error);
  } finally {
    extractSupplementBtn.disabled = false;
  }
}

async function generateOnePager() {
  if (!currentDocument) {
    generateStatus.textContent = "请先抽取原文。";
    return;
  }
  if (!redactionConfirmed) {
    generateStatus.textContent = "请先检查并确认信息脱敏。";
    return;
  }

  if (activeGeneration) return;
  const generation = { id: crypto.randomUUID(), controller: new AbortController(), cancelled: false, sent: false };
  activeGeneration = generation;
  generateBtn.disabled = true;
  clearBtn.disabled = true;
  const generationJobId = crypto.randomUUID().replaceAll("-", "");
  let generationFinished = false;
  const generationStartedAt = Date.now();
  let stageStartedAt = generationStartedAt;
  let currentStage = "";
  const progressTimer = setInterval(async () => {
    try {
      const response = await fetch(`/api/generation-status/${generationJobId}`, { cache: "no-store" });
      if (response.ok) {
        const progress = await response.json();
        if (progress.ok && !generationFinished && !generation.cancelled) {
          if (progress.message !== currentStage) {
            currentStage = progress.message;
            stageStartedAt = Date.now();
          }
          const stageSeconds = Math.floor((Date.now() - stageStartedAt) / 1000);
          const totalSeconds = Math.floor((Date.now() - generationStartedAt) / 1000);
          generateStatus.textContent = `${progress.message}；本阶段 ${stageSeconds} 秒，累计 ${totalSeconds} 秒。`;
        }
      }
    } catch { /* 主请求会显示最终错误。 */ }
  }, 1500);
  cancelGenerateBtn.hidden = false;
  const previousContact = currentOnePager?.business_contact;
  generateStatus.textContent = "正在生成一纸通；长材料或模型繁忙时可能需要数分钟，请勿重复点击。";
  generateStatus.classList.remove("error", "warning");
  try {
    const requirements = guidanceValues();
    if (maxCharsSelect.value === "custom" && (!Number.isInteger(requirements.max_chars) || requirements.max_chars < 100 || requirements.max_chars > 2000)) {
      throw new Error("自定义字数上限请输入 100—2000 的整数。");
    }
    const audience = await maskGuidanceText(audienceCustom.value.trim() || audienceSelect.value);
    requirements.detail_target = await maskGuidanceText(requirements.detail_target);
    requirements.must_keep = await maskGuidanceText(requirements.must_keep);
    requirements.exclude_sections = await maskGuidanceText(requirements.exclude_sections);
    requirements.other_requirements = await maskGuidanceText(requirements.other_requirements);
    if (generation.cancelled) return;
    generation.sent = true;
    const response = await fetch("/api/generate", {
      method: "POST",
      signal: generation.controller.signal,
      headers: {
        "Content-Type": "application/json",
        "X-Generation-Job-ID": generationJobId,
        "X-Generation-ID": generation.id,
        ...modelRequestHeaders(),
      },
      body: JSON.stringify({
        document_id: currentDocument.id,
        confirmation_token: confirmationToken,
        audience,
        template: templateSelect.value,
        document_type: documentTypeSelect.value,
        focus: requirements.detail_target,
        requirements,
      }),
    });
    const payload = await response.json();
    if (generation.cancelled) return;
    if (!payload.ok) throw new Error(payload.error || "生成失败");
    currentOnePager = payload.one_pager;
    currentOnePager.generation_requirements.presentation_mode = requirements.presentation_mode;
    if (previousContact) currentOnePager.business_contact = previousContact;
    editContactBtn.disabled = false;
    pendingAnswer = null;
    qaInclude.hidden = true;
    qaPanel.hidden = false;
    documentTypeSelect.value = payload.detected_document_type || currentOnePager.meta?.document_type || documentTypeSelect.value;
    updateRequirementsPreview();
    documentTypeStatus.textContent = `识别结果：${payload.detected_document_type || currentOnePager.meta?.document_type || "未知"}；全文共 ${payload.chunk_count || 1} 批参与生成。`;
    generateStatus.textContent = payload.mode === "llm" ? "大模型生成完成，正在检查单页版面。" :
      payload.mode === "local_rules" ? "本地规则草稿已生成，请核对事实与出处。" :
        "未配置大模型 API，已生成本地规则草稿，请核对事实与出处。";
    generateStatus.classList.toggle("warning", payload.mode !== "llm");
    renderOnePager();
    setStep("review");
    await openContactDialog(true);
  } catch (error) {
    if (!generation.cancelled) {
      generateStatus.textContent = friendlyError(error);
      generateStatus.classList.add("error");
    }
  } finally {
    generationFinished = true;
    clearInterval(progressTimer);
    clearBtn.disabled = false;
    if (activeGeneration === generation) {
      activeGeneration = null;
      cancelGenerateBtn.hidden = true;
      generateBtn.disabled = false;
    }
  }
}

function cancelGeneration() {
  const generation = activeGeneration;
  if (!generation) return Promise.resolve();
  generation.cancelled = true;
  generation.controller.abort();
  cancelGenerateBtn.hidden = true;
  generateStatus.textContent = "已取消生成；再次生成将从头开始。已发出的模型请求可能仍会计费。";
  if (generation.sent) {
    return fetch("/api/generate/cancel", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ generation_id: generation.id }),
    }).catch(() => {});
  }
  return Promise.resolve();
}

async function clearAll() {
  clearBtn.disabled = true;
  extractBtn.disabled = true;
  if (activeGeneration) await cancelGeneration();
  if (activeAudioJob) {
    try {
      await fetch("/api/audio/cancel", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: activeAudioJob }) });
    } catch (_) { /* the active upload is removed when this service run ends */ }
  }
  if (currentDocument?.id) {
    try {
      await clearServerDocument(currentDocument.id);
    } catch (error) {
      extractStatus.textContent = `清空失败，材料仍保留在本地：${friendlyError(error)}`;
      extractStatus.classList.add("error");
      clearBtn.disabled = false;
      extractBtn.disabled = false;
      return;
    }
  }
  visiblePreviewItems = new Map();
  sessionCustomTerms = [];
  managedCustomTerms = new Set(savedCustomTerms);
  renderCustomTerms();
  activeAudioJob = "";
  currentDocument = null;
  showingAllImages = false;
  currentOnePager = null;
  contactCandidates = [];
  editContactBtn.disabled = true;
  qaExtraSources = [];
  supplementalOriginalSegments = [];
  supplementalMaskedSegments = [];
  supplementalDocumentPreviews = [];
  sensitiveCandidates = [];
  imageRegions = [];
  parsingConfirmed = false;
  redactionConfirmed = false;
  confirmationToken = "";
  showMaskedPreview = false;
  undoStack = [];
  redoStack = [];
  redactionActionLog = [];
  decisionManifest = null;
  selectedSourceText = "";
  activeCandidateId = "";
  activeOccurrenceId = "";
  activeRedactionView = "context";
  fileInput.value = "";
  pendingAnswer = null;
  qaPanel.hidden = true;
  qaInclude.hidden = true;
  questionInput.value = "";
  fileMeta.textContent = "文档最大 1024MB；录音最大 200MB、120分钟";
  audioModelRow.hidden = true;
  audioTermsRow.hidden = true;
  audioTermsInput.value = "";
  extractStatus.textContent = "请先上传文件，然后在本地解析文字和图片。";
  extractStatus.classList.remove("error");
  parseCount.textContent = "请先上传并解析材料";
  parseStatus.textContent = "完成解析并确认后，才能进入信息脱敏。";
  showAllImagesBtn.hidden = true;
  showAllImagesBtn.textContent = "显示全部图片";
  openParseWorkspaceBtn.disabled = true;
  downloadParsedBtn.disabled = true;
  openParseWorkspaceBtn.textContent = "查看本地解析结果";
  confirmParseBtn.disabled = true;
  generateStatus.textContent = "完成解析和脱敏后可生成。";
  documentTypeSelect.value = "auto";
  presentationModeSelect.value = "text";
  documentTypeStatus.textContent = "系统将在生成时自动判断材料类型，也可以手动指定。";
  focusInput.value = "";
  audienceCustom.value = "";
  maxCharsSelect.value = "";
  customMaxChars.value = "";
  detailDepth.value = "normal";
  writingTone.value = "plain";
  includeOverview.checked = true;
  includeFullStructure.checked = true;
  includeArchitecture.checked = true;
  includePractice.checked = true;
  mustKeepInput.value = "";
  excludeSectionsInput.value = "";
  explainTerms.checked = false;
  extraRequirements.value = "";
  updateRequirementsPreview();
  redactionStatus.textContent = "尚未确认，不能发送给大模型服务。";
  redactionCount.textContent = "请先抽取材料";
  selectionStatus.textContent = "如有遗漏，请在材料中选中文字，再点击“将选中文字设为脱敏”。";
  askStatus.textContent = "请先生成一纸通，再根据主材料追问。";
  qaAnswer.innerHTML = "<p>回答会显示在这里，并保留原文出处。</p>";
  generateBtn.disabled = true;
  confirmRedactionBtn.disabled = true;
  downloadRedactedBtn.disabled = true;
  openRedactionWorkspaceBtn.disabled = true;
  addSelectionBtn.disabled = true;
  togglePreviewBtn.disabled = true;
  togglePreviewBtn.textContent = "查看脱敏效果";
  exportDecisionCsvBtn.disabled = true;
  exportDecisionJsonBtn.disabled = true;
  redactionOperator.value = "";
  fileFilter.innerHTML = '<option value="all">全部文件</option>';
  statusFilter.value = "all";
  updateHistoryButtons();
  updateRedactionStats();
  closeParseWorkspace();
  closeRedactionWorkspace();
  renderParseSources();
  renderSources();
  renderCandidates();
  renderOnePager();
  clearBtn.disabled = false;
  extractBtn.disabled = false;
}

function renderAnswer(answer, mode) {
  const ids = answer.source_ids || [];
  qaAnswer.innerHTML = `
    <article class="answer-card">
      <div class="answer-head">
        <strong>${mode === "llm" ? "大模型回答" : "本地规则草稿"}</strong>
        ${answer.needs_confirmation ? '<span class="confirm-chip">需人工确认</span>' : ""}
      </div>
      <p>${escapeHtml(answer.answer || "现有材料未找到明确依据。")}</p>
      <div class="item-actions">
        <button class="source-link" type="button" data-source-ids="${escapeHtml(ids.join(","))}">查看出处</button>
        <span class="source-note">${escapeHtml(sourceSummary(answer))}</span>
      </div>
    </article>
  `;
  qaAnswer.querySelector(".source-link").addEventListener("click", (event) => {
    const sourceIds = event.currentTarget.dataset.sourceIds
      ? event.currentTarget.dataset.sourceIds.split(",").filter(Boolean)
      : [];
    showSources(sourceIds);
  });
}

async function askQuestion() {
  const question = questionInput.value.trim();
  if (!question) {
    askStatus.textContent = "请先输入问题。";
    return;
  }
  if (!currentOnePager) {
    askStatus.textContent = "请先生成一纸通。";
    return;
  }
  if (!redactionConfirmed) {
    askStatus.textContent = "请先完成并确认信息脱敏。";
    return;
  }

  askBtn.disabled = true;
  askStatus.textContent = "正在检查问题中的敏感信息...";
  try {
    let redactionResponse = await fetch("/api/desensitize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        document_id: currentDocument.id,
        confirmation_token: confirmationToken,
        free_text: question,
        confirm_free_text: false,
      }),
    });
    let redactionPayload = await redactionResponse.json();
    if (!redactionPayload.ok) throw new Error(redactionPayload.error || "问题脱敏检查失败");
    const questionCandidates = redactionPayload.free_text_candidates || [];
    if (questionCandidates.length) {
      const names = questionCandidates.map((item) => `${item.type_label}“${item.value}”`).join("、");
      const accepted = window.confirm(`问题中发现新的敏感信息：${names}\n\n是否将这些内容脱敏后再提问？`);
      if (!accepted) {
        askStatus.textContent = "已取消发送。请修改问题后重试。";
        return;
      }
      redactionResponse = await fetch("/api/desensitize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          document_id: currentDocument.id,
          confirmation_token: confirmationToken,
          free_text: question,
          confirm_free_text: true,
        }),
      });
      redactionPayload = await redactionResponse.json();
      if (!redactionPayload.ok) throw new Error(redactionPayload.error || "问题脱敏失败");
    }
    askStatus.textContent = "正在查找依据并回答...";
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...modelRequestHeaders(),
      },
      body: JSON.stringify({
        question: redactionPayload.masked_free_text,
        document_id: currentDocument.id,
        confirmation_token: confirmationToken,
      }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "提问失败");
    qaExtraSources = supplementalMaskedSegments;
    pendingAnswer = { question: redactionPayload.masked_free_text, ...payload.answer };
    qaInclude.hidden = false;
    includeAnswer.checked = false;
    applyAnswerBtn.disabled = true;
    if (!pendingAnswer.source_ids?.length || pendingAnswer.needs_confirmation) {
      qaInclude.hidden = true;
      askStatus.textContent = "回答缺少可核对依据，暂不能纳入一纸通。";
    }
    askStatus.textContent = payload.mode === "llm" ? "回答完成。" :
      payload.mode === "local_rules" ? "本地规则回答已生成，请核对依据。" : "未配置大模型 API，已生成本地规则草稿。";
    renderAnswer(payload.answer, payload.mode);
  } catch (error) {
    askStatus.textContent = friendlyError(error);
  } finally {
    askBtn.disabled = false;
  }
}

function safeFileName(value, extension) {
  const base = String(value || "一纸通").replace(/[\\/:*?"<>|]/g, "-").slice(0, 60);
  return `${base || "一纸通"}.${extension}`;
}

function onePagerExportName(extension) {
  const meta = currentOnePager?.meta || {};
  const source = String(meta.file_name || currentDocument?.file_name || "上传材料").replace(/\.[^.]+$/, "");
  const date = String(meta.generated_at || "").match(/^\d{4}-\d{2}-\d{2}/)?.[0]
    || new Date().toLocaleDateString("sv-SE");
  return safeFileName(`${source.slice(0, 45)}-一纸通-${date}`, extension);
}

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function markOnePagerConfirmed() {
  if (!currentOnePager) return;
  currentOnePager.status = "已确认";
  const badge = paper.querySelector("#reviewStatus");
  if (badge) {
    badge.textContent = "已确认";
    badge.classList.add("approved");
  }
}

async function downloadIntermediateDocx(kind) {
  if (!currentDocument) return;
  const isRedacted = kind === "redacted";
  const button = isRedacted ? downloadRedactedBtn : downloadParsedBtn;
  const status = isRedacted ? redactionStatus : parseStatus;
  const originalLabel = button.textContent;
  button.disabled = true;
  button.textContent = "正在生成 Word...";
  status.textContent = isRedacted ? "正在生成已确认的脱敏文件..." : "正在生成解析结果，文件可能包含未脱敏信息...";
  try {
    const response = await fetch(isRedacted ? "/api/export/redacted-docx" : "/api/export/parsed-docx", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(isRedacted
        ? { document_id: currentDocument.id, confirmation_token: confirmationToken }
        : { document_id: currentDocument.id, document_version: currentDocument.document_version }),
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || "Word 导出失败");
    }
    const base = String(currentDocument.file_name || "材料").replace(/\.[^.]+$/, "");
    downloadBlob(await response.blob(), safeFileName(`${base}-${isRedacted ? "脱敏版" : "解析结果"}`, "docx"));
    status.textContent = isRedacted
      ? "脱敏版 Word 已生成；请仍按内部资料要求妥善保存。"
      : "解析结果 Word 已生成。该文件可能包含未脱敏信息。";
  } catch (error) {
    status.textContent = friendlyError(error);
  } finally {
    button.textContent = originalLabel;
    button.disabled = isRedacted ? !redactionConfirmed : !currentDocument;
  }
}

function markdownOnePager() {
  const meta = currentOnePager.meta || {};
  const contactLine = contactText() ? `**业务联系：**${contactText()}\n` : "";
  if (currentOnePager.schema_version === "3.0") {
    const architecture = currentOnePager.knowledge_architecture || {};
    const r = currentOnePager.generation_requirements || {};
    const lines = [`# ${meta.title || "培训一纸通"}`, "", contactLine, ""];
    if (r.include_overview !== false && meta.overview) lines.push("## 核心结论", "", meta.overview, "");
    if (r.include_full_structure !== false && currentOnePager.original_structure?.length) {
      lines.push("## 全文架构", "");
      currentOnePager.original_structure.forEach((item, index) => lines.push(`${index + 1}. ${item.title || ""}`));
      lines.push("");
    }
    if (r.presentation_mode === "framework" && (architecture.modules || []).length) {
      lines.push(`## 知识架构（${architectureTypeLabels[architecture.type] || architecture.type || "分组型"}）`, "");
      (architecture.modules || []).forEach((item, index) => lines.push(`${index + 1}. **${item.title || ""}**：${item.description || ""}`));
    }
    if (r.include_knowledge_modules !== false && currentOnePager.knowledge_modules?.length) {
      lines.push("", `## ${{policy: "关键规定", operation: "办理步骤", product: "产品要点", general: "核心知识"}[meta.training_type] || "核心知识"}`, "");
      (currentOnePager.knowledge_modules || []).forEach((group) => {
        lines.push(`### ${group.title || "知识模块"}`, "");
        (group.points || []).forEach((item) => lines.push(`- ${item.text || ""}`));
        lines.push("");
      });
    }
    if (r.include_practice !== false && currentOnePager.practical_application?.length) {
      lines.push("## 实际工作应用", "");
      (currentOnePager.practical_application || []).forEach((group) => {
        lines.push(`### ${group.title || "实务应用"}`, "");
        (group.items || []).forEach((item) => lines.push(`- ${item.text || ""}`));
        lines.push("");
      });
    }
    if (currentOnePager.key_reminders?.length) {
      lines.push("## 关键提醒", "");
      (currentOnePager.key_reminders || []).forEach((item) => lines.push(`- ${item.text || ""}`));
    }
    if ((currentOnePager.ambiguities || []).length) {
      lines.push("", "## 材料疑点（需人工确认）", "");
      currentOnePager.ambiguities.forEach((item) => lines.push(`- ${item.text || ""}`));
    }
    if ((currentOnePager.qa_items || []).length) {
      lines.push("", "## 材料问答", "");
      currentOnePager.qa_items.forEach((item) => lines.push(`- **问：${item.question}** 答：${item.answer}`));
    }
    return lines.join("\n");
  }
  const lines = [`# ${meta.title || "一纸通"}`, "", `> ${meta.subtitle || ""}`, contactLine, "",
    `来源：${meta.file_name || ""}｜${meta.page_count || 1}页｜${meta.document_type || ""}｜${meta.generated_at || ""}`, "",
    "## 核心结论", ""];
  (currentOnePager.conclusions || []).forEach((item) => lines.push(`- ${item.text}`));
  lines.push("", "## 关键数据", "", "| 指标 | 数值 | 对比 |", "|---|---:|---|");
  (currentOnePager.metrics || []).forEach((item) => lines.push(`| ${item.label || ""} | ${item.value || ""} | ${item.comparison || ""} |`));
  lines.push("", `## 逻辑结构：${currentOnePager.logic?.type || ""}`, "");
  (currentOnePager.logic?.nodes || []).forEach((item, index) => lines.push(`${index + 1}. **${item.title || ""}**：${item.text || ""}`));
  lines.push("", "## 重点事项", "");
  (currentOnePager.actions || []).forEach((item) => lines.push(`- **${item.priority || "medium"} · ${item.kind || "待办"}** ${item.text || ""}（${item.owner || "负责人待定"}；${item.due || "时间待定"}）`));
  if ((currentOnePager.supplements || []).length) {
    lines.push("", "## 补充信息", "");
    currentOnePager.supplements.forEach((item) => lines.push(`- **${item.term || ""}**：${item.explanation || ""}`));
  }
  if ((currentOnePager.qa_items || []).length) {
    lines.push("", "## 材料问答", "");
    currentOnePager.qa_items.forEach((item) => lines.push(`- **问：${item.question}** 答：${item.answer}`));
  }
  return lines.join("\n");
}

async function capturePaperCanvas(scale = 2) {
  paper.classList.add("exporting");
  try {
  const pageRect = paper.getBoundingClientRect();
  const diagramRect = paper.querySelector(".framework-map")?.getBoundingClientRect();
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(paper.offsetWidth * scale);
  canvas.height = Math.round(paper.offsetHeight * scale);
  const context = canvas.getContext("2d");
  const factor = canvas.width / pageRect.width;
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.save();
  context.beginPath();
  context.rect(0, 0, canvas.width, canvas.height);
  context.clip();
  const hidden = ".editor-only,.no-print,.source-link,.confirm-chip,.model-note,.quality-warnings";
  const coordinates = (rect) => ({ x: (rect.left - pageRect.left) * factor,
    y: (rect.top - pageRect.top) * factor, width: rect.width * factor, height: rect.height * factor });
  const drawNode = (node) => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      if (node !== paper && node.matches(hidden)) return;
      const style = getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return;
      const rect = node.getBoundingClientRect();
      if (rect.width && rect.height) {
        const box = coordinates(rect);
        if (style.backgroundColor !== "rgba(0, 0, 0, 0)" && style.backgroundColor !== "transparent") {
          context.fillStyle = style.backgroundColor;
          const radius = Math.min(parseFloat(style.borderTopLeftRadius) * factor || 0, box.height / 2);
          context.beginPath();
          context.roundRect(box.x, box.y, box.width, box.height, radius);
          context.fill();
        }
        for (const [side, x, y, width, height] of [
          ["Top", box.x, box.y, box.width, parseFloat(style.borderTopWidth) * factor],
          ["Left", box.x, box.y, parseFloat(style.borderLeftWidth) * factor, box.height],
          ["Right", box.x + box.width - parseFloat(style.borderRightWidth) * factor, box.y, parseFloat(style.borderRightWidth) * factor, box.height],
          ["Bottom", box.x, box.y + box.height - parseFloat(style.borderBottomWidth) * factor, box.width, parseFloat(style.borderBottomWidth) * factor],
        ]) {
          if (width > 0 && height > 0 && style[`border${side}Style`] !== "none") {
            context.fillStyle = style[`border${side}Color`];
            context.fillRect(x, y, width, height);
          }
        }
      }
      node.childNodes.forEach(drawNode);
    } else if (node.nodeType === Node.TEXT_NODE && node.textContent?.trim()) {
      const style = getComputedStyle(node.parentElement);
      context.fillStyle = style.color;
      context.font = `${style.fontStyle} ${style.fontWeight} ${parseFloat(style.fontSize) * factor}px ${style.fontFamily}`;
      const range = document.createRange();
      for (let index = 0; index < node.textContent.length; index++) {
        const character = node.textContent[index];
        if (/\s/.test(character)) continue;
        range.setStart(node, index);
        range.setEnd(node, index + 1);
        const rect = range.getBoundingClientRect();
        if (!rect.width || !rect.height) continue;
        const box = coordinates(rect);
        context.fillText(character, box.x, box.y + box.height * .82);
      }
      range.detach?.();
    }
  };
  drawNode(paper);
  context.restore();
  if (diagramRect) canvas.diagramBox = { x: Math.round((diagramRect.left - pageRect.left) * factor),
    y: Math.round((diagramRect.top - pageRect.top) * factor),
    width: Math.round(diagramRect.width * factor), height: Math.round(diagramRect.height * factor) };
  return canvas;
  } finally { paper.classList.remove("exporting"); }
}

async function frameworkDiagramPng() {
  const map = paper.querySelector(".framework-map");
  if (!map) return "";
  const pageCanvas = await capturePaperCanvas();
  const box = pageCanvas.diagramBox;
  const crop = document.createElement("canvas");
  crop.width = Math.max(1, box.width);
  crop.height = Math.max(1, box.height);
  crop.getContext("2d").drawImage(pageCanvas, box.x, box.y, box.width, box.height, 0, 0, box.width, box.height);
  return crop.toDataURL("image/png");
}

function canvasLines(context, text, maxWidth) {
  const lines = [];
  let current = "";
  for (const character of String(text || "")) {
    const probe = current + character;
    if (current && context.measureText(probe).width > maxWidth) {
      lines.push(current);
      current = character;
    } else current = probe;
  }
  if (current) lines.push(current);
  return lines;
}

function canvasText(context, text, x, y, maxWidth, lineHeight, maxLines = 2) {
  const lines = canvasLines(context, text, maxWidth).slice(0, maxLines);
  lines.forEach((line, index) => context.fillText(line, x, y + index * lineHeight));
  return y + lines.length * lineHeight;
}

async function exportKnowledgePng() {
  layoutStatus.textContent = "正在生成知识架构版图片...";
  const canvas = document.createElement("canvas");
  const scale = 2;
  canvas.width = 794 * scale;
  canvas.height = 1123 * scale;
  const context = canvas.getContext("2d");
  context.scale(scale, scale);
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, 794, 1123);
  const meta = currentOnePager.meta || {};
  const dark = meta.training_type === "operation" ? "#195467" : meta.training_type === "policy" ? "#173b60" : "#173f64";
  const accent = meta.training_type === "operation" ? "#327c91" : meta.training_type === "policy" ? "#315e8b" : "#2f6fa5";
  const soft = meta.training_type === "operation" ? "#eef8fa" : "#edf5fb";
  const roundBox = (x, y, width, height, fill = "#fff", stroke = "#d7e2ea") => {
    context.fillStyle = fill; context.strokeStyle = stroke; context.lineWidth = 1;
    context.beginPath(); context.roundRect(x, y, width, height, 7); context.fill(); context.stroke();
  };
  const sectionTitle = (number, title, x, y) => {
    context.fillStyle = accent; context.font = "800 9px Microsoft YaHei, PingFang SC, sans-serif"; context.fillText(number, x, y);
    context.fillStyle = dark; context.font = "800 13px Microsoft YaHei, PingFang SC, sans-serif"; context.fillText(title, x + 22, y);
  };
  context.fillStyle = accent; context.font = "800 8px Microsoft YaHei, sans-serif";
  context.fillText("TRAINING KNOWLEDGE MAP", 32, 31);
  context.textAlign = "right";
  context.fillText(`${trainingTypeLabels[meta.training_type] || "培训一纸通"} · ${meta.audience || ""}`, 762, 31);
  context.textAlign = "left";
  context.fillStyle = "#142d44"; context.font = "800 25px Microsoft YaHei, PingFang SC, sans-serif";
  canvasText(context, meta.title || "培训一纸通", 32, 66, 670, 30, 1);
  context.fillStyle = "#71808d"; context.font = "8px Microsoft YaHei, sans-serif";
  context.fillText(`${meta.file_name || ""} · ${meta.page_count || 1}页 · ${meta.generated_at || ""}`, 32, 86);
  context.fillStyle = dark; context.fillRect(32, 96, 730, 3);

  roundBox(32, 110, 730, 92, "#f7fbfe");
  sectionTitle("01", "培训内容概览", 44, 132);
  context.fillStyle = "#3a4d5c"; context.font = "10.5px Microsoft YaHei, PingFang SC, sans-serif";
  canvasText(context, meta.overview || "", 44, 153, 704, 16, 3);

  roundBox(32, 212, 730, 171);
  sectionTitle("02", "知识架构图", 44, 234);
  const architecture = currentOnePager.knowledge_architecture || {};
  context.fillStyle = "#768795"; context.font = "8px Microsoft YaHei, sans-serif";
  context.fillText(architectureTypeLabels[architecture.type] || "分组型", 154, 234);
  const modules = architecture.modules || [];
  const gap = architecture.type === "process" ? 16 : 6;
  const nodeWidth = Math.max(92, (704 - gap * Math.max(0, modules.length - 1)) / Math.max(1, modules.length));
  let nodeY = 274;
  if (architecture.type !== "process") {
    context.fillStyle = dark; context.beginPath(); context.roundRect(287, 245, 220, 24, 12); context.fill();
    context.fillStyle = "#fff"; context.font = "800 10px Microsoft YaHei, sans-serif"; context.textAlign = "center";
    context.fillText(architecture.central_topic || meta.title || "", 397, 261); context.textAlign = "left";
  } else nodeY = 252;
  modules.forEach((item, index) => {
    const x = 44 + index * (nodeWidth + gap);
    roundBox(x, nodeY, nodeWidth, architecture.type === "process" ? 105 : 92, soft, "#cbdde9");
    context.fillStyle = accent; context.fillRect(x, nodeY, nodeWidth, 3);
    context.fillStyle = dark; context.font = "800 10px Microsoft YaHei, sans-serif";
    canvasText(context, item.title || "", x + 7, nodeY + 22, nodeWidth - 14, 13, 2);
    context.fillStyle = "#5b6c79"; context.font = "8px Microsoft YaHei, sans-serif";
    canvasText(context, item.description || "", x + 7, nodeY + 50, nodeWidth - 14, 12, 3);
    if (architecture.type === "process" && index < modules.length - 1) {
      context.fillStyle = accent; context.font = "800 15px sans-serif"; context.fillText("→", x + nodeWidth + 2, nodeY + 57);
    }
  });

  roundBox(32, 393, 730, 357);
  sectionTitle("03", "核心知识要点", 44, 415);
  const groups = currentOnePager.knowledge_modules || [];
  const cardGap = 7;
  const cardWidth = (704 - cardGap) / 2;
  const rows = Math.max(1, Math.ceil(groups.length / 2));
  const cardHeight = Math.min(145, (319 - cardGap * (rows - 1)) / rows);
  groups.forEach((group, index) => {
    const col = index % 2; const row = Math.floor(index / 2);
    const x = 44 + col * (cardWidth + cardGap); const y = 426 + row * (cardHeight + cardGap);
    roundBox(x, y, cardWidth, cardHeight, "#f8fafc", "#e0e7ec");
    context.fillStyle = accent; context.fillRect(x, y, 3, cardHeight);
    context.fillStyle = dark; context.font = "800 10px Microsoft YaHei, sans-serif";
    context.fillText(`${String(index + 1).padStart(2, "0")}  ${group.title || "知识模块"}`, x + 9, y + 18);
    let pointY = y + 37;
    (group.points || []).forEach((point) => {
      context.fillStyle = accent; context.beginPath(); context.arc(x + 11, pointY - 3, 2, 0, Math.PI * 2); context.fill();
      context.fillStyle = "#354956"; context.font = "8.5px Microsoft YaHei, sans-serif";
      pointY = canvasText(context, point.text || "", x + 18, pointY, cardWidth - 27, 12, 2) + 4;
    });
  });

  roundBox(32, 760, 438, 316);
  sectionTitle("04", "实际工作应用", 44, 782);
  let practiceY = 797;
  (currentOnePager.practical_application || []).forEach((group) => {
    context.fillStyle = dark; context.font = "800 9.5px Microsoft YaHei, sans-serif"; context.fillText(group.title || "实务应用", 44, practiceY + 12);
    practiceY += 27;
    (group.items || []).forEach((item) => {
      context.fillStyle = "#354956"; context.font = "8.5px Microsoft YaHei, sans-serif";
      practiceY = canvasText(context, `• ${item.text || ""}`, 48, practiceY, 406, 12, 2) + 4;
    });
    practiceY += 2;
  });
  roundBox(480, 760, 282, 316, "#fcf8f4", "#e5d8cb");
  sectionTitle("05", "关键提醒", 492, 782);
  let reminderY = 801;
  (currentOnePager.key_reminders || []).forEach((item) => {
    context.fillStyle = item.level === "high" ? "#fff8f6" : "#fff"; context.fillRect(492, reminderY, 258, 55);
    context.fillStyle = item.level === "high" ? "#a54c43" : "#b68a5d"; context.fillRect(492, reminderY, 3, 55);
    context.fillStyle = "#55493e"; context.font = "8.5px Microsoft YaHei, sans-serif";
    canvasText(context, item.text || "", 503, reminderY + 17, 236, 12, 3);
    reminderY += 62;
  });
  context.strokeStyle = "#dce3e8"; context.beginPath(); context.moveTo(32, 1088); context.lineTo(762, 1088); context.stroke();
  context.fillStyle = "#7a8791"; context.font = "8px Microsoft YaHei, sans-serif";
  context.fillText("内容依据脱敏原文提炼；出处仅供工作台在线核对", 32, 1105);
  context.textAlign = "right"; context.fillText("AI-2 培训一纸通 · 知识架构版", 762, 1105); context.textAlign = "left";
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("浏览器未能生成 PNG 图片。");
  markOnePagerConfirmed();
  downloadBlob(blob, safeFileName(meta.title, "png"));
  layoutStatus.textContent = "知识架构版图片导出完成";
}

async function exportPng() {
  if (!currentOnePager) return;
  if (document.activeElement?.isContentEditable) document.activeElement.blur();
  if (checkPageOverflow()) return;
  layoutStatus.textContent = "正在按当前预览生成图片...";
  const canvas = await capturePaperCanvas(300 / 96);
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("浏览器未能生成图片。");
  markOnePagerConfirmed();
  downloadBlob(blob, onePagerExportName("png"));
  layoutStatus.textContent = "图片导出完成";
}

async function exportDocx() {
  if (checkPageOverflow()) return;
  layoutStatus.textContent = "正在生成可编辑 Word...";
  const diagramPng = currentOnePager.generation_requirements?.presentation_mode === "framework" ? await frameworkDiagramPng() : "";
  const response = await fetch("/api/export/docx", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ document_id: currentDocument.id, confirmation_token: confirmationToken, one_pager: { ...currentOnePager, status: "已确认" }, diagram_png: diagramPng }),
  });
  if (!response.ok) {
    let message = "Word 导出失败";
    try { message = (await response.json()).error || message; } catch (_) { /* ignore */ }
    throw new Error(message);
  }
  const blob = await response.blob();
  markOnePagerConfirmed();
  downloadBlob(blob, onePagerExportName("docx"));
  layoutStatus.textContent = "Word 导出完成";
}

async function compactCurrentOnePager() {
  if (!currentOnePager) return;
  if (currentOnePager.complete_result) {
    currentOnePager = currentOnePager.complete_result;
    renderOnePager();
    layoutStatus.textContent = "已恢复压缩前的完整结构化内容";
    return;
  }
  compactBtn.disabled = true;
  layoutStatus.textContent = "正在压缩一纸通内容...";
  try {
    const response = await fetch("/api/compact-one-pager", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document_id: currentDocument.id, confirmation_token: confirmationToken, one_pager: currentOnePager }),
    });
    const payload = await response.json();
    if (!payload.ok) throw new Error(payload.error || "压缩失败");
    currentOnePager = payload.one_pager;
    renderOnePager();
  } catch (error) {
    layoutStatus.textContent = friendlyError(error);
  } finally {
    compactBtn.disabled = false;
  }
}

extractBtn.addEventListener("click", () => extractFile());
downloadParsedBtn.addEventListener("click", () => downloadIntermediateDocx("parsed"));
showAllImagesBtn.addEventListener("click", () => extractFile(!showingAllImages));
openParseWorkspaceBtn.addEventListener("click", openParseWorkspace);
closeParseWorkspaceBtn.addEventListener("click", closeParseWorkspace);
confirmParseBtn.addEventListener("click", confirmParsing);
confirmRedactionBtn.addEventListener("click", confirmRedaction);
downloadRedactedBtn.addEventListener("click", () => downloadIntermediateDocx("redacted"));
addSelectionBtn.addEventListener("click", addManualSelection);
addCustomTermsBtn.addEventListener("click", addCustomTerms);
customTermsList.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-custom-term]");
  if (!button) return;
  const value = button.dataset.customTerm;
  savedCustomTerms = savedCustomTerms.filter((term) => term !== value);
  sessionCustomTerms = sessionCustomTerms.filter((term) => term !== value);
  localStorage.setItem(customTermsStorageKey, JSON.stringify(savedCustomTerms));
  try { await refreshCustomTerms(`已删除“${value}”。`); }
  catch (error) { customTermsStatus.textContent = friendlyError(error); }
});
savedCustomTerms = readSavedCustomTerms();
managedCustomTerms = new Set(savedCustomTerms);
renderCustomTerms();
extractSupplementBtn?.addEventListener("click", extractSupplements);
redactionFilter.addEventListener("change", renderCandidates);
confidenceFilter.addEventListener("change", renderCandidates);
statusFilter.addEventListener("change", renderCandidates);
fileFilter.addEventListener("change", renderCandidates);
redactionViewTabs.forEach((button) => button.addEventListener("click", () => setRedactionView(button.dataset.redactionView)));
openRedactionWorkspaceBtn.addEventListener("click", openRedactionWorkspace);
closeRedactionWorkspaceBtn.addEventListener("click", closeRedactionWorkspace);
exportDecisionCsvBtn.addEventListener("click", () => exportDecisionManifest("csv"));
exportDecisionJsonBtn.addEventListener("click", () => exportDecisionManifest("json"));
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !parseWorkspace.hidden) closeParseWorkspace();
  if (event.key === "Escape" && !redactionWorkspace.hidden && !sourceDialog.open) closeRedactionWorkspace();
});

function occurrenceMatchesFilters(candidate, occurrence) {
  return (redactionFilter.value === "all" || candidate.category === redactionFilter.value)
    && (confidenceFilter.value === "all" || candidate.sensitivity === confidenceFilter.value)
    && (statusFilter.value === "all" || occurrenceStatus(occurrence) === statusFilter.value)
    && (fileFilter.value === "all" || occurrence.file_name === fileFilter.value);
}

function applyVisibleStatus(status) {
  if (!currentDocument) return;
  recordHistory(status === "confirmed" ? "批量确认筛选项" : status === "cancelled" ? "批量排除筛选项" : "批量恢复筛选项");
  let changed = 0;
  sensitiveCandidates.forEach((candidate) => {
    candidate.occurrences.forEach((occurrence) => {
      if (occurrenceMatchesFilters(candidate, occurrence)) {
        setOccurrenceStatus(occurrence, status);
        occurrence.decision_origin = "batch_filter";
        changed += 1;
      }
    });
    refreshCandidateState(candidate);
  });
  if (!changed) {
    undoStack.pop();
    updateHistoryButtons();
    return;
  }
  invalidateRedaction("批量脱敏状态已修改，请重新确认。");
  renderCandidates();
}

confirmVisibleBtn.addEventListener("click", () => applyVisibleStatus("confirmed"));
cancelVisibleBtn.addEventListener("click", () => applyVisibleStatus("cancelled"));
restoreVisibleBtn.addEventListener("click", () => applyVisibleStatus("pending"));
undoBtn.addEventListener("click", undoRedaction);
redoBtn.addEventListener("click", redoRedaction);
togglePreviewBtn.addEventListener("click", () => {
  if (!currentDocument) return;
  showMaskedPreview = !showMaskedPreview;
  togglePreviewBtn.textContent = showMaskedPreview ? "返回高亮检查" : "查看脱敏效果";
  renderSources();
});
function applyGroupDecision(candidate, status, origin, message) {
  const before = candidate.group_state || candidate.status || "pending";
  recordHistory("修改词形分组");
  candidate.occurrences.forEach((occurrence) => {
    setOccurrenceStatus(occurrence, status);
    occurrence.decision_origin = origin;
  });
  refreshCandidateState(candidate);
  logRedactionAction(message, { candidate_id: candidate.id, affected_count: candidate.occurrences.length,
    before_state: before, after_state: candidate.group_state });
  invalidateRedaction(message);
  selectionStatus.textContent = message;
  renderCandidates();
}

function handleGroupSingleClick(target) {
  const candidate = sensitiveCandidates.find((item) => item.id === target.dataset.candidateId);
  if (!candidate) return;
  refreshCandidateState(candidate);
  const exclude = candidate.occurrences.some((occurrence) => occurrenceStatus(occurrence) !== "cancelled");
  applyGroupDecision(candidate, exclude ? "cancelled" : "confirmed", "group_single_click",
    exclude ? `已取消全文 ${candidate.occurrences.length} 处“${candidate.value}”的黄色标记` : `已将全文 ${candidate.occurrences.length} 处“${candidate.value}”标为黄色`);
}

function handleInstanceDoubleClick(target) {
  const candidate = sensitiveCandidates.find((item) => item.id === target.dataset.candidateId);
  const occurrence = candidate?.occurrences.find((item) => item.id === target.dataset.occurrenceId);
  if (!candidate || !occurrence) return;
  const timer = markClickTimers.get(candidate.id);
  if (timer) clearTimeout(timer);
  markClickTimers.delete(candidate.id);
  const before = candidate.group_state || candidate.status || "confirmed";
  recordHistory("切换单个出现位置");
  const willHighlight = occurrenceStatus(occurrence) === "cancelled";
  setOccurrenceStatus(occurrence, willHighlight ? "confirmed" : "cancelled");
  occurrence.decision_origin = "instance_double_click";
  refreshCandidateState(candidate);
  const message = willHighlight ? `已将当前位置“${candidate.value}”标为黄色` : `已取消当前位置“${candidate.value}”的黄色标记`;
  logRedactionAction(message, { candidate_id: candidate.id,
    affected_count: 1, before_state: before, after_state: candidate.group_state });
  invalidateRedaction(message);
  selectionStatus.textContent = message;
  renderCandidates();
}

sourceList.addEventListener("click", (event) => {
  const target = event.target.closest(".sensitive-mark");
  if (!target || showMaskedPreview) return;
  const key = target.dataset.candidateId;
  const existing = markClickTimers.get(key);
  if (existing) clearTimeout(existing);
  markClickTimers.set(key, setTimeout(() => {
    markClickTimers.delete(key);
    handleGroupSingleClick(target);
  }, 300));
});
sourceList.addEventListener("dblclick", (event) => {
  const target = event.target.closest(".sensitive-mark");
  if (!target || showMaskedPreview) return;
  event.preventDefault();
  event.stopPropagation();
  handleInstanceDoubleClick(target);
});
sourceList.addEventListener("keydown", (event) => {
  const target = event.target.closest(".sensitive-mark");
  if (target && !showMaskedPreview && (event.key === "Enter" || event.key === " ")) {
    event.preventDefault();
    handleGroupSingleClick(target);
  }
});
keepMixedBtn.addEventListener("click", () => mixedGroupDialog.close());
confirmWholeGroupBtn.addEventListener("click", () => mixedGroupDialog.close());
sourceList.addEventListener("mouseup", () => {
  if (showMaskedPreview) return;
  const selection = window.getSelection();
  const text = selection?.toString().trim() || "";
  if (!text) return;
  const anchor = selection.anchorNode?.parentElement?.closest(".source-text");
  const focus = selection.focusNode?.parentElement?.closest(".source-text");
  if (!anchor || anchor !== focus) {
    selectionStatus.textContent = "请只选择同一段原文中的文字。";
    return;
  }
  selectedSourceText = text;
  selectionStatus.textContent = `已选择“${text}”，点击“将选中文字设为脱敏”。`;
});
testApiBtn.addEventListener("click", testApiConnection);
modelToggleBtn.addEventListener("click", () => setModelSettingsCollapsed(!modelSettingsBody.hidden));
modelProvider.addEventListener("change", updateModelProvider);
modelBaseUrl.addEventListener("input", invalidateModelConnection);
modelName.addEventListener("change", () => { modelSelectionManual = true; updateReasoningChoices(); updateModelName(); });
presetManualModel.addEventListener("input", () => { updateReasoningChoices(); updateModelName(); });
refreshModelsBtn.addEventListener("click", () => refreshModelChoices(undefined, true));
modelReasoning.addEventListener("change", updateModelName);
customModelName.addEventListener("input", updateModelName);
apiKeyInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") testApiConnection();
});
toggleApiKeyBtn.addEventListener("click", () => {
  const showing = apiKeyInput.type === "text";
  apiKeyInput.type = showing ? "password" : "text";
  toggleApiKeyBtn.textContent = showing ? "显示" : "隐藏";
  toggleApiKeyBtn.setAttribute("aria-label", `${showing ? "显示" : "隐藏"} API Key`);
});
clearApiBtn.addEventListener("click", () => {
  apiKey = "";
  modelDiscoveryCache.clear();
  activeModelSettings = {};
  apiKeyInput.value = "";
  apiKeyInput.placeholder = "在这里粘贴 API Key";
  apiKeyInput.type = "password";
  toggleApiKeyBtn.textContent = "显示";
  toggleApiKeyBtn.setAttribute("aria-label", "显示 API Key");
  clearApiBtn.disabled = true;
  modelRecommendation.textContent = "连接后会显示实际选用的模型。";
  apiStatus.textContent = "页面密钥已清除；可选择本地规则整理草稿。";
  updateModelConnectionSummary();
  setModelSettingsCollapsed(false);
});
updateModelProvider();
generateBtn.addEventListener("click", generateOnePager);
cancelGenerateBtn.addEventListener("click", cancelGeneration);
askBtn.addEventListener("click", askQuestion);
includeAnswer.addEventListener("change", () => { applyAnswerBtn.disabled = !includeAnswer.checked; });
applyAnswerBtn.addEventListener("click", async () => {
  if (!includeAnswer.checked || !pendingAnswer || !currentOnePager) return;
  const primaryIds = new Set((currentDocument.masked_segments || []).map((item) => item.id));
  const sourceIds = (pendingAnswer.source_ids || []).filter((id) => primaryIds.has(id));
  if (!sourceIds.length) { askStatus.textContent = "回答没有主材料出处，无法纳入一纸通。"; return; }
  if (pendingAnswer.question.length > 160 || pendingAnswer.answer.length > 500) {
    askStatus.textContent = "本条问答过长，暂不能直接纳入一纸通；请缩小问题范围后重试。";
    return;
  }
  const citedText = sourceIds.map((id) => getSourceMap().get(id)?.text || "").join(" ").replaceAll(",", "");
  const answerNumbers = pendingAnswer.answer.match(/(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)(?:%|％|万|亿|万元|亿元|元|人|次|天|月|年|日)?/g) || [];
  if (answerNumbers.some((number) => !citedText.includes(number.replaceAll(",", "")))) {
    askStatus.textContent = "回答中的数字无法从所引原文核对，暂不能纳入一纸通。";
    return;
  }
  const items = currentOnePager.qa_items || [];
  if (items.length >= 3) { askStatus.textContent = "一纸通最多纳入 3 条问答，请先精简已有内容。"; return; }
  const candidate = JSON.parse(JSON.stringify(currentOnePager));
  candidate.qa_items = [...items, { question: pendingAnswer.question, answer: pendingAnswer.answer, source_ids: sourceIds, needs_confirmation: false }];
  const limit = candidate.generation_requirements?.max_chars;
  if (limit && visibleContentChars(candidate) > limit) {
    applyAnswerBtn.disabled = true;
    askStatus.textContent = "正在压缩一纸通，为问答留出篇幅...";
    try {
      const response = await fetch("/api/compact-one-pager", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document_id: currentDocument.id, confirmation_token: confirmationToken, one_pager: candidate }),
      });
      const payload = await response.json();
      if (!payload.ok) throw new Error(payload.error || "问答纳入失败");
      currentOnePager = payload.one_pager;
    } catch (error) {
      askStatus.textContent = friendlyError(error);
      applyAnswerBtn.disabled = false;
      return;
    }
    applyAnswerBtn.disabled = false;
  } else {
    currentOnePager = candidate;
  }
  currentOnePager.status = "待确认";
  renderOnePager();
  qaInclude.hidden = true;
  askStatus.textContent = "问答已加入一纸通，字数已重新检查；请核对出处和 A4 单页版面。";
});
document.querySelectorAll("#audienceCustom, #maxChars, #customMaxChars, #focusInput, #excludeSectionsInput, #explainTerms, #detailDepth, #writingTone, #includeOverview, #includeFullStructure, #includeArchitecture, #includePractice, #mustKeepInput, #extraRequirements, #documentType, #templateType, #presentationMode").forEach((element) => element.addEventListener("input", updateRequirementsPreview));
presentationModeSelect.addEventListener("change", () => {
  if (currentOnePager?.schema_version !== "3.0") return;
  currentOnePager.generation_requirements = { ...(currentOnePager.generation_requirements || {}), presentation_mode: presentationModeSelect.value };
  currentOnePager.status = "待确认";
  renderOnePager();
});
updateRequirementsPreview();
clearBtn.addEventListener("click", clearAll);
editContactBtn.addEventListener("click", () => openContactDialog().catch((error) => { layoutStatus.textContent = friendlyError(error); }));
contactNameInput.addEventListener("input", () => { selectedContactSourceIds = []; });
contactMethodInput.addEventListener("input", () => { selectedContactSourceIds = []; });
document.querySelector("#skipContactBtn").addEventListener("click", () => contactDialog.close());
document.querySelector("#saveContactBtn").addEventListener("click", () => {
  const name = contactNameInput.value.trim();
  const method = contactMethodInput.value.trim();
  if (/[\n\r]/.test(name + method)) { contactValidation.textContent = "请将信息填写在一行内。"; return; }
  if (method && !/^[+\d()（）\s-]{7,30}$/.test(method) && !/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(method)) {
    contactValidation.textContent = "联系方式格式可能有误，请核对电话号码或邮箱。";
    return;
  }
  currentOnePager.business_contact = { name, method, source_ids: selectedContactSourceIds };
  currentOnePager.status = "待确认";
  contactDialog.close();
  renderOnePager();
  setStep("review");
});
closeDialogBtn.addEventListener("click", () => sourceDialog.close());

pdfBtn.addEventListener("click", () => {
  if (checkPageOverflow()) return;
  markOnePagerConfirmed();
  const previousTitle = document.title;
  document.title = onePagerExportName("pdf").replace(/\.pdf$/, "");
  window.addEventListener("afterprint", () => { document.title = previousTitle; }, { once: true });
  window.print();
});
compactBtn.addEventListener("click", compactCurrentOnePager);
pngBtn.addEventListener("click", () => exportPng().catch((error) => { layoutStatus.textContent = friendlyError(error); }));
docxBtn.addEventListener("click", () => exportDocx().catch((error) => { layoutStatus.textContent = friendlyError(error); }));
markdownBtn.addEventListener("click", () => {
  markOnePagerConfirmed();
  downloadBlob(new Blob([markdownOnePager()], { type: "text/markdown;charset=utf-8" }), onePagerExportName("md"));
});
jsonBtn.addEventListener("click", () => {
  markOnePagerConfirmed();
  downloadBlob(new Blob([JSON.stringify(currentOnePager, null, 2)], { type: "application/json;charset=utf-8" }), onePagerExportName("json"));
});
templateSelect.addEventListener("change", () => {
  if (!currentOnePager) return;
  const nextIsKnowledge = templateSelect.value.startsWith("knowledge-");
  const currentIsKnowledge = currentOnePager.schema_version === "3.0";
  if (nextIsKnowledge !== currentIsKnowledge) {
    generateStatus.textContent = "已切换新版/旧版模板，请点击“生成一纸通”生成对应结构；当前结果会保留到新结果生成完成。";
    return;
  }
  currentOnePager.meta.template = templateSelect.value;
  if (currentIsKnowledge) {
    const trainingType = { "knowledge-product": "product", "knowledge-policy": "policy", "knowledge-operation": "operation" }[templateSelect.value];
    if (trainingType) currentOnePager.meta.training_type = trainingType;
  }
  renderOnePager();
});
documentTypeSelect.addEventListener("change", () => {
  if (currentOnePager && documentTypeSelect.value !== "auto") {
    currentOnePager.meta.document_type = documentTypeSelect.value;
    documentTypeStatus.textContent = `已手动设为：${documentTypeSelect.value}`;
    renderOnePager();
  }
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files?.[0];
  if (file) {
    fileMeta.textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
  }
});

supplementInput?.addEventListener("change", () => {
  if ((supplementInput.files || []).length) {
    askStatus.textContent = `已选择 ${supplementInput.files.length} 份补充材料，请点击“抽取补充材料”。`;
  }
});

window.addEventListener("resize", redrawImageCanvases);
document.addEventListener("keydown", (event) => {
  if (!(event.ctrlKey || event.metaKey) || event.key.toLowerCase() !== "z") return;
  const editable = event.target.matches("input, textarea, [contenteditable='true']");
  if (editable) return;
  event.preventDefault();
  if (event.shiftKey) redoRedaction();
  else undoRedaction();
});
