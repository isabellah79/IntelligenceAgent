const {test}=require('node:test');
const assert=require('node:assert/strict');
const C=require('./state.js');
const data={dataset_id:'test-dataset',cases:[{case_id:'treatment',input_id:'portable.json',input_sha256:'a'.repeat(64),populations:[{option_id:'a'},{option_id:'b'}]}]};
function review(){return C.fresh(data,'r1','2026-10-30T00:00:00Z');}
function fill(state,id,value){for(const d of C.DIMENSIONS)C.grade(state,id,d,value,'2026-10-30T01:00:00Z');}
test('zero ratings are real completed grades, not missing values',()=>{
 const state=review();fill(state,'a',0);
 assert.equal(C.summary(state).independent,1);
 assert.equal(C.score(state.populations.a,{evidence_strength:.35,population_applicability:.25,selection_justification:.25,tradeoffs:.15}),0);
 assert.equal(C.calibration(state,data)[0].scientific_grades.tradeoffs,0);
});
test('incomplete and unable-to-assess feedback cannot enter numeric calibration',()=>{
 const state=review();fill(state,'a',2);C.grade(state,'a','tradeoffs','unable','later');
 assert.equal(C.summary(state).reviewed,1);
 assert.equal(C.summary(state).numeric,0);
 assert.deepEqual(C.calibration(state,data),[]);
});
test('revealing AI before grading makes subsequent ratings assisted',()=>{
 const state=review();C.reveal(state,'a','before');fill(state,'a',4);
 assert.equal(C.complete(state.populations.a),true);
 assert.deepEqual(C.calibration(state,data),[]);
});
test('independent snapshot stays intact after AI exposure and assisted edits',()=>{
 const state=review();fill(state,'a',2);C.note(state,'a','notes','Independent reasoning','before');
 C.reveal(state,'a','reveal');C.grade(state,'a','evidence_strength',4,'after');C.note(state,'a','notes','Assisted reasoning','after');
 const item=C.calibration(state,data)[0];
 assert.equal(item.scientific_grades.evidence_strength,2);
 assert.equal(item.notes,'Independent reasoning');
 assert.equal(state.populations.a.scientific_grades.evidence_strength,4);
 assert.equal(item.ai_viewed_after_snapshot,true);
});
test('pre-AI edits refresh the independent snapshot',()=>{
 const state=review();fill(state,'a',2);C.grade(state,'a','evidence_strength',3,'later');
 assert.equal(C.calibration(state,data)[0].scientific_grades.evidence_strength,3);
});
test('exposure to one population does not contaminate a different independent review',()=>{
 const state=review();C.reveal(state,'a','earlier');fill(state,'b',3);
 assert.deepEqual(C.calibration(state,data).map(x=>x.option_id),['b']);
});
test('ratings survive a save/import round trip with exposure history',()=>{
 const state=review();fill(state,'a',3);C.reveal(state,'a','viewed');
 const restored=C.restore(JSON.parse(JSON.stringify({review:state})),data);
 assert.equal(restored.populations.a.ai_viewed_at,'viewed');
 assert.equal(C.calibration(restored,data).length,1);
});
test('import cannot cross dataset identities or invent populations',()=>{
 const state=review();state.dataset_id='different';assert.throws(()=>C.restore(state,data));
 const other=review();other.populations.fake=other.populations.a;assert.throws(()=>C.restore(other,data));
});
test('invalid numeric grades and Boolean grades are rejected',()=>{
 for(const n of [true,1.5,5,-1,NaN])assert.throws(()=>C.grade(review(),'a','evidence_strength',n,'now'));
});
test('script serialization cannot terminate the data script',()=>{
 const text=C.scriptJSON({notes:'</script><img src=x onerror=alert(1)>'});
 assert.equal(text.includes('</script>'),false);
 assert.equal(JSON.parse(text).notes,'</script><img src=x onerror=alert(1)>');
});
test('portable calibration output includes a full content hash and no host path',()=>{
 const state=review();fill(state,'a',4);
 const item=C.calibration(state,data)[0];
 assert.equal(item.input_sha256,'a'.repeat(64));
 assert.equal(item.file,'portable.json');
 assert.equal(JSON.stringify(item).includes('/Users/'),false);
});
