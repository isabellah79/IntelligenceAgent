'use strict';
const $ = id => document.getElementById(id);
const state = {bootstrap: null, result: null, filter: 'all', stale: false, reviews: [], pendingReview: null, forecast: null, forecastStale: false, judgmentParent: null};
const dimensions={match:'Context match',evidence:'Evidence applicability',readiness:'Known review flags',preference:'Delivery preference'};
const statusLabels = {discuss: 'Relevant for discussion', needs_information: 'Needs more information', later_line: 'Later-line requirement', not_matched: 'Does not match this case'};
const tri = [['detected', 'Detected'], ['not_detected', 'Not detected'], ['unknown', 'Unknown / not tested']];
const fields = [
  {section: 'Disease & prior treatment'},
  {key: 'age', label: 'Age', type: 'number', min: 18, max: 120},
  {key: 'menopausal', label: 'Menopausal / sex context', choices: [['postmenopausal', 'Postmenopausal woman'], ['premenopausal', 'Premenopausal woman'], ['male', 'Man'], ['unknown', 'Unknown']]},
  {key: 'er_positive', label: 'ER-positive disease', type: 'checkbox'},
  {key: 'her2', label: 'HER2 pathology', choices: [['low', 'Low: IHC 1+ or 2+/ISH−'], ['ultralow', 'Ultralow: IHC 0 + staining'], ['zero', 'IHC 0, no membrane staining'], ['unknown', 'Unknown'], ['positive', 'HER2-positive (outside scope)']]},
  {key: 'prior_cdk', label: 'Prior CDK4/6 inhibitor', choices: [['ribociclib', 'Ribociclib'], ['palbociclib', 'Palbociclib'], ['abemaciclib', 'Abemaciclib'], ['unknown', 'Unknown agent (exposure confirmed)']]},
  {key: 'prior_endocrine', label: 'Prior endocrine partner', choices: [['aromatase_inhibitor', 'Aromatase inhibitor'], ['fulvestrant', 'Fulvestrant'], ['other', 'Other'], ['unknown', 'Unknown']]},
  {key: 'endocrine_months', label: 'Months on prior endocrine + CDK4/6', type: 'number', min: 0, max: 240},
  {section: 'Biomarkers'},
  ...[['esr1','ESR1'], ['pik3ca','PIK3CA'], ['akt1','AKT1'], ['pten','PTEN qualifying alteration'], ['gbrca','Germline BRCA1/2']].map(([key,label]) => ({key,label,choices:tri})),
  {section: 'Treatment sequence'},
  {key: 'prior_metastatic_chemo', label: 'Metastatic chemotherapy regimens', type:'number', min:0, max:20},
  {key: 'additional_metastatic_lines', label: 'Additional metastatic regimens after initial endocrine + CDK4/6 (include chemotherapy)', type:'number', min:0, max:30},
  {key: 'prior_adc', label: 'Prior ADC exposure', type:'checkbox'},
  {section: 'Clinical context & priorities'},
  {key: 'ecog', label: 'ECOG performance status', type:'number', min:0, max:4},
  {key: 'organ_function', label:'Organ function', choices:[['adequate','Preserved'],['impaired','Impaired'],['unknown','Unknown']]},
  {key: 'visceral_crisis', label:'Visceral crisis / organ compromise', type:'checkbox'},
  {key: 'diabetes', label:'Diabetes', choices:[['no','No'],['controlled','Controlled'],['uncontrolled','Uncontrolled'],['unknown','Unknown']]},
  {key: 'ild_history', label:'History of ILD / pneumonitis', choices:[['no','No'],['yes','Yes'],['unknown','Unknown']]},
  {key: 'preference', label:'Discussion priority', choices:[['fewer_visits','Fewer hospital visits'],['disease_control','Disease control'],['balanced','Balance benefit and burden']]},
];

function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function refs(ids) {
  const span = el('span', undefined, 'source-links');
  for (const id of ids) { const a = el('a', `[${id}]`); a.href = `#source-${id}`; a.title = state.bootstrap.sources[id]?.title || id; span.append(a); }
  return span;
}
function cited(statement, tag = 'p') {
  const node = el(tag, statement.text + ' '); node.append(refs(statement.source_ids)); return node;
}
function buildForm() {
  for (const field of fields) {
    if (field.section) { $('fields').append(el('div',field.section,'field-section')); continue; }
    const label = el('label',field.label); label.htmlFor = `case-${field.key}`;
    let input;
    if (field.choices) {
      input = el('select');
      for (const [value,text] of field.choices) { const opt=el('option',text); opt.value=value; input.append(opt); }
    } else {
      input = el('input'); input.type=field.type;
      if (field.type === 'number') { input.min=field.min; input.max=field.max; input.step='1'; input.placeholder='Unknown'; }
      if (field.type === 'checkbox') label.className='check-label';
    }
    input.id=`case-${field.key}`; input.name=field.key;
    label.append(input); $('fields').append(label);
  }
}
function setCase(c) {
  for (const f of fields.filter(f=>f.key)) { const input=$(`case-${f.key}`); if(f.type==='checkbox') input.checked=c[f.key]; else input.value=c[f.key] ?? ''; }
}
function readCase() {
  return Object.fromEntries(fields.filter(f=>f.key).map(f=>{
    const input=$(`case-${f.key}`);
    return [f.key, f.type==='checkbox' ? input.checked : f.type==='number' ? (input.value==='' ? null : Number(input.value)) : input.value];
  }));
}
function buildWeights() {
  for(const [key,title] of Object.entries(dimensions)) {
    const label=el('label',title);label.htmlFor=`weight-${key}`;
    const input=el('input');input.type='number';input.id=`weight-${key}`;input.min=0;input.max=100;input.step=1;input.required=true;
    label.append(input);$('weight-fields').append(label);
  }
  $('reset-weights').addEventListener('click',()=>{setWeights();dirty();});
  $('case-preference').addEventListener('change',()=>{setWeights();dirty();});
}
function setWeights() {
  const weights=state.bootstrap.weight_presets[$('case-preference').value];
  for(const [key,value] of Object.entries(weights))$(`weight-${key}`).value=value;
}
function readWeights() {return Object.fromEntries(Object.keys(dimensions).map(key=>[key,Number($(`weight-${key}`).value)]));}
function readEndpointDesign() {
  const overrides={};for(const input of document.querySelectorAll('[data-factor-option]')){const id=input.dataset.factorOption;overrides[id]??={};overrides[id][input.dataset.factorId]=Number(input.value);}
  return {events:Number($('endpoint-events').value),z_threshold:Number($('endpoint-z').value),prior:$('endpoint-prior').value===''?null:Number($('endpoint-prior').value),use_reference_effect:$('endpoint-source-effect').checked,evidence_strength:Number($('endpoint-evidence-strength').value),blend_a:Number($('endpoint-blend').value),factor_overrides:overrides};
}
function dirty() {
  if (!state.result) return;
  state.stale=true; $('stale').hidden=false; $('export').disabled=true;
  document.querySelectorAll('.card-actions button, .model-judgments button').forEach(b=>b.disabled=true);
}
async function api(path, payload) {
  const response = await fetch(path, payload ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)} : {});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function renderLibrary() {
  const box=$('library'); box.replaceChildren();
  for(const source of Object.values(state.bootstrap.sources)) {
    const row=el('div',undefined,'source-entry'); row.id=`source-${source.id}`;
    row.append(el('div',source.id,'small-label'));
    const body=el('div'); const a=el('a',source.title+' ↗'); a.href=source.url; a.target='_blank'; a.rel='noopener noreferrer';
    body.append(a, el('p',source.scope), el('p',`${source.kind} · Source checked ${source.checked_on} · Clinical review pending`)); row.append(body);box.append(row);
  }
}
function renderCard(o) {
  const card=el('article',undefined,`card ${o.status==='not_matched'||o.status==='later_line'?'dimmed':''}`);
  card.id=`option-${o.id}`;
  card.append(el('div',statusLabels[o.status],`status ${o.status}`),el('h3',o.title),el('p',o.route,'route'));
  const score=o.priority_score;
  if(score) {
    const badge=el('div',undefined,'score-badge');badge.append(el('strong',score.value===null?'—':`${score.value}/100`),el('span',score.value===null?'Review required · no score':'Discussion priority · policy score'));card.append(badge);
    const breakdown=el('details',undefined,'score-details');breakdown.append(el('summary','Score calculation & reasons'));
    if(score.value===null) {for(const reason of score.blocked_reasons)breakdown.append(el('p',reason));}
    for(const row of score.components) {
      const p=el('p',`${row.label}: ${row.points}/5 × ${row.weight} = ${row.contribution} points. ${row.reason} `);p.append(refs(row.source_ids));breakdown.append(p);
    }
    breakdown.append(el('p','Numeric assignments are prototype policy choices; sources support the underlying facts, not the points.'));card.append(breakdown);
  }
  const fit=el('div',o.fit_reason+' ','fit'); fit.append(refs(o.fit_source_ids)); card.append(fit);
  for(const [key,title] of [['pros','Why consider it'],['cons','Trade-offs & risks']]) {
    card.append(el('div',title,`section-label ${key}`));const list=el('ul'); o[key].forEach(s=>list.append(cited(s,'li')));card.append(list);
  }
  for(const s of o.case_concerns) { const p=cited(s);p.className='case-concern';card.append(p); }
  const evidence=el('div',undefined,'evidence'); evidence.append(el('div','Evidence in its own population','section-label'));
  o.evidence.forEach(s=>evidence.append(cited(s)));card.append(evidence);
  const detail=el('details');detail.append(el('summary','Applicability & uncertainty'),el('p',o.limits));card.append(detail);
  if(o.trial_forecast) {
    const f=o.trial_forecast, detail=el('details');detail.append(el('summary',`Historical linked-trial forecast: ${(f.combined*100).toFixed(1)}%`),el('p',f.interpretation+' Trial endpoint probability; zero weight in the treatment score.'));
    const a=el('a','Inspect original assumptions ↓');a.href='#forecast-lab';detail.append(a);card.append(detail);
  }
  const actions=el('div',undefined,'card-actions');
  for(const [action,text] of [['select','Select for discussion'],['edit','Propose edit'],['reject','Reject']]) {
    const button=el('button',text);button.type='button';button.disabled=state.stale;button.addEventListener('click',()=>openReview(o,action));actions.append(button);
  }
  card.append(actions);
  const review=state.reviews.filter(r=>r.option_id===o.id).at(-1);
  if(review) card.append(el('div',`Review saved: ${review.action}${review.comment?' · '+review.comment:''}`,'reviewed'));
  return card;
}
function renderPriority(r) {
  const panel=el('section',undefined,'priority-panel');const rec=r.recommendation;
  panel.append(el('div','NEXT STEP · EXPLAINABLE DISCUSSION PRIORITY','eyebrow'),el('h3',rec.title),el('p',rec.text));
  if(rec.score!==null)panel.append(el('p',`Highest policy score ${rec.score}/100 · ${r.priority_policy.tie_margin}-point shortlist margin`,'score-caption'));
  for(const reason of rec.reasons){panel.append(el('strong',reason.title),cited(reason));}
  if(r.ranking.length) {
    const table=el('table',undefined,'rank-table');const head=el('thead');const tr=el('tr');['Treatment discussion','Policy score'].forEach(s=>tr.append(el('th',s)));head.append(tr);table.append(head);const body=el('tbody');
    for(const item of r.ranking) {const row=el('tr');const name=el('td');const a=el('a',item.title);a.href=`#option-${item.option_id}`;name.append(a);row.append(name,el('td',`${item.score}/100`));body.append(row);}table.append(body);panel.append(table);
  }
  const detail=el('details');detail.append(el('summary','Why alternatives score lower / policy sensitivity'));
  for(const row of rec.comparison) {detail.append(el('strong',`${row.title} · ${row.score}/100`));for(const d of row.differences)detail.append(cited({text:`${d.policy_point_gap} fewer points on ${d.dimension}: ${d.reason}`,source_ids:d.source_ids}));}
  const titles=Object.fromEntries(r.options.map(o=>[o.id,o.title]));
  for(const s of r.priority_policy.sensitivity)detail.append(el('p',`Evidence weight ${s.weights.evidence}, delivery preference ${s.weights.preference}: ${s.shortlist_ids.map(id=>titles[id]).join('; ')}.`));
  detail.append(el('p','Sensitivity shifts 10 weight points between evidence and delivery preference. It is a policy stress test, not a clinical confidence interval.'));panel.append(detail);
  if(rec.next_checks.length){const list=el('ul');rec.next_checks.forEach(s=>list.append(el('li',s)));panel.append(list);}
  panel.append(el('p',`${r.priority_policy.provenance}. ${r.priority_policy.limitations} Trial forecasts have 0% weight.`,'policy-note'));
  return panel;
}
function renderLegacyCards() {
  const r=state.result, root=$('result');root.replaceChildren();
  for(const s of r.alerts) { const notice=cited(s);notice.className='notice';root.append(notice); }
  root.append(renderPriority(r));
  const synthesis=el('section',undefined,'synthesis');
  synthesis.append(el('span',r.mode==='curated'?'CURATED EVIDENCE · TRANSPARENT RULES':`MODEL SYNTHESIS · ${r.model}`,'mode-badge'),el('h3','What this case brings into focus'));
  for(const s of r.synthesis) {const p=cited(s);p.prepend(el('span',s.kind,'claim-kind'));synthesis.append(p);}
  root.append(synthesis);
  const filters=el('div',undefined,'counts');
  for(const [key,label] of [['all','All strategies'],['discuss','Relevant'],['needs_information','Conditional'],['later_line','Later line'],['not_matched','Not matched']]) {
    const count=key==='all'?r.options.length:r.options.filter(o=>o.status===key).length;
    const b=el('button',`${label} ${count}`,`filter ${state.filter===key?'active':''}`);b.setAttribute('aria-pressed',String(state.filter===key));b.addEventListener('click',()=>{state.filter=key;render();});filters.append(b);
  }
  root.append(filters);
  const options=r.options.filter(o=>state.filter==='all'||o.status===state.filter);
  for(const family of [...new Set(options.map(o=>o.family))]) {
    root.append(el('h3',family,'family-title'));const grid=el('div',undefined,'cards');options.filter(o=>o.family===family).forEach(o=>grid.append(renderCard(o)));root.append(grid);
  }
  if(!options.length) root.append(el('p','No options in this view.','muted'));
  const notes=el('div',undefined,'method-note');notes.append(el('strong',`Evidence snapshot ${r.evidence_as_of} · ${r.jurisdiction} · Version ${r.evidence_version}`));
  const ul=el('ul');r.limitations.forEach(s=>ul.append(el('li',s)));notes.append(ul);root.append(notes);
}
function treatmentReferences(ids) {
  const span=el('span',undefined,'treatment-references');
  for(const id of [...new Set(ids)]) {
    const s=state.bootstrap.sources[id],a=el('a',`[${id}]`);a.href=s.url;a.title=s.title;a.target='_blank';a.rel='noopener noreferrer';span.append(a,document.createTextNode(' '));
  }
  return span;
}
function render() {
  const r=state.result,root=$('result');root.replaceChildren();
  for(const s of r.alerts){const p=cited(s);p.className='notice';root.append(p);}
  const c=r.case,strip=el('p',`Current case: ${c.er_positive?'ER+':'ER−'} / HER2-${c.her2}; ESR1 ${c.esr1}; PIK3CA ${c.pik3ca}; prior CDK4/6: ${c.prior_cdk}; metastatic chemotherapy regimens: ${c.prior_metastatic_chemo??'unknown'}.`,'case-strip');root.append(strip);
  const design=r.endpoint_design;
  const definition=el('div',undefined,'endpoint-definition');
  definition.append(el('strong','Provisional PFS endpoint forecast · equation and weights are open for review.'),el('p',`${design.events} assumed PFS events · 1:1 allocation · z threshold ${design.z_threshold} · ${design.prior===null?'No prior: original method B conditional power.':`Starting prior ${(design.prior*100).toFixed(1)}% (analyst assumption); A/B weights ${design.blend_a}/${1-design.blend_a}; evidence strength ${design.evidence_strength}.`} ${r.endpoint_score_definition.effect_assumption}`),el('p',r.endpoint_score_definition.limitations));
  const apply=el('button','Recalculate with current evidence weights ↗','secondary');apply.id='apply-endpoint';apply.type='button';apply.addEventListener('click',()=>{$('mode').value='curated';dirty();run();});definition.append(apply);
  const modelStatus=state.bootstrap.model_status;
  if(modelStatus?.configured){const judge=el('button',`Run ${modelStatus.provider==='vertex'?'Gemini':'model'} evidence review ↗`,'secondary');judge.id='run-judgment';judge.type='button';judge.addEventListener('click',()=>{$('mode').value='model';dirty();run();});definition.append(judge,el('p',`${modelStatus.model}${modelStatus.provider==='vertex'?` · Vertex AI · ${modelStatus.project} · ${modelStatus.location}`:''}. An explicit review request sends this fictional case and evidence to the model.`,'muted'));}
  root.append(definition);
  if(r.run_id){const saved=el('a','Reopen this saved review','muted');saved.href=`?run=${encodeURIComponent(r.run_id)}#result`;definition.append(saved);}
  if(r.mode==='model_synthesis')root.append(renderJudgments(r));
  if(r.applied_model_judgments?.length){root.append(el('p',`Applied ${r.applied_model_judgments.length} reviewed model weight suggestions from run ${r.parent_model_judgment_run_id}. Python recalculated the endpoint scores; the original model review is retained.`,'notice'));root.append(renderJudgments({model:r.parent_model_metadata.model,model_metadata:r.parent_model_metadata,synthesis:r.parent_model_synthesis,model_judgments:r.applied_model_judgments,options:r.options},true));}
  const wrap=el('div',undefined,'endpoint-table-wrap');wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Next treatments with endpoint scores and references');wrap.tabIndex=0;
  const table=el('table',undefined,'endpoint-table');const caption=el('caption','Possible next treatments after CDK4/6 progression. Each reference immediately follows its treatment name.');table.append(caption);
  const head=el('thead'),header=el('tr');for(const s of ['Treatment & references','Fit for this case','Primary endpoint: published evidence','Provisional PFS forecast score','Pros','Cons / limitations']){const th=el('th',s);th.scope='col';header.append(th);}head.append(header);table.append(head);
  const body=el('tbody');
  for(const o of r.options) {
    const e=o.endpoint_comparison,row=el('tr');row.id=`option-${o.id}`;
    if(o.status!=='discuss')row.className='not-current';
    const name=el('th');name.scope='row';name.append(el('span',o.title,'treatment-name'),document.createTextNode(' '),treatmentReferences(e.source_ids),el('p',o.route,'muted'));
    const fit=el('td');fit.append(el('strong',statusLabels[o.status]),el('p',o.fit_reason));
    const evidence=el('td');evidence.append(el('strong',e.trial),el('p',`${e.primary_endpoint} · ${e.population}`));
    if(e.median_pfs_months)evidence.append(el('p',`Median PFS: ${e.median_pfs_months[0]} vs ${e.median_pfs_months[1]} months.`));
    if(e.hazard_ratio!==null)evidence.append(el('p',`Published PFS HR: ${e.hazard_ratio} vs ${e.comparator}.`));
    else evidence.append(el('p',e.comparator));
    const score=el('td');
    if(e.score===null)score.append(el('strong','Not estimated','endpoint-unavailable'),el('p',e.unavailable_reason));
    else {score.append(el('strong',`${(e.score*100).toFixed(1)}%`,'endpoint-number'),el('p',e.score_type));const detail=el('details');detail.append(el('summary','Calculation assumptions'),el('p',`Assumed true HR ${e.hazard_ratio}; ${design.events} events; z > ${design.z_threshold}. B: ${(e.method_b*100).toFixed(1)}%.`));if(e.method_a!==null)detail.append(el('p',`Adjusted A: ${(e.method_a*100).toFixed(1)}%; score = ${design.blend_a} × A + ${1-design.blend_a} × B.`));detail.append(el('p','Published outcome is already known. This is a hypothetical source-cohort calculation, not a forecast validated before readout.'));score.append(detail);}
    if(e.evidence_adjustments.length){
      const ledger=el('details',undefined,'adjustment-ledger');ledger.append(el('summary','Literature + / − evidence weights'));
      for(const f of e.evidence_adjustments){
        ledger.append(cited({text:f.finding,source_ids:f.source_ids}));const label=el('label',`${f.id.replaceAll('_',' ')} · odds multiplier`);const input=el('input');input.type='number';input.min='.25';input.max='4';input.step='.01';input.value=f.factor;input.dataset.factorOption=o.id;input.dataset.factorId=f.id;input.setAttribute('aria-label',`${o.title}: ${f.id} multiplier`);input.addEventListener('input',()=>{state.judgmentParent=null;dirty();});label.append(input);ledger.append(label,el('p',`${f.rationale} Effective multiplier ${f.effective_factor.toFixed(3)} after evidence-strength damping. ${f.weight_provenance}.`));
      }
      if(e.evidence_delta!==null)ledger.append(el('p',`Literature adjustment changes the blended score by ${e.evidence_delta>=0?'+':''}${(e.evidence_delta*100).toFixed(2)} percentage points, from ${(e.unadjusted_score*100).toFixed(1)}% to ${(e.score*100).toFixed(1)}%.`));
      else ledger.append(el('p','Weights are recorded, but no adjusted score is calculated while the case is on hold or a prior is missing.'));score.append(ledger);
    }
    const pros=el('td'),cons=el('td');for(const [node,statements] of [[pros,o.pros],[cons,o.cons]]){const ul=el('ul');statements.forEach(s=>ul.append(cited(s,'li')));node.append(ul);}
    if(e.note)cons.append(el('p',e.note,'table-caveat'));
    for(const s of o.case_concerns)cons.append(cited(s));
    const actions=el('div',undefined,'card-actions');for(const [action,text] of [['select','Discuss'],['edit','Edit'],['reject','Reject']]){const b=el('button',text);b.type='button';b.disabled=state.stale;b.addEventListener('click',()=>openReview(o,action));actions.append(b);}name.append(actions);
    const review=state.reviews.filter(x=>x.option_id===o.id).at(-1);if(review)name.append(el('p',`Review saved: ${review.action}${review.comment?' · '+review.comment:''}`,'reviewed'));
    row.append(name,fit,evidence,score,pros,cons);body.append(row);
  }
  table.append(body);wrap.append(table);root.append(el('p','On a narrow screen, scroll the table sideways to see endpoint scores, pros and cons.','table-scroll-hint'));root.append(wrap);
  root.append(el('p','Higher conditional power here does not establish a better treatment: the source cohorts, comparators and subgroup analyses differ. Missing or inapplicable estimates are left blank.','method-note'));
}
async function run(event) {
  event?.preventDefault();$('error').hidden=true;$('busy').hidden=false;$('run').disabled=true;$('export').disabled=true;
  if($('apply-endpoint'))$('apply-endpoint').disabled=true;
  if($('run-judgment'))$('run-judgment').disabled=true;
  const requestedCase=readCase(), mode=$('mode').value, weights=readWeights(),endpointDesign=readEndpointDesign();
  if(mode==='model')state.judgmentParent=null;
  try {
    const result=await api('/api/compare',{case:requestedCase,mode,weights,endpoint_design:endpointDesign,judgment_parent_run:state.judgmentParent});
    state.result=result;state.filter='all';state.reviews=[];
    state.stale=JSON.stringify(requestedCase)!==JSON.stringify(readCase()) || mode!==$('mode').value || JSON.stringify(weights)!==JSON.stringify(readWeights()) || JSON.stringify(endpointDesign)!==JSON.stringify(readEndpointDesign());
    $('stale').hidden=!state.stale;$('export').disabled=state.stale;render();
  } catch(error) { $('error').textContent=error.message;$('error').hidden=false; if(state.result)dirty(); }
  finally { $('busy').hidden=true;$('run').disabled=false;if($('apply-endpoint'))$('apply-endpoint').disabled=false;if($('run-judgment'))$('run-judgment').disabled=false; }
}
function renderJudgments(r,applied=false){
  const panel=el('section',undefined,'model-judgments');panel.append(el('p',`${r.model} · ${r.model_metadata.provider} · actual model response`,'mode-badge'),el('h3',`${r.model_metadata.provider==='vertex'?'Gemini’s':'Model'} evidence judgment`));
  for(const s of r.synthesis)panel.append(cited(s));
  const names=Object.fromEntries(r.options.map(o=>[o.id,o.title]));
  for(const p of r.model_judgments||[]){const box=el('div',undefined,'weight-proposal');box.append(el('strong',`${names[p.option_id]} · ${p.factor_id}: ${p.previous_factor} → ${p.proposed_factor}`),cited({text:p.reason,source_ids:p.source_ids}));panel.append(box);}
  panel.append(el('p',`These are model judgments. Known claim IDs were checked; neither clinical support nor weight magnitude is independently verified. ${applied?'These reviewed suggestions were applied to the Python calculation below.':'Scores are unchanged until you apply the suggestions.'}`,'muted'));
  if(!applied&&r.model_judgments?.length){const b=el('button','Apply model suggestions & recalculate with Python','secondary');b.type='button';b.disabled=state.stale;b.addEventListener('click',applyJudgments);panel.append(b);}
  return panel;
}
async function applyJudgments(){
  if(state.stale||!state.result?.model_judgments?.length)return;
  for(const p of state.result.model_judgments){const input=document.querySelector(`[data-factor-option="${p.option_id}"][data-factor-id="${p.factor_id}"]`);if(input)input.value=p.proposed_factor;}
  state.judgmentParent=state.result.run_id;$('mode').value='curated';dirty();await run();
}
function openReview(o,action) {
  if(state.stale) return;
  state.pendingReview={option_id:o.id,action,run_id:state.result.run_id};
  $('review-title').textContent={select:'Select for clinical discussion',edit:'Propose a change',reject:'Reject this option'}[action];
  $('review-option').textContent=o.title;$('review-comment').value='';$('review-comment').required=action==='edit';$('review-error').hidden=true;$('review-dialog').showModal();
}
async function saveReview(event) {
  event.preventDefault();const button=event.submitter;button.disabled=true;
  try {
    if(state.stale || state.pendingReview.run_id!==state.result.run_id) throw new Error('Case changed; rerun the comparison before reviewing.');
    const payload={...state.pendingReview,comment:$('review-comment').value};const saved=await api('/api/feedback',payload);
    state.reviews.push({...payload,id:saved.id});$('review-dialog').close();render();
    $('toast').textContent='Researcher review saved locally.';$('toast').hidden=false;setTimeout(()=>$('toast').hidden=true,4000);
  } catch(error) {$('review-error').textContent=error.message;$('review-error').hidden=false;}
  finally {button.disabled=false;}
}
function exportResult() {
  if(state.stale||!state.result) return;
  const blob=new Blob([JSON.stringify({...state.result,reviews:state.reviews,experimental_forecast:state.forecastStale?null:state.forecast,forecast_inputs_changed:state.forecastStale},null,2)],{type:'application/json'});
  const url=URL.createObjectURL(blob),a=el('a');a.href=url;a.download=`treatment-review-${state.result.run_id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function loadForecastExample() {
  const key=$('forecast-example').value;
  if(key==='custom') {
    $('forecast-input').value=JSON.stringify({trial:'Specify treatment, comparator and trial endpoint',as_of:state.bootstrap.evidence_as_of,method_a:{prior:null,prior_note:'Supply an independently justified reference class',factors:[]},method_b:{events:null,scenarios:[],bars:[]}},null,2);
    $('forecast-option').value='';
  } else {
    const example=state.bootstrap.forecast_examples[key];$('forecast-input').value=JSON.stringify(example.case,null,2);$('forecast-option').value=example.option_id||'';
  }
  dirtyForecast();
}
function dirtyForecast() {state.forecastStale=true;$('forecast-stale').hidden=!state.forecast;}
function renderForecast(f) {
  const root=$('forecast-result');root.replaceChildren();
  root.append(el('p',f.provenance,'mode-badge'),el('h3',f.target),el('p',f.interpretation,'notice'));
  if(f.as_of_in_future)root.append(el('p','The assumed forecast date is in the future; check the time context.','notice'));
  const metrics=el('div',undefined,'forecast-metrics');
  for(const [key,name] of [['method_a','A · Adjusted odds'],['method_b','B · Effect scenarios'],['combined','Equal-weight average']]) {
    const box=el('div');box.append(el('strong',`${(f[key]*100).toFixed(1)}%`),el('span',name));metrics.append(box);
  }
  root.append(metrics,el('p',`Methods differ by ${(f.method_disagreement*100).toFixed(1)} percentage points. This is not a confidence interval.`,'muted'));
  const a=el('details');a.open=true;a.append(el('summary','Method A · reference-class adjustments'));
  for(const row of f.method_a_steps)a.append(el('p',`${row.name}${row.factor===null?'':` · odds × ${row.factor}`} → ${(row.probability*100).toFixed(1)}%`));root.append(a);
  const b=el('details');b.append(el('summary','Method B · effect-size scenarios'));
  b.append(el('p',`${f.input.method_b.events} assumed events; expected z = −ln(HR) × √events / 2, for 1:1 allocation.`));
  for(const row of f.method_b_scenarios)b.append(el('p',`${row.name} · HR ${row.hr} · z threshold ${row.z_threshold}: ${(row.probability*100).toFixed(1)}% chance of crossing the bar, conditional on this assumed true effect.`));root.append(b);
  const list=el('ul',undefined,'method-note');f.limitations.forEach(s=>list.append(el('li',s)));root.append(list);
  root.append(refs(f.source_ids));
}
async function runForecast(event) {
  event?.preventDefault();$('forecast-error').hidden=true;$('forecast-run').disabled=true;
  const raw=$('forecast-input').value, optionId=$('forecast-option').value;
  try {
    const forecast_case=JSON.parse(raw), result=await api('/api/forecast',{forecast_case,option_id:optionId||null});state.forecast=result;
    state.forecastStale=raw!==$('forecast-input').value||optionId!==$('forecast-option').value;$('forecast-stale').hidden=!state.forecastStale;renderForecast(result);
  } catch(error){$('forecast-error').textContent=error.message;$('forecast-error').hidden=false;dirtyForecast();}
  finally {$('forecast-run').disabled=false;}
}
function initForecast() {
  for(const o of state.bootstrap.option_names){const opt=el('option',o.title);opt.value=o.id;$('forecast-option').append(opt);}
  $('forecast-form').addEventListener('submit',runForecast);$('forecast-example').addEventListener('change',loadForecastExample);
  $('forecast-input').addEventListener('input',dirtyForecast);$('forecast-option').addEventListener('change',dirtyForecast);
  loadForecastExample();
}
async function init() {
  try {
    state.bootstrap=await api('/api/bootstrap');buildForm();setCase(state.bootstrap.default_case);buildWeights();setWeights();renderLibrary();initForecast();
    $('evidence-date').textContent=`U.S. evidence snapshot · ${state.bootstrap.evidence_as_of}`;
    const model=state.bootstrap.model_configured;
    $('mode').querySelector('[value=model]').disabled=!model;
    const modelInfo=state.bootstrap.model_status;
    $('mode').querySelector('[value=model]').textContent=modelInfo?.provider==='vertex'?`Gemini evidence judgment (${modelInfo.model})`:'Model synthesis of curated evidence';
    $('model-status').textContent=model?`${modelInfo.model} configured. ${modelInfo.detail}. Claim-ID checks do not verify clinical support.`:modelInfo?.detail||'Model connection not configured. Curated mode is fully usable without an API key.';
    $('case-form').addEventListener('submit',run);$('case-form').addEventListener('input',()=>{state.judgmentParent=null;dirty();});$('case-form').addEventListener('change',()=>{state.judgmentParent=null;dirty();});
    $('preset').addEventListener('change',()=>{
      const c={...state.bootstrap.default_case};
      if($('preset').value==='unknown') for(const key of ['esr1','pik3ca','akt1','pten','gbrca','her2'])c[key]='unknown';
      if($('preset').value==='later') {c.prior_metastatic_chemo=2;c.additional_metastatic_lines=2;c.esr1='not_detected';c.pik3ca='not_detected';}
      setCase(c);setWeights();state.judgmentParent=null;dirty();
    });
    $('export').addEventListener('click',exportResult);$('cancel-review').addEventListener('click',()=>$('review-dialog').close());$('review-form').addEventListener('submit',saveReview);
    const savedRun=new URLSearchParams(location.search).get('run');
    if(savedRun){
      const saved=await api(`/api/runs/${encodeURIComponent(savedRun)}`);
      state.result=saved;state.reviews=saved.saved_reviews||[];state.bootstrap.sources=saved.sources;setCase(saved.case);setWeights();renderLibrary();
      for(const [key,value] of Object.entries(saved.priority_policy.weights))$(`weight-${key}`).value=value;
      const d=saved.endpoint_design;
      for(const [id,value] of Object.entries({'endpoint-events':d.events,'endpoint-z':d.z_threshold,'endpoint-prior':d.prior??'','endpoint-evidence-strength':d.evidence_strength,'endpoint-blend':d.blend_a}))$(id).value=value;
      $('endpoint-source-effect').checked=d.use_reference_effect;$('mode').value='curated';$('export').disabled=false;render();
    }else await run();
    await runForecast();
  } catch(error) {$('error').textContent=`Could not initialize demo: ${error.message}`;$('error').hidden=false;}
}
init();
