'use strict';
const $=id=>document.getElementById(id);
const state={bootstrap:null,result:null,stale:false,busy:false,reviews:[],pending:null,forecast:null,forecastStale:true};
const kindNames={reference:'Reference-supported starting point',exploratory:'Exploratory evidence',hypothesis:'Untested population hypothesis',broader:'Broader research population',alternative:'Alternative regimen'};
const purposeNames={scope:'Parent population',efficacy:'Efficacy selection',evidence_alignment:'Evidence alignment',safety:'Safety',design:'Protocol design',generalizability:'Generalizability'};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function references(ids){const span=el('span',undefined,'references');for(const id of [...new Set(ids)]){const s=(state.result?.sources||state.bootstrap.population_sources)[id];if(!s)continue;const a=el('a',`[${id}]`);a.href=s.url;a.title=s.title;a.target='_blank';a.rel='noopener noreferrer';span.append(a,document.createTextNode(' '));}return span;}
function cited(row,tag='p'){const n=el(tag,row.text+' ');n.append(references(row.source_ids));return n;}
function statementList(rows){const ul=el('ul');rows.forEach(r=>ul.append(cited(r,'li')));return ul;}
function button(text,fn,cls='secondary'){const b=el('button',text,cls);b.type='button';b.addEventListener('click',fn);return b;}
function focused(){return state.result.treatments.find(t=>t.id===state.result.focus_treatment_id);}
function dirty(){if(!state.result)return;state.stale=true;$('stale').hidden=false;document.querySelectorAll('.review-action,.apply-model,#export').forEach(b=>b.disabled=true);}
async function api(path,payload){const r=await fetch(path,payload?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}:{});const value=await r.json();if(!r.ok)throw new Error(value.error||'Request failed');return value;}
function setDesign(d){for(const [id,k] of [['events','events'],['z','z_threshold'],['prior','prior'],['strength','evidence_strength'],['blend','blend_a']])$(id).value=d[k]??'';$('reference-effect').checked=d.use_reference_effect;$('extrapolation').checked=d.allow_extrapolation;}
function readDesign(){
  const d=structuredClone(state.result?.design||state.bootstrap.population_design);
  Object.assign(d,{events:Number($('events').value),z_threshold:Number($('z').value),prior:$('prior').value===''?null:Number($('prior').value),evidence_strength:Number($('strength').value),blend_a:Number($('blend').value),use_reference_effect:$('reference-effect').checked,allow_extrapolation:$('extrapolation').checked});
  for(const input of document.querySelectorAll('[data-effect-population]')){const pid=input.dataset.effectPopulation,comp=document.querySelector(`[data-comparator-population="${pid}"]`);if(input.value==='')delete d.effect_overrides[pid];else d.effect_overrides[pid]={hr:Number(input.value),comparator:comp.value};}
  for(const input of document.querySelectorAll('[data-factor-population]')){const pid=input.dataset.factorPopulation;d.factor_overrides[pid]??={};d.factor_overrides[pid][input.dataset.factorId]=Number(input.value);}
  return d;
}
function requestFields(){return {context:{...state.bootstrap.population_context,objective:$('objective').value},design:readDesign(),focus_treatment_id:$('treatment').value};}
async function run(mode='curated',parent=null){
  if(state.busy)return;
  const request=requestFields(),signature=JSON.stringify(request);state.busy=true;$('error').hidden=true;$('busy').hidden=false;
  $('busy').textContent=mode==='model'?'Gemini is reviewing the candidate populations, criteria and evidence…':'Building population proposals and recalculating explicit scenarios…';
  $('build').disabled=true;$('gemini').disabled=true;document.querySelectorAll('.review-action,.apply-model,#export').forEach(b=>b.disabled=true);
  try{
    const result=await api('/api/populations',{...request,mode,judgment_parent_run:parent});
    const changed=signature!==JSON.stringify(requestFields());state.result=result;state.reviews=[];state.stale=changed;render();
  }catch(e){$('error').textContent=e.message;$('error').hidden=false;dirty();}
  finally{state.busy=false;$('busy').hidden=true;$('build').disabled=false;$('gemini').disabled=!state.bootstrap.model_status.configured;}
}
function render(){
  const r=state.result,t=focused(),root=$('result');root.replaceChildren();$('stale').hidden=!state.stale;
  for(const treatment of r.treatments){const o=document.querySelector(`#treatment option[value="${treatment.id}"]`);if(o)o.textContent=treatment.title;}
  const bar=el('div',undefined,'result-heading'),heading=el('div');heading.append(el('p',t.family+' · '+t.route,'eyebrow'),el('h2',t.title),references(t.source_ids));
  const actions=el('div',undefined,'actions'),exportButton=button('Export population review ↓',exportResult);exportButton.id='export';exportButton.disabled=state.stale;
  const saved=el('a','Reopen saved review','saved-link');saved.href=`?run=${encodeURIComponent(r.run_id)}#result`;actions.append(exportButton,saved);bar.append(heading,actions);root.append(bar);
  root.append(el('p',r.recommendation_policy,'method-note'));
  const count=el('p',`${r.treatments.length} treatments · ${r.treatments.reduce((n,x)=>n+x.populations.length,0)} candidate populations · 3 alternatives shown below · evidence ${r.evidence_as_of}`,'muted');root.append(count);
  if(r.model_review)root.append(renderModelReview(r));
  const wrap=el('div',undefined,'table-wrap');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label','Candidate populations and evidence');
  const table=el('table',undefined,'population-table');table.append(el('caption','Candidate populations for this treatment. Compare the scientific rationale and trade-offs before inspecting the criteria drafts.'));
  const head=el('thead'),hr=el('tr');for(const text of ['Candidate population','Evidence of benefit','Pros / cons','Conditional PFS scenario']){const th=el('th',text);th.scope='col';hr.append(th);}head.append(hr);table.append(head);
  const body=el('tbody');
  for(const p of t.populations){
    const row=el('tr');row.dataset.populationId=p.id;
    const name=el('th');name.scope='row';name.append(el('span',kindNames[p.kind],'badge '+p.kind),el('h3',p.title),references(p.source_ids),el('p',`Axis: ${p.axis}`,'muted'));
    const jump=el('a','Inspect inclusion / exclusion criteria ↓');jump.href=`#criteria-${p.id}`;name.append(jump);
    const evidence=el('td');evidence.append(cited(p.benefit_statement));
    if(p.effect){evidence.append(el('p',`${p.effect.trial}${p.effect.hazard_ratio===null?' · Comparative HR not populated':` · published HR ${p.effect.hazard_ratio}`} vs ${p.effect.comparator}.`));if(p.effect.median_pfs_months)evidence.append(el('p',`Median PFS ${p.effect.median_pfs_months[0]} vs ${p.effect.median_pfs_months[1]} months.`));evidence.append(el('p',`Reference population: ${p.effect.population}`,'muted'));}
    evidence.append(el('p',p.transfer==='unestablished'?'No comparative effect transfer is established for this proposal.':p.transfer==='direct'?'Reference setting is relevant; final protocol details remain to be confirmed.':`Source-to-target difference: ${p.transfer.replaceAll('_',' ')}. Extrapolation is explicit.`,'muted'));
    const tradeoffs=el('td');tradeoffs.append(el('strong','Pros','section-label'),statementList(p.pros),el('strong','Cons / uncertainty','section-label'),statementList(p.cons));if(p.scope_note)tradeoffs.append(el('p',p.scope_note,'note'));
    row.append(name,evidence,tradeoffs,renderForecastCell(p));body.append(row);
  }
  table.append(body);wrap.append(table);root.append(el('p','On narrow screens, scroll this table sideways. Full criteria drafts appear immediately below.','scroll-hint'),wrap);
  root.append(el('h2','Candidate inclusion and exclusion criteria','criteria-heading'),el('p','Each criterion records its purpose, rationale and evidence status. These cohort-defining drafts include unresolved protocol items for scientific and clinical review.','muted'));
  for(const [index,p] of t.populations.entries())root.append(renderCriteria(p,index));
  root.append(renderOverview(r));
  const limits=el('details',undefined,'limitations');limits.append(el('summary','Scope and interpretation'),...r.limitations.map(s=>el('p',s,'muted')));root.append(limits);
  renderLibrary();
}
function renderForecastCell(p){
  const cell=el('td'),f=p.forecast;
  if(f.score===null)cell.append(el('strong','Not estimated','no-score'),el('p',f.unavailable_reason,'muted'));
  else{cell.append(el('strong',`${(f.score*100).toFixed(1)}%`,'score'),el('p',f.score_type,'muted'),el('p',f.effect_origin,'muted'));const details=el('details');details.append(el('summary','Calculation'),el('p',`Assumed true HR ${f.assumed_hr} vs ${f.comparator}; ${state.result.design.events} events; z threshold ${state.result.design.z_threshold}.`),el('p',`B conditional power: ${(f.method_b*100).toFixed(1)}%.${f.method_a===null?'':` A adjusted prior: ${(f.method_a*100).toFixed(1)}%.`}`),el('p',f.interpretation));cell.append(details);}
  const assumptions=el('details',undefined,'local-assumptions');assumptions.append(el('summary','Population-specific effect & weights'));
  const label=el('label','Hypothetical true HR · analyst assumption'),input=el('input');input.type='number';input.min='.05';input.max='5';input.step='.01';input.placeholder='No override';input.dataset.effectPopulation=p.id;input.value=state.result.design.effect_overrides[p.id]?.hr??'';input.setAttribute('aria-label',`${p.title}: hypothetical HR`);input.addEventListener('input',dirty);label.append(input);assumptions.append(label);
  const compLabel=el('label','Comparator for the hypothetical effect'),comp=el('input');comp.type='text';comp.maxLength=300;comp.dataset.comparatorPopulation=p.id;comp.value=state.result.design.effect_overrides[p.id]?.comparator||p.effect?.comparator||'';comp.placeholder='Specify comparator';comp.setAttribute('aria-label',`${p.title}: hypothetical comparator`);comp.addEventListener('input',dirty);compLabel.append(comp);assumptions.append(compLabel);
  assumptions.append(el('p','An entered HR is your scenario assumption, not a new clinical finding. Rebuild to calculate.','muted'));
  for(const factor of f.factors){const lab=el('label',factor.finding+' · odds multiplier'),n=el('input');n.type='number';n.min='.25';n.max='4';n.step='.01';n.value=factor.factor;n.dataset.factorPopulation=p.id;n.dataset.factorId=factor.id;n.setAttribute('aria-label',`${p.title}: ${factor.id.split('.').at(-1)} multiplier`);n.addEventListener('input',dirty);lab.append(n);assumptions.append(lab,references(factor.source_ids),el('p',`${factor.weight_provenance} Effective multiplier: ${factor.effective_factor.toFixed(3)}.`,'muted'));}
  cell.append(assumptions);return cell;
}
function renderCriteria(p,index){
  const details=el('details',undefined,'criteria-card');details.id=`criteria-${p.id}`;details.open=index===0;
  const summary=el('summary');summary.append(el('span',`0${index+1}`,'step'),el('span',p.title),el('span',kindNames[p.kind],'badge '+p.kind));details.append(summary);
  const body=el('div',undefined,'criteria-body');body.append(el('p',p.regimen,'regimen'),references(p.source_ids));
  const columns=el('div',undefined,'criteria-columns');
  for(const [key,title] of [['inclusion','Include'],['exclusion','Exclude / adjudicate']]){const column=el('section');column.append(el('h3',title));const list=el('ol');for(const c of p[key]){const item=el('li');item.dataset.criterionId=c.id;item.append(el('span',`${purposeNames[c.purpose]} · ${c.status.replaceAll('_',' ')}`,'criterion-purpose'),cited(c),el('p',c.reason,'criterion-reason'));list.append(item);}column.append(list);columns.append(column);}
  body.append(columns,el('h3','Protocol details to finalize'),statementList(p.protocol_pending));
  const actions=el('div',undefined,'actions');for(const [action,text] of [['select','Select for protocol discussion'],['edit','Propose criteria revision'],['reject','Reject this population']]){const b=button(text,()=>openReview(p,action));b.classList.add('review-action');b.disabled=state.stale;actions.append(b);}body.append(actions);
  for(const review of state.reviews.filter(r=>r.population_id===p.id)){const note=el('div',undefined,'researcher-note');note.append(el('strong',`Researcher review: ${review.action}`));if(review.comment)note.append(el('p',review.comment));body.append(note);}
  details.append(body);return details;
}
function renderModelReview(r){
  const review=r.model_review,t=focused(),panel=el('details',undefined,'model-review');panel.open=true;
  panel.append(el('summary','Gemini’s population-design review'),el('p',`${r.model_metadata.model} · actual ${r.model_metadata.provider} response`,'eyebrow'));
  if(r.parent_model_judgment_run_id)panel.append(el('p',`Python applied ${r.applied_model_weights.length} reviewed weight suggestions. Original review: ${r.parent_model_judgment_run_id}.`,'note'));
  for(const s of review.synthesis)panel.append(cited(s));
  const chosen=t.populations.find(p=>p.id===review.recommendation.population_id),rec=el('div',undefined,'recommendation');rec.append(el('strong','Suggested starting draft: '+chosen.title),cited({text:review.recommendation.reason,source_ids:review.recommendation.source_ids}));panel.append(rec);
  for(const proposal of review.criterion_proposals){const p=t.populations.find(p=>p.id===proposal.population_id),box=el('div',undefined,'model-proposal');box.append(el('strong',`${p.title} · ${proposal.action} criterion`));const before=[...p.inclusion,...p.exclusion].find(c=>c.id===proposal.criterion_id);box.append(el('p','Current: '+before.text));if(proposal.replacement_text)box.append(el('p','Proposed: '+proposal.replacement_text));box.append(cited({text:proposal.reason,source_ids:proposal.source_ids}));const b=button('Record a criteria revision for review',()=>openReview(p,'edit',`Criterion: ${before.text}\nProposed ${proposal.action}: ${proposal.replacement_text||'Remove this criterion'}\nModel rationale: ${proposal.reason}`));b.classList.add('review-action');b.disabled=state.stale;box.append(b);panel.append(box);}
  for(const proposal of review.weight_proposals){const p=t.populations.find(p=>p.id===proposal.population_id);panel.append(el('strong',`${p.title} · ${proposal.factor_id.split('.').at(-1)}: ${proposal.previous_factor} → ${proposal.proposed_factor}`),cited({text:proposal.reason,source_ids:proposal.source_ids}));}
  panel.append(el('p',review.verification+' Criteria changes remain proposed amendments; weight changes require an explicit recalculation.','muted'));
  if(review.weight_proposals.length&&!r.parent_model_judgment_run_id){const b=button('Apply reviewed weights & recalculate with Python',applyWeights);b.classList.add('apply-model');b.disabled=state.stale;panel.append(b);}
  return panel;
}
async function applyWeights(){if(state.stale||!state.result?.model_review||state.busy)return;const parent=state.result.run_id;for(const p of state.result.model_review.weight_proposals){const n=document.querySelector(`[data-factor-id="${p.factor_id}"]`);if(n)n.value=p.proposed_factor;}await run('curated',parent);}
function renderOverview(r){
  const details=el('details',undefined,'overview');details.append(el('summary',`All ${r.treatments.length} treatments and their candidate populations`));const wrap=el('div',undefined,'table-wrap'),table=el('table',undefined,'overview-table'),head=el('thead'),row=el('tr');for(const text of ['Treatment & references','Reference starting population','Alternatives to investigate'])row.append(el('th',text));head.append(row);table.append(head);const body=el('tbody');
  for(const t of r.treatments){const tr=el('tr'),name=el('td');const b=button(t.title,async()=>{$('treatment').value=t.id;await run();});name.append(b,references(t.source_ids));const base=el('td',t.populations[0].title),alternatives=el('td');for(const p of t.populations.slice(1))alternatives.append(el('p',p.title),el('small',kindNames[p.kind]));tr.append(name,base,alternatives);body.append(tr);}table.append(body);wrap.append(table);details.append(wrap);return details;
}
function renderLibrary(){const root=$('library');root.replaceChildren();for(const s of Object.values(state.result?.sources||state.bootstrap.population_sources)){const row=el('div',undefined,'source-entry');row.id=`source-${s.id}`;const a=el('a',s.title+' ↗');a.href=s.url;a.target='_blank';a.rel='noopener noreferrer';row.append(el('strong',s.id),a,el('p',s.scope),el('small',`${s.kind} · Checked ${s.checked_on} · Clinical review pending`));root.append(row);}}
function openReview(p,action,comment=''){if(state.stale||state.busy)return;state.pending={run_id:state.result.run_id,population_id:p.id,action};$('review-title').textContent={select:'Select a population for discussion',edit:'Propose a criteria revision',reject:'Reject a candidate population'}[action];$('review-population').textContent=p.regimen+' · '+p.title;$('review-comment').value=comment;$('review-comment').required=action==='edit';$('review-error').hidden=true;$('review-dialog').showModal();}
async function saveReview(event){event.preventDefault();if(state.stale||state.pending.run_id!==state.result.run_id)return;$('save-review').disabled=true;try{const row=await api('/api/population-feedback',{...state.pending,comment:$('review-comment').value});state.reviews.push(row);$('review-dialog').close();render();}catch(e){$('review-error').textContent=e.message;$('review-error').hidden=false;}finally{$('save-review').disabled=false;}}
function exportResult(){if(state.stale||!state.result)return;const output={...state.result,reviews:state.reviews,worked_forecast:state.forecastStale?null:state.forecast};const url=URL.createObjectURL(new Blob([JSON.stringify(output,null,2)],{type:'application/json'})),a=el('a');a.href=url;a.download=`population-design-${state.result.run_id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function loadExample(){const key=$('forecast-example').value;$('forecast-input').value=JSON.stringify(state.bootstrap.forecast_examples[key].case,null,2);state.forecastStale=true;$('forecast-result').replaceChildren(el('p','Calculate these assumptions to view the worked example.','muted'));}
async function runForecast(event){event.preventDefault();$('forecast-run').disabled=true;$('forecast-error').hidden=true;try{const text=$('forecast-input').value,key=$('forecast-example').value,example=state.bootstrap.forecast_examples[key],r=await api('/api/forecast',{forecast_case:JSON.parse(text),option_id:example.option_id});state.forecast=r;state.forecastStale=text!==$('forecast-input').value;const root=$('forecast-result');root.replaceChildren(el('p',r.provenance,'badge'),el('h3',r.target),el('p',r.interpretation,'note'));for(const [k,title] of [['method_a','A · Adjusted odds'],['method_b','B · Effect scenarios'],['combined','Equal-weight average']])root.append(el('p',`${title}: ${(r[k]*100).toFixed(1)}%`));root.append(statementList(r.limitations.map(text=>({text,source_ids:[]}))));}catch(e){$('forecast-error').textContent=e.message;$('forecast-error').hidden=false;state.forecastStale=true;}finally{$('forecast-run').disabled=false;}}
async function init(){
  try{
    state.bootstrap=await api('/api/bootstrap');
    for(const t of state.bootstrap.option_names){const o=el('option',t.title);o.value=t.id;$('treatment').append(o);}
    setDesign(state.bootstrap.population_design);$('evidence-date').textContent=`U.S. evidence snapshot · ${state.bootstrap.evidence_as_of}`;
    const model=state.bootstrap.model_status;$('gemini').disabled=!model.configured;$('model-status').textContent=model.configured?`${model.model} · ${model.provider==='vertex'?'Vertex AI':'Anthropic'}. An explicit Gemini review sends the selected treatment’s three population drafts and cited evidence to the provider.`:model.detail;
    $('design-form').addEventListener('submit',e=>{e.preventDefault();run();});$('gemini').addEventListener('click',()=>run('model'));
    $('treatment').addEventListener('change',()=>run());$('objective').addEventListener('change',dirty);
    document.querySelector('.assumptions').addEventListener('input',dirty);document.querySelector('.assumptions').addEventListener('change',dirty);
    $('reset-design').addEventListener('click',()=>{setDesign(state.bootstrap.population_design);if(state.result)state.result.design=structuredClone(state.bootstrap.population_design);document.querySelectorAll('[data-effect-population]').forEach(n=>n.value='');document.querySelectorAll('[data-factor-id]').forEach(n=>{const p=focused().populations.find(p=>p.id===n.dataset.factorPopulation);n.value=p.forecast.factors.find(f=>f.id===n.dataset.factorId).default_factor;});run();});
    $('review-form').addEventListener('submit',saveReview);$('cancel-review').addEventListener('click',()=>$('review-dialog').close());
    for(const [id,example] of Object.entries(state.bootstrap.forecast_examples)){const o=el('option',example.title);o.value=id;$('forecast-example').append(o);}
    $('forecast-example').addEventListener('change',loadExample);$('forecast-input').addEventListener('input',()=>{state.forecastStale=true;$('forecast-result').replaceChildren(el('p','Inputs changed. Recalculate this worked example.','muted'));});$('forecast-form').addEventListener('submit',runForecast);loadExample();
    const savedId=new URLSearchParams(location.search).get('run');
    if(savedId){const r=await api(`/api/runs/${encodeURIComponent(savedId)}`);if(r.task!=='population_design'){const box=$('result');box.replaceChildren(el('h2','Saved review from the earlier individual-case demo'),el('p','This record retains its original task and evidence. Open it in the archived comparison view, or start the population-design workspace.'));const old=el('a','Open original saved comparison');old.href=`/legacy.html?run=${encodeURIComponent(savedId)}#result`;const fresh=el('a','Start population design');fresh.href='/';box.append(old,el('p'),fresh);return;}state.result=r;state.reviews=r.saved_reviews||[];setDesign(r.design);$('treatment').value=r.focus_treatment_id;$('objective').value=r.context.objective;render();}
    else await run();
  }catch(e){$('error').textContent='Could not initialize population design: '+e.message;$('error').hidden=false;}
}
init();
