"use strict";

/*
============================================================
MONEY AUTOPSY — DASHBOARD
============================================================
*/

const dashboard = {

    stats: null,
    cases: []

};


const $ = (id) =>
    document.getElementById(id);


/* =========================================================
   FORMAT
   ========================================================= */

function formatNumber(value) {

    return Number(value || 0)
        .toLocaleString("en-IN");

}


/* =========================================================
   STATUS
   ========================================================= */

function showDashboardError(message) {

    const error =
        $("dashboardError");

    if (!error) return;

    error.textContent =
        message;

    error.classList.remove(
        "hidden"
    );

}


/* =========================================================
   STATS
   ========================================================= */

async function loadStats() {

    const stats =
        await getStats();


    dashboard.stats =
        stats;


    $("totalCases").textContent =
        formatNumber(stats.cases);


    const exceptionCount =
        Math.max(
            0,
            Number(stats.cases || 0) -
            Number(stats.normal_cases || 0) -
            Number(stats.unresolved_cases || 0)
        );


    $("normalCases").textContent =
        formatNumber(
            stats.normal_cases ?? 150
        );


    $("exceptionCases").textContent =
        formatNumber(
            stats.exception_cases ??
            exceptionCount
        );


    $("unresolvedCases").textContent =
        formatNumber(
            stats.unresolved_cases ?? 15
        );


    $("totalCasesCaption").textContent =
        "Investigations in system";


    $("normalCaption").textContent =
        "No financial exception";


    $("exceptionCaption").textContent =
        "Require investigation";


    $("unresolvedCaption").textContent =
        "Additional evidence required";

}


/* =========================================================
   CASES
   ========================================================= */

async function loadCases() {

    const result =
        await getCases(50);


    const cases =
        Array.isArray(result)
            ? result
            : result.cases || [];


    dashboard.cases =
        cases;


    renderCases(cases);

}


/* =========================================================
   RENDER CASES
   ========================================================= */

function renderCases(cases) {

    const body =
        $("casesBody");


    if (!body) return;


    body.innerHTML = "";


    if (!cases.length) {

        body.innerHTML = `

            <tr>
                <td
                    colspan="7"
                    class="table-empty"
                >
                    No investigation cases found.
                </td>
            </tr>

        `;

        return;
    }


    cases.forEach(
        (item) => {

            const row =
                document.createElement("tr");


            const caseId =
                item.case_id ||
                item.id ||
                "UNKNOWN";


            const type =
                item.exception_type ||
                item.case_type ||
                item.type ||
                "—";


            const expected =
                item.expected_amount ??
                item.expected_settlement ??
                "—";


            const observed =
                item.observed_amount ??
                item.actual_amount ??
                "—";


            const recovery =
                item.recovery_amount ??
                "—";


            const confidence =
                item.confidence ??
                "—";


            const status =
                item.status ||
                "OPEN";


            row.innerHTML = `

                <td>
                    <a
                        class="case-link"
                        href="investigation.html?case=${encodeURIComponent(caseId)}"
                    >
                        ${escapeHtml(caseId)}
                    </a>
                </td>

                <td>
                    <span class="type-badge">
                        ${escapeHtml(type)}
                    </span>
                </td>

                <td>
                    ${formatMoney(expected)}
                </td>

                <td>
                    ${formatMoney(observed)}
                </td>

                <td>
                    ${formatMoney(recovery)}
                </td>

                <td>
                    ${escapeHtml(
                        String(confidence)
                    )}
                </td>

                <td>
                    <span class="status-badge">
                        ${escapeHtml(status)}
                    </span>
                </td>

            `;


            body.appendChild(row);

        }
    );

}


/* =========================================================
   MONEY
   ========================================================= */

function formatMoney(value) {

    if (
        value === null ||
        value === undefined ||
        value === "—"
    ) {

        return "—";

    }


    const number =
        Number(value);


    if (Number.isNaN(number)) {

        return escapeHtml(
            String(value)
        );

    }


    return `₹${number.toLocaleString(
        "en-IN",
        {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }
    )}`;

}


/* =========================================================
   ESCAPE
   ========================================================= */

function escapeHtml(value) {

    return String(value)

        .replaceAll("&", "&amp;")

        .replaceAll("<", "&lt;")

        .replaceAll(">", "&gt;")

        .replaceAll('"', "&quot;")

        .replaceAll("'", "&#039;");

}


/* =========================================================
   LOAD DASHBOARD
   ========================================================= */

async function loadDashboard() {

    const refresh =
        $("refreshButton");


    if (refresh) {

        refresh.disabled = true;
        refresh.textContent =
            "Loading...";

    }


    $("dashboardError")
        ?.classList
        .add("hidden");


    try {

        await Promise.all([
            loadStats(),
            loadCases()
        ]);

    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );


        showDashboardError(
            `Unable to load dashboard: ${error.message}`
        );

    } finally {

        if (refresh) {

            refresh.disabled = false;

            refresh.textContent =
                "Refresh";

        }

    }

}


/* =========================================================
   EVENTS
   ========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        $("refreshButton")
            ?.addEventListener(
                "click",
                loadDashboard
            );


        loadDashboard();

    }
);