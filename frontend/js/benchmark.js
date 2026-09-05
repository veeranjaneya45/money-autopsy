// ============================================================
// MONEY AUTOPSY
// BENCHMARK FRONTEND
// ============================================================

"use strict";


const BENCHMARK_API =
    "http://127.0.0.1:8000/api/benchmark";


const elements = {

    loading:
        document.getElementById(
            "benchmarkLoading"
        ),

    error:
        document.getElementById(
            "benchmarkError"
        ),

    errorText:
        document.getElementById(
            "benchmarkErrorText"
        ),

    runButton:
        document.getElementById(
            "runBenchmarkBtn"
        ),

    totalCases:
        document.getElementById(
            "totalCases"
        ),

    overallAccuracy:
        document.getElementById(
            "overallAccuracy"
        ),

    failedCases:
        document.getElementById(
            "failedCases"
        ),

    classificationAccuracy:
        document.getElementById(
            "classificationAccuracy"
        ),

    classificationCount:
        document.getElementById(
            "classificationCount"
        ),

    statusAccuracy:
        document.getElementById(
            "statusAccuracy"
        ),

    statusCount:
        document.getElementById(
            "statusCount"
        ),

    recoveryAccuracy:
        document.getElementById(
            "recoveryAccuracy"
        ),

    recoveryCount:
        document.getElementById(
            "recoveryCount"
        ),

    resolutionAccuracy:
        document.getElementById(
            "resolutionAccuracy"
        ),

    resolutionCount:
        document.getElementById(
            "resolutionCount"
        ),

    unresolvedAccuracy:
        document.getElementById(
            "unresolvedAccuracy"
        ),

    unresolvedCount:
        document.getElementById(
            "unresolvedCount"
        ),

    proofAccuracy:
        document.getElementById(
            "proofAccuracy"
        ),

    proofCount:
        document.getElementById(
            "proofCount"
        ),

    elapsedTime:
        document.getElementById(
            "elapsedTime"
        ),

    throughput:
        document.getElementById(
            "throughput"
        ),

    benchmarkVersion:
        document.getElementById(
            "benchmarkVersion"
        ),

    failurePanel:
        document.getElementById(
            "failurePanel"
        ),

    aiBenchmarkStatus:
        document.getElementById(
            "aiBenchmarkStatus"
        )
};


// ============================================================
// FORMAT
// ============================================================

function percent(value) {

    return `${Number(value).toFixed(2)}%`;

}


function number(value, decimals = 2) {

    return Number(value).toFixed(decimals);

}


function countText(correct, total) {

    return `${correct} / ${total} cases passed`;

}


// ============================================================
// LOADING
// ============================================================

function setLoading(isLoading) {

    if (isLoading) {

        elements.loading.classList.remove(
            "hidden"
        );

        elements.runButton.disabled = true;

        elements.runButton.textContent =
            "Running...";

    } else {

        elements.loading.classList.add(
            "hidden"
        );

        elements.runButton.disabled = false;

        elements.runButton.textContent =
            "Run Benchmark";
    }

}


// ============================================================
// ERROR
// ============================================================

function clearError() {

    elements.error.classList.add(
        "hidden"
    );

}


function showError(message) {

    elements.error.classList.remove(
        "hidden"
    );

    elements.errorText.textContent =
        message;

}


// ============================================================
// VALIDATE RESPONSE
// ============================================================

function validateBenchmarkResponse(data) {

    const required =
        [
            "benchmark_version",
            "pipeline",
            "total_cases",
            "classification",
            "status",
            "recovery",
            "resolution",
            "unresolved_preservation",
            "proof_chain",
            "performance",
            "failed_cases",
            "failed_count"
        ];


    for (const key of required) {

        if (
            data[key] === undefined ||
            data[key] === null
        ) {

            throw new Error(
                `Benchmark API response is missing: ${key}`
            );

        }

    }


    if (
        data.classification.accuracy === undefined ||
        data.status.accuracy === undefined ||
        data.recovery.accuracy === undefined ||
        data.resolution.accuracy === undefined ||
        data.unresolved_preservation.accuracy === undefined ||
        data.proof_chain.integrity === undefined
    ) {

        throw new Error(
            "Benchmark API returned an invalid metric structure."
        );

    }


    return true;

}


// ============================================================
// RENDER
// ============================================================

function renderBenchmark(data) {

    validateBenchmarkResponse(data);


    // --------------------------------------------------------
    // HERO
    // --------------------------------------------------------

    elements.totalCases.textContent =
        data.total_cases;


    const metrics = [

        Number(
            data.classification.accuracy
        ),

        Number(
            data.status.accuracy
        ),

        Number(
            data.recovery.accuracy
        ),

        Number(
            data.resolution.accuracy
        ),

        Number(
            data.unresolved_preservation.accuracy
        ),

        Number(
            data.proof_chain.integrity
        )

    ];


    const overall =
        metrics.reduce(
            (sum, value) =>
                sum + value,
            0
        ) / metrics.length;


    elements.overallAccuracy.textContent =
        percent(overall);


    elements.failedCases.textContent =
        data.failed_count;


    // --------------------------------------------------------
    // CLASSIFICATION
    // --------------------------------------------------------

    elements.classificationAccuracy.textContent =
        percent(
            data.classification.accuracy
        );

    elements.classificationCount.textContent =
        countText(
            data.classification.correct,
            data.classification.total
        );


    // --------------------------------------------------------
    // STATUS
    // --------------------------------------------------------

    elements.statusAccuracy.textContent =
        percent(
            data.status.accuracy
        );

    elements.statusCount.textContent =
        countText(
            data.status.correct,
            data.status.total
        );


    // --------------------------------------------------------
    // RECOVERY
    // --------------------------------------------------------

    elements.recoveryAccuracy.textContent =
        percent(
            data.recovery.accuracy
        );

    elements.recoveryCount.textContent =
        countText(
            data.recovery.correct,
            data.recovery.total
        );


    // --------------------------------------------------------
    // RESOLUTION
    // --------------------------------------------------------

    elements.resolutionAccuracy.textContent =
        percent(
            data.resolution.accuracy
        );

    elements.resolutionCount.textContent =
        countText(
            data.resolution.correct,
            data.resolution.total
        );


    // --------------------------------------------------------
    // UNRESOLVED
    // --------------------------------------------------------

    elements.unresolvedAccuracy.textContent =
        percent(
            data.unresolved_preservation.accuracy
        );

    elements.unresolvedCount.textContent =
        countText(
            data.unresolved_preservation.correct,
            data.unresolved_preservation.total
        );


    // --------------------------------------------------------
    // PROOF CHAIN
    // --------------------------------------------------------

    elements.proofAccuracy.textContent =
        percent(
            data.proof_chain.integrity
        );

    elements.proofCount.textContent =
        countText(
            data.proof_chain.correct,
            data.proof_chain.total
        );


    // --------------------------------------------------------
    // PERFORMANCE
    // --------------------------------------------------------

    elements.elapsedTime.textContent =
        number(
            data.performance.elapsed_seconds
        );


    elements.throughput.textContent =
        number(
            data.performance
                .throughput_cases_per_second
        );


    elements.benchmarkVersion.textContent =
        data.benchmark_version;


    // --------------------------------------------------------
    // FAILURES
    // --------------------------------------------------------

    renderFailures(
        data.failed_cases
    );


    // --------------------------------------------------------
    // AI
    // --------------------------------------------------------

    if (
        data.ai_benchmark &&
        data.ai_benchmark.executed === false
    ) {

        elements.aiBenchmarkStatus.textContent =
            "NOT EXECUTED";

    } else {

        elements.aiBenchmarkStatus.textContent =
            "EXECUTED";

    }

}


// ============================================================
// FAILED CASES
// ============================================================

function renderFailures(failures) {

    if (
        !Array.isArray(failures) ||
        failures.length === 0
    ) {

        elements.failurePanel.className =
            "empty-panel success-panel";


        elements.failurePanel.innerHTML = `

            <div class="empty-icon">
                ✓
            </div>

            <h3>
                No failed cases
            </h3>

            <p>
                All benchmark cases passed the
                deterministic pipeline.
            </p>

        `;

        return;

    }


    elements.failurePanel.className =
        "failure-list";


    elements.failurePanel.innerHTML = "";


    failures.forEach(
        (failure) => {

            const item =
                document.createElement(
                    "div"
                );


            item.className =
                "failure-item";


            const caseId =
                failure.case_id ||
                failure.case ||
                "UNKNOWN";


            item.innerHTML = `

                <div class="failure-case">
                    ${escapeHtml(caseId)}
                </div>

                <div class="failure-reason">
                    ${escapeHtml(
                        JSON.stringify(
                            failure
                        )
                    )}
                </div>

            `;


            elements.failurePanel
                .appendChild(item);

        }
    );

}


// ============================================================
// ESCAPE
// ============================================================

function escapeHtml(value) {

    return String(value)

        .replaceAll(
            "&",
            "&amp;"
        )

        .replaceAll(
            "<",
            "&lt;"
        )

        .replaceAll(
            ">",
            "&gt;"
        )

        .replaceAll(
            '"',
            "&quot;"
        )

        .replaceAll(
            "'",
            "&#039;"
        );

}


// ============================================================
// FETCH BENCHMARK
// ============================================================

async function fetchBenchmark() {

    const response =
        await fetch(
            `${BENCHMARK_API}?_=${Date.now()}`,
            {
                method: "GET",

                cache: "no-store",

                headers: {
                    "Accept":
                        "application/json"
                }
            }
        );


    if (!response.ok) {

        throw new Error(
            `Benchmark API returned HTTP ${response.status}`
        );

    }


    const data =
        await response.json();


    console.log(
        "MONEY AUTOPSY BENCHMARK API:",
        data
    );


    return data;

}


// ============================================================
// RUN
// ============================================================

async function runBenchmark() {

    clearError();

    setLoading(true);


    try {

        const data =
            await fetchBenchmark();


        renderBenchmark(data);


        console.log(
            "Benchmark rendered successfully."
        );


    } catch (error) {

        console.error(
            "Benchmark failed:",
            error
        );


        showError(
            error.message ||
            "Unable to load benchmark."
        );


    } finally {

        setLoading(false);

    }

}


// ============================================================
// EVENTS
// ============================================================

elements.runButton.addEventListener(
    "click",
    runBenchmark
);


// ============================================================
// INITIAL LOAD
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    () => {

        runBenchmark();

    }
);