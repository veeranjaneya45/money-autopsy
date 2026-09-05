"use strict";

/*
============================================================
MONEY AUTOPSY — INVESTIGATION
============================================================
*/

const $ = (id) =>
    document.getElementById(id);


/* =========================================================
   QUERY PARAMETER
   ========================================================= */

function getCaseId() {

    const params =
        new URLSearchParams(
            window.location.search
        );


    return (
        params.get("case") ||
        params.get("case_id") ||
        ""
    );

}


/* =========================================================
   ESCAPE
   ========================================================= */

function escapeHtml(value) {

    return String(value ?? "")

        .replaceAll("&", "&amp;")

        .replaceAll("<", "&lt;")

        .replaceAll(">", "&gt;")

        .replaceAll('"', "&quot;")

        .replaceAll("'", "&#039;");

}


/* =========================================================
   MONEY
   ========================================================= */

function money(value) {

    if (
        value === null ||
        value === undefined
    ) {

        return "—";

    }


    const n =
        Number(value);


    if (Number.isNaN(n)) {

        return escapeHtml(value);

    }


    return `₹${n.toLocaleString(
        "en-IN",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    )}`;

}


/* =========================================================
   RENDER
   ========================================================= */

function renderInvestigation(
    data
) {

    const investigation =
        data.investigation ||
        data;


    const truth =
        investigation.truth ||
        investigation.truth_result ||
        data.truth ||
        {};


    const proof =
        investigation.proof_chain ||
        data.proof_chain ||
        [];


    const caseId =
        investigation.case_id ||
        truth.case_id ||
        data.case_id ||
        getCaseId();


    const classification =
        truth.classification ||
        investigation.classification ||
        "UNKNOWN";


    const status =
        truth.status ||
        investigation.status ||
        "UNKNOWN";


    $("caseId").textContent =
        caseId;


    $("classification").textContent =
        classification;


    $("caseStatus").textContent =
        status;


    $("recoveryAmount").textContent =
        money(
            truth.recovery_amount ??
            investigation.recovery_amount
        );


    $("expectedAmount").textContent =
        money(
            truth.expected_amount ??
            investigation.expected_amount
        );


    $("observedAmount").textContent =
        money(
            truth.observed_amount ??
            investigation.observed_amount
        );


    renderRecords(
        investigation
    );


    renderProof(
        proof
    );

}


/* =========================================================
   RECORDS
   ========================================================= */

function renderRecords(
    investigation
) {

    const container =
        $("recordsContainer");


    const records =
        investigation.records ||
        [];


    if (!records.length) {

        container.innerHTML = `

            <div class="empty-panel">

                <div class="empty-icon">
                    ⓘ
                </div>

                <h3>
                    No evidence records returned
                </h3>

                <p>
                    The deterministic investigation did not
                    return source records for this case.
                </p>

            </div>

        `;

        return;
    }


    container.innerHTML =
        records.map(
            (record) => {

                const type =
                    record.evidence_type ||
                    record.type ||
                    "RECORD";


                const id =
                    record.payment_id ||
                    record.order_id ||
                    record.refund_id ||
                    record.fee_id ||
                    record.settlement_id ||
                    record.bank_transaction_id ||
                    record.ledger_entry_id ||
                    record.record_id ||
                    record.id ||
                    "—";


                return `

                    <div class="evidence-row">

                        <div class="evidence-type">
                            ${escapeHtml(type)}
                        </div>

                        <div class="evidence-id">
                            ${escapeHtml(id)}
                        </div>

                    </div>

                `;

            }
        )
        .join("");

}


/* =========================================================
   PROOF CHAIN
   ========================================================= */

function renderProof(
    proof
) {

    const container =
        $("proofContainer");


    if (!Array.isArray(proof)) {

        container.innerHTML =
            "<p>No proof chain available.</p>";

        return;
    }


    if (!proof.length) {

        container.innerHTML = `

            <div class="empty-panel">

                <div class="empty-icon">
                    ⓘ
                </div>

                <h3>
                    No proof steps returned
                </h3>

            </div>

        `;

        return;
    }


    container.innerHTML =
        proof.map(
            (step, index) => {

                const title =
                    step.title ||
                    step.step ||
                    step.name ||
                    `Evidence step ${index + 1}`;


                const description =
                    step.description ||
                    step.explanation ||
                    step.detail ||
                    "";


                return `

                    <div class="proof-step">

                        <div class="proof-index">
                            ${String(
                                index + 1
                            ).padStart(2, "0")}
                        </div>

                        <div>

                            <div class="proof-title">
                                ${escapeHtml(title)}
                            </div>

                            <div class="proof-description">
                                ${escapeHtml(description)}
                            </div>

                        </div>

                    </div>

                `;

            }
        )
        .join("");

}


/* =========================================================
   NO CASE
   ========================================================= */

function renderNoCase() {

    $("caseId").textContent =
        "NO CASE SELECTED";


    $("classification").textContent =
        "—";


    $("caseStatus").textContent =
        "—";


    $("recoveryAmount").textContent =
        "—";


    $("expectedAmount").textContent =
        "—";


    $("observedAmount").textContent =
        "—";


    $("recordsContainer").innerHTML = `

        <div class="empty-panel">

            <div class="empty-icon">
                ⌕
            </div>

            <h3>
                Select an investigation case
            </h3>

            <p>
                Open an investigation from the
                Command Center to inspect its evidence,
                proof chain and financial impact.
            </p>

            <a
                class="primary-button inline-button"
                href="dashboard.html#cases"
            >
                Open Investigation Queue
            </a>

        </div>

    `;


    $("proofContainer").innerHTML = "";

}


/* =========================================================
   LOAD
   ========================================================= */

async function loadInvestigation() {

    const caseId =
        getCaseId();


    if (!caseId) {

        renderNoCase();

        return;

    }


    $("loadingPanel")
        .classList
        .remove("hidden");


    $("errorPanel")
        .classList
        .add("hidden");


    try {

        const data =
            await getInvestigation(
                caseId
            );


        renderInvestigation(
            data
        );


    } catch (error) {

        console.error(
            "Investigation error:",
            error
        );


        $("errorPanel")
            .classList
            .remove("hidden");


        $("errorPanel").textContent =
            `Unable to load investigation: ${error.message}`;

    } finally {

        $("loadingPanel")
            .classList
            .add("hidden");

    }

}


/* =========================================================
   START
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    loadInvestigation
);