const API_BASE = "http://127.0.0.1:8000";
async function request(path, options={}){const response=await fetch(`${API_BASE}${path}`,{headers:{"Content-Type":"application/json",...(options.headers||{})},...options});if(!response.ok){let detail=`HTTP ${response.status}`;try{const body=await response.json();detail=body.detail||body.message||detail}catch(_){}throw new Error(detail)}return response.json()}
async function getStats(){return request("/api/stats")}
async function getCases(limit=50){return request(`/api/cases?limit=${encodeURIComponent(limit)}`)}
async function getCase(caseId){return request(`/api/cases/${encodeURIComponent(caseId)}`)}
async function getInvestigation(caseId){return request(`/api/cases/${encodeURIComponent(caseId)}/investigation`)}
async function getReport(caseId){return request(`/api/cases/${encodeURIComponent(caseId)}/report`)}
async function getReviews(caseId){return request(`/api/cases/${encodeURIComponent(caseId)}/reviews`)}
async function getReplay(replayId){return request(`/api/replays/${encodeURIComponent(replayId)}`)}
async function getBenchmark(force=false){return request(`/api/benchmark${force?"?force=true":""}`)}
async function submitReview(caseId,payload){return request(`/api/cases/${encodeURIComponent(caseId)}/review`,{method:"POST",body:JSON.stringify(payload)})}
window.MoneyAutopsyAPI={API_BASE,request,getStats,getCases,getCase,getInvestigation,getReport,getReviews,getReplay,getBenchmark,submitReview};window.getStats=getStats;window.getCases=getCases;window.getCase=getCase;window.getInvestigation=getInvestigation;window.getReport=getReport;window.getReviews=getReviews;window.getReplay=getReplay;window.getBenchmark=getBenchmark;window.submitReview=submitReview;
