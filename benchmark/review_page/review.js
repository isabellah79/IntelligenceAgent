(function () {
  'use strict';
  const C = globalThis.OncologyReviewCore;
  const DATA = JSON.parse(document.getElementById('review-data').textContent);
  const embedded = JSON.parse(document.getElementById('review-state').textContent);
  const now = () => new Date().toISOString();
  const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; };
  const uuid = () => globalThis.crypto?.randomUUID?.() || `review-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const percent = value => typeof value === 'number' ? (value*100).toFixed(1) : 'Unavailable';
  const labels = {evidence_strength:'Evidence strength',population_applicability:'Population applicability',selection_justification:'Selection justification',tradeoffs:'Tradeoffs'};
  const purposes = {scope:'Parent population',efficacy:'Population selection',evidence_alignment:'Source alignment',safety:'Safety screening',design:'Trial design',generalizability:'Generalizability'};
  const key = `oncology-review:${DATA.dataset_id}:${embedded?.review_id || 'draft'}`;
  let state, storageAvailable = true, saveTimer, toastTimer;
  try {
    const local = localStorage.getItem(key);
    const cached = local ? C.restore(JSON.parse(local), DATA) : null;
    const saved = embedded ? C.restore(embedded, DATA) : null;
    state = cached && saved ? (Date.parse(cached.updated_at) > Date.parse(saved.updated_at) ? cached : saved)
      : cached || saved || C.fresh(DATA, uuid(), now());
  } catch (_) {
    storageAvailable = false;
    try { state = embedded ? C.restore(embedded, DATA) : C.fresh(DATA, uuid(), now()); }
    catch (_) { state = C.fresh(DATA, uuid(), now()); }
  }
  if (!state.reviewer.review_date) state.reviewer.review_date = today();
  const app = document.getElementById('app');
  function refs(ids, scientific) {
    return `<span class="citations">${[...new Set(ids || [])].map(id => {
      const s = DATA.sources[id];
      if (!s) return esc(id);
      return `<a class="citation" href="${esc(scientific ? s.scientific_url : s.url)}" target="_blank" rel="noopener noreferrer" title="${esc(s.title)}">${esc(id)}</a>`;
    }).join('')}</span>`;
  }
  function rows(items, criteria) {
    return `<ul class="criteria">${items.map(row => `<li>${criteria ? `<span class="purpose">${esc(purposes[row.purpose] || 'Proposed criterion')}</span>` : ''}${esc(row.text)}${row.reason ? `<p class="criterion-reason">${esc(row.reason)}</p>` : ''}${refs(row.source_ids)}</li>`).join('')}</ul>`;
  }
  function points(items) {
    return items.map(row => `<p class="point">${esc(row.text)}<br>${refs(row.source_ids)}</p>`).join('');
  }
  function feedback(p, field, title, placeholder) {
    const value = state.populations[p.option_id][field];
    return `<label class="feedback-label" for="${p.option_id}-${field}">${title}</label><textarea class="feedback editable" id="${p.option_id}-${field}" data-pid="${p.option_id}" data-field="${field}" maxlength="20000" placeholder="${esc(placeholder)}">${esc(value)}</textarea><div class="print-value" id="print-${p.option_id}-${field}">${esc(value)}</div>`;
  }
  function rating(p, d) {
    const review = state.populations[p.option_id], value = review.scientific_grades[d], status = review.statuses[d];
    const anchor = status === 'unable' ? 'Unable to assess — explain the missing evidence below.' : Number.isInteger(value) ? DATA.anchors[d][value] : 'Choose 0–4. Open the rubric for the full grade definitions.';
    return `<fieldset><legend>${labels[d]} <span class="weight">${Math.round(DATA.config.dimension_weights[d]*100)}%</span></legend><div class="ratings">${[0,1,2,3,4].map(n => `<label class="rating"><input type="radio" name="${p.option_id}-${d}" value="${n}" data-pid="${p.option_id}" data-dimension="${d}" aria-label="${esc(labels[d])}: ${n} — ${esc(DATA.anchors[d][n])}" ${status==='scored' && value===n ? 'checked' : ''}><span>${n}</span></label>`).join('')}<label class="rating unable"><input type="radio" name="${p.option_id}-${d}" value="unable" data-pid="${p.option_id}" data-dimension="${d}" aria-label="${esc(labels[d])}: unable to assess" ${status==='unable' ? 'checked' : ''}><span>Unable to assess</span></label></div><p class="anchor-description" id="anchor-${p.option_id}-${d}">${esc(anchor)}</p></fieldset>`;
  }
  function aiPanel(p) {
    const ai=p.ai, f=p.forecast;
    return `<div class="ai-panel" id="ai-${p.option_id}" hidden><span class="eyebrow">Prototype assessment · uncalibrated</span><p class="small muted">${esc(ai.model || ai.method)}. These are scientific-defense grades, not treatment-benefit probabilities.</p><div class="ai-metrics"><div><span class="ai-metric-label">Final defense /100</span><span class="ai-metric-number">${percent(ai.defense_score)}</span></div><div><span class="ai-metric-label">Scientific /100</span><span class="ai-metric-number">${percent(ai.scientific_score)}</span></div><div><span class="ai-metric-label">Completeness /100</span><span class="ai-metric-number">${percent(ai.checklist_score)}</span></div></div>${ai.dimensions.map(d => `<div class="ai-dimension"><strong>${esc(d.label)} · ${d.grade}/4</strong>${esc(d.reason)}<br>${refs(d.source_ids,true)}</div>`).join('')}<div class="forecast-box"><strong>Separate primary-endpoint forecast</strong><p>${f.score==null ? 'Unavailable. '+esc(f.reason || '') : esc(f.score.toFixed(3))+' · '+esc(f.score_type || 'Conditional endpoint forecast')+'. Assumed HR: '+esc(f.assumed_hr)+'; comparator: '+esc(f.comparator)+'.'}</p><p class="small muted">${esc(f.interpretation || 'A conditional trial-statistic illustration, not a probability of patient benefit.')} This forecast contributes no weight to the defense grade.</p></div></div>`;
  }
  function population(p, c, i) {
    const review=state.populations[p.option_id];
    return `<article class="population-panel" id="population-${p.option_id}" data-population="${p.option_id}" data-case="${c.case_id}" hidden><div class="population-title"><span class="letter">${String.fromCharCode(65+i)}</span><div><h3>${esc(p.population)}</h3><p>${esc(p.axes.join(' · '))}</p></div></div><div class="columns"><section class="card proposal" aria-label="Population proposal and evidence"><p class="section-label">Proposed scientific rationale</p>${p.defense.map(row => `<p class="defense-text">${esc(row.text)}</p>${refs(row.source_ids)}`).join('')}<details open><summary>Inclusion criteria <span class="muted small">(${p.inclusion.length})</span></summary><div class="details-content">${rows(p.inclusion,true)}</div></details><details><summary>Exclusion criteria <span class="muted small">(${p.exclusion.length})</span></summary><div class="details-content">${rows(p.exclusion,true)}</div></details><details><summary>Proposed advantages &amp; tradeoffs</summary><div class="details-content split"><div><h4>Advantages</h4>${points(p.pros)}</div><div><h4>Limitations &amp; tradeoffs</h4>${points(p.cons)}</div></div></details><details><summary>Protocol details still to resolve</summary><div class="details-content pending">${rows(p.protocol_pending,false)}</div></details></section><section class="card assessment" aria-label="Your independent ratings for ${esc(p.population)}"><div class="assessment-heading"><div><p class="section-label">Your review</p><h4>Scientific defensibility</h4><p>0 = weakest support · 4 = strongest support</p></div><output class="own-score" id="score-${p.option_id}" aria-label="Your weighted scientific score">—</output></div>${C.DIMENSIONS.map(d=>rating(p,d)).join('')}${feedback(p,'notes','Reasoning behind your ratings','Which evidence or selection rule most influenced your assessment?')}<div class="two-fields"><div><label class="feedback-label" for="${p.option_id}-decision">Population proposal</label><select class="editable" id="${p.option_id}-decision" data-pid="${p.option_id}" data-field="decision"><option value="">Choose an assessment</option>${[['retain','Defensible as drafted'],['revise','Needs revision'],['unsupported','Not sufficiently supported'],['uncertain','Unable to assess']].map(([v,l])=>`<option value="${v}" ${review.decision===v?'selected':''}>${l}</option>`).join('')}</select><div class="print-value" id="print-${p.option_id}-decision">${esc(review.decision)}</div></div><div><label class="feedback-label" for="${p.option_id}-confidence">Review confidence</label><select class="editable" id="${p.option_id}-confidence" data-pid="${p.option_id}" data-field="confidence"><option value="">Optional</option>${['High','Moderate','Low'].map(v=>`<option ${review.confidence===v?'selected':''}>${v}</option>`).join('')}</select><div class="print-value" id="print-${p.option_id}-confidence">${esc(review.confidence)}</div></div></div><details><summary>Suggest criteria changes or flag evidence errors</summary><div class="details-content">${feedback(p,'criteria_edits','Suggested inclusion/exclusion changes','Identify the criterion, proposed change and scientific reason.')}${feedback(p,'evidence_notes','Reference or evidence concerns','Note unsupported claims, missing studies, inaccurate interpretation or population mismatch.')}</div></details><div class="exposure-note" id="exposure-${p.option_id}" hidden></div><div class="assessment-footer"><span class="status-chip" id="status-${p.option_id}">Not yet rated</span><button class="btn" type="button" data-action="next" data-pid="${p.option_id}">Next population →</button></div></section></div><div class="ai-toggle-row"><div><strong>Compare with the prototype after your independent review</strong><p>Revealing AI grades records exposure. Ratings saved before exposure remain available for independent calibration; later edits are kept as assisted feedback.</p></div><button class="btn" type="button" data-action="toggle-ai" aria-controls="ai-${p.option_id}">Show AI assessment</button></div>${aiPanel(p)}</article>`;
  }
  function treatment(c, i) {
    const review=state.treatments[c.case_id];
    return `<section class="treatment-panel" id="case-${c.case_id}" hidden><div class="case-heading"><p class="eyebrow">Treatment ${String(i+1).padStart(2,'0')} / ${String(DATA.cases.length).padStart(2,'0')}</p><h2>${esc(c.treatment)}</h2><p>Compare three candidate trial populations. Cohorts may overlap; a higher defense grade does not establish greater treatment benefit.</p></div><nav class="population-tabs" aria-label="Populations for ${esc(c.treatment)}">${c.populations.map((p,j)=>`<button class="population-tab" type="button" data-action="population" data-case="${c.case_id}" data-pid="${p.option_id}" aria-selected="false">Population ${String.fromCharCode(65+j)}<span class="tick" id="tick-${p.option_id}"></span></button>`).join('')}</nav>${c.populations.map((p,j)=>population(p,c,j)).join('')}<section class="preference"><h4>Your preference for this treatment</h4><p>Which population is the most defensible starting point for a trial? This is an optional research-design judgment.</p><label class="field" for="preferred-${c.case_id}">Preferred population</label><select class="editable" id="preferred-${c.case_id}" data-treatment="${c.case_id}" data-treatment-field="preferred"><option value="">No preference recorded</option>${c.populations.map((p,j)=>`<option value="${p.option_id}" ${review.preferred===p.option_id?'selected':''}>${String.fromCharCode(65+j)} · ${esc(p.population)}</option>`).join('')}${[['tie','Equally defensible / tie'],['uncertain','Insufficient evidence to choose'],['none','None is sufficiently defensible']].map(([v,l])=>`<option value="${v}" ${review.preferred===v?'selected':''}>${l}</option>`).join('')}</select><div class="print-value" id="print-preferred-${c.case_id}">${esc(review.preferred)}</div><label class="feedback-label" for="preference-reason-${c.case_id}">Reason for your preference</label><textarea class="feedback editable" id="preference-reason-${c.case_id}" data-treatment="${c.case_id}" data-treatment-field="reason" maxlength="20000" placeholder="Explain the evidence and tradeoffs that distinguish your choice.">${esc(review.reason)}</textarea><div class="print-value" id="print-preference-reason-${c.case_id}">${esc(review.reason)}</div></section></section>`;
  }
  function render() {
    app.innerHTML=`<a class="skip-link" href="#review-workspace">Skip to population review</a><header class="masthead"><div class="wrap"><div class="topline"><div class="brand"><span class="brand-mark" aria-hidden="true">＋</span>Population design review</div><div class="private-tag"><span class="dot"></span>Self-contained · no upload</div></div><div class="hero"><div class="hero-copy"><p class="eyebrow">Independent oncology assessment</p><h1>Which population is<br>scientifically justified?</h1><p>Review treatment-specific subgroups in <strong>HR+/HER2− metastatic breast cancer after endocrine therapy + CDK4/6 progression.</strong> Assess the evidence, the selection rule and its tradeoffs.</p></div><div class="hero-side"><div class="progress-number"><b id="review-count">0</b><span> / ${Object.keys(state.populations).length}</span></div><p class="small muted">populations reviewed</p><div class="progress-bar"><span id="progress-fill"></span></div><p class="small muted" id="independent-count">0 independent ratings</p></div></div><div class="notice"><span class="notice-icon" aria-hidden="true">i</span><div><strong>Start with your own assessment.</strong> AI grades and endpoint forecasts are hidden by default to reduce anchoring. Rate each dimension 0–4, or choose “Unable to assess.” This is a research review, not a formally blinded evaluation or a patient-treatment recommendation.</div></div><div class="reviewer-row"><label class="field" for="reviewer-name">Reviewer name or code <span class="muted">(optional)</span><input id="reviewer-name" data-reviewer="name" maxlength="1000" value="${esc(state.reviewer.name)}" autocomplete="off" placeholder="Name or anonymous code"></label><label class="field" for="reviewer-specialty">Specialty / role <span class="muted">(optional)</span><input id="reviewer-specialty" data-reviewer="specialty" maxlength="1000" value="${esc(state.reviewer.specialty)}" autocomplete="off" placeholder="e.g. Breast medical oncology"></label><label class="field" for="review-date">Review date<input id="review-date" type="date" data-reviewer="review_date" value="${esc(state.reviewer.review_date)}"></label></div></div></header><div class="actions"><div class="wrap action-inner"><div><div class="action-buttons"><button class="btn primary" type="button" data-action="save-html">Save review HTML</button><button class="btn" type="button" data-action="export-json">Export review JSON</button><button class="btn" id="calibration-export" type="button" data-action="calibration">Export independent ratings</button><button class="btn quiet" type="button" data-action="import">Import JSON</button><button class="btn quiet" type="button" data-action="print">Print / PDF</button></div><p class="export-help">Send the saved HTML or review JSON back to the researcher. Independent export includes completed pre-AI ratings only.</p></div><span class="save-status" id="save-status" aria-live="polite">${storageAvailable?'Your work stays in this browser':'Browser autosave unavailable; download your review to keep it'}</span></div></div><div class="wrap workspace" id="review-workspace"><aside class="sidebar"><p class="eyebrow">Treatment cases</p><nav class="treatment-nav" aria-label="Treatment cases">${DATA.cases.map((c,i)=>`<button class="treatment-button" type="button" data-action="case" data-case="${c.case_id}" aria-selected="false"><span>${String(i+1).padStart(2,'0')} &nbsp;${esc(c.treatment)}</span><span class="nav-count" id="nav-count-${c.case_id}">0 / ${c.populations.length}</span></button>`).join('')}</nav><div class="sidebar-help"><strong>Four scientific dimensions</strong><p>Evidence strength<br>Population applicability<br>Selection justification<br>Tradeoffs</p><button class="btn quiet" data-action="rubric" type="button">View 0–4 grading rubric ↗</button><p>Evidence snapshot: ${esc(DATA.evidence_as_of)}.<br>Clinical adjudication pending.</p></div></aside><main>${DATA.cases.map(treatment).join('')}</main></div><footer class="wrap footer"><p><strong>About this review.</strong> Your scientific score uses fixed weights: evidence 35%, applicability 25%, selection 25%, tradeoffs 15%. The prototype’s final defense combines 80% scientific assessment and 20% completeness. Endpoint forecasts contribute no weight. Scores remain provisional.</p><p style="margin-top:9px">Nothing is sent to a server. Browser autosave may be unavailable or cleared; save an HTML or JSON copy before closing. Reviewer details and feedback are included in your exported review. Do not enter patient-identifying information.</p><div class="action-buttons" style="margin-top:13px"><button class="btn" type="button" data-action="rubric">Read the full rubric</button><button class="btn quiet" type="button" data-action="blank-html">Download a blank copy</button><button class="btn quiet" type="button" data-action="new">Start a new review</button></div><details><summary>Reference library · ${Object.keys(DATA.sources).length} sources</summary><ol class="reference-list">${Object.entries(DATA.sources).map(([id,s])=>`<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(id)} · ${esc(s.title)}</a></li>`).join('')}</ol></details></footer><dialog id="rubric-dialog" aria-labelledby="rubric-title"><button class="dialog-close" type="button" data-action="close-rubric" aria-label="Close rubric">×</button><p class="eyebrow">Scientific grading · version 3</p><h2 id="rubric-title">Use the evidence, not the presentation.</h2><p>Rate the scientific defensibility of each proposal. Grade 0–4 independently on each dimension; select “Unable to assess” if the supplied evidence is insufficient for your judgment. A trial eligibility rule or an observed subgroup benefit does not, by itself, establish a predictive treatment-effect interaction.</p><div style="overflow-x:auto"><table class="rubric-table"><thead><tr><th>Grade</th>${C.DIMENSIONS.map(d=>`<th>${labels[d]}<br><span class="muted">${Math.round(DATA.config.dimension_weights[d]*100)}%</span></th>`).join('')}</tr></thead><tbody>${[0,1,2,3,4].map(n=>`<tr><td>${n}</td>${C.DIMENSIONS.map(d=>`<td>${esc(DATA.anchors[d][n])}</td>`).join('')}</tr>`).join('')}</tbody></table></div><p style="margin-top:16px">Different populations may legitimately tie. A larger observed effect or a higher conditional endpoint forecast does not automatically mean stronger evidence. These anchors and weights require oncologist calibration.</p></dialog><input class="file-input" id="import-file" type="file" accept="application/json,.json" aria-label="Import saved review JSON">`;
    applyVisibility(); refresh();
  }
  function active() {
    const c=DATA.cases.find(c=>c.case_id===state.active_case) || DATA.cases[0];
    const p=c.populations.find(p=>p.option_id===state.active_populations[c.case_id]) || c.populations[0];
    return {c,p};
  }
  function applyVisibility() {
    const {c,p}=active();
    document.querySelectorAll('.treatment-panel').forEach(el=>el.hidden=el.id!==`case-${c.case_id}`);
    document.querySelectorAll('.population-panel').forEach(el=>el.hidden=el.id!==`population-${p.option_id}`);
    document.querySelectorAll('[data-action="case"]').forEach(el=>el.setAttribute('aria-selected',String(el.dataset.case===c.case_id)));
    document.querySelectorAll('[data-action="population"]').forEach(el=>el.setAttribute('aria-selected',String(el.dataset.pid===p.option_id)));
    document.querySelectorAll('.ai-panel').forEach(el=>el.hidden=!state.show_ai);
    document.querySelectorAll('[data-action="toggle-ai"]').forEach(el=>{el.textContent=state.show_ai?'Hide AI assessment':'Show AI assessment';el.setAttribute('aria-expanded',String(state.show_ai));});
    if(state.show_ai) C.reveal(state,p.option_id,now());
  }
  function refresh() {
    const progress=C.summary(state);
    document.getElementById('review-count').textContent=progress.reviewed;
    document.getElementById('independent-count').textContent=`${progress.independent} independent rating sets`;
    document.getElementById('progress-fill').style.width=`${100*progress.reviewed/progress.total}%`;
    document.getElementById('calibration-export').disabled=progress.independent===0;
    for(const c of DATA.cases){
      document.getElementById(`nav-count-${c.case_id}`).textContent=`${c.populations.filter(p=>C.answered(state.populations[p.option_id])).length} / ${c.populations.length}`;
      for(const p of c.populations){
        const r=state.populations[p.option_id],score=C.score(r,DATA.config.dimension_weights);
        document.getElementById(`score-${p.option_id}`).innerHTML=score===null?'—':`${score.toFixed(1)}<span> /100</span>`;
        const status=document.getElementById(`status-${p.option_id}`);
        status.textContent=C.complete(r)?'Four numeric ratings recorded':C.answered(r)?'Reviewed · includes unable to assess':`${C.DIMENSIONS.filter(d=>r.statuses[d]!=='unrated').length} of 4 dimensions rated`;
        status.classList.toggle('done',C.answered(r));
        document.getElementById(`tick-${p.option_id}`).textContent=C.answered(r)?'✓':'';
        const exposure=document.getElementById(`exposure-${p.option_id}`);
        exposure.hidden=!r.ai_viewed_at;
        exposure.textContent=r.independent_snapshot?'Pre-AI ratings are preserved for calibration. Further changes are assisted feedback.':'AI grades have been viewed. This feedback is retained as assisted review and excluded from independent calibration export.';
        for(const d of C.DIMENSIONS){
          const v=r.scientific_grades[d];
          document.getElementById(`anchor-${p.option_id}-${d}`).textContent=r.statuses[d]==='unable'?'Unable to assess — explain the missing evidence below.':Number.isInteger(v)?DATA.anchors[d][v]:'Choose 0–4. Open the rubric for the full grade definitions.';
        }
      }
    }
  }
  function persist() {
    clearTimeout(saveTimer);
    saveTimer=setTimeout(()=>{
      const target=document.getElementById('save-status');
      try{localStorage.setItem(key,JSON.stringify(state));storageAvailable=true;target.textContent='Saved in this browser · download a copy to share';}
      catch(_){storageAvailable=false;target.textContent='Autosave unavailable · save HTML or JSON before closing';}
    },250);
  }
  function toast(message) {
    clearTimeout(toastTimer); const el=document.getElementById('toast');el.textContent=message;el.classList.add('visible');
    toastTimer=setTimeout(()=>el.classList.remove('visible'),6500);
  }
  function download(content,type,name) {
    const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),20000);
  }
  function fileName(suffix) {
    const reviewer=(state.reviewer.name || 'review').replace(/[^a-zA-Z0-9_-]+/g,'-').slice(0,50)||'review';
    return `oncology-${reviewer}-${state.reviewer.review_date||today()}.${suffix}`;
  }
  function saveHTML(blank) {
    const cloned=document.documentElement.cloneNode(true);
    cloned.querySelector('#review-state').textContent=C.scriptJSON(blank?null:state);
    cloned.querySelector('#app').innerHTML='';cloned.querySelector('#toast').textContent='';cloned.querySelector('#toast').className='';
    download('<!doctype html>\n'+cloned.outerHTML,'text/html;charset=utf-8',blank?'oncology-review-blank.html':fileName('html'));
    toast(blank?'Blank form downloaded. Share this one HTML file.':'Review HTML downloaded, including your ratings and comments.');
  }
  function moveNext(id) {
    const all=DATA.cases.flatMap(c=>c.populations.map(p=>({c,p})));const index=all.findIndex(x=>x.p.option_id===id);
    if(index===all.length-1){toast('You reached the last population. Check your treatment preferences, then save your review.');return;}
    const next=all[index+1];state.active_case=next.c.case_id;state.active_populations[next.c.case_id]=next.p.option_id;
    applyVisibility();refresh();persist();document.getElementById('review-workspace').scrollIntoView({behavior:'smooth',block:'start'});
  }
  app.addEventListener('input',handleInput);
  app.addEventListener('change',event=>{if(event.target.id==='import-file') importFile(event.target.files?.[0]);else if(event.target.tagName==='SELECT') handleInput(event);});
  function handleInput(event) {
    const el=event.target;
    if(el.dataset.dimension){C.grade(state,el.dataset.pid,el.dataset.dimension,el.value==='unable'?'unable':Number(el.value),now());refresh();}
    else if(el.dataset.field){C.note(state,el.dataset.pid,el.dataset.field,el.value,now());const mirror=document.getElementById(`print-${el.dataset.pid}-${el.dataset.field}`);if(mirror)mirror.textContent=el.value;}
    else if(el.dataset.reviewer){state.reviewer[el.dataset.reviewer]=el.value;state.updated_at=now();}
    else if(el.dataset.treatment){state.treatments[el.dataset.treatment][el.dataset.treatmentField]=el.value;state.updated_at=now();const mirror=document.getElementById(el.dataset.treatmentField==='preferred'?`print-preferred-${el.dataset.treatment}`:`print-preference-reason-${el.dataset.treatment}`);if(mirror)mirror.textContent=el.value;}
    else return;
    persist();
  }
  app.addEventListener('click',event=>{
    const button=event.target.closest('button[data-action]');if(!button)return;
    const action=button.dataset.action;
    if(action==='case'){state.active_case=button.dataset.case;applyVisibility();refresh();persist();}
    else if(action==='population'){state.active_populations[button.dataset.case]=button.dataset.pid;applyVisibility();refresh();persist();}
    else if(action==='next')moveNext(button.dataset.pid);
    else if(action==='rubric')document.getElementById('rubric-dialog').showModal();
    else if(action==='close-rubric')document.getElementById('rubric-dialog').close();
    else if(action==='toggle-ai'){state.show_ai=!state.show_ai;applyVisibility();refresh();persist();}
    else if(action==='save-html')saveHTML(false);
    else if(action==='blank-html')saveHTML(true);
    else if(action==='export-json'){
      download(JSON.stringify({schema_version:C.VERSION,dataset_id:DATA.dataset_id,exported_at:now(),review:state,
        case_manifest:DATA.cases.map(c=>({case_id:c.case_id,treatment:c.treatment,input_id:c.input_id,input_sha256:c.input_sha256}))},null,2),'application/json',fileName('json'));toast('Full review JSON downloaded, including assisted feedback and saved independent snapshots.');
    }
    else if(action==='calibration'){
      const entries=C.calibration(state,DATA);if(!entries.length){toast('Complete four numeric ratings before revealing AI grades to create an independent rating set.');return;}
      download(JSON.stringify(entries,null,2),'application/json',fileName('independent-ratings.json'));toast(`${entries.length} independent rating set${entries.length===1?'':'s'} exported. Other feedback stays in the full review.`);
    }
    else if(action==='import')document.getElementById('import-file').click();
    else if(action==='print')window.print();
    else if(action==='new' && window.confirm('Start a new review? Download the current review first if you want to keep it.')){
      state=C.fresh(DATA,uuid(),now());state.reviewer.review_date=today();render();persist();toast('New independent review started.');
    }
  });
  async function importFile(file) {
    if(!file)return;
    if(file.size>2000000){toast('Review JSON is too large. Choose a review export smaller than 2 MB.');return;}
    try{const imported=C.restore(JSON.parse(await file.text()),DATA);state=imported;render();persist();toast('Saved review imported. Independent and assisted rating histories are preserved.');}
    catch(error){toast(`Import failed: ${error.message}`);}
  }
  let printDetails=[];
  window.addEventListener('beforeprint',()=>{
    if(state.show_ai)for(const id of Object.keys(state.populations))C.reveal(state,id,now());
    printDetails=[...document.querySelectorAll('details')].map(el=>[el,el.open]);printDetails.forEach(([el])=>el.open=true);refresh();persist();
  });
  window.addEventListener('afterprint',()=>printDetails.forEach(([el,open])=>el.open=open));
  render();persist();
})();
