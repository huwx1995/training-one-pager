// Preview rendering shared by parsing and redaction views.
function renderParsePagedPreview(preview, previewIndex) {
  return (preview.pages || []).slice(0, visiblePreviewItems.get(`page-${previewIndex}`) || previewPageBatch).map((page) => {
    const format = preview.format || "document";
    const ordered = [...(page.elements || [])].sort((a, b) => Number(a.order || 0) - Number(b.order || 0));
    const elements = ordered.map((element) => element.kind === "image"
      ? parseImage(element.asset_id)
      : `<section class="flow-paragraph">${(element.segment_ids || []).map(parseSegment).join("")}</section>`).join("");
    const annotationLabel = (page.annotations || []).some((item) => item.kind === "pptx_chart_data") ? "图表数据与备注" : "备注与批注";
    const annotations = (page.annotations || []).length
      ? `<aside class="page-annotations"><strong>${annotationLabel}</strong>${page.annotations.map((item) => (item.segment_ids || []).map(parseSegment).join("")).join("")}</aside>`
      : "";
    return `<article class="document-page-card" id="parse-preview-${previewIndex}-page-${page.number}">
      <header><strong>${format === "pptx" ? "幻灯片" : "第"} ${page.number}${format === "pptx" ? "" : " 页"}</strong></header>
      <div class="structured-page-content">${elements || (page.background_url
        ? `<img class="structured-page-background" src="${escapeHtml(page.background_url)}" alt="第${page.number}页预览">`
        : '<p class="hint">本页没有可提取的文字或图片。</p>')}</div>${annotations}
    </article>`;
  }).join("");
}

function renderParseFlowPreview(preview, previewIndex) {
  const blocks = preview.flow_blocks || [];
  const visibleBlocks = preview.format === "audio" ? blocks : blocks.slice(0, visiblePreviewItems.get(`flow-${previewIndex}`) || previewFlowBatch);
  return `${preview.spreadsheet_notice ? `<p class="hint">${escapeHtml(preview.spreadsheet_notice)}</p>` : ""}<article class="flow-document parse-flow-document">
    ${visibleBlocks.map((block) => {
      if (block.kind === "image") return parseImage(block.asset_id);
      const content = (block.segment_ids || []).map(parseSegment).join("");
      return block.kind === "table_row" ? `<div class="flow-table-row">${content}</div>` : `<section class="flow-paragraph">${content}</section>`;
    }).join("")}
  </article>`;
}

function previewMoreButton(preview, index, parsing = false) {
  if (preview.format === "audio") return "";
  const paged = preview.mode === "paged";
  const key = `${paged ? "page" : "flow"}-${index}`;
  const total = paged ? (preview.pages || []).length : (preview.flow_blocks || []).length;
  const shown = visiblePreviewItems.get(key) || (paged ? previewPageBatch : previewFlowBatch);
  return shown < total ? `<button class="ghost preview-load-more" type="button" data-preview-more="${key}" data-parsing="${parsing}">继续显示（已显示 ${Math.min(shown, total)} / ${total} ${paged ? "页" : "段"}）</button>` : "";
}

function setupPreviewMore(container, parsing) {
  container.querySelectorAll("[data-preview-more]").forEach((button) => button.addEventListener("click", () => {
    const key = button.dataset.previewMore;
    const batch = key.startsWith("page-") ? previewPageBatch : previewFlowBatch;
    visiblePreviewItems.set(key, (visiblePreviewItems.get(key) || batch) + batch);
    const scroller = container.closest(parsing ? ".parse-workspace-body" : ".simple-redaction-workspace");
    const previousScroll = scroller?.scrollTop || 0;
    if (parsing) renderParseSources(); else renderSources();
    if (scroller) scroller.scrollTop = previousScroll;
  }));
}


function previewSegment(segmentId, extraClass = "") {
  const segment = allOriginalSegments().find((item) => item.id === segmentId);
  if (!segment) return "";
  return `<div class="source-text preview-text-block ${extraClass}" id="source-${escapeHtml(segment.id)}" data-segment-id="${escapeHtml(segment.id)}">
    ${segment.source_type === "audio" ? `<span class="audio-time">${formatAudioTime(segment.start_ms)}–${formatAudioTime(segment.end_ms)} ${escapeHtml(segment.speaker || "")}</span>` : ""}
    ${showMaskedPreview ? maskedPreviewText(segment) : highlightedSourceText(segment)}
  </div>`;
}

function previewImage(assetId, className = "") {
  const asset = allImageAssets().find((item) => item.id === assetId);
  if (!asset) return "";
  const label = asset.source?.kind === "pptx_chart" ? "图表" : "图片";
  const regions = imageRegions.filter((region) => region.asset_id === asset.id);
  return `<div class="preview-image-wrap ${className}" id="image-${escapeHtml(asset.id)}">
    <div class="image-stage" data-asset-id="${escapeHtml(asset.id)}">
      <img src="${escapeHtml(asset.preview_url)}" alt="${escapeHtml(asset.file_name)} 第${asset.page}页${label}" draggable="false">
      <canvas class="redaction-canvas" data-asset-id="${escapeHtml(asset.id)}"></canvas>
    </div>
    <button class="ghost image-add-region" type="button" data-add-image-region="${escapeHtml(asset.id)}">添加图片脱敏框</button>
    ${regions.length ? `<div class="image-region-list">${regions.map((region) => `
      <div class="image-region-row" data-region-id="${escapeHtml(region.id)}">
        <span>${escapeHtml(regionTypeLabel(region.type))}</span>
        ${[["x", "左"], ["y", "上"], ["width", "宽"], ["height", "高"]].map(([field, label]) => `<label>${label}<input type="number" min="0" max="100" step="1" value="${Math.round(region[field] * 100)}" data-region-field="${field}" aria-label="图片脱敏框${label}（百分比）"></label>`).join("")}
        <button class="region-delete" type="button" data-region-id="${escapeHtml(region.id)}">删除</button>
      </div>`).join("")}</div>` : ""}
  </div>`;
}

function renderPagedPreview(preview, previewIndex) {
  return (preview.pages || []).slice(0, visiblePreviewItems.get(`page-${previewIndex}`) || previewPageBatch).map((page) => {
    const format = preview.format || "document";
    const orderedElements = [...(page.elements || [])].sort((a, b) => Number(a.order || 0) - Number(b.order || 0));
    const elements = orderedElements.map((element) => {
      if (element.kind === "image") return previewImage(element.asset_id, "flow-preview-image");
      return `<section class="flow-paragraph">${(element.segment_ids || []).map((id) => previewSegment(id)).join("")}</section>`;
    }).join("");
    const annotationLabel = (page.annotations || []).some((item) => item.kind === "pptx_chart_data") ? "图表数据与备注" : "备注与批注";
    const annotations = (page.annotations || []).length ? `<aside class="page-annotations"><strong>${annotationLabel}</strong>${page.annotations.map((item) => (item.segment_ids || []).map((id) => previewSegment(id)).join("")).join("")}</aside>` : "";
    return `<article class="document-page-card" id="preview-${previewIndex}-page-${page.number}">
      <header><strong>${format === "pptx" ? "幻灯片" : "第"} ${page.number}${format === "pptx" ? "" : " 页"}</strong></header>
      <div class="structured-page-content">${elements || (page.background_url ? `<img class="structured-page-background" src="${escapeHtml(page.background_url)}" alt="第${page.number}页预览">` : '<p class="hint">本页没有可提取的文字或图片。</p>')}</div>${annotations}
    </article>`;
  }).join("");
}

function renderFlowPreview(preview, previewIndex) {
  return `${preview.spreadsheet_notice ? `<p class="hint">${escapeHtml(preview.spreadsheet_notice)}</p>` : ""}<article class="flow-document" id="preview-${previewIndex}-flow">
    ${(preview.flow_blocks || []).slice(0, visiblePreviewItems.get(`flow-${previewIndex}`) || previewFlowBatch).map((block) => {
      if (block.kind === "image") return previewImage(block.asset_id, "flow-preview-image");
      const ids = block.segment_ids || [];
      if (block.kind === "table_row") return `<div class="flow-table-row">${ids.map((id) => previewSegment(id)).join("")}</div>`;
      const story = block.story && block.story !== "body" ? `<span class="story-label">${escapeHtml(block.story.replaceAll("docx_", ""))}</span>` : "";
      return `<section class="flow-paragraph">${story}${ids.map((id) => previewSegment(id)).join("")}</section>`;
    }).join("")}
  </article>`;
}

