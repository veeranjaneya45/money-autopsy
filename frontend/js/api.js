"use strict";

/*
============================================================
MONEY AUTOPSY — API CLIENT
============================================================
Central API layer used by Dashboard + Investigation.

Backend:
http://127.0.0.1:8000
============================================================
*/

const API_BASE = "http://127.0.0.1:8000/api";


async function apiRequest(
    path,
    options = {}
) {

    const response = await fetch(
        `${API_BASE}${path}`,
        {
            cache: "no-store",

            headers: {
                "Accept": "application/json",
                ...(options.headers || {})
            },

            ...options
        }
    );


    if (!response.ok) {

        let message =
            `API request failed: HTTP ${response.status}`;

        try {

            const error =
                await response.json();

            if (error.detail) {
                message = error.detail;
            }

        } catch (_) {}

        throw new Error(message);
    }


    return response.json();
}


/* =========================================================
   HEALTH
   ========================================================= */

async function getHealth() {

    return apiRequest("/../health");

}


/* =========================================================
   STATS
   ========================================================= */

async function getStats() {

    return apiRequest("/stats");

}


/* =========================================================
   CASES
   ========================================================= */

async function getCases(
    limit = 50
) {

    return apiRequest(
        `/cases?limit=${encodeURIComponent(limit)}`
    );

}


/* =========================================================
   SINGLE CASE
   ========================================================= */

async function getCase(
    caseId
) {

    return apiRequest(
        `/cases/${encodeURIComponent(caseId)}`
    );

}


/* =========================================================
   INVESTIGATION
   ========================================================= */

async function getInvestigation(
    caseId
) {

    return apiRequest(
        `/cases/${encodeURIComponent(caseId)}/investigation`
    );

}


/* =========================================================
   REPORT
   ========================================================= */

async function getReport(
    caseId
) {

    return apiRequest(
        `/cases/${encodeURIComponent(caseId)}/report`
    );

}


/* =========================================================
   REVIEWS
   ========================================================= */

async function getReviews(
    caseId
) {

    return apiRequest(
        `/cases/${encodeURIComponent(caseId)}/reviews`
    );

}


/* =========================================================
   HUMAN REVIEW
   ========================================================= */

async function submitReview(
    caseId,
    payload
) {

    return apiRequest(
        `/cases/${encodeURIComponent(caseId)}/review`,
        {
            method: "POST",

            headers: {
                "Content-Type":
                    "application/json"
            },

            body:
                JSON.stringify(payload)
        }
    );

}


/* =========================================================
   REPLAY
   ========================================================= */

async function getReplay(
    replayId
) {

    return apiRequest(
        `/replays/${encodeURIComponent(replayId)}`
    );

}


/* =========================================================
   BENCHMARK
   ========================================================= */

async function getBenchmark() {

    return apiRequest(
        `/benchmark?_=${Date.now()}`
    );

}


/* =========================================================
   GLOBAL COMPATIBILITY
============================================================
dashboard.js previously expected getStats().
Make everything explicitly available globally.
============================================================
*/

window.MoneyAutopsyAPI = {

    apiRequest,
    getHealth,
    getStats,
    getCases,
    getCase,
    getInvestigation,
    getReport,
    getReviews,
    submitReview,
    getReplay,
    getBenchmark

};


window.getStats = getStats;
window.getCases = getCases;
window.getCase = getCase;
window.getInvestigation = getInvestigation;
window.getReport = getReport;
window.getReviews = getReviews;
window.submitReview = submitReview;
window.getReplay = getReplay;
window.getBenchmark = getBenchmark;