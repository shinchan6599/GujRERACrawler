const state = {
  listing: null,
  filteredProjects: [],
  selectedProjectId: null,
  detail: null,
  showAllInventory: false,
  selectedInventoryIndex: 0,
  selectedQuarterId: null,
  quarterDetail: null,
  quarterDetailLoading: false,
  activeSyncRunId: null,
  syncPollTimer: null,
};

const els = {
  totalProjects: document.getElementById("totalProjects"),
  filteredProjects: document.getElementById("filteredProjects"),
  summaryStats: document.getElementById("summaryStats"),
  projectList: document.getElementById("projectList"),
  detailState: document.getElementById("detailState"),
  detailContent: document.getElementById("detailContent"),
  listCountBadge: document.getElementById("listCountBadge"),
  searchInput: document.getElementById("searchInput"),
  districtFilter: document.getElementById("districtFilter"),
  typeFilter: document.getElementById("typeFilter"),
  statusFilter: document.getElementById("statusFilter"),
  storageSummary: document.getElementById("storageSummary"),
  refreshStorage: document.getElementById("refreshStorage"),
  syncLimit: document.getElementById("syncLimit"),
  syncOffset: document.getElementById("syncOffset"),
  syncConcurrency: document.getElementById("syncConcurrency"),
  startSync: document.getElementById("startSync"),
  syncStatus: document.getElementById("syncStatus"),
  ragQuery: document.getElementById("ragQuery"),
  askRag: document.getElementById("askRag"),
  ragAnswer: document.getElementById("ragAnswer"),
  ragCitations: document.getElementById("ragCitations"),
};

function formatNumber(value) {
  if (value === null || value === undefined || value === "") return "NA";
  return Number(value).toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

function formatCurrency(value) {
  if (value === null || value === undefined) return "NA";
  return `Rs ${formatNumber(value)}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function getStatusClass(status) {
  const text = (status || "").toLowerCase();
  if (text.includes("complete")) return "status-completed";
  if (text.includes("ongoing")) return "status-ongoing";
  if (text.includes("new")) return "status-new";
  return "status-default";
}

function buildOptions(select, values, placeholder) {
  select.innerHTML = "";
  const baseOption = document.createElement("option");
  baseOption.value = "";
  baseOption.textContent = placeholder;
  select.appendChild(baseOption);
  [...values]
    .filter(Boolean)
    .sort((a, b) => a.localeCompare(b))
    .forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      select.appendChild(option);
    });
}

function renderSummaryStats(summaryStats) {
  els.summaryStats.innerHTML = summaryStats
    .map((stat) => {
      const districts = Object.entries(stat.counts || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 3)
        .map(([name, count]) => `${name}: ${formatNumber(count)}`)
        .join(" · ");
      return `
        <article class="stat-card">
          <p>${escapeHtml(stat.project_type || "Unknown Type")}</p>
          <strong>${formatNumber(stat.total)}</strong>
          <h3>District spread</h3>
          <p>${escapeHtml(districts || "No district split available")}</p>
        </article>
      `;
    })
    .join("");
}

function applyFilters() {
  const search = els.searchInput.value.trim().toLowerCase();
  const district = els.districtFilter.value;
  const type = els.typeFilter.value;
  const status = els.statusFilter.value;
  const all = state.listing?.projects || [];

  state.filteredProjects = all.filter((project) => {
    const matchesSearch =
      !search ||
      [project.project_name, project.promoter_name, project.reg_no]
        .filter(Boolean)
        .some((value) => value.toLowerCase().includes(search));
    const matchesDistrict =
      !district || project.district_name === district || project.district_type === district;
    const matchesType = !type || project.project_type === type;
    const matchesStatus = !status || project.project_status === status;
    return matchesSearch && matchesDistrict && matchesType && matchesStatus;
  });

  renderProjectList();
  els.filteredProjects.textContent = formatNumber(state.filteredProjects.length);
  els.listCountBadge.textContent = `${state.filteredProjects.length} results`;
}

function renderProjectList() {
  if (!state.filteredProjects.length) {
    els.projectList.innerHTML = `<div class="empty-state"><h2>No matches</h2><p>Adjust the filters and try again.</p></div>`;
    return;
  }

  els.projectList.innerHTML = state.filteredProjects
    .map((project) => `
      <article class="project-card ${project.project_reg_id === state.selectedProjectId ? "active" : ""}" data-project-id="${project.project_reg_id}">
        <div class="project-meta">
          <span>${escapeHtml(project.district_name || "Unknown District")}</span>
          <span>${escapeHtml(project.project_type || "Unknown Type")}</span>
          <span class="badge ${getStatusClass(project.project_status)}">${escapeHtml(project.project_status || "Unknown")}</span>
        </div>
        <h3>${escapeHtml(project.project_name)}</h3>
        <p>${escapeHtml(project.promoter_name || "Promoter unavailable")}</p>
        <p>${escapeHtml(project.reg_no || "Registration unavailable")}</p>
        <p>${escapeHtml(project.project_address || "Address unavailable")}</p>
      </article>
    `)
    .join("");

  els.projectList.querySelectorAll(".project-card").forEach((card) => {
    card.addEventListener("click", () => selectProject(Number(card.dataset.projectId)));
  });
}

function detailKeyValue(label, value) {
  return `
    <div class="kv-item">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "NA")}</strong>
    </div>
  `;
}

function renderStorageSummary(summary) {
  els.storageSummary.innerHTML = [
    ["DB Path", summary.db_path],
    ["Projects", formatNumber(summary.project_count)],
    ["Blocks", formatNumber(summary.block_count)],
    ["Quarters", formatNumber(summary.quarter_count)],
    ["Inventory Rows", formatNumber(summary.inventory_count)],
    ["RAG Chunks", formatNumber(summary.rag_chunk_count)],
  ].map(([label, value]) => detailKeyValue(label, value)).join("");

  const last = summary.last_sync_run;
  if (last) {
    els.syncStatus.textContent =
      `Last sync run #${last.id}: ${last.status}. Synced ${last.synced_projects}/${last.total_projects ?? "?"}, failed ${last.failed_projects}.`;
  }
}

async function loadStorageSummary() {
  try {
    const response = await fetch("/api/storage/summary");
    if (!response.ok) {
      throw new Error(`Storage summary failed with ${response.status}`);
    }
    const summary = await response.json();
    renderStorageSummary(summary);
  } catch (error) {
    els.storageSummary.innerHTML = detailKeyValue("Storage", error.message);
  }
}

async function pollSyncRun(runId) {
  if (state.syncPollTimer) {
    clearTimeout(state.syncPollTimer);
    state.syncPollTimer = null;
  }
  try {
    const response = await fetch(`/api/storage/runs/${runId}`);
    if (!response.ok) {
      throw new Error(`Sync status failed with ${response.status}`);
    }
    const run = await response.json();
    els.syncStatus.textContent =
      `Run #${run.id}: ${run.status}. Synced ${run.synced_projects}/${run.total_projects ?? "?"}, failed ${run.failed_projects}.`;
    if (run.status === "running") {
      state.syncPollTimer = setTimeout(() => pollSyncRun(runId), 2500);
    } else {
      await loadStorageSummary();
    }
  } catch (error) {
    els.syncStatus.textContent = error.message;
  }
}

async function startLocalSync() {
  els.syncStatus.textContent = "Starting local sync...";
  const payload = {
    limit: els.syncLimit.value ? Number(els.syncLimit.value) : null,
    offset: els.syncOffset.value ? Number(els.syncOffset.value) : 0,
    concurrency: els.syncConcurrency.value ? Number(els.syncConcurrency.value) : 4,
  };
  try {
    const response = await fetch("/api/storage/sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      throw new Error(`Sync start failed with ${response.status}`);
    }
    const run = await response.json();
    state.activeSyncRunId = run.id;
    pollSyncRun(run.id);
  } catch (error) {
    els.syncStatus.textContent = error.message;
  }
}

async function askLocalKnowledge() {
  const query = els.ragQuery.value.trim();
  if (!query) {
    els.ragAnswer.textContent = "Enter a query first.";
    return;
  }
  els.ragAnswer.textContent = "Querying local knowledge base...";
  els.ragCitations.innerHTML = "";
  try {
    const response = await fetch("/api/rag/answer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, limit: 8 }),
    });
    if (!response.ok) {
      throw new Error(`RAG answer failed with ${response.status}`);
    }
    const result = await response.json();
    els.ragAnswer.textContent = result.answer;
    els.ragCitations.innerHTML = result.citations.slice(0, 8).map((item) => `
      <button class="ghost rag-open-project" data-project-id="${item.project_reg_id}">
        ${escapeHtml(item.project_name || "Unknown project")} · ${escapeHtml(item.section)} · ${escapeHtml(item.title)}
      </button>
    `).join("");
    els.ragCitations.querySelectorAll(".rag-open-project").forEach((button) => {
      button.addEventListener("click", () => {
        selectProject(Number(button.dataset.projectId));
      });
    });
  } catch (error) {
    els.ragAnswer.textContent = error.message;
  }
}

function renderTrendSvg(trend) {
  if (!trend.length) {
    return `<p class="note">Quarterly progress trend is not available for this project.</p>`;
  }
  const width = 760;
  const height = 220;
  const pad = 24;
  const values = trend.map((item) => item.progress_pct || 0);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 100);
  const stepX = trend.length === 1 ? 0 : (width - pad * 2) / (trend.length - 1);
  const points = trend
    .map((item, index) => {
      const x = pad + index * stepX;
      const y = height - pad - ((item.progress_pct || 0) - min) / (max - min || 1) * (height - pad * 2);
      return [x, y];
    });
  const polyline = points.map(([x, y]) => `${x},${y}`).join(" ");
  const dots = points
    .map(([x, y], index) => `<circle cx="${x}" cy="${y}" r="4.5" fill="#d96c2d"><title>${escapeHtml(trend[index].quarter_name)}: ${formatNumber(trend[index].progress_pct)}%</title></circle>`)
    .join("");

  return `
    <svg class="trend" viewBox="0 0 ${width} ${height}" role="img" aria-label="Quarterly progress trend">
      <rect x="0" y="0" width="${width}" height="${height}" rx="16" fill="rgba(255,255,255,0.55)"></rect>
      <line x1="${pad}" y1="${height - pad}" x2="${width - pad}" y2="${height - pad}" stroke="rgba(30,42,47,0.18)"></line>
      <line x1="${pad}" y1="${pad}" x2="${pad}" y2="${height - pad}" stroke="rgba(30,42,47,0.18)"></line>
      <polyline fill="none" stroke="#0c8b7a" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" points="${polyline}"></polyline>
      ${dots}
    </svg>
    <div class="trend-labels">${trend.map((item) => `<span>${escapeHtml(item.quarter_name || "")}</span>`).join("")}</div>
  `;
}

function buildDocumentLinks(documents) {
  const buckets = [
    ...(documents.project_docs || []),
    ...(documents.financial_docs || []),
  ].slice(0, 28);
  const fixed = [
    documents.certificate,
    documents.project_image,
    documents.project_brochure,
    documents.promoter_registration_certificate,
  ].filter((item) => item?.download_url);
  const links = [
    ...fixed.map((item, index) => ({
      label: ["Certificate", "Project image", "Project brochure", "Promoter registration"][index] || "Document",
      download_url: item.download_url,
    })),
    ...buckets,
  ];
  if (!links.length) {
    return `<p class="note">No document links were available in the public payload.</p>`;
  }
  return `<div class="list-links">${links
    .map((doc) => `<a href="${doc.download_url}" target="_blank" rel="noreferrer">${escapeHtml(doc.label)}</a>`)
    .join("")}</div>`;
}

function renderInventoryRows(items) {
  const limit = state.showAllInventory ? items.length : 30;
  return items.slice(0, limit).map((item) => `
    <tr>
      <td>${escapeHtml(item.flat_no || "")}</td>
      <td>${escapeHtml(item.block_name || "")}</td>
      <td>${escapeHtml(item.usage || "")}</td>
      <td>${escapeHtml(item.unit_status || "")}</td>
      <td>${formatNumber(item.carpet_area_sqm)}</td>
      <td>${formatNumber(item.balcony_area_sqm)}</td>
      <td>${formatCurrency(item.unit_consideration)}</td>
      <td>${formatCurrency(item.received_amount)}</td>
      <td>${escapeHtml(item.date_of_agreement || "NA")}</td>
      <td>${escapeHtml(item.allottee_name || "NA")}</td>
      <td>${escapeHtml(item.type_of_kyc || "NA")}</td>
      <td>${escapeHtml(item.kyc_id || "NA")}</td>
      <td>${escapeHtml(item.mobile_number || "NA")}</td>
      <td><button class="ghost inventory-select" data-inventory-index="${items.indexOf(item)}">View</button></td>
    </tr>
  `).join("");
}

function buildQuarterProgressRows(detail) {
  const trend = detail.progress?.quarterly_trend || [];
  return trend.map((item, index) => {
    const previous = index > 0 ? trend[index - 1].progress_pct : null;
    const delta = previous === null || previous === undefined || item.progress_pct === null || item.progress_pct === undefined
      ? null
      : item.progress_pct - previous;
    const quarterMeta = detail.quarters?.[index] || null;
    return {
      sequence: index + 1,
      quarter_name: item.quarter_name,
      progress_pct: item.progress_pct,
      delta,
      filing_quarter: quarterMeta?.quarter_name || null,
      submitted_on: quarterMeta?.submitted_on || null,
      range: quarterMeta ? `${quarterMeta.start_date || "NA"} to ${quarterMeta.end_date || "NA"}` : null,
      extended_date: quarterMeta?.extended_date || null,
      filing_status: quarterMeta?.status || quarterMeta?.payment_status || null,
    };
  });
}

function renderInventoryFocus(unit) {
  if (!unit) {
    return `<p class="note">Select a unit row to inspect unit-level details.</p>`;
  }
  return `
    <div class="kv-grid">
      ${detailKeyValue("Flat No", unit.flat_no)}
      ${detailKeyValue("Block", unit.block_name)}
      ${detailKeyValue("Usage", unit.usage)}
      ${detailKeyValue("Status", unit.unit_status)}
      ${detailKeyValue("Carpet Area", unit.carpet_area_sqm === null || unit.carpet_area_sqm === undefined ? "NA" : `${formatNumber(unit.carpet_area_sqm)} sqm`)}
      ${detailKeyValue("Balcony Area", unit.balcony_area_sqm === null || unit.balcony_area_sqm === undefined ? "NA" : `${formatNumber(unit.balcony_area_sqm)} sqm`)}
      ${detailKeyValue("Agreement Date", unit.date_of_agreement)}
      ${detailKeyValue("Allottee", unit.allottee_name)}
      ${detailKeyValue("KYC Type", unit.type_of_kyc)}
      ${detailKeyValue("KYC ID", unit.kyc_id)}
      ${detailKeyValue("Mobile", unit.mobile_number)}
      ${detailKeyValue("Encumbrance", unit.encumbrance_status)}
    </div>
  `;
}

function renderQuarterDocumentLinks(quarterDetail) {
  const docs = quarterDetail?.public_documents || {};
  const links = [
    { label: "Form 1 PDF", href: docs.form_one_pdf?.download_url },
    { label: "Form 2 PDF", href: docs.form_two_pdf?.download_url },
    { label: "Form 3 PDF", href: docs.form_three_pdf?.download_url },
    { label: "Form 8 PDF", href: docs.form_eight_pdf?.download_url },
  ].filter((item) => item.href);
  if (!links.length) {
    return `<p class="note">No downloadable public form files were available for this quarter.</p>`;
  }
  return `<div class="list-links">${links.map((item) => `<a href="${item.href}" target="_blank" rel="noreferrer">${escapeHtml(item.label)}</a>`).join("")}</div>`;
}

function pickDefaultQuarter(detail) {
  const quarters = detail?.quarters || [];
  const regular = quarters.filter((item) => /^Q-\d+$/i.test(item.quarter_name || ""));
  const source = regular.length ? regular : quarters;
  return source.length ? source[source.length - 1].quarter_id : null;
}

function renderQuarterDetailPanel() {
  if (state.quarterDetailLoading) {
    return `<p class="note">Loading selected quarter details...</p>`;
  }
  if (!state.quarterDetail) {
    return `<p class="note">Click a quarter row below to fetch the detailed quarter view.</p>`;
  }
  const detail = state.quarterDetail;
  return `
    <div class="kv-grid">
      ${detailKeyValue("Quarter", detail.quarter_name)}
      ${detailKeyValue("Index", detail.qtr_index)}
      ${detailKeyValue("Progress", detail.progress_pct === null || detail.progress_pct === undefined ? "NA" : `${formatNumber(detail.progress_pct)}%`)}
      ${detailKeyValue("Delta", detail.delta_from_previous_pct === null || detail.delta_from_previous_pct === undefined ? "NA" : `${detail.delta_from_previous_pct >= 0 ? "+" : ""}${formatNumber(detail.delta_from_previous_pct)}%`)}
      ${detailKeyValue("Range", `${detail.start_date || "NA"} to ${detail.end_date || "NA"}`)}
      ${detailKeyValue("Extended Date", detail.extended_date)}
      ${detailKeyValue("Status", detail.status || detail.payment_status)}
      ${detailKeyValue("Submitted", detail.submitted_on)}
      ${detailKeyValue("Enquiry Open", detail.enquiry_open === null ? "NA" : detail.enquiry_open ? "Yes" : "No")}
      ${detailKeyValue("Application Type", detail.public_documents?.application_type)}
      ${detailKeyValue("Public Submission", detail.public_documents?.submission_date)}
    </div>
    <div style="margin-top:16px;">
      ${renderQuarterDocumentLinks(detail)}
    </div>
  `;
}

async function loadQuarterDetail(projectId, quarterId) {
  state.selectedQuarterId = quarterId;
  state.quarterDetailLoading = true;
  renderDetail(state.detail);
  try {
    const response = await fetch(`/api/projects/${projectId}/quarters/${quarterId}`);
    if (!response.ok) {
      throw new Error(`Quarter request failed with ${response.status}`);
    }
    state.quarterDetail = await response.json();
  } catch (error) {
    state.quarterDetail = {
      quarter_name: "Unavailable",
      public_documents: {},
      status: error.message,
    };
  } finally {
    state.quarterDetailLoading = false;
    renderDetail(state.detail);
  }
}

function renderDetail(detail) {
  const blocksTable = detail.blocks.length ? `
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Block</th>
            <th>Timeline</th>
            <th>Booking</th>
            <th>Progress</th>
          </tr>
        </thead>
        <tbody>
          ${detail.blocks.map((block) => `
            <tr>
              <td>
                <strong>${escapeHtml(block.block_name || "NA")}</strong><br>
                ${escapeHtml(block.block_id || "")}
              </td>
              <td>${escapeHtml(block.dev_start_date || "NA")} to ${escapeHtml(block.dev_end_date || "NA")}</td>
              <td>${formatNumber(block.units_booked)} booked / ${formatNumber(block.units_unbooked)} open</td>
              <td>
                ${formatNumber(block.block_progress_pct)}%
                <div class="meter"><span style="width:${Math.max(0, Math.min(100, block.block_progress_pct || 0))}%"></span></div>
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  ` : `<p class="note">Block data unavailable.</p>`;

  const applicationsTable = detail.applications.length ? `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Type</th><th>Approval Date</th><th>Application Number</th></tr></thead>
        <tbody>
          ${detail.applications.map((item) => `
            <tr>
              <td>${escapeHtml(item.type || "")}</td>
              <td>${escapeHtml(item.approval_date || "")}</td>
              <td>${escapeHtml(item.application_number || "")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  ` : `<p class="note">No application history was returned.</p>`;

  const quartersTable = detail.quarters.length ? `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Quarter</th><th>Index</th><th>Range</th><th>Extended Date</th><th>Status</th><th>Submitted</th><th>Action</th></tr></thead>
        <tbody>
          ${detail.quarters.map((item) => `
            <tr>
              <td>${escapeHtml(item.quarter_name || "")}</td>
              <td>${escapeHtml(item.qtr_index || "NA")}</td>
              <td>${escapeHtml(item.start_date || "")} to ${escapeHtml(item.end_date || "")}</td>
              <td>${escapeHtml(item.extended_date || "NA")}</td>
              <td>${escapeHtml(item.status || item.payment_status || "NA")}</td>
              <td>${escapeHtml(item.submitted_on || "NA")}</td>
              <td><button class="ghost quarter-select" data-quarter-id="${item.quarter_id}">${item.quarter_id === state.selectedQuarterId ? "Selected" : "View details"}</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  ` : `<p class="note">Quarterly filing history unavailable.</p>`;
  const quarterProgressRows = buildQuarterProgressRows(detail);
  const quarterProgressTable = quarterProgressRows.length ? `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Seq</th><th>Reported Period</th><th>Progress %</th><th>Delta</th><th>Filed Quarter</th><th>Range</th><th>Status</th><th>Submitted</th></tr></thead>
        <tbody>
          ${quarterProgressRows.map((item) => `
            <tr>
              <td>${escapeHtml(item.sequence)}</td>
              <td>${escapeHtml(item.quarter_name || "NA")}</td>
              <td>${item.progress_pct === null || item.progress_pct === undefined ? "NA" : `${formatNumber(item.progress_pct)}%`}</td>
              <td>${item.delta === null ? "NA" : `${item.delta >= 0 ? "+" : ""}${formatNumber(item.delta)}%`}</td>
              <td>${escapeHtml(item.filing_quarter || "NA")}</td>
              <td>${escapeHtml(item.range || "NA")}</td>
              <td>${escapeHtml(item.filing_status || "NA")}</td>
              <td>${escapeHtml(item.submitted_on || "NA")}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  ` : `<p class="note">Quarter-to-quarter progress data is unavailable.</p>`;

  const auditsTable = detail.annual_audits.length ? `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Financial Year</th><th>Status</th><th>Submitted On</th><th>PDF</th></tr></thead>
        <tbody>
          ${detail.annual_audits.map((item) => `
            <tr>
              <td>${escapeHtml(item.financial_year || "")}</td>
              <td>${escapeHtml(item.status || "")}</td>
              <td>${escapeHtml(item.submitted_on || "NA")}</td>
              <td>${item.pdf_download_url ? `<a href="${item.pdf_download_url}" target="_blank" rel="noreferrer">Open</a>` : "NA"}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  ` : `<p class="note">Form 5 records unavailable.</p>`;

  const inventory = detail.inventory || [];
  if (state.selectedInventoryIndex >= inventory.length) {
    state.selectedInventoryIndex = 0;
  }
  const selectedInventory = inventory[state.selectedInventoryIndex] || inventory[0] || null;
  const canToggleInventory = inventory.length > 30;
  const firstCoordinate = detail.location.coordinates?.[0];
  const mapLink = firstCoordinate
    ? `https://www.google.com/maps?q=${firstCoordinate.lat},${firstCoordinate.lng}`
    : null;

  els.detailContent.innerHTML = `
    <section class="detail-hero panel-card full">
      <div>
        <div class="hero-stack">
          <span class="badge ${getStatusClass(detail.registration.project_status)}">${escapeHtml(detail.registration.project_status || "Unknown Status")}</span>
          <span class="chip">${escapeHtml(detail.registration.project_type || "Unknown Type")}</span>
          <span class="chip">${escapeHtml(detail.registration.project_reg_no || "No registration number")}</span>
        </div>
        <h2>${escapeHtml(detail.registration.project_name || "Unnamed project")}</h2>
        <p class="lede">${escapeHtml(detail.promoter.name || "Promoter unavailable")}</p>
      </div>
      <div class="kv-grid">
        ${detailKeyValue("District", detail.location.district)}
        ${detailKeyValue("Taluka", detail.location.taluka)}
        ${detailKeyValue("Approved", detail.registration.approved_on)}
        ${detailKeyValue("Original End", detail.registration.original_end_date)}
      </div>
    </section>

    <section class="detail-grid">
      <article class="panel-card">
        <h3>Registration</h3>
        <div class="kv-grid">
          ${detailKeyValue("Project Reg ID", detail.registration.project_reg_id)}
          ${detailKeyValue("Acknowledgement", detail.registration.project_ack_no)}
          ${detailKeyValue("Start Date", detail.registration.start_date)}
          ${detailKeyValue("Extended End", detail.registration.extended_end_date)}
          ${detailKeyValue("Workflow ID", detail.registration.wfo_id)}
          ${detailKeyValue("Last Updated", detail.registration.last_updated_on)}
        </div>
      </article>

      <article class="panel-card">
        <h3>Promoter</h3>
        <div class="kv-grid">
          ${detailKeyValue("Type", detail.promoter.type)}
          ${detailKeyValue("Mobile", detail.promoter.mobile_no)}
          ${detailKeyValue("Email", detail.promoter.email_id)}
          ${detailKeyValue("PAN", detail.promoter.pan_no_masked)}
          ${detailKeyValue("Company Reg", detail.promoter.company_reg_no)}
          ${detailKeyValue("Address", detail.promoter.address)}
        </div>
      </article>

      <article class="panel-card">
        <h3>Financials</h3>
        <div class="kv-grid">
          ${detailKeyValue("Total Project Cost", formatCurrency(detail.financials.total_project_cost))}
          ${detailKeyValue("Registration Fee", formatCurrency(detail.financials.registration_fee))}
          ${detailKeyValue("Payment Status", detail.financials.payment_status)}
          ${detailKeyValue("Units", formatNumber(detail.financials.total_units))}
          ${detailKeyValue("Min Unit Cost", formatCurrency(detail.financials.min_unit_cost))}
          ${detailKeyValue("Max Unit Cost", formatCurrency(detail.financials.max_unit_cost))}
        </div>
      </article>

      <article class="panel-card">
        <h3>Progress</h3>
        <div class="kv-grid">
          ${detailKeyValue("Headline Score", formatNumber(detail.progress.score))}
          ${detailKeyValue("Label", detail.progress.label)}
          ${detailKeyValue("Architect Score", formatNumber(detail.progress.arch_score))}
          ${detailKeyValue("Engineer Score", formatNumber(detail.progress.engg_score))}
          ${detailKeyValue("Time Laps Ratio", formatNumber(detail.progress.time_laps_ratio))}
          ${detailKeyValue("Has Extension", detail.registration.has_extension ? "Yes" : "No")}
        </div>
      </article>

      <article class="panel-card full">
        <h3>Quarterly Trend</h3>
        ${renderTrendSvg(detail.progress.quarterly_trend || [])}
      </article>

      <article class="panel-card full">
        <h3>Blocks</h3>
        ${blocksTable}
      </article>

      <article class="panel-card">
        <h3>Units Summary</h3>
        <div class="kv-grid">
          ${detailKeyValue("Total Units", formatNumber(detail.units_summary.total_units))}
          ${detailKeyValue("Avg Carpet Area", `${formatNumber(detail.units_summary.average_unit_size_sqm)} sqm`)}
          ${detailKeyValue("Min Carpet Area", `${formatNumber(detail.units_summary.min_carpet_area_sqm)} sqm`)}
          ${detailKeyValue("Max Carpet Area", `${formatNumber(detail.units_summary.max_carpet_area_sqm)} sqm`)}
          ${detailKeyValue("Total Carpet Area", `${formatNumber(detail.units_summary.total_carpet_area_sqm)} sqm`)}
          ${detailKeyValue("Inventory Blocks", String(detail.financials.inventory_by_block.length))}
        </div>
      </article>

      <article class="panel-card">
        <h3>Location</h3>
        <div class="kv-grid">
          ${detailKeyValue("Address", detail.location.address)}
          ${detailKeyValue("Process Type", detail.location.process_type)}
          ${detailKeyValue("Coordinates", detail.location.coordinates.length ? `${detail.location.coordinates.length} points` : "NA")}
          ${detailKeyValue("Map", mapLink ? "Open externally" : "NA")}
        </div>
        ${mapLink ? `<p class="note" style="margin-top:12px;"><a href="${mapLink}" target="_blank" rel="noreferrer">Open first coordinate in Google Maps</a></p>` : ""}
      </article>

      <article class="panel-card full">
        <div class="toggle-row">
          <h3>Inventory</h3>
          ${canToggleInventory ? `<button id="inventoryToggle" class="ghost">${state.showAllInventory ? "Show first 30" : `Show all ${inventory.length}`}</button>` : ""}
        </div>
        <div style="margin-bottom:16px;">
          ${renderInventoryFocus(selectedInventory)}
        </div>
        ${inventory.length ? `
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Flat No</th>
                  <th>Block</th>
                  <th>Usage</th>
                  <th>Status</th>
                  <th>Carpet Area</th>
                  <th>Balcony Area</th>
                  <th>Consideration</th>
                  <th>Received</th>
                  <th>Agreement Date</th>
                  <th>Allottee</th>
                  <th>KYC Type</th>
                  <th>KYC ID</th>
                  <th>Mobile</th>
                  <th>Inspect</th>
                </tr>
              </thead>
              <tbody>${renderInventoryRows(inventory)}</tbody>
            </table>
          </div>
        ` : `<p class="note">Inventory is unavailable. This often means no public Form 3 submission exists yet.</p>`}
      </article>

      <article class="panel-card full">
        <h3>Quarter Filings</h3>
        ${quartersTable}
      </article>

      <article class="panel-card full">
        <h3>Selected Quarter Detail</h3>
        ${renderQuarterDetailPanel()}
      </article>

      <article class="panel-card full">
        <h3>Quarter-to-Quarter Progress</h3>
        ${quarterProgressTable}
      </article>

      <article class="panel-card full">
        <h3>Applications</h3>
        ${applicationsTable}
      </article>

      <article class="panel-card">
        <h3>Bank Accounts</h3>
        <div class="kv-grid">
          ${detailKeyValue("Collection Bank", detail.bank_accounts.collection_account?.bank_name)}
          ${detailKeyValue("Collection IFSC", detail.bank_accounts.collection_account?.ifsc_code)}
          ${detailKeyValue("Retention Bank", detail.bank_accounts.retention_account?.bank_name)}
          ${detailKeyValue("Retention IFSC", detail.bank_accounts.retention_account?.ifsc_code)}
          ${detailKeyValue("Collection Account", detail.bank_accounts.collection_account?.account_number)}
          ${detailKeyValue("Retention Account", detail.bank_accounts.retention_account?.account_number)}
        </div>
      </article>

      <article class="panel-card">
        <h3>Documents</h3>
        ${buildDocumentLinks(detail.documents || {})}
      </article>

      <article class="panel-card full">
        <h3>Annual Audits</h3>
        ${auditsTable}
      </article>
    </section>
  `;

  const inventoryToggle = document.getElementById("inventoryToggle");
  if (inventoryToggle) {
    inventoryToggle.addEventListener("click", () => {
      state.showAllInventory = !state.showAllInventory;
      renderDetail(detail);
    });
  }
  els.detailContent.querySelectorAll(".inventory-select").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedInventoryIndex = Number(button.dataset.inventoryIndex);
      renderDetail(detail);
    });
  });
  els.detailContent.querySelectorAll(".quarter-select").forEach((button) => {
    button.addEventListener("click", () => {
      loadQuarterDetail(state.selectedProjectId, Number(button.dataset.quarterId));
    });
  });
}

async function selectProject(projectId) {
  state.selectedProjectId = projectId;
  state.showAllInventory = false;
  renderProjectList();
  els.detailState.classList.add("hidden");
  els.detailContent.classList.remove("hidden");
  const template = document.getElementById("loadingTemplate");
  els.detailContent.innerHTML = template.innerHTML;

  try {
    const response = await fetch(`/api/projects/${projectId}`);
    if (!response.ok) {
      throw new Error(`Request failed with ${response.status}`);
    }
    state.detail = await response.json();
    state.selectedInventoryIndex = 0;
    state.selectedQuarterId = pickDefaultQuarter(state.detail);
    state.quarterDetail = null;
    state.quarterDetailLoading = false;
    renderDetail(state.detail);
    if (state.selectedQuarterId) {
      loadQuarterDetail(projectId, state.selectedQuarterId);
    }
  } catch (error) {
    els.detailContent.innerHTML = `
      <div class="empty-state">
        <h2>Detail load failed</h2>
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

async function bootstrap() {
  els.projectList.innerHTML = document.getElementById("loadingTemplate").innerHTML;
  try {
    const response = await fetch("/api/projects");
    if (!response.ok) {
      throw new Error(`Listing request failed with ${response.status}`);
    }
    state.listing = await response.json();
    state.filteredProjects = [...state.listing.projects];
    els.totalProjects.textContent = formatNumber(state.listing.total_projects);
    els.filteredProjects.textContent = formatNumber(state.listing.filtered_projects);
    renderSummaryStats(state.listing.summary_stats);
    buildOptions(els.districtFilter, new Set(state.listing.projects.map((item) => item.district_name || item.district_type)), "All districts");
    buildOptions(els.typeFilter, new Set(state.listing.projects.map((item) => item.project_type)), "All project types");
    buildOptions(els.statusFilter, new Set(state.listing.projects.map((item) => item.project_status)), "All statuses");
    renderProjectList();
    els.listCountBadge.textContent = `${state.filteredProjects.length} results`;
    await loadStorageSummary();
  } catch (error) {
    els.projectList.innerHTML = `
      <div class="empty-state">
        <h2>Listing load failed</h2>
        <p>${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

[els.searchInput, els.districtFilter, els.typeFilter, els.statusFilter].forEach((element) => {
  element.addEventListener("input", applyFilters);
  element.addEventListener("change", applyFilters);
});

els.refreshStorage.addEventListener("click", loadStorageSummary);
els.startSync.addEventListener("click", startLocalSync);
els.askRag.addEventListener("click", askLocalKnowledge);
els.ragQuery.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    askLocalKnowledge();
  }
});

bootstrap();
