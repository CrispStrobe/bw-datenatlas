'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const root=path.join(__dirname,'..');
const data=JSON.parse(fs.readFileSync(path.join(root,'docs/data/institutions.json'),'utf8'));
const code=fs.readFileSync(path.join(root,'docs/assets/app.js'),'utf8');
const select={dataset:{},html:'',insertAdjacentHTML(_where,html){this.html+=html;}};
const state={onlyLandtag:true,instOrganisation:'',instSource:''};
const context=vm.createContext({URL,Set,Map,state,INST:data,
 $:id=>id==='filter-organisation'?select:null,esc:s=>String(s)});
vm.runInContext(code.slice(code.indexOf('const SECURITY_LANDTAG_DOCUMENTS='),code.indexOf('function refreshInstitutionFilter()')),context);
test('security filter excludes regular Ahmadiyya lists while retaining documented contexts',()=>{
 const ahmadiyya=data.institutions.filter(i=>i.organisation==='Ahmadiyya Muslim Jamaat');
 assert.equal(ahmadiyya.length,29);
 assert.equal(ahmadiyya.filter(i=>i.affiliation_restated_url).length,18);
 assert.ok(ahmadiyya.every(i=>!context.matchesInstitutionFilter(i)));
 const selected=context.institutionsShown();assert.equal(selected.length,55);
 for(const {inst,idx} of selected)assert.equal(data.institutions[idx],inst);
 assert.equal(selected.filter(({inst})=>inst.organisation==='Verbandszugehörigkeit nicht belegt').length,10);
 assert.ok(!context.namedInSecurityLandtagPaper({affiliation_source_url:'https://example.org/16_1462_D.pdf'}));
 assert.ok(!context.namedInSecurityLandtagPaper({affiliation_source_url:'not a URL'}));
});
test('canonical dropdown has one option per federation and retains all institutions',()=>{
 state.onlyLandtag=false;
 assert.equal(context.institutionsShown().length,555);
 context.fillOrganisationFilter();
 assert.equal((select.html.match(/<option /g)||[]).length,11);
 for(const [org,n] of [['Verbandszugehörigkeit nicht belegt',62],['Alevitische Gemeinde Deutschland',40],['Islamische Gemeinschaft Millî Görüş (IGMG)',64],['Türkisch-Demokratische Idealistenvereine (ADÜTDF)',31]]){
  assert.ok(select.html.includes(org+' ('+n+')'));
  state.instOrganisation=org;assert.equal(context.institutionsShown().length,n);
 }
 const before=select.html;context.fillOrganisationFilter();assert.equal(select.html,before);
});
