"use strict";

const $ = (id) => document.getElementById(id);

function getCaseId() {
    return new URLSearchParams(window.location.search).get("case_id") || "";
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function money(value) {
    if (value === null || value === undefined || value === "") return "—";

    const n = Number(value);

    if (Number.isNaN(n)) return escapeHtml(value);

    return `₹${n.toLocaleString("en-IN", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    })}`;
}

function renderRecords(records) {
    const container = $("recordsContainer");

    if (!records || records.length === 0) {
        container.innerHTML = `<div class="empty-box">No evidence records returned.</div>`;
        return;
    }

    container.innerHTML = records.map(record => `
        <div class="record">
            <div class="record-type">
                ${escapeHtml(String(record.evidence_type || "RECORD").replaceAll("_", " "))}
            </div>
            <div class="record-id">
                ${escapeHtml(record.record_id || "—")}
            </div>
        </div>
    `).join("");
}

function renderProof(proof) {
    const container = $("proofContainer");

    if (!proof || proof.length === 0) {
        container.innerHTML = `<div class="empty-box">No proof-chain steps returned.</div>`;
        return;
    }

    container.innerHTML = proof.map(step => `
        <div class="proof-step">
            <div class="proof-number">
                ${String(step.step || "").padStart(2, "0")}
            </div>

            <div>
                <div class="proof-title">
                    ${escapeHtml(step.title || step.type || "Evidence step")}
                </div>

                <div class="proof-description">
                    ${escapeHtml(step.description || "")}
                </div>

                ${
                    step.calculation
                    ? `<div class="proof-description" style="margin-top:8px;font-family:Consolas,monospace;color:#c8d7e8;">
                        ${escapeHtml(step.calculation)}
                       </div>`
                    : ""
                }

                ${
                    Array.isArray(step.evidence)
                    ? `<div class="proof-description" style="margin-top:8px;">
                        Evidence: ${step.evidence.map(escapeHtml).join(" · ")}
                       </div>`
                    : ""
                }
            </div>
        </div>
    `).join("");
}

async function loadInvestigation() {

    const caseId = getCaseId();

    if (!caseId) {
        $("loadingPanel").classList.add("hidden");
        $("emptyPanel").classList.remove("hidden");
        return;
    }

    try {

        const data = await window.getInvestigation(caseId);

        console.log("Investigation API response:", data);

        const c = data.case;
        const finding = data.finding;
        const trace = data.financial_trace;

        $("caseId").textContent = c.case_id;

        $("caseSubtitle").textContent =
            `${c.exception_type.replaceAll("_", " ")} investigation — trace the money, prove the outcome.`;

        $("classification").textContent =
            c.exception_type.replaceAll("_", " ");

        $("caseStatus").textContent =
            c.status.replaceAll("_", " ");

        $("classification").className =
            "status-pill " +
            (c.status === "UNRESOLVED" ? "unresolved" :
             c.status === "NORMAL" ? "normal" : "exception");

        $("expectedAmount").textContent =
            money(c.expected_amount);

        $("observedAmount").textContent =
            money(c.observed_amount);

        $("recoveryAmount").textContent =
            money(c.potential_recovery_amount);

        $("whyContainer").innerHTML =
            `<strong>${escapeHtml(c.exception_type.replaceAll("_", " "))}</strong><br><br>
             ${escapeHtml((finding.reasons || []).join(" "))}<br><br>
             <span style="color:#71859d;">
             Payment ₹${escapeHtml(trace.payment_amount)}
             − Refunds ₹${escapeHtml(trace.refund_total)}
             − Fees ₹${escapeHtml(trace.fee_total)}
             = Expected settlement ₹${escapeHtml(trace.expected_settlement)}
             </span>`;

        $("decisionValue").textContent =
            String(c.resolution || "REVIEW").replaceAll("_", " ");

        $("decisionReason").textContent =
            c.resolution === "REVIEW"
                ? "The identified exception should be reviewed by an authorized human operator."
                : "No consequential action is required.";

        renderRecords(data.evidence);
        renderProof(data.proof_chain);

        $("loadingPanel").classList.add("hidden");
        $("errorPanel").classList.add("hidden");
        $("emptyPanel").classList.add("hidden");
        $("investigationContent").classList.remove("hidden");

    } catch (error) {

        console.error(error);

        $("loadingPanel").classList.add("hidden");
        $("errorPanel").textContent =
            `Unable to load investigation: ${error.message}`;
        $("errorPanel").classList.remove("hidden");
    }
}

document.addEventListener("DOMContentLoaded", loadInvestigation);