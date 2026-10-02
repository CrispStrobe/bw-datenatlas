'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.join(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'docs/data/survey-items.json'),'utf8'));
const code=fs.readFileSync(path.join(root,'docs/assets/app.js'),'utf8');
const seen=new Set();
const element=()=>({innerHTML:'',textContent:'',options:[{}],addEventListener(){}});
const elements=new Map(['survey-blocks','survey-select','survey-note','survey-warning','survey-enlarge'].map(key=>[key,element()]));
const context=vm.createContext({Intl,Set,Map,window:{ATLAS_SURVEY_ITEMS:data},
 pf:new Intl.NumberFormat('de-DE',{minimumFractionDigits:1,maximumFractionDigits:2}),
 t:s=>{if(s)seen.add(s);return s;},tf:(s,...values)=>{seen.add(s);return s.replace(/\{(\d+)\}/g,(_,n)=>values[n]);},
 integer:n=>new Intl.NumberFormat('de-DE').format(n),pct:n=>n.toFixed(1).replace('.',',')+' %',
 esc:s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;'),
 $:id=>elements.get(id),
 table:(heads,rows)=>'<table><thead>'+heads.map(s=>'<th>'+s+'</th>').join('')+'</thead><tbody>'+rows.map(row=>'<tr>'+row.map(s=>'<td>'+s+'</td>').join('')+'</tr>').join('')+'</tbody></table>'});
vm.runInContext(code.slice(code.indexOf('const surveySeriesColors='),code.indexOf('function renderPublishedAges()')),context);
function render(id){elements.get('survey-select').value=String(data.blocks.findIndex(b=>b.block===id));context.renderSurveyItems();return elements.get('survey-blocks').innerHTML;}
const get=id=>data.blocks.find(b=>b.block===id);
test('every thematic collection renders all sources without invalid values',()=>{
 for(const topic of data.topics)for(const id of topic.blocks){
  const html=render(id);assert.ok(html.length>100,id);assert.ok(!/NaN|undefined/.test(html),id);
  assert.equal((html.match(/class="compact-details survey-evidence"/g)||[]).length,1,id);
 }
});
test('political trust compares years in compact matrices and keeps methods after charts',()=>{
 const html=render('svr2026_politisches_vertrauen');
 assert.equal((html.match(/class="survey-matrix"/g)||[]).length,2);
 assert.ok(html.includes('2020')&&html.includes('2022')&&html.includes('2024'));
 assert.ok(html.indexOf('survey-evidence')>html.lastIndexOf('survey-matrix'));
 assert.equal(context.surveySources(get('svr2026_politisches_vertrauen'),data).flatMap(b=>b.items).length,20);
 assert.ok(html.includes('rgba(149,90,54,')&&html.includes('rgba(33,107,122,'));
 const q=context.surveyQuestions(get('nadira2025_politisches_vertrauen'),data);
 assert.ok(q.includes('<p>Vertrauen in die Bundesregierung'));assert.ok(!q.includes('„Vertrauen in die Bundesregierung'));
});
test('0–10 means retain their scale and licensed source attribution',()=>{
 const html=context.surveyBars(get('demmrich2025_institutionenvertrauen'),data);
 assert.ok(!html.includes('%'));assert.ok(html.includes('5,76')&&html.includes('5,69'));
 const alpha=Number(html.match(/rgba\(33,107,122,([^)]*)\)/)[1]);assert.ok(alpha>.30&&alpha<.34);
 const combined=render('rias2026_muslim_antisemitismus');
 assert.equal((combined.match(/href="https:\/\/creativecommons.org\/licenses\/by\/4.0\/"/g)||[]).length,1);
 assert.ok(combined.includes('Sarah Demmrich')&&combined.includes('p = 0,56'));
 assert.ok(combined.includes('34,8 %')&&combined.includes('712'),'bundled sources retain response levels and sample sizes in the evidence table');
});
test('bundled contacts preserve every earlier result and one shared legend per distribution',()=>{
 const sources=context.surveySources(get('fgz2023_network_religion'),data).map(b=>b.block);
 for(const id of ['rm2015_freizeit_nichtmuslime','rm2017_europa_kontakte','fgz2025_trust_region','fgz2025_trust_migration'])assert.ok(sources.includes(id));
 const chart=context.surveyBars({...get('rias2026_muslim_antisemitismus'),chart:get('rias2026_muslim_antisemitismus').chart.main_chart},data);
 assert.equal((chart.match(/class="survey-key survey-shared-key"/g)||[]).length,1);
});
test.after(()=>{
 if(process.env.ATLAS_STRING_OUTPUT){
 for(const topic of data.topics){seen.add(topic.title);for(const id of topic.blocks)seen.add(get(id).chart?.title||get(id).title);}
 fs.writeFileSync(process.env.ATLAS_STRING_OUTPUT,JSON.stringify([...seen].sort(),null,2)+'\n');
 }
});
