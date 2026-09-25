(function () {
'use strict';
const D=window.ATLAS_DATA, G=window.ATLAS_GEOMETRY, M=window.AtlasModel;
const EST=window.ATLAS_ESTIMATE||null;
const CTX=window.ATLAS_CONTEXT||null;
const AGE=window.ATLAS_AGE||null;
const GEN=window.ATLAS_GENERATIONS||null;
const NAT=window.ATLAS_NATIONALITIES||null;
const BOUND=window.ATLAS_BOUND||null;
const TS=window.ATLAS_TIMESERIES||null;
const BASES=window.ATLAS_BASES||null;
const DEM=window.ATLAS_DEMOGRAPHY||null;
const INST=window.ATLAS_INSTITUTIONS||null;
// One colour per source of the entry. OpenStreetMap is deliberately a separate colour:
// those points come from a community map, not from the organisation itself.
const INST_COLOURS=[['Alevitische','#236a7b'],['LBE-BW','#a8743a'],['DITIB','#8a4b6d'],['OpenStreetMap','#5f7a4a'],['Unabhängig','#8c5a2b'],['Einzeln belegt','#7a6a58']];
// A link is named after the site it leads to — "murrhardt", "dasoertliche", "mapcarta" —
// which tells a reader more at a glance than a description of the source's category.
function siteName(url){
 try{
  const host=new URL(url).hostname.replace(/^(www|m|de|en)\./,'');
  const parts=host.split('.');
  const second=['co','com','org','net','gov'].includes(parts[parts.length-2]||'')?3:2;
  return parts.slice(Math.max(0,parts.length-second))[0]||host;
 }catch(e){return 'Quelle';}
}
function instColour(org){for(const [k,c] of INST_COLOURS)if(org.startsWith(k))return c;return '#6b7280';}
const $=id=>document.getElementById(id);
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const nf=new Intl.NumberFormat('de-DE',{maximumFractionDigits:0});
const precise=new Intl.NumberFormat('de-DE',{maximumFractionDigits:8});
const number=v=>v===null||v===undefined?'Nicht verfügbar':precise.format(v);
const pf=new Intl.NumberFormat('de-DE',{minimumFractionDigits:1,maximumFractionDigits:1});
const integer=v=>v===null||v===undefined?'Nicht verfügbar':nf.format(v);
const pct=v=>v===null||v===undefined?'Nicht verfügbar':pf.format(v)+' %';
const approx=v=>'≈ '+nf.format(Math.round(v/1000)*1000);
const state={layer:'district_population',selected:{type:'state',id:'08'},variant:'migration_background',origin:'de_origins',allOrigins:false,areaPage:0,researchPage:0,researchRows:null,onlyLandtag:false,azrIndicator:'turkey',flowArea:'countries',compositionDetail:false,flowRange:'years',instOrganisation:'',instSource:'',zoom:{x:0,y:0,w:760,h:700}};
const districts=new Map(D.districts.map(r=>[r.id,r]));
const municipalities=new Map(D.municipalities.map(r=>[r.geo_id,r]));
const palette=['#deedf0','#b5d8dd','#83b9c4','#4d929f','#236a7b','#113f55'];
const warmPalette=['#f6ebd5','#e8d1a5','#d1ae6b','#b38641','#91602d','#65421f'];
const regionColors={'Türkei':'#12596b','Naher Osten':'#358597','Südosteuropa':'#6587a2','SO-Europa':'#6587a2','Mittlerer Osten':'#81759c','Nordafrika':'#b49b65'};
// D.sources stammt aus der Forschungssammlung und kennt nur deren Quellen. Ebenen aus
// später hinzugekommenen Datensätzen bringen ihre Quelle selbst mit; ohne diesen Ausweg
// wirft der SVG-Export auf ihnen, weil er D.sources[l.source] ohne Prüfung liest.
const AZR_SOURCE={title:'Migration, Integration, Regionen — Ausländerzentralregister je Kreis',publisher:'Statistisches Bundesamt (Destatis)',publication_period:'2026',url:'https://service.destatis.de/DE/karten/migration_integration_regionen.html',limitation:'Anteile beziehen sich auf die ausländische Bevölkerung des Kreises, nicht auf seine Einwohner. Staatsangehörigkeit ist keine Religionszugehörigkeit.'};
function sourceFor(layer){return D.sources[layer.source]||layer.sourceInfo||AZR_SOURCE;}
const layers={
 religion_state:{title:'Muslimische Bevölkerung · Landeswert',badge:'Veröffentlichte Modellspanne',date:'Bezugsjahr 2025 · veröffentlicht 2026',source:'bamf_fb55',note:'Die einheitliche Landesfläche bedeutet nicht, dass jeder Kreis denselben Muslimanteil hat. Für Kreise und Gemeinden fehlen entsprechende Quellendaten.'},

 municipal_foreign_share:{title:'Ausländische Staatsangehörige · Gemeindeanteil',badge:'Amtliche Bevölkerungsdaten',date:'2025 · 1.101 Gemeinden',source:'stala_gemeinden_2024_06',sourceInfo:{title:'Anteil Ausländerinnen und Ausländer je Gemeinde 2025',publisher:'Statistisches Landesamt Baden-Württemberg',publication_period:'2026',url:'https://www.statistik-bw.de/leben-und-arbeiten/bevoelkerung-und-gebiet/migration-und-nationalitaet/',limitation:'Staatsangehörigkeit ist keine Religionszugehörigkeit und keine Herkunft.'},thresholds:[6,9,12,16,22],unit:'percent',note:'Anteil der Einwohnerinnen und Einwohner ohne deutsche Staatsangehörigkeit, je Gemeinde. Eingebürgerte und ihre in Deutschland geborenen Kinder zählen als Deutsche und sind hier unsichtbar — in den lange ansässigen Gemeinschaften ist das die Mehrheit. Eine Gemeinde mit niedrigem Ausländeranteil kann eine lange ansässige Zuwanderungsbevölkerung haben. Dies ist gemessen, nicht modelliert: die einzige direkt erhobene Größe, die der Atlas auf Gemeindeebene neben die Modellrechnung stellen kann.'},

 azr_recruitment:{title:'Aus den Anwerbestaaten · Anteil an den Ausländern',badge:'Ausländerzentralregister',date:'Stichtag 31.12.2025 · 44 Kreise',source:'destatis_azr_regionen',sourceInfo:AZR_SOURCE,sourceInfo:AZR_SOURCE,sourceInfo:AZR_SOURCE,thresholds:[30,35,40,45,50],unit:'percent',note:'Anteil der ausländischen Bevölkerung des Kreises, der aus den Gastarbeiter-Anwerbestaaten stammt — Türkei, Italien, Griechenland, Spanien, Portugal, Marokko, Tunesien, ehemaliges Jugoslawien. Der Nenner ist die ausländische Bevölkerung des Kreises, nicht seine Einwohnerschaft. Staatsangehörigkeit ist keine Religionszugehörigkeit.'},

 azr_turkey:{title:'Türkische Staatsangehörige · Anteil an den Ausländern',badge:'Ausländerzentralregister',date:'Stichtag 31.12.2025 · 44 Kreise',source:'destatis_azr_regionen',thresholds:[6,8,10,13,16],unit:'percent',note:'Anteil der ausländischen Bevölkerung des Kreises mit türkischer Staatsangehörigkeit. Nicht die Zahl der Menschen türkischer Herkunft: Eingebürgerte und hier geborene Nachkommen haben einen deutschen Pass und fehlen vollständig. Bundesweiter Median: 7,5 Prozent.'},

 azr_long_resident:{title:'Seit 25 Jahren oder länger hier · Anteil an den Ausländern',badge:'Ausländerzentralregister',date:'Stichtag 31.12.2025 · 44 Kreise',source:'destatis_azr_regionen',thresholds:[18,22,26,30,34],unit:'percent',note:'Anteil der ausländischen Bevölkerung des Kreises, der seit mindestens 25 Jahren in Deutschland lebt. Auch diese Zahl zählt nur Menschen ohne deutschen Pass — gerade bei den lange Ansässigen fehlen die Eingebürgerten, sodass die Verweildauer der Herkunftsgruppen eher unterschätzt wird. Bundesweiter Median: 17,4 Prozent.'},

 foreign_share:{title:'Ausländische Staatsangehörige · Kreisanteil',badge:'Amtliche Bevölkerungsdaten',date:'Stichtag 30.11.2024 · 44 Kreise',source:'stala_pm_2025',thresholds:[10,15,20,25,30],unit:'percent',note:'Anteil der Bevölkerung ohne deutsche Staatsangehörigkeit. Selbst berechnet aus gleichzeitigen amtlichen Beständen. Keine Aussage über Religion, Geburtsland oder Herkunft der Eltern.'},
 district_population:{title:'Bevölkerung insgesamt · Kreise',badge:'Amtliche Bevölkerungsdaten',date:'Stichtag 30.11.2024 · 44 Kreise',source:'stala_pm_2025',thresholds:[150000,250000,350000,500000,750000],unit:'persons',note:'Absolute Einwohnerzahl, keine Bevölkerungsdichte und keine Religionsstatistik. Bevölkerung der Gemeinden wird mit einem anderen Stichtag ausgewiesen.'},
 municipality_population:{title:'Bevölkerung insgesamt · Gemeinden',badge:'Amtliche Bevölkerungsdaten',date:'Stichtag 30.06.2024 · 1.101 statistische Gemeinden',source:'stala_gemeinden_2024_06',thresholds:[2000,5000,10000,20000,50000],unit:'persons',note:'Einwohnerzahl zum 30.06.2024. Grau schraffiert: kein zugeordneter statistischer Wert. Amtliche Gemeindeschlüssel werden beim Geodatenaufbau über Namen innerhalb desselben Kreises zugeordnet; unklare Treffer bleiben offen.'},
 institutions:{title:'Islamische und alevitische Einrichtungen',badge:'Selbstveröffentlicht',date:'Ortsebene · eigene Verzeichnisse der Verbände, Kommunen, Drucksachen und OpenStreetMap · Stand 2026',source:'bamf_fb55',unit:'points',note:'Punkte sind Einrichtungen, keine Bevölkerungszahlen. Jeder Punkt liegt in der Ortsmitte seiner Gemeinde und bezeichnet kein Gebäude: Dieser Atlas führt keine Anschriftenliste zusammen. Belegt ist der Ort, und jeder Eintrag verlinkt die Quelle — die eigene Seite der Einrichtung, ein Vereinsverzeichnis der Stadt, eine Landtagsdrucksache —, auf der die Anschrift steht. Aufgenommen ist, was öffentlich bekannt und öffentlich belegt ist. Eine Verbandszugehörigkeit wird nur genannt, wenn eine Quelle sie selbst behauptet, und dann mit Urheber und Datum; sonst steht die Einrichtung ohne Verband. Keine personenbezogenen Angaben. Aus Einrichtungen lässt sich keine Zahl von Gläubigen ableiten.'},
 muni_under25:{title:'Unter 25-Jährige · Gemeinden',badge:'Vollerhebung',date:'Zensus 2022 · Stichtag 15.05.2022 · 1.101 Gemeinden',source:'bamf_fb55',thresholds:[21,23,25,27,29],unit:'percent',note:'Anteil der unter 25-Jährigen an der Bevölkerung, aus dem Zensus 2022. Anders als die Kreisebene aus dem Mikrozensus ist dies eine Vollerhebung und für alle Gemeinden vorhanden. Keine Angabe zur Religionszugehörigkeit und keine Größe der Modellrechnung.'},
 mh_change:{title:'Veränderung des Migrationshintergrunds · 2021 bis 2025',badge:'Amtliche Erhebung',date:'Mikrozensus 2021 bis 2025 · 44 Kreise',source:'stala_pm_2025',thresholds:[0,2,4,6,8],unit:'points',note:'Veränderung des Anteils der Bevölkerung mit Migrationshintergrund in Prozentpunkten über den gesamten Zeitraum. Stichprobenerhebung: einzelne Jahre schwanken stärker als die Entwicklung. Die Modellrechnung zur muslimischen Bevölkerung wird nicht in die Vergangenheit fortgeschrieben.'},
 second_generation:{title:'Zweite Generation mit deutschem Pass',badge:'Amtliche Erhebung',date:'Mikrozensus 2024 · 44 Kreise',source:'stala_pm_2025',thresholds:[27,29,31,33,35],unit:'percent',note:'Anteil der hier geborenen Menschen mit deutschem Pass an der Bevölkerung mit Migrationshintergrund. Genau diese Menschen fehlen in der Ausländerstatistik – deshalb braucht die Modellrechnung eine Korrektur um Eingebürgerte und Nachkommen. Keine Angabe zur Religionszugehörigkeit.'},
 mh_under25:{title:'Unter 25-Jährige · Bevölkerung mit Migrationshintergrund',badge:'Amtliche Erhebung',date:'Mikrozensus 2024 · 44 Kreise',source:'stala_pm_2025',thresholds:[29,31,33,35,37],unit:'percent',note:'Anteil der unter 25-Jährigen an der Bevölkerung mit Migrationshintergrund. Schraffiert: die Quelle hält zu viele Altersgruppen geheim, um einen belastbaren Anteil zu bilden. Migrationshintergrund ist eine weit größere Gruppe als die modellierte muslimische Bevölkerung; dies ist nicht deren Altersgliederung.'},
 mh_employment:{title:'Erwerbstätige · Bevölkerung mit Migrationshintergrund',badge:'Amtliche Erhebung',date:'Mikrozensus 2024 · ab 15 Jahren · 44 Kreise',source:'stala_pm_2025',thresholds:[60,63,66,69,72],unit:'percent',note:'Anteil der Erwerbstätigen an der Bevölkerung ab 15 Jahren mit Migrationshintergrund. Stichprobenerhebung. Keine Erwerbslosenquote, weil die Quelle die Erwerbslosen in fast allen Kreisen geheim hält. Dies ist kein Merkmal der Religionszugehörigkeit und geht nicht in die Modellrechnung ein.'},
 religion_estimate:{title:'Muslimische Bevölkerung · Modell je Kreis',badge:'Modellrechnung',date:'Landessumme 2025 · Herkunft 31.12.2024 · 44 Kreise',source:'bamf_fb55',thresholds:[5,7.5,10,12.5,15],unit:'percent',note:'Modellrechnung, keine Messung. Die veröffentlichte Landessumme wird nach Herkunft verteilt: ausländische Bevölkerung je Staatsangehörigkeit mal bundesweitem muslimischen Anteil dieser Herkunftsgruppe. Es gibt keine amtliche Religionsstatistik je Kreis.'},
 religion_estimate_municipal:{title:'Muslimische Bevölkerung · Modell je Gemeinde',badge:'Modellrechnung',date:'Verteilung des Kreiswerts · Herkunftsmuster 2022 · 1.101 Gemeinden',source:'bamf_fb55',thresholds:[5,7.5,10,12.5,15],unit:'percent',note:'Modellrechnung, keine Messung. Die Gemeindewerte verteilen den jeweiligen Kreiswert. Der türkische und bosnische Anteil folgt dem im Zensus gemessenen Siedlungsmuster, der Rest der Einwanderungsgeschichte je Gemeinde; für Syrien, Afghanistan, Irak und Kosovo gibt es keine eigenen Gemeindedaten. Die Spannen sind entsprechend breit.'}
};
let toastTimer;
function sourceLink(id,text='Originalquelle ↗') {const s=D.sources[id];return s?`<a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(text)}</a>`:'';}
function toast(text){$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,4500);}
function download(content,filename,type='application/json'){const blob=new Blob([content],{type});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
function exportJSON(payload,filename){download(JSON.stringify(payload,null,2),filename);}
function toCSV(rows){if(!rows.length)return '';const keys=Object.keys(rows[0]);const cell=x=>{if(x===null||x===undefined)return '';let s=typeof x==='object'?JSON.stringify(x):String(x);if(typeof x==='string'&&/^[=+\-@]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';};return '\uFEFF'+[keys.map(cell).join(','),...rows.map(r=>keys.map(k=>cell(r[k])).join(','))].join('\r\n');}
// Die erste Spalte ist der Name, alle weiteren sind Zahlen. Die Zellen bekamen dafür
// schon die Klasse "numeric", die Überschriften nicht — linksbündige Köpfe über
// rechtsbündigen Zahlen, in jeder Tabelle der Seite.
function table(headers,rows,caption=''){return `<table>${caption?`<caption>${esc(caption)}</caption>`:''}<thead><tr>${headers.map((h,i)=>`<th scope="col"${i?' class="numeric"':''}>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.map(row=>`<tr>${row.map((c,i)=>`<td${i?' class="numeric"':''}>${c}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${headers.length}" class="empty-state">Keine passenden Werte.</td></tr>`}</tbody></table>`;}
function metric(label,value,meta=''){return `<div class="detail-stat"><span class="label">${esc(label)}</span><strong>${esc(value)}</strong><span class="meta">${meta}</span></div>`;}
function setSelected(type,id){state.selected={type,id};$('search-results').hidden=true;renderDetail();renderMap();}
function isEstimate(){return state.layer==='religion_estimate'||state.layer==='religion_estimate_municipal';}
function updateLayer(){state.layer=$('layer').value;const est=isEstimate()&&!!EST;const box=$('model-controls');if(box)box.hidden=!est;const ibox=$('institution-controls');if(ibox){ibox.hidden=state.layer!=='institutions';if(!ibox.hidden){fillOrganisationFilter();refreshInstitutionFilter();}}if(est&&EST){const c=EST.meta.coverage;$('model-coverage').textContent='Herkunftsdaten erklären '+c.corrected_share_of_published_high_percent+' bis '+c.corrected_share_of_published_low_percent+' Prozent der veröffentlichten Landessumme; der Rest wird nach Bevölkerung mit Migrationshintergrund verteilt.';}state.areaPage=0;renderMap();renderDetail();renderAreaTable();}
function selectedPayload(){const base={atlas_version:D.version,built_on:D.built_on,layer:state.layer,definition:layers[state.layer].note,selected:state.selected,source:sourceFor(layers[state.layer])};if(state.selected.type==='institution')return {...base,institution:INST?INST.institutions[state.selected.id]:null,not_a_population_measure:INST?INST.not_a_population_measure:null};
 if(state.selected.type==='state')return {...base,religion_estimate_bw:D.bw,religion_share_bw:D.bw_pct,model:isEstimate()&&EST?EST.meta:null};if(state.selected.type==='district')return {...base,data:districts.get(state.selected.id),model:isEstimate()&&EST?{...EST.meta,result:estimateDistrict(state.selected.id)}:null};return {...base,data:municipalities.get(state.selected.id),muslim_count:null,muslim_pct:null,religion_status:'not_available'};}
function renderDetail(){
 const s=state.selected;
 // An institution is a place with a source, not a figure. The panel therefore shows
 // where the entry comes from and links back to it, so every point can be checked.
 // Several institutions at one address: zooming cannot separate them, so they are
 // listed and the reader picks one.
 if(s.type==='institution-group'&&INST){
  const items=(s.id||[]).map(i=>INST.institutions[i]).filter(Boolean);
  $('detail-kind').textContent='Einrichtungen an einem Ort';
  $('detail-name').textContent=items.length+' Einrichtungen';
  $('detail-content').innerHTML=
   '<div class="metric"><ol class="inst-group-list">'
   +items.map((i,n)=>'<li><button type="button" data-pick="'+s.id[n]+'">'
     +esc(i.name)+'<span class="meta">'+esc(i.municipality||i.city)
     +' · '+esc(i.organisation)+'</span></button></li>').join('')
   +'</ol></div>';
  $('detail-content').querySelectorAll('button[data-pick]').forEach(b=>
   b.addEventListener('click',()=>setSelected('institution',Number(b.dataset.pick))));
  return;
 }
 if(s.type==='institution'&&INST){
  const i=INST.institutions[s.id];
  if(i){
   $('detail-kind').textContent='Einrichtung';$('detail-name').textContent=i.name;
   const address=[i.street,[i.postcode,i.city].filter(Boolean).join(' ')].filter(Boolean).join(', ');
   const vague=i.location_precision==='municipality';
   let html=metric('Organisation',esc(i.organisation),
     esc(i.municipality||i.city)+(i.postcode?' · '+esc(i.postcode):''));
   // Ein Punkt ohne Anschrift darf nicht aussehen wie einer mit. Er steht auf dem
   // Beschriftungspunkt der Gemeinde aus den amtlichen Grenzen und meint den Ort,
   // nicht das Gebäude — und das steht hier, nicht nur in der Legende.
   // Dieser Atlas veröffentlicht keine Anschriften. Was er veröffentlicht, ist der
   // Ort und der Beleg — und der Beleg führt zu der Seite, auf der die Einrichtung
   // selbst oder eine Behörde die Anschrift nennt. Das steht beim Punkt, damit
   // niemand die Ortsmitte für das Gebäude hält.
   html+=metric('Genauigkeit dieses Punktes','Ort, nicht Anschrift',
     'Der Punkt liegt in der Ortsmitte von '+esc(i.municipality||i.city)
     +' und bezeichnet kein Gebäude. Anschriften führt dieser Atlas nicht zusammen; '
     +'wer eine sucht, folgt dem Beleg zur Quelle.'
     +(i.why_no_address?' '+esc(i.why_no_address):''));
   const links=[];
   if(i.website)links.push([siteName(i.website),i.website]);
   if(i.source_url)links.push([siteName(i.source_url),i.source_url]);
   if(i.second_source_url&&i.second_source_url!==i.source_url)links.push([siteName(i.second_source_url),i.second_source_url]);
   if(i.openstreetmap_url&&i.openstreetmap_url!==i.source_url)links.push([siteName(i.openstreetmap_url),i.openstreetmap_url]);
   if(i.facebook)links.push(['Facebook',i.facebook]);
   if(i.instagram)links.push(['Instagram',i.instagram]);
   html+='<div class="metric"><span class="metric-label">Belege</span><div class="inst-links">'
     +links.map(([label,url])=>'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+label+'</a>').join('')
     +'</div><span class="meta">'+(links.length>1?'Dieser Eintrag ist durch mehr als eine Quelle belegt. ':'Für diesen Eintrag gibt es bislang nur diese eine Quelle. ')
     +(false?'':'Die Koordinate ist der Beschriftungspunkt der Gemeinde (BKG VG250).')
     +'</span></div>';
   // A federation attribution is someone else's finding about this association, and
   // for the ADÜTDF it is a damaging one. It therefore appears on the point itself with
   // its claimant and its date, not only in the downloadable data.
   if(i.affiliation_source_url){
    const stale=/landtag-bw\.de/.test(i.affiliation_source_url);
    html+=metric('Verbandszugehörigkeit — wer sie behauptet',
      stale?'Innenministerium Baden-Württemberg, Stand 2011':'Siehe Beleg',
      esc(i.affiliation_note||'')+' <a href="'+esc(i.affiliation_source_url)+'" target="_blank" rel="noopener">Beleg ↗</a>'
      +(stale?' <strong>Der Stand ist 2011.</strong> Ob der Verein heute noch besteht, unter diesem Namen firmiert und dieser Zuordnung unterliegt, sagt die Quelle nicht.':''));
   }
   // Die 2011er Zuordnung altert; wo das Ministerium denselben Verband später noch
   // einmal für denselben Ort genannt hat, steht das direkt darunter. Bewusst als
   // eigenes Feld: die späteren Drucksachen nennen Orte, nicht diesen Verein und
   // nicht diese Anschrift, und dürfen deshalb nicht wie eine Bestätigung des
   // Eintrags gelesen werden.
   if(i.affiliation_restated_url){
    html+=metric('Später noch einmal amtlich genannt','Für den Ort, nicht für diese Anschrift',
      esc(i.affiliation_restated_note||'')
      +' <a href="'+esc(i.affiliation_restated_url)+'" target="_blank" rel="noopener">Beleg ↗</a>');
   }
   // Eine Aussage einer Behörde ÜBER diesen Verein, nicht seine Zugehörigkeit. Sie
   // steht wörtlich da, mit Urheber und Datum, und wird nicht zu einem Merkmal
   // verdichtet: Das Ministerium sprach von Kontakten, nicht von der Ausrichtung des
   // Vereins, und der Unterschied verschwindet, sobald man ihn zu einem Etikett macht.
   if(i.state_characterisation_url){
    html+=metric('Was eine Behörde über diesen Verein gesagt hat','Innenministerium BW, Stand 2017',
      esc(i.state_characterisation_note||'')
      +' <a href="'+esc(i.state_characterisation_url)+'" target="_blank" rel="noopener">Drucksache 16/1462 ↗</a>'
      +' <strong>Der Stand ist 2017.</strong> Ob die Aussage heute noch gilt, sagt die Quelle nicht.');
   }
   html+=metric('Was dieser Punkt nicht sagt','Keine Bevölkerungszahl','Eine Einrichtung ist keine Personenzahl. Aus der Zahl der Moscheen lässt sich weder die Zahl der Gläubigen noch ihr Anteil ableiten; diese Punkte gehen in keine Modellrechnung ein.');
   $('detail-content').innerHTML=html;
   return;
  }
 }
 if(s.type==='state'){
  $('detail-kind').textContent='Landesprofil';$('detail-name').textContent='Baden-Württemberg';
  const total=D.districts.reduce((a,r)=>a+r.population,0),foreign=D.districts.reduce((a,r)=>a+r.foreign,0);
  let html=metric('BAMF-Näherungswert · 2025',`${integer(D.bw.value_lower)}–${integer(D.bw.value_upper)}`,'Muslimische und alevitische Religionsangehörige nach Quellendefinition.')+metric('Anteil an privater Hauptwohnsitzbevölkerung',`${pf.format(D.bw_pct.value_lower)}–${pf.format(D.bw_pct.value_upper)} %`,'Mikrozensus 2025; nicht aus der 2024er Bevölkerung neu berechnet.');
  if(isEstimate()&&EST)html+=metric('Modellsumme aller Kreise',integer(EST.meta.state_total.persons_low)+'–'+integer(EST.meta.state_total.persons_high),`<span class="selected-flag">Modellrechnung</span> Die Verteilung erfindet keine Summe: sie verteilt genau diese veröffentlichte Spanne.`);
  else if(['foreign_share','district_population','municipality_population'].includes(state.layer))html+=metric('Einwohnerzahl · 30.11.2024',integer(total),'44 Kreise; Ausländeranteil: '+pct(100*foreign/total));
  html+=`<div class="notice">Landesverteilung aus 2019 auf 2025 übertragen. <strong>Keine veröffentlichte Aufteilung auf Kreise oder Gemeinden.</strong></div><p class="source-note">${sourceLink('bamf_fb55','BAMF FB55 · Tabelle 3 / Abbildung 4 ↗')}</p>`;
  $('detail-content').innerHTML=html;
 }else if(s.type==='district'){
  const d=districts.get(s.id);if(!d)return;
  $('detail-kind').textContent='Kreisprofil · '+d.id;$('detail-name').textContent=d.name;
  let html=metric('Bevölkerung · 30.11.2024',integer(d.population))+metric('Ausländische Staatsangehörige',integer(d.foreign),'<span class="kind-tag kind-fortschreibung">Fortschreibung</span> Stand 30.11.2024 · Anteil '+pct(d.foreign_pct)+' · keine Religionsangabe.');
  const nat=NAT?NAT.districts[d.id]:null;
  if(nat&&nat.nationalities){
    const rows=Object.entries(nat.nationalities).sort((a,b)=>b[1].persons-a[1].persons);
    const shown=state.layer==='foreign_share'?rows:rows.slice(0,5);
    const named=rows.reduce((s,[,v])=>s+v.persons,0);
    const max=rows.length?rows[0][1].share_of_foreign_percent:0;
    html+='<div class="detail-stat"><span class="label">Staatsangehörigkeiten · Anteil an den Ausländern</span>'
      +'<div class="cohort-bars nationality-bars">'+shown.map(([name,v])=>
        `<div class="cohort-row"><span>${esc(name)}</span><span class="cohort-track"><i style="width:${max?(100*v.share_of_foreign_percent/max).toFixed(1):0}%"></i></span><span class="cohort-value">${pf.format(v.share_of_foreign_percent)} %</span></div>`
      ).join('')+'</div>'
      +`<span class="meta"><span class="kind-tag kind-register">Register</span> Ausländerzentralregister, Stand 31.12.2024: ${integer(nat.foreign_total)} Personen. Die Karte oben zeigt ${integer(d.foreign)} aus der Bevölkerungsfortschreibung zum 30.11.2024 — beide Quellen zählen nicht dasselbe zum selben Stichtag (<a href="#grundlagen">Grundlagen</a>). ${pf.format(100*named/nat.foreign_total)} % entfallen auf die ${rows.length} ausgewiesenen Staatsangehörigkeiten, der Rest auf alle übrigen Staaten. Staatsangehörigkeit ist keine Religionszugehörigkeit.${state.layer==='foreign_share'?'':' Ebene „Ausländische Staatsangehörige“ zeigt alle.'}</span></div>`;
  }
  const ctx=CTX?CTX.districts[d.id]:null;
  if(ctx&&ctx.mh&&ctx.mh.employed_pct!==null){
    html+=metric('Erwerbstätige ab 15 Jahren',pf.format(ctx.mh.employed_pct)+' % mit / '+(ctx.no_mh.employed_pct!==null?pf.format(ctx.no_mh.employed_pct)+' % ohne':'– ')+' Migrationshintergrund','<span class=\'kind-tag kind-sample\'>Stichprobe</span> Mikrozensus 2024. Kein Merkmal der Religionszugehörigkeit.');
    if(ctx.mh.high_pct!==null)html+=metric('Hoher Bildungsabschluss (ISCED)',pf.format(ctx.mh.high_pct)+' % mit / '+(ctx.no_mh.high_pct!==null?pf.format(ctx.no_mh.high_pct)+' % ohne':'– ')+' Migrationshintergrund','Anteil an der Bevölkerung ab 15 Jahren der jeweiligen Gruppe.'+(ctx.shared_region?' Rastatt und Baden-Baden bilden eine gemeinsame Erhebungsregion.':''));
  }
  const ts=TS?TS.districts[d.id]:null;
  if(ts&&ts.change!==null){
    const ys=TS.meta.years,vals=ys.map(y=>ts.shares[y]).filter(v=>v!==null);
    const lo=Math.min(...vals),hi=Math.max(...vals),span=(hi-lo)||1;
    html+='<div class="detail-stat"><span class="label">Migrationshintergrund über die Zeit</span>'
      +'<strong>'+(ts.change>0?'+':'')+pf.format(ts.change)+' Punkte seit '+ys[0]+'</strong>'
      +'<div class="spark">'+ys.map(y=>{const v=ts.shares[y];
        return v===null?'<span class="spark-col"><i style="height:0"></i><em>'+esc(y.slice(2))+'</em></span>'
        :`<span class="spark-col" title="${esc(y)}: ${pf.format(v)} %"><i style="height:${(18+62*(v-lo)/span).toFixed(0)}%"></i><em>${esc(y.slice(2))}</em></span>`;}).join('')+'</div>'
      +'<span class="meta">Anteil '+pf.format(ts.shares[ys[0]])+' % auf '+pf.format(ts.shares[ys[ys.length-1]])+' %. Stichprobe: einzelne Jahre schwanken stärker als die Entwicklung.</span></div>';
  }
  const gen=GEN?GEN.districts[d.id]:null;
  if(gen&&gen.second_pct!==null){
    html+=metric('Zweite Generation mit deutschem Pass',pf.format(gen.second_pct)+' % der Bevölkerung mit Migrationshintergrund','<span class=\'kind-tag kind-sample\'>Stichprobe</span> Mikrozensus 2024. Hier geboren, deutscher Pass; in der Ausländerstatistik nicht sichtbar.');
    if(gen.invisible)html+=metric('In der Ausländerstatistik unsichtbar',integer(gen.invisible)+' Personen','Migrationshintergrund abzüglich ausländischer Staatsangehöriger. Begründet die Korrektur der Modellrechnung.');
  }
  const age=AGE?AGE.districts[d.id]:null;
  if(age&&age.mh&&age.mh.u25!==null){
    html+=metric('Unter 25-Jährige',pf.format(age.mh.u25)+' % mit / '+(age.no_mh&&age.no_mh.u25!==null?pf.format(age.no_mh.u25)+' % ohne':'– ')+' Migrationshintergrund','<span class=\'kind-tag kind-sample\'>Stichprobe</span> Mikrozensus 2024. Altersgliederung der Bevölkerung mit Migrationshintergrund, nicht der modellierten muslimischen Bevölkerung.');
    const g=age.mh.groups,labels=AGE.labels,order=AGE.age_groups;
    const known=order.filter(k=>g[k]!==null&&g[k]!==undefined);
    const sum=known.reduce((s,k)=>s+g[k],0);
    if(sum>0)html+='<div class="cohort-bars age-bars">'+order.map(k=>{
      const v=g[k];
      if(v===null||v===undefined)return `<div class="cohort-row"><span>${esc(labels[k])}</span><span class="cohort-missing">geheim gehalten</span></div>`;
      return `<div class="cohort-row"><span>${esc(labels[k])}</span><span class="cohort-track"><i style="width:${(100*v/sum).toFixed(1)}%"></i></span><span class="cohort-value">${pf.format(100*v/sum)} %</span></div>`;
    }).join('')+'</div>';
  }
  const est=isEstimate()?estimateDistrict(d.id):null;
  if(est){const v=est.variants[state.variant];
    html+=metric('Muslimische Bevölkerung · Modell',pf.format(v.pct_low)+'–'+pf.format(v.pct_high)+' %',integer(v.low)+'–'+integer(v.high)+' Personen · '+(state.variant==='migration_background'?'mit Korrektur für Eingebürgerte':'nur Staatsangehörigkeit'));
    const other=est.variants[state.variant==='migration_background'?'citizenship':'migration_background'];
    html+=metric('Andere Variante',pf.format(other.pct_low)+'–'+pf.format(other.pct_high)+' %','Der Abstand zwischen beiden Varianten gehört zur Unsicherheit.');
    const top=Object.entries(est.by_origin).sort((a,b)=>b[1]-a[1]).slice(0,4).map(([g,v])=>esc(g)+' '+integer(v)).join(' · ');
    html+=metric('Größte Herkunftsbeiträge',top,'Aus Staatsangehörigkeit mal bundesweitem Anteil, korrigiert um Eingebürgerte.');
    html+=`<div class="notice warning"><strong>Modellrechnung, keine Messung.</strong> Es gibt keine amtliche Religionsstatistik je Kreis. Die Spanne umfasst die veröffentlichte Landesspanne und die Wahl des Schlüssels.</div>`;}
  else html+=metric('Muslimische Bevölkerung des Kreises','Nicht verfügbar','Kein entsprechender Quellenwert in dieser Sammlung. Nicht null.')+`<div class="notice">Die Landesquote von 10,1–10,7 % wird diesem Kreis nicht als eigener Wert zugewiesen.</div>`;
  html+=`<p class="source-note">${sourceLink(d.source_id,'Landesamt · Tabelle 2 ↗')}</p>`;$('detail-content').innerHTML=html;
 }else{
  const d=municipalities.get(s.id);if(!d)return;$('detail-kind').textContent='Gemeindeprofil';$('detail-name').textContent=d.municipality_name;
  const crosswalk=G?.crosswalk?.find(r=>r.geo_id===d.geo_id);
  const est=isEstimate()?estimateMunicipality(d.geo_id):null;
  const bound=BOUND?BOUND.municipalities[d.geo_id]:null;
  const estimateMetric=est
    ? metric('Muslimische Bevölkerung · Modell',pf.format(est.pct)+' %','Spanne '+pf.format(est.pct_low)+'–'+pf.format(est.pct_high)+' % · '+integer(est.low)+'–'+integer(est.high)+' Personen. Verteilung des Kreiswerts, keine eigene Erhebung.')
    : metric('Muslimische Bevölkerung','Nicht verfügbar','Weder Religionszahl noch kommunale Herkunftsmatrix enthalten.');
  const dem=DEM?DEM.municipalities[d.geo_id]:null;
  const demMetric=dem&&dem.u25!==null
    ? metric('Unter 25-Jährige',pf.format(dem.u25)+' %','<span class="kind-tag kind-census">Vollerhebung</span> Zensus 2022, Stichtag 15.05.2022.'
        +(dem.revision!==null?' Der Zensus korrigierte die fortgeschriebene Einwohnerzahl dieser Gemeinde um '+(dem.revision>0?'+':'')+pf.format(dem.revision)+' %.':''))
    : '';
  const boundMetric=(est&&bound&&bound.ceiling!==null)
    ? metric('Obergrenze aus dem Zensus 2022',pf.format(bound.ceiling)+' %','Anteil der Kategorie „Sonstige, keine, ohne Angabe“. Muslimische Einwohner fallen zwangsläufig hierunter, der Modellwert kann also nicht darüber liegen. Die Kategorie ist selbst kein Muslimanteil, sie besteht überwiegend aus Konfessionslosen.')
    : '';
  $('detail-content').innerHTML=metric('Einwohnerzahl · 30.06.2024',integer(d.population_total),esc(d.district_name))+metric('Männlich / weiblich',`${integer(d.population_male)} / ${integer(d.population_female)}`,'Veröffentlichte Kategorien der Bevölkerungsstatistik.')+estimateMetric+boundMetric+demMetric+`<div class="notice${isEstimate()?' warning':''}">${isEstimate()?'<strong>Modellrechnung, keine Messung.</strong> Der Kreiswert wird verteilt: der türkische und bosnische Anteil nach gemessenem Siedlungsmuster, der Rest nach der Einwanderungsgeschichte der Gemeinde. ':''}${crosswalk?'Amtlicher Gemeindeschlüssel: '+esc(crosswalk.ags):'Geografische Zuordnung noch nicht bestätigt.'} Keine Ableitung der Religion aus dem Gemeindenamen oder der Einwohnerzahl.</div><p class="source-note">${sourceLink(d.source_id,'Landesamt · Tabelle 5, S. '+d.source_page+' ↗')}</p>`;
 }
}
function estimateDistrict(id){return EST?EST.districts[id]:null;}
function estimateMunicipality(geoId){return EST?EST.municipalities[geoId]:null;}
function valueForFeature(f){const p=f.properties;
 if(state.layer==='religion_estimate_municipal'){const e=estimateMunicipality(p.statistical_geo_id);return e?e.pct:null;}
 if(state.layer==='muni_under25'){const x=DEM?DEM.municipalities[p.statistical_geo_id]:null;return x?x.u25:null;}
 if(state.layer==='municipality_population')return municipalities.get(p.statistical_geo_id)?.population_total??null;
 if(state.layer==='religion_estimate'){const e=estimateDistrict(p.id);if(!e)return null;const v=e.variants[state.variant];return v?(v.pct_low+v.pct_high)/2:null;}
 if(state.layer==='mh_employment'){const c=CTX?CTX.districts[p.id]:null;return c&&c.mh?c.mh.employed_pct:null;}
 if(state.layer==='mh_under25'){const g=AGE?AGE.districts[p.id]:null;return g&&g.mh?g.mh.u25:null;}
 if(state.layer==='second_generation'){const g=GEN?GEN.districts[p.id]:null;return g?g.second_pct:null;}
 if(state.layer==='mh_change'){const t=TS?TS.districts[p.id]:null;return t?t.change:null;}
 if(state.layer==='municipal_foreign_share'){
  const m=MUNI_FOREIGN?MUNI_FOREIGN.municipalities[p.id]:null;
  return m?m.foreign_share_percent:null;
 }
 if(state.layer.startsWith('azr_')){
  if(!AZR)return null;
  const field={azr_recruitment:'recruitment_states',azr_turkey:'turkey',azr_long_resident:'resident_25_years_or_more'}[state.layer];
  const row=AZR.districts.find(r=>r.id===p.id);
  return row?row[field+'_share_of_foreign']:null;
 }
 const d=districts.get(p.id);if(!d)return null;if(state.layer==='foreign_share')return d.foreign_pct;if(state.layer==='district_population')return d.population;return null;}
function forEachPoint(geom,fn){const walk=a=>{if(typeof a[0]==='number')fn(a);else a.forEach(walk);};walk(geom.coordinates);}
let projection=null,svgPaths=new Map();
function initProjection(){if(!G)return;let xmin=Infinity,ymin=Infinity,xmax=-Infinity,ymax=-Infinity;const merc=p=>[p[0]*Math.PI/180,-Math.log(Math.tan(Math.PI/4+p[1]*Math.PI/360))];forEachPoint(G.state.geometry,p=>{const [x,y]=merc(p);xmin=Math.min(xmin,x);xmax=Math.max(xmax,x);ymin=Math.min(ymin,y);ymax=Math.max(ymax,y);});const scale=Math.min(700/(xmax-xmin),650/(ymax-ymin));const ox=(760-(xmax-xmin)*scale)/2,oy=(700-(ymax-ymin)*scale)/2;projection=p=>{const [x,y]=merc(p);return [ox+(x-xmin)*scale,oy+(y-ymin)*scale];};}
function pathFor(g){const ring=r=>r.map((p,i)=>{const [x,y]=projection(p);return (i?'L':'M')+x.toFixed(2)+','+y.toFixed(2);}).join('')+'Z';if(g.type==='Polygon')return g.coordinates.map(ring).join('');if(g.type==='MultiPolygon')return g.coordinates.map(p=>p.map(ring).join('')).join('');return '';}
function colorFor(v){const l=layers[state.layer];if(v===null)return 'url(#no-data)';return palette[M.bucket(v,l.thresholds)]??'url(#no-data)';}
function mapValueText(f){if(state.layer==='religion_state')return 'BW gesamt: 10,1–10,7 % · Näherungswert 2025';const v=valueForFeature(f);if(v===null)return 'Kein zugeordneter statistischer Wert';if(state.layer==='foreign_share')return pct(v)+' ausländische Staatsangehörige · 30.11.2024';if(state.layer==='mh_employment')return pf.format(v)+' % erwerbstätig · Mikrozensus 2024';if(state.layer==='mh_under25')return pf.format(v)+' % unter 25 · Mikrozensus 2024';if(state.layer==='second_generation')return pf.format(v)+' % zweite Generation · Mikrozensus 2024';if(state.layer==='mh_change')return (v>0?'+':'')+pf.format(v)+' Punkte seit 2021';if(state.layer==='muni_under25')return pf.format(v)+' % unter 25 · Zensus 2022';if(isEstimate()){const e=state.layer==='religion_estimate'?estimateDistrict(f.properties.id):estimateMunicipality(f.properties.statistical_geo_id);const band=e?(state.layer==='religion_estimate'?e.variants[state.variant]:e):null;return pf.format(v)+' % · Modellrechnung'+(band?' · Spanne '+pf.format(band.pct_low)+'–'+pf.format(band.pct_high)+' %':'');}return integer(v)+' Einwohner · '+(state.layer==='municipality_population'?'30.06.2024':'30.11.2024');}
// What the institutions layer does NOT contain, stated on the page rather than left to
// be inferred from a thin map. An organisation missing here is missing for a reason, and
// the reason is worth more than the gap is misleading.
function renderInstitutionCoverage(){
 const box=$('inst-coverage');if(!box)return;
 if(state.layer!=='institutions'||!INST){box.hidden=true;box.innerHTML='';return;}
 // Count what is actually on the map, not what the harvest pulled in: entries that
 // turned out to be the same place were merged, and a few could not be located.
 const shown=new Map();
 for(const {inst:i} of institutionsShown())shown.set(i.organisation,(shown.get(i.organisation)||0)+1);
 const harvested=[...shown].sort((a,b)=>b[1]-a[1]);
 const missing=Object.entries(INST.not_yet_harvested||{});
 box.hidden=false;
 // Zugeklappt wie die Gebietstabelle: Die Liste ist wichtig, aber sie ist eine
 // Auskunft auf Nachfrage und nicht der erste Blick auf die Karte.
 const total=harvested.reduce((a,[,n])=>a+n,0);
 box.innerHTML='<details class="data-details"><summary>Ausgewertete Quellen '
  +'<span>'+total+' Einrichtungen aus '+harvested.length+' Verzeichnissen</span></summary>'
  +'<div class="inst-coverage-body"><ul class="inst-coverage-list">'
  +harvested.map(([k,n])=>'<li><strong>'+esc(k)+'</strong> · '+n+'</li>').join('')
  +'</ul>'
  +(missing.length?'<p class="inst-coverage-head">Nicht enthalten — und warum</p><ul class="inst-coverage-list">'
   +missing.map(([k,why])=>'<li><strong>'+esc(k)+'</strong> '+esc(why)+'</li>').join('')+'</ul>':'')
  +'<p class="meta">'+esc(INST.inclusion_rule)+'</p></div></details>';
}
// Institutions are drawn as points on the state outline. They are places, not
// quantities, so they are never shaded into the choropleth.
//
// Where several sit within a few streets of each other they are drawn as one circle
// carrying their number, because 581 dots at state scale is an ink blot: the ones in
// Stuttgart cover each other, and a reader cannot tell two mosques from nine. Clicking
// the circle zooms to just those, which splits them apart, and repeating that ends at
// individual points. Where several genuinely share a building — an umbrella and its
// member associations at one address — zooming can no longer separate them, so the
// circle opens a list instead of zooming forever.
const CLUSTER_SCREEN_PX = 26;   // how close is "too close to tell apart"
const MAP_WIDTH = 760;

// Named in a Landtag paper: the 2011 ADÜTDF and IGMG attributions, the later
// restatements, and the associations the Innenministerium listed in 2017. It is a
// property of the DOCUMENT — "an official paper names this entry" — not a judgement
// this atlas makes about the institution, which is why the filter is worded that way
// and why it mixes federation members with unaffiliated mosques.
function namedInLandtagPaper(i){
 return Boolean(i.state_characterisation_url||i.affiliation_restated_url
   ||(i.affiliation_source_url&&/landtag-bw\.de/.test(i.affiliation_source_url)));
}
// Pairs, not a filtered array: every other part of the page addresses an institution
// by its index in INST.institutions — the detail panel, the export, the group list —
// so filtering must not renumber them.
function matchesInstitutionFilter(i){
 if(state.onlyLandtag&&!namedInLandtagPaper(i))return false;
 if(state.instOrganisation&&i.organisation!==state.instOrganisation)return false;
 if(state.instSource==='two'&&!i.second_source_url)return false;
 if(state.instSource==='one'&&i.second_source_url)return false;
 if(state.instSource==='own'&&!i.website)return false;
 return true;
}
function institutionsShown(){
 const all=INST?INST.institutions:[];
 const out=[];
 all.forEach((inst,idx)=>{if(matchesInstitutionFilter(inst))out.push({inst,idx});});
 return out;
}
// Die Verbandsliste kommt aus den Daten, nicht aus einer gepflegten Aufzählung: Ein
// neuer Verband im Verzeichnis soll im Filter auftauchen, ohne dass hier etwas
// nachgetragen werden muss.
function fillOrganisationFilter(){
 const select=$('filter-organisation');
 if(!select||!INST||select.dataset.filled)return;
 const counts=new Map();
 for(const i of INST.institutions)counts.set(i.organisation,(counts.get(i.organisation)||0)+1);
 select.insertAdjacentHTML('beforeend',[...counts].sort((a,b)=>b[1]-a[1])
   .map(([name,n])=>'<option value="'+esc(name)+'">'+esc(name)+' ('+n+')</option>').join(''));
 select.dataset.filled='1';
}
function refreshInstitutionFilter(){
 const shown=institutionsShown().length;
 const all=INST?INST.institutions.length:0;
 const label=$('filter-count');
 if(label)label.textContent=shown===all?all+' Einrichtungen':shown+' von '+all+' Einrichtungen';
 if(state.selected.type==='institution'||state.selected.type==='institution-group')setSelected('state','08');
 renderMap();renderDetail();
}
function clusterInstitutions(){
 const z=state.zoom;
 // One screen pixel is z.w/MAP_WIDTH units of the drawing, so the grid grows as the
 // reader zooms out and the grouping stays the same size under the eye.
 const cell=CLUSTER_SCREEN_PX*(z.w/MAP_WIDTH);
 const buckets=new Map();
 institutionsShown().forEach(({inst,idx})=>{
  const [x,y]=projection([inst.lon,inst.lat]);
  const key=Math.round(x/cell)+'|'+Math.round(y/cell);
  let b=buckets.get(key);
  if(!b){b={x:0,y:0,items:[],minx:Infinity,miny:Infinity,maxx:-Infinity,maxy:-Infinity};buckets.set(key,b);}
  b.x+=x;b.y+=y;b.items.push({inst,idx,x,y});
  b.minx=Math.min(b.minx,x);b.maxx=Math.max(b.maxx,x);
  b.miny=Math.min(b.miny,y);b.maxy=Math.max(b.maxy,y);
 });
 for(const b of buckets.values()){b.x/=b.items.length;b.y/=b.items.length;}
 return [...buckets.values()];
}

function zoomToCluster(b){
 // Not separable by zooming: the points are on top of each other. Offer the list.
 const spread=Math.max(b.maxx-b.minx,b.maxy-b.miny);
 if(spread<0.4||state.zoom.w<=192){setSelected('institution-group',b.items.map(i=>i.idx));return;}
 const pad=Math.max(spread*0.9,6);
 const nw=Math.max(190,Math.min(1000,spread+pad*2));
 const nh=nw*700/MAP_WIDTH;
 state.zoom={x:b.x-nw/2,y:b.y-nh/2,w:nw,h:nh};
 applyZoom();
}

function renderInstitutionPoints(){
 const host=$('map-features');
 host.querySelectorAll('g[data-institutions]').forEach(n=>n.remove());
 const g=document.createElementNS('http://www.w3.org/2000/svg','g');
 g.setAttribute('data-institutions','');
 const NS='http://www.w3.org/2000/svg';
 // Single points first, clusters over them: a number that a neighbouring dot covers
 // is worse than no number at all.
 const groups=clusterInstitutions().sort((a,b)=>a.items.length-b.items.length);
 for(const b of groups){
  if(b.items.length===1){
   const {inst,idx,x,y}=b.items[0];
   const c=document.createElementNS(NS,'circle');
   // Ein Punkt, dessen Anschrift nicht belegt ist, wird hohl und gestrichelt
   // gezeichnet und etwas größer: Er behauptet einen Ort, keine Stelle, und das
   // muss man sehen, bevor man klickt. Ein gefüllter Punkt an der Ortsmitte wäre
   // eine Genauigkeit, die es nicht gibt.
   const vague=inst.location_precision==='municipality';
   c.setAttribute('cx',x);c.setAttribute('cy',y);c.setAttribute('r',vague?4.4:3.2);
   c.setAttribute('class',vague?'inst-point inst-point-vague':'inst-point');
   if(vague){
    c.setAttribute('fill','none');
    c.setAttribute('stroke',instColour(inst.organisation));
    c.setAttribute('stroke-width','1.6');
    c.setAttribute('stroke-dasharray','2.4 1.8');
   }else{
    c.setAttribute('fill',instColour(inst.organisation));
   }
   c.setAttribute('tabindex','0');c.setAttribute('role','button');
   c.setAttribute('aria-label',inst.name+', '+inst.city
     +(vague?', Anschrift nicht belegt, Punkt in der Ortsmitte':''));
   const t=document.createElementNS(NS,'title');
   t.textContent=inst.name+' · '+inst.city+' · '+inst.organisation
     +(vague?' · Anschrift nicht belegt':'');
   c.appendChild(t);
   const open=e=>{e.stopPropagation();setSelected('institution',idx);};
   c.addEventListener('click',open);
   c.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open(e);}});
   g.appendChild(c);
   continue;
  }
  const n=b.items.length;
  const r=5.5+2.6*Math.log2(n);
  const knot=document.createElementNS(NS,'g');
  knot.setAttribute('class','inst-cluster');
  knot.setAttribute('tabindex','0');knot.setAttribute('role','button');
  knot.setAttribute('aria-label',n+' Einrichtungen in diesem Bereich, zum Aufteilen auswählen');
  const c=document.createElementNS(NS,'circle');
  c.setAttribute('cx',b.x);c.setAttribute('cy',b.y);c.setAttribute('r',r);
  const label=document.createElementNS(NS,'text');
  label.setAttribute('x',b.x);label.setAttribute('y',b.y);
  label.setAttribute('class','inst-cluster-count');
  label.textContent=n;
  const t=document.createElementNS(NS,'title');
  t.textContent=n+' Einrichtungen — auswählen, um sie aufzuteilen';
  knot.append(c,label,t);
  const open=e=>{e.stopPropagation();zoomToCluster(b);};
  knot.addEventListener('click',open);
  knot.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open(e);}});
  g.appendChild(knot);
 }
 host.appendChild(g);
}
function renderLegend(){const l=layers[state.layer];renderInstitutionCoverage();if(state.layer==='religion_state'){$('map-legend').innerHTML='<span class="legend-key"><i class="legend-swatch" style="background:#236a7b"></i>BW insgesamt · 10,1–10,7 % · keine Kreisquote</span>';return;}if(state.layer==='institutions'){const list=institutionsShown().map(p=>p.inst);const counts=new Map();for(const i of list){const k=INST_COLOURS.find(([p])=>i.organisation.startsWith(p));const label=k?k[0]:'Sonstige';counts.set(label,(counts.get(label)||0)+1);}
  $('map-legend').innerHTML='<span class="legend-key"><i class="legend-swatch" style="background:#17505f;border-radius:50%;width:13px;height:13px"></i>Zahl = mehrere Einrichtungen dicht beieinander; auswählen teilt sie auf</span>'+[...counts].map(([label,n])=>'<span class="legend-key"><i class="legend-swatch" style="background:'+instColour(label)+';border-radius:50%;width:10px;height:10px"></i>'+esc(label)+' · '+n+'</span>').join('')+'<span class="legend-key"><i class="legend-swatch" style="background:none;border:1.6px dashed #6b7280;border-radius:50%;width:11px;height:11px"></i>Jeder Punkt steht in der Ortsmitte, nicht am Gebäude</span>'+'<span class="legend-key">'+list.length+' Einrichtungen · keine Bevölkerungszahl</span>';return;}
 const p=palette,fmt=l.unit==='percent'?v=>pf.format(v)+' %':l.unit==='points'?v=>(v>0?'+':'')+pf.format(v)+' Pkt.':integer;const th=l.thresholds;const texts=[`< ${fmt(th[0])}`,...th.slice(0,-1).map((v,i)=>`${fmt(v)} – < ${fmt(th[i+1])}`),`≥ ${fmt(th.at(-1))}`];$('map-legend').innerHTML=texts.map((t,i)=>`<span class="legend-key"><i class="legend-swatch" style="background:${p[i]}"></i>${esc(t)}</span>`).join('')+'<span class="legend-key">Schraffiert: kein Wert</span>';}
function renderMap(){const l=layers[state.layer];$('map-title').textContent=l.title;$('map-period').textContent=l.date;$('map-badge').textContent=l.badge;$('map-badge').className='pill'+(isEstimate()?' warning':'');$('map-note').textContent=l.note;$('map-svg-title').textContent=l.title;$('map-svg-desc').textContent=l.date+'. '+l.note;renderLegend();$('map-unavailable').hidden=!!G;$('map').hidden=!G;$('export-map').disabled=!G;['zoom-in','zoom-out','zoom-reset'].forEach(id=>$(id).disabled=!G);if(!G)return;
 const municipalLayer=state.layer==='municipality_population'||state.layer==='religion_estimate_municipal'||state.layer==='muni_under25'||state.layer==='municipal_foreign_share';const pointLayer=state.layer==='institutions';
 const features=state.layer==='religion_state'||pointLayer?[G.state]:(municipalLayer?G.municipalities:G.districts);const frag=document.createDocumentFragment();svgPaths.clear();
 for(const f of features){const p=f.properties,el=document.createElementNS('http://www.w3.org/2000/svg','path');el.setAttribute('d',pathFor(f.geometry));el.setAttribute('fill',state.layer==='religion_state'?'#236a7b':colorFor(valueForFeature(f)));el.setAttribute('fill-rule','evenodd');el.setAttribute('class','map-feature');el.setAttribute('data-id',p.id);el.setAttribute('tabindex',municipalLayer?'-1':'0');el.setAttribute('role','button');el.setAttribute('aria-label',p.name+': '+mapValueText(f));
 const selected=state.selected.type==='district'&&state.selected.id===p.id||state.selected.type==='municipality'&&state.selected.id===p.statistical_geo_id;if(selected)el.classList.add('is-selected');
 const title=document.createElementNS('http://www.w3.org/2000/svg','title');title.textContent=p.name+' · '+mapValueText(f);el.appendChild(title);
 const choose=()=>{if(state.layer==='religion_state')setSelected('state','08');else if(municipalLayer){if(p.statistical_geo_id)setSelected('municipality',p.statistical_geo_id);else toast('Für diese Fläche ist kein statistischer Gemeindewert zugeordnet.');}else setSelected('district',p.id);};
 el.addEventListener('click',()=>{if(!drag.moved)choose();});el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}});el.addEventListener('pointerenter',()=>{$('map-tooltip').innerHTML=`<strong>${esc(p.name)}</strong>${esc(mapValueText(f))}`;$('map-tooltip').hidden=false;});el.addEventListener('pointerleave',()=>$('map-tooltip').hidden=true);el.addEventListener('focus',()=>{$('map-tooltip').textContent=p.name+' · '+mapValueText(f);$('map-tooltip').hidden=false;});el.addEventListener('blur',()=>$('map-tooltip').hidden=true);frag.appendChild(el);svgPaths.set(p.id,el);
 }
 $('map-features').replaceChildren(frag);$('map-labels').replaceChildren();
 // Institutions are drawn as points on the state outline. They are places, not
 // quantities, so they are never shaded into the choropleth.
 if(pointLayer&&INST)renderInstitutionPoints();
 // Only annotate known district labels from source geometry; no hand-positioned place coordinates.
 if(state.layer!=='municipality_population'&&state.layer!=='religion_state')for(const f of G.districts.filter(f=>['08111','08212','08222','08311','08421'].includes(f.properties.id))){const p=f.properties,[x,y]=projection(p.label_point);const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',x+8);t.setAttribute('y',y-7);t.setAttribute('class','map-label');t.textContent=p.name;$('map-labels').appendChild(t);}
 if(state.layer==='religion_state'&&state.selected.type!=='state'){const f=state.selected.type==='district'?G.districts.find(f=>f.properties.id===state.selected.id):G.municipalities.find(f=>f.properties.statistical_geo_id===state.selected.id);if(f){const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',pathFor(f.geometry));p.setAttribute('fill','none');p.setAttribute('stroke','#dfc185');p.setAttribute('stroke-width','2');p.setAttribute('vector-effect','non-scaling-stroke');$('map-labels').appendChild(p);}}
 applyZoom();
}
function applyZoom(){const z=state.zoom;$('map').setAttribute('viewBox',`${z.x} ${z.y} ${z.w} ${z.h}`);
 // The grouping depends on the zoom, so it is rebuilt with it rather than once at draw.
 if(state.layer==='institutions'&&INST&&$('map-features').querySelector('g[data-institutions]'))renderInstitutionPoints();}
function zoom(factor){const z=state.zoom;const nw=Math.max(190,Math.min(1000,z.w*factor));const nh=nw*700/760;state.zoom={x:z.x+(z.w-nw)/2,y:z.y+(z.h-nh)/2,w:nw,h:nh};applyZoom();}
const drag={active:false,moved:false,x:0,y:0,view:null};
$('map').addEventListener('pointerdown',e=>{if(e.button!==0)return;drag.active=true;drag.moved=false;drag.x=e.clientX;drag.y=e.clientY;drag.view={...state.zoom};});
window.addEventListener('pointermove',e=>{if(!drag.active)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>6)drag.moved=true;if(!drag.moved)return;const rect=$('map').getBoundingClientRect();state.zoom={...drag.view,x:drag.view.x-dx*drag.view.w/rect.width,y:drag.view.y-dy*drag.view.h/rect.height};applyZoom();});
window.addEventListener('pointerup',()=>{drag.active=false;});
function areaRows(){let rows;if(state.layer==='municipality_population'||state.layer==='religion_estimate_municipal')rows=D.municipalities.map(m=>({name:m.municipality_name,key:m.district_code,geo_id:m.geo_id,population:m.population_total,male:m.population_male,female:m.population_female,reference:'2024-06-30',kind:'municipality'}));else rows=D.districts.map(d=>({name:d.name,key:d.id,geo_id:d.geo_id,population:d.population,foreign:d.foreign,foreign_pct:d.foreign_pct,reference:d.reference_period,kind:'district',estimate:isEstimate()?estimateDistrict(d.id):null}));const q=M.normalize($('area-filter').value);return rows.filter(r=>M.normalize(r.name+' '+r.key).includes(q));}
function renderAreaTable(){const rows=areaRows(),n=25,pages=Math.max(1,Math.ceil(rows.length/n));state.areaPage=Math.min(state.areaPage,pages-1);const shown=rows.slice(state.areaPage*n,(state.areaPage+1)*n);const muni=state.layer==='municipality_population'||state.layer==='religion_estimate_municipal',est=isEstimate();const headers=muni?['Gemeinde','Kreis','Einwohner','Männlich','Weiblich',...(est?['Modell · Anteil']:[])]:['Kreis','Schlüssel','Einwohner','Ausländisch','Anteil ausländisch',est?'Modell · Anteil':'Lokale Muslimzahl'];const cells=shown.map(r=>[`<button class="link-button" data-area-kind="${r.kind}" data-area-id="${esc(muni?r.geo_id:r.key)}">${esc(r.name)}</button>`,esc(r.key),integer(r.population),muni?integer(r.male):integer(r.foreign),muni?integer(r.female):pct(r.foreign_pct),...(muni?(est?[(()=>{const e=estimateMunicipality(r.geo_id);return e?pf.format(e.pct_low)+'–'+pf.format(e.pct_high)+' %':'Nicht verfügbar';})()]:[]):[est&&r.estimate?pf.format(r.estimate.variants[state.variant].pct_low)+'–'+pf.format(r.estimate.variants[state.variant].pct_high)+' %':'Nicht verfügbar'])]);$('area-table').innerHTML=table(headers,cells,muni?'Bevölkerung am 30.06.2024. Die Tabelle ist auch ohne Geodatenaufbau vollständig.'+(est?' Modellwerte verteilen den Kreiswert und sind keine Messung.':''):'Bevölkerung am 30.11.2024.'+(est?' Modellwerte sind eine Verteilung der veröffentlichten Landessumme, keine Messung.':''));$('area-page').textContent=`Seite ${state.areaPage+1} / ${pages} · ${integer(rows.length)} Treffer`;$('area-prev').disabled=state.areaPage===0;$('area-next').disabled=state.areaPage>=pages-1;$('area-table-count').textContent=integer(rows.length)+' Gebiete';$('area-table').querySelectorAll('[data-area-id]').forEach(b=>b.addEventListener('click',()=>setSelected(b.dataset.areaKind,b.dataset.areaId)));}
function originView(){let title,badge,note,source,rows,unit='Personen';switch(state.origin){case 'de_origins':title='Muslimische Bevölkerung nach Herkunftsgruppe';badge='Deutschland · BAMF-Modell · 2025';note='Diese Verteilung gilt für Deutschland, nicht für Baden-Württemberg und nicht für einen ausgewählten Kreis. Herkunft bezeichnet im Quellensinn eigene beziehungsweise elterliche Herkunft – nicht allein den Pass oder das eigene Geburtsland.';source='bamf_fb55';rows=D.origins_de_2025.map(r=>({name:r.dimensions.origin_group,value:r.value,low:r.value_lower,high:r.value_upper,share:r.share_of_published_de_total,source:r}));break;case 'de_regions':title='Muslimische Bevölkerung nach Herkunftsregion';badge='Deutschland · BAMF-Modell · 2025';note='Anteile an der in der BAMF-Hochrechnung erfassten muslimischen Bevölkerung Deutschlands. Keine eigene BW-Herkunftsverteilung.';source='bamf_fb55';unit='Prozent';rows=D.origin_composition.filter(r=>r.reference_period==='2025').map(r=>({name:r.dimensions.origin_region,value:r.value,source:r}));break;case 'bw_nationalities_2024':case 'bw_nationalities_2025':{const year=state.origin.endsWith('2025')?'2025':'2024';title='Ausgewählte ausländische Staatsangehörigkeiten';badge='BW · AZR · '+(year==='2024'?'31.12.2024':'Bezugsjahr 2025');note=year==='2024'?'25 in der Veröffentlichung ausgewiesene Staatsangehörigkeiten. Das sind keine Muslimzahlen. Deutsche Staatsangehörige und damit viele Eingebürgerte und Nachkommen werden hier nicht abgebildet.':'Nur vier im Pressetext veröffentlichte Staatsangehörigkeiten; der genaue Stichtag ist in der übernommenen Zeile nicht bestätigt. Keine vollständige Rangliste und keine Muslimzahlen. Der kleinere Ausschnitt darf nicht als Bevölkerungsrückgang gegenüber der 2024er Auswahl gelesen werden.';source=year==='2024'?'stala_pm_2025':'stala_pm_2026';rows=D.nationalities_bw.filter(r=>r.reference_period===(year==='2024'?'2024-12-31':'2025')).map(r=>({name:r.dimensions.nationality,value:r.value,source:r}));break;}case 'bw_historical':title='Drei publizierte Herkunftsangaben des BW-Modells';badge='BW · historische Hauptvariante · 2018';note='Historische Angaben aus Brachat-Schwarz (2020), keine aktuellen Werte und keine vollständige Herkunftsverteilung. Die übrigen Gruppen werden nicht durch eine pauschale Restschätzung ergänzt.';source='stala_monat_2020';rows=D.historical_bw.filter(r=>r.indicator==='estimated_muslim_persons_by_origin').map(r=>({name:r.dimensions.origin_group,value:r.value,source:r}));break;default:throw new Error('Unknown origin view');}rows.sort((a,b)=>b.value-a.value);return {title,badge,note,source,rows,unit};}
function renderOrigins(){const v=originView();$('origin-chart-title').textContent=v.title;$('origin-badge').textContent=v.badge;$('origin-badge').className='pill'+(state.origin.startsWith('bw_nationalities')?' neutral':'');$('origin-unit').textContent=v.unit;$('origin-warning').textContent=v.note;const shown=state.allOrigins?v.rows:v.rows.slice(0,8);const max=Math.max(...v.rows.map(r=>r.high??r.value));$('origin-bars').setAttribute('aria-label',v.title+'. '+v.badge+'. '+v.note);$('origin-bars').innerHTML=shown.map(r=>{const value=v.unit==='Prozent'?pct(r.value):integer(r.value);const tooltip=r.low!==undefined?`Publizierte Spanne: ${integer(r.low)}–${integer(r.high)}; mittlerer Wert: ${integer(r.value)}`:`${r.name}: ${value}`;const color=state.origin==='de_regions'?regionColors[r.name]||'#12596b':state.origin.startsWith('bw_nationalities')?'#507c91':'#12596b';return `<div class="bar-row"><span class="bar-name">${esc(r.name)}</span><div class="bar-track" title="${esc(tooltip)}"><div class="bar-fill" style="width:${100*r.value/max}%;background:${color}"></div>${r.low!==undefined?`<span class="bar-whisker" style="left:${100*r.low/max}%;width:${100*(r.high-r.low)/max}%"></span>`:''}</div><span class="bar-value">${value}${r.share!==undefined?`<small>${pct(r.share)} der DE-Modellsumme *</small>`:r.low!==undefined?`<small>${integer(r.low)}–${integer(r.high)}</small>`:''}</span></div>`;}).join('');$('all-origins').hidden=v.rows.length<=8;$('all-origins').textContent=state.allOrigins?'Nur acht Gruppen zeigen':`Alle ${v.rows.length} Gruppen zeigen`;$('all-origins').setAttribute('aria-pressed',String(state.allOrigins));let foot=sourceLink(v.source);if(state.origin==='de_origins')foot+=' · Tabelle 2: mittlere Werte und veröffentlichte Spannen (schwarze Markierungen). * Anteil selbst berechnet aus gerundeten veröffentlichten Mittelwerten; Nenner 6.821.000. Kein Anteil muslimischer Menschen innerhalb einer Herkunftsgruppe. Kleine Rundungsdifferenzen zwischen Summe der Gruppen und Gesamtsumme bleiben erhalten.';else if(state.origin==='de_regions')foot+=' · Abbildung 3: veröffentlichte Anteile.';$('origin-footnote').innerHTML=foot;$('origin-table').innerHTML=table(['Gruppe',v.unit==='Prozent'?'Anteil':'Mittlerer Wert / Bestand',...(state.origin==='de_origins'?['Untergrenze','Obergrenze','Anteil an DE-Modellsumme *']:[])],v.rows.map(r=>[esc(r.name),v.unit==='Prozent'?pct(r.value):integer(r.value),...(state.origin==='de_origins'?[integer(r.low),integer(r.high),pct(r.share)]:[])]));}
function renderContext(){renderComposition();renderBwNationalities();renderDistrictAzr();renderResidence();renderNaturalisations();renderAreaFlows();renderFlows();}
const AZR=typeof window!=='undefined'?window.ATLAS_DISTRICT_AZR:null;
const MUNI_FOREIGN=typeof window!=='undefined'?window.ATLAS_MUNICIPAL_FOREIGN:null;
// Jeder Anteil hier bezieht sich auf die ausländische Bevölkerung des Kreises, nicht auf
// seine Einwohner. Das ist die naheliegendste Fehllesart dieser Zahlen, also steht der
// Nenner in jeder Beschriftung und nicht nur in der Fußnote.
function renderDistrictAzr(){
 const box=$('azr-bars'),select=$('azr-indicator');
 if(!box||!select||!AZR)return;
 if(!select.dataset.filled){
  select.innerHTML=Object.entries(AZR.labels).filter(([k])=>k!=='foreign_total')
    .map(([k,text])=>'<option value="'+esc(k)+'">'+esc(text[0].toUpperCase()+text.slice(1))+'</option>').join('');
  select.dataset.filled='1';
 }
 const key=(state.azrIndicator||select.value||'turkey')+'_share_of_foreign';
 const rows=AZR.districts.filter(r=>r[key]!==null).sort((a,b)=>b[key]-a[key]);
 if(!rows.length)return;
 const national=AZR.germany_distribution[key];
 const max=Math.max(rows[0][key],national?national.max:0)||1;
 $('azr-note').textContent='Anteil der Ausländerinnen und Ausländer im Kreis, die '
   +AZR.labels[state.azrIndicator||'turkey']+' sind — als Anteil an allen Ausländern des Kreises, nicht an seinen Einwohnern.'
   +(national?' Bundesweiter Median: '+pf.format(national.median)+' %, Spanne '+pf.format(national.min)+' bis '+pf.format(national.max)+' %.':'');
 box.innerHTML=rows.map(r=>`<div class="bar-row"><span class="bar-name">${esc(r.name)}</span><div class="bar-track">${national?`<span class="bar-reference" style="left:${100*national.median/max}%" title="Bundesmedian ${pf.format(national.median)} %"></span>`:''}<div class="bar-fill" style="width:${100*r[key]/max}%"></div></div><span class="bar-value">${pf.format(r[key])} %<small>${integer(r[key]*r.foreign_total/100)} von ${integer(r.foreign_total)}</small></span></div>`).join('');
 $('azr-source').textContent=AZR.what_a_share_means+' '+AZR.not_a_religion_measure+' Stand '+AZR.reference_date+'. Quelle: '+AZR.source+'. '+AZR.licence+'.';
}
const BWF=typeof window!=='undefined'?window.ATLAS_BW_FLOWS:null;
// Der Atlas konnte bisher sagen, wie viele Menschen welcher Herkunft in einem Kreis
// leben, und kein Wort über Bewegung — den Mechanismus hinter jeder Zahl, die er zeigt.
// Ein Saldo ist dabei kein Bevölkerungswachstum und ein Zuzug keine Person, sondern ein
// Meldevorgang; das steht unter dem Diagramm und nicht im Kleingedruckten.
function renderAreaFlows(){
 const box=$('flow-area-bars');
 if(!box||!BWF)return;
 const scope=state.flowArea||'countries';
 let rows,note;
 if(scope==='districts'){
  rows=BWF.districts_total_population.filter(r=>r.kind==='district')
    .sort((a,b)=>b.balance-a.balance)
    .map(r=>({name:r.name,value:r.balance,detail:integer(r.arrivals)+' Zuzüge, '+integer(r.departures)+' Fortzüge'}));
  note='Wanderungssaldo je Stadt- und Landkreis 2023, alle Wanderungen über die Gemeindegrenze. Positiv heißt: mehr Zuzüge als Fortzüge.';
 }else if(scope==='ages'){
  rows=BWF.by_age_group.map(r=>({name:r.age_group+' Jahre',value:r.balance,
    detail:integer(r.arrivals)+' Zuzüge, davon '+integer(r.arrivals_foreign)+' ohne deutschen Pass'}));
  note='Wanderungssaldo über die Landesgrenze 2023 nach Altersgruppen.';
 }else{
  rows=BWF.by_country.filter(r=>r.level>=2&&Math.abs(r.balance)>=400)
    .sort((a,b)=>b.balance-a.balance)
    .map(r=>({name:r.area,value:r.balance,
      detail:integer(r.arrivals)+' Zuzüge, '+integer(r.departures)+' Fortzüge'}));
  note='Wanderungssaldo über die Landesgrenze 2023 nach Herkunfts- und Zielgebiet, Gebiete mit einem Saldo von mindestens 400 Personen.';
 }
 const max=Math.max(...rows.map(r=>Math.abs(r.value)),1);
 $('flow-area-note').textContent=note;
 box.innerHTML=rows.map(r=>{const w=100*Math.abs(r.value)/max;
  return `<div class="bar-row"><span class="bar-name">${esc(r.name)}</span><div class="bar-track bar-track-signed"><div class="bar-fill${r.value<0?' negative':''}" style="width:${w/2}%;margin-left:${r.value<0?50-w/2:50}%"></div></div><span class="bar-value">${r.value>0?'+':''}${integer(r.value)}<small>${esc(r.detail)}</small></span></div>`;}).join('');
 $('flow-area-source').textContent=BWF.what_is_counted+' '+BWF.not_a_religion_measure+' Quelle: '+BWF.source+'. '+BWF.licence+'.';
}
const BWX=typeof window!=='undefined'?window.ATLAS_BW_MIGRATION:null;
// Der Atlas modelliert nach Herkunft und sagt nichts darüber, wie lange jemand hier ist
// — was den Eindruck stehen lässt, beides sei dasselbe. Die Zahlen widersprechen dem
// deutlich genug, dass sie neben der Karte stehen sollten.
function renderResidence(){
 const box=$('residence-bars');
 if(!box||!BWX)return;
 const block=BWX.average_residence_years,rows=block.rows;
 const max=rows[0].years;
 box.innerHTML=rows.map(r=>`<div class="bar-row"><span class="bar-name">${esc(r.nationality)}</span><div class="bar-track"><div class="bar-fill" style="width:${100*r.years/max}%"></div></div><span class="bar-value">${pf.format(r.years)} Jahre</span></div>`).join('');
 $('residence-caveat').textContent=block.caveat+' Quelle: '+BWX.source+', '+BWX.licence+'.';
}
function renderNaturalisations(){
 const box=$('naturalisation-chart');
 if(!box||!BWX)return;
 const rows=BWX.naturalisations.rows;
 const max=Math.max(...rows.map(r=>r.count));
 box.style.gridTemplateColumns='repeat('+rows.length+',1fr)';
 box.innerHTML=rows.map((r,i)=>`<div class="vbar-cell"><div class="vbar-fill" style="height:${145*r.count/max}px" title="${esc(r.year)}: ${integer(r.count)}"></div><span class="vbar-label">${i%5===0||i===rows.length-1?esc(r.year.slice(2)):''}</span></div>`).join('');
 $('naturalisation-note').textContent=BWX.naturalisations.why_it_matters+' Quelle: '+BWX.source+', '+BWX.licence+'.';
}
// Das Vergleichsdiagramm daneben gilt für Deutschland. Diese Zahlen sind
// baden-württembergisch und messen etwas anderes — den Pass, nicht die Herkunft und
// erst recht nicht die Religion. Beides nebeneinander, mit dem Unterschied dabei.
function renderBwNationalities(){
 const box=$('bw-nationalities');
 if(!box||!D.nationalities_bw)return;
 const rows=D.nationalities_bw.filter(r=>r.reference_period==='2024-12-31')
   .sort((a,b)=>b.value-a.value).slice(0,12);
 if(!rows.length)return;
 const max=rows[0].value;
 box.innerHTML=rows.map(r=>`<div class="bar-row"><span class="bar-name">${esc(r.dimensions.nationality)}</span><div class="bar-track"><div class="bar-fill" style="width:${100*r.value/max}%"></div></div><span class="bar-value">${integer(r.value)}</span></div>`).join('');
 const source=D.sources[rows[0].source_id];
 if(source)$('nat-source').href=source.url;
}
function renderComposition(){
 const years=['2008','2015','2019','2025'];const regionOrder=['Türkei','Naher Osten','Südosteuropa','Mittlerer Osten','Nordafrika'];const groups=D.origin_composition;
 const canonical=n=>n==='SO-Europa'?'Südosteuropa':n;
 // 2008, 2015 und 2019 gibt es nur nach fünf Regionen — mehr enthält die Quelle nicht.
 // Für 2025 liegen dagegen achtzehn Herkunftsgruppen vor, jede mit ihrer Region. Wer
 // will, bekommt die feine Aufschlüsselung; die Vergleichbarkeit über die Jahre bleibt
 // erhalten, weil die Balkenlänge dieselbe Größe misst.
 const fine=state.compositionDetail;
 $('composition-chart').innerHTML=years.map(year=>{
  const rows=groups.filter(r=>r.reference_period===year);
  let segments;
  if(fine&&year==='2025'&&D.origins_de_2025){
   const byRegion=new Map(regionOrder.map(r=>[r,[]]));
   for(const g of D.origins_de_2025){
    const region=canonical(g.dimensions.origin_region);
    if(byRegion.has(region))byRegion.get(region).push(g);
   }
   segments=regionOrder.flatMap(region=>byRegion.get(region)
     .sort((a,b)=>b.share_of_published_de_total-a.share_of_published_de_total)
     .map(g=>{const share=g.share_of_published_de_total;
      return `<span class="stack-segment" style="flex:${share};background:${regionColors[region]}" title="${esc(g.dimensions.origin_group)} (${esc(region)}): ${pct(share)}" aria-label="2025, ${esc(g.dimensions.origin_group)}, ${pct(share)}">${share>4?esc(g.dimensions.origin_group.split('/')[0]):''}</span>`;})).join('');
  }else{
   segments=regionOrder.map(region=>{const r=rows.find(r=>canonical(r.dimensions.origin_region)===region);if(!r)return '';return `<span class="stack-segment" style="flex:${r.value};background:${regionColors[region]}" title="${esc(region)}: ${pct(r.value)}" aria-label="${year}, ${esc(region)}, ${pct(r.value)}">${pf.format(r.value)}</span>`;}).join('');
  }
  return `<div class="stack-row"><span class="stack-year">${year}</span><div class="stack-track">${segments}</div></div>`;
 }).join('');
 $('composition-legend').innerHTML=regionOrder.map(n=>`<span><i class="legend-swatch" style="background:${regionColors[n]}"></i>${esc(n)}</span>`).join('');
 // Die Datei enthält zwölf Jahreswerte von 2014 bis 2025 und zwölf Monatswerte.
 // Gezeigt wurden davon acht Monate eines angefangenen Jahres — die kürzeste und am
 // wenigsten aussagekräftige Auswahl aus allem, was da ist.
}
const MONTH_NAMES=['Jan','Feb','Mär','Apr','Mai','Jun','Jul','Aug','Sep','Okt','Nov','Dez'];
function renderFlows(){
 const byYear=D.flows_bw.filter(r=>r.reference_period_type==='year')
   .sort((a,b)=>a.reference_period.localeCompare(b.reference_period));
 const byMonth=D.flows_bw.filter(r=>r.reference_period_type==='month')
   .sort((a,b)=>a.reference_period.localeCompare(b.reference_period)).slice(-12);
 const monthly=state.flowRange==='months';
 const rows=monthly?byMonth:byYear;
 if(!rows.length)return;
 const label=r=>monthly
   ?MONTH_NAMES[Number(r.reference_period.slice(5,7))-1]+' '+r.reference_period.slice(2,4)
   :r.reference_period;
 const total=monthly
   ?{value:rows.reduce((a,r)=>a+r.value,0),source_id:rows.at(-1).source_id,
     note:'Registrierungen in zwölf Monaten'}
   :{value:rows.at(-1).value,source_id:rows.at(-1).source_id,
     note:'Registrierungen im Jahr '+rows.at(-1).reference_period};
 $('flow-total').innerHTML=integer(total.value)+'<small>'+esc(total.note)+'</small>';
 const max=Math.max(...rows.map(r=>r.value));
 const chart=$('flow-chart');
 chart.style.gridTemplateColumns='repeat('+rows.length+',1fr)';
 chart.innerHTML=rows.map(r=>`<div class="vbar-cell"><div class="vbar-fill" style="height:${145*r.value/max}px" title="${esc(r.reference_period)}: ${integer(r.value)}"><span class="vbar-value">${integer(r.value)}</span></div><span class="vbar-label">${esc(label(r))}</span></div>`).join('');
 $('flow-heading').textContent=monthly
   ?'Asylregistrierungen, letzte zwölf Monate'
   :'Asylregistrierungen je Jahr, 2014–2025';
 $('flow-source').href=D.sources[total.source_id].url;
 $('states-table').innerHTML=table(['Schätzeinheit','Untergrenze','Obergrenze','Anteil: Untergrenze','Anteil: Obergrenze'],D.states.map(r=>[esc(r.name),integer(r.low),integer(r.high),pct(r.pct_low),pct(r.pct_high)]),'BAMF FB55, Tabelle 3 und Abbildung 4. Die Länderpaare bleiben gemeinsam.');
 const historical=D.historical_bw.filter(r=>r.indicator==='muslim_persons_historical');const scen={'main':'Hauptvariante','alternative':'Nebenvariante','census_republished':'Volkszählungsangabe, wiedergegeben','ministerial_report_republished':'Ministerratsbericht, wiedergegeben'};$('history-table').innerHTML=table(['Bezugsjahr','Quellenmodell','Personen'],historical.map(r=>[esc(r.reference_period),esc(scen[r.dimensions.scenario]||r.dimensions.scenario),integer(r.value)]),'Brachat-Schwarz, Statistisches Monatsheft 4/2020. Verschiedene historische Verfahren.');
 const purposeNames={spouse_reunification:'Ehegattennachzug',parent_reunification:'Elternnachzug',child_reunification:'Kindernachzug',other_family_reunification:'Sonstiger Familiennachzug',study_and_preparation:'Studium / Vorbereitung / Bewerbung',language_course_school:'Sprachkurs / Schulbesuch',employment_broad:'Erwerbstätigkeit (breite Kategorie)',jewish_immigration:'Jüdische Zuwanderung',ethnic_german_resettlers:'Spätaussiedlerinnen und Spätaussiedler',humanitarian_admission_resettlement:'Humanitäre Aufnahme / Resettlement',other_residence_purposes:'Sonstige Aufenthaltszwecke',not_assigned:'Nicht zugeordnet',total:'Insgesamt (nicht zusätzlich summieren)'};
 const purposes=[...new Set(D.visa_purposes.map(r=>r.dimensions.purpose))];$('visa-table').innerHTML=table(['Zweck','2024','2025'],purposes.map(p=>[esc(purposeNames[p]||p),...['2024','2025'].map(y=>integer(D.visa_purposes.find(r=>r.dimensions.purpose===p&&r.reference_period===y)?.value))]),'AA-Jahres-PDFs: bearbeitete nationale Visa. Summe und Unterkategorien nicht addieren.');
 const issues=D.source_audit.parameter_comparison.filter(r=>r.table1_differs_from_original_mld);$('audit-table').innerHTML=table(['Herkunftsgruppe','FB55 Tabelle 1, E','FB55 Tabelle 2','FB38 Original'],issues.map(r=>[esc(r.origin_group),pct(r.fb55_table1_column_E_published),pct(r.fb55_table2_mld_share_published),pct(r.fb38_table2_3_mld_share_published)]));
}
function renderSources(){const ids=['bamf_fb55','stala_pm_2025','stala_gemeinden_2024_06','stala_pm_2026','stala_monat_2020','bamf_mld2020_full','bw_jum_asyl_2026_08','aa_national_visas_2024','aa_national_visas_2025'];$('sources-list').innerHTML=ids.map(id=>{const s=D.sources[id];return `<article class="source-item" id="source-${esc(id)}"><a href="${esc(s.url)}" target="_blank" rel="noreferrer">${esc(s.title)} ↗</a><span>${esc(s.publisher)} · veröffentlicht ${esc(s.publication_period)}</span>${s.locator?`<p>${esc(s.locator)}</p>`:''}${s.limitation?`<p>${esc(s.limitation)}</p>`:''}</article>`;}).join('')+`<article class="source-item"><a href="https://gdz.bkg.bund.de/index.php/default/open-data/verwaltungsgebiete-1-250-000-stand-01-01-vg250-01-01.html" target="_blank" rel="noreferrer">BKG: Verwaltungsgebiete VG250 ↗</a><span>Archivstand 01.01.2024 · dl-de/by-2-0 · keine Bevölkerungswerte aus den Geometrien übernommen</span><p>${G?`Geodatenaufbau ausgeführt; ${G.municipality_match_count}/1101 Gemeindewerte zugeordnet. ${G.municipalities_unmatched.length} statistische Gemeinden ohne eindeutige Geometriezuordnung.`:'Amtliche Geometrien noch nicht lokal bezogen. Der GitHub-Workflow baut diese vor der Veröffentlichung auf.'}</p></article>`;}
function searchPlaces(){const q=M.normalize($('place-search').value);if(q.length<2){$('search-results').hidden=true;return;}const candidates=[...D.districts.map(d=>({type:'district',id:d.id,name:d.name,detail:'Kreis '+d.id})),...D.municipalities.map(m=>({type:'municipality',id:m.geo_id,name:m.municipality_name,detail:m.district_name}))].filter(r=>M.normalize(r.name+' '+r.detail).includes(q)).slice(0,10);$('search-results').hidden=false;$('search-results').innerHTML=candidates.length?candidates.map((r,i)=>`<button type="button" data-result="${i}"><strong>${esc(r.name)}</strong><br><span class="small-muted">${esc(r.detail)} · ${r.type==='municipality'?'Gemeinde':'Kreis'}</span></button>`).join(''):'<p class="empty-state">Kein Treffer.</p>';$('search-results').querySelectorAll('[data-result]').forEach(b=>b.addEventListener('click',()=>{const r=candidates[Number(b.dataset.result)];$('place-search').value=r.name;setSelected(r.type,r.id);}));}
let researchLoading=false;
async function loadResearch(){if(state.researchRows||researchLoading)return;researchLoading=true;$('research-load-note').textContent='Die lokale Forschungssammlung wird geladen …';try{const response=await fetch('data/research-observations.json');if(!response.ok)throw new Error(String(response.status));state.researchRows=await response.json();renderResearch();$('research-load-note').textContent='Unveränderte Originalbeobachtungen der Datensammlung.';}catch(e){$('research-load-note').textContent='Die Einzeldatei konnte nicht geladen werden. Bei file:// die Seite über einen lokalen HTTP-Server öffnen. Der ZIP-Download enthält dieselben Daten.';console.warn('Research data load unavailable:',e.message);}finally{researchLoading=false;}}
function filteredResearch(){if(!state.researchRows)return [];const id=$('dataset-select').value,q=M.normalize($('research-search').value);return state.researchRows.filter(r=>r.dataset_id===id&&(!q||M.normalize(r.geo_name+' '+r.indicator+' '+r.reference_period+' '+JSON.stringify(r.dimensions)).includes(q)));}
function renderResearch(){const id=$('dataset-select').value,ds=D.datasets.find(r=>r.dataset_id===id);$('dataset-description').textContent=ds?.scope||'';if(!state.researchRows)return;const rows=filteredResearch(),pages=Math.max(1,Math.ceil(rows.length/30));state.researchPage=Math.min(state.researchPage,pages-1);const visible=rows.slice(state.researchPage*30,(state.researchPage+1)*30);$('research-table').innerHTML=table(['Gebiet / Gruppe','Bezug','Kennzahl','Wert / Spanne','Einheit / Herkunft'],visible.map(r=>[`${esc(r.geo_name)}<br><span class="small-muted">${esc(Object.values(r.dimensions).join(' · '))}</span>`,esc(r.reference_period),`<span title="${esc(r.observation_id)}">${esc(r.indicator)}</span>`,r.value!==null?number(r.value)+(r.value_lower!==null?`<br><span class="small-muted">[${number(r.value_lower)}–${number(r.value_upper)}]</span>`:''):r.value_lower!==null?`${number(r.value_lower)}–${number(r.value_upper)}`:'Nicht ausgewiesen',`${esc(r.unit)}<br>${esc(r.provenance)}<br><span class="tiny">${esc(r.source_locator)}</span>`]));$('research-page').textContent=`Seite ${state.researchPage+1} / ${pages} · ${integer(rows.length)} Beobachtungen`;$('research-prev').disabled=state.researchPage===0;$('research-next').disabled=state.researchPage>=pages-1;}
function exportSVG(){if(!G){toast('Zuerst die amtlichen Kartengrenzen aufbauen.');return;}const l=layers[state.layer],svg=$('map').cloneNode(true);svg.setAttribute('x','0');svg.setAttribute('y','90');svg.setAttribute('width','760');svg.setAttribute('height','700');svg.querySelectorAll('path').forEach(p=>{p.setAttribute('stroke',p.getAttribute('stroke')||'#ffffff');p.setAttribute('stroke-width',p.getAttribute('stroke-width')||'.8');});svg.querySelectorAll('.map-label').forEach(t=>{t.setAttribute('font-size','13');t.setAttribute('fill','#142d3a');t.setAttribute('font-family','sans-serif');});const serializer=new XMLSerializer();const warning=isEstimate()?'MODELLRECHNUNG – KEINE AMTLICHE RELIGIONSSTATISTIK':state.layer==='religion_state'?'NUR LANDESWERT – KEINE GLEICHE QUOTE FÜR ALLE KREISE':'BEZUGSJAHR UND STATISTISCHES MERKMAL BEACHTEN';const extra=isEstimate()&&EST?`Veröffentlichte Landessumme ${integer(EST.meta.state_total.persons_low)}–${integer(EST.meta.state_total.persons_high)}, verteilt nach Herkunft. Spannen je Gebiet beachten.`:state.layer==='religion_state'?'BW insgesamt: 1.133.000–1.197.000; 10,1–10,7 %. Quelle: BAMF FB55.':l.note;const legend=$('map-legend').textContent;const wrap=(text,max=102)=>{const words=text.split(' ');let out=[''];for(const word of words){const i=out.length-1;if(out[i].length+word.length>max)out.push(word);else out[i]+=(out[i]?' ':'')+word;}return out;};const lines=[...wrap(extra),...wrap('Legende: '+legend),'Grenzen: © BKG 2026 · VG250, 01.01.2024; BW-Auswahl, vereinfacht.', 'BKG: https://www.bkg.bund.de · Lizenz: https://www.govdata.de/dl-de/by-2-0', ...wrap('Datenquellen: https://sgx.geodatenzentrum.de/web_public/gdz/datenquellen/datenquellen_vg_nuts.pdf'),...wrap('Daten: '+sourceFor(l).publisher+'; '+l.date)];const meta={atlas_version:D.version,layer:state.layer,note:l.note,source:sourceFor(l),geometry:{date:G.geometry_reference,source:G.source_url,license:G.license_url},model:isEstimate()&&EST?EST.meta:null};const out=`<?xml version="1.0" encoding="UTF-8"?><svg xmlns="http://www.w3.org/2000/svg" width="760" height="${835+lines.length*18}" viewBox="0 0 760 ${835+lines.length*18}"><rect width="100%" height="100%" fill="white"/><metadata>${esc(JSON.stringify(meta))}</metadata><text x="22" y="31" font-family="sans-serif" font-size="19" fill="#142d3a">${esc(l.title)}</text><text x="22" y="54" font-family="sans-serif" font-size="12">${esc(l.date)}</text><text x="22" y="77" font-family="sans-serif" font-size="11" font-weight="bold">${esc(warning)}</text>${serializer.serializeToString(svg)}${lines.map((t,i)=>`<text x="22" y="${805+i*18}" font-family="sans-serif" font-size="10" fill="#334e58">${esc(t)}</text>`).join('')}</svg>`;download(out,'bw-atlas-'+state.layer+(isEstimate()?'-MODELLRECHNUNG':'')+'.svg','image/svg+xml');}
// Events and progressive enhancement.
$('layer').addEventListener('change',updateLayer);
const azrPick=$('azr-indicator');
if(azrPick)azrPick.addEventListener('change',()=>{state.azrIndicator=azrPick.value;renderDistrictAzr();});
const flowArea=$('flow-area-scope');
if(flowArea)flowArea.addEventListener('change',()=>{state.flowArea=flowArea.value;renderAreaFlows();});
const compDetail=$('composition-detail');
if(compDetail)compDetail.addEventListener('change',()=>{state.compositionDetail=compDetail.checked;renderComposition();});
const flowRange=$('flow-range');
if(flowRange)flowRange.addEventListener('change',()=>{state.flowRange=flowRange.value;renderFlows();});
const onlyLandtag=$('only-landtag');
if(onlyLandtag)onlyLandtag.addEventListener('change',()=>{state.onlyLandtag=onlyLandtag.checked;refreshInstitutionFilter();});
const orgFilter=$('filter-organisation');
if(orgFilter)orgFilter.addEventListener('change',()=>{state.instOrganisation=orgFilter.value;refreshInstitutionFilter();});
const srcFilter=$('filter-source');
if(srcFilter)srcFilter.addEventListener('change',()=>{state.instSource=srcFilter.value;refreshInstitutionFilter();});
const infoToggle=$('landtag-info-toggle');
if(infoToggle)infoToggle.addEventListener('click',e=>{e.preventDefault();const box=$('landtag-info');const open=box.hidden;box.hidden=!open;infoToggle.setAttribute('aria-expanded',String(open));});
const variantSelect=$('estimate-variant');
if(variantSelect)variantSelect.addEventListener('change',()=>{state.variant=variantSelect.value;renderMap();renderDetail();renderAreaTable();});
$('zoom-in').addEventListener('click',()=>zoom(.8));$('zoom-out').addEventListener('click',()=>zoom(1.25));$('zoom-reset').addEventListener('click',()=>{state.zoom={x:0,y:0,w:760,h:700};applyZoom();});
$('reset-place').addEventListener('click',()=>{$('place-search').value='';setSelected('state','08');state.zoom={x:0,y:0,w:760,h:700};applyZoom();});
$('place-search').addEventListener('input',searchPlaces);$('place-search').addEventListener('keydown',e=>{if(e.key==='Escape')$('search-results').hidden=true;if(e.key==='Enter'){e.preventDefault();$('search-results').querySelector('button')?.click();}});document.addEventListener('click',e=>{if(!e.target.closest('.search-field'))$('search-results').hidden=true;});
$('area-filter').addEventListener('input',()=>{state.areaPage=0;renderAreaTable();});$('area-prev').addEventListener('click',()=>{state.areaPage--;renderAreaTable();});$('area-next').addEventListener('click',()=>{state.areaPage++;renderAreaTable();});
$('export-selection').addEventListener('click',()=>exportJSON(selectedPayload(),'bw-atlas-'+state.selected.id+'.json'));
$('export-map').addEventListener('click',exportSVG);
$('export-area-csv').addEventListener('click',()=>{const est=isEstimate();const rows=areaRows().map(r=>{const v=est&&r.estimate?r.estimate.variants[state.variant]:null;const {estimate,...rest}=r;return {...rest,model_status:est?'modelled_not_measured':'not_applicable',model_variant:est?state.variant:null,model_percent_low:v?v.pct_low:null,model_percent_high:v?v.pct_high:null,model_persons_low:v?v.low:null,model_persons_high:v?v.high:null,source_muslim_count:null,source_muslim_pct:null,note:layers[state.layer].note};});download(toCSV(rows),'bw-atlas-'+state.layer+(est?'-MODELLRECHNUNG':'')+'.csv','text/csv;charset=utf-8');});
$('origin-scope').addEventListener('change',()=>{state.origin=$('origin-scope').value;state.allOrigins=false;renderOrigins();});$('all-origins').addEventListener('click',()=>{state.allOrigins=!state.allOrigins;renderOrigins();});$('export-origins').addEventListener('click',()=>{const v=originView();exportJSON({atlas_version:D.version,scope:state.origin,title:v.title,definition:v.note,unit:v.unit,source:D.sources[v.source],rows:v.rows},'bw-atlas-'+state.origin+'.json');});
$('dataset-select').innerHTML=D.datasets.map(d=>`<option value="${esc(d.dataset_id)}">${esc(d.title)} (${d.observation_count})</option>`).join('');$('dataset-select').addEventListener('change',()=>{state.researchPage=0;renderResearch();});$('research-search').addEventListener('input',()=>{state.researchPage=0;renderResearch();});$('research-explorer').addEventListener('toggle',()=>{if($('research-explorer').open)loadResearch();});$('research-prev').addEventListener('click',()=>{state.researchPage--;renderResearch();});$('research-next').addEventListener('click',()=>{state.researchPage++;renderResearch();});$('research-export').addEventListener('click',()=>{if(!state.researchRows){toast('Forschungssammlung zunächst laden oder ZIP nutzen.');return;}const dataset=D.datasets.find(d=>d.dataset_id===$('dataset-select').value);exportJSON({dataset,scope:'Unveränderte Originalbeobachtungen der Datensammlung.',observations:filteredResearch()},'bw-atlas-'+dataset.dataset_id+'.json');});
// Age structure for the state, as three panels: everyone, men, women.
//
// One mirrored pyramid answers "how do the sexes differ" and hides "how large is this
// age group", because the two halves have to be added up by eye. Three panels answer
// both: the first is read directly, the other two are compared with each other.
//
// All three share one scale, so a bar in the men's panel is the same length as the same
// number in the total. That is the point of small multiples, and it is why the men's
// and women's bars come out at roughly half the width of the total's — which is true.
//
// The three categories are ordered, not merely different — no immigration history, one
// parent, both — so they are shaded as one hue from light to dark rather than given
// three unrelated colours. Suppressed cells stay blank instead of becoming zero.
function renderPyramid(){
const host=$('pyramid');if(!host)return;
const P=window.ATLAS_PYRAMID;
if(!P){host.innerHTML='<p class="empty-state">Keine Altersdaten geladen.</p>';return;}
const keys=['with','one_parent','without'];
const colors={with:'#17505f',one_parent:'#5b9dad',without:'#e1ecee'};
const sexes=['Männlich','Weiblich'];
const val=(row,sex,k)=>(sex==='Gesamt'
  ? sexes.reduce((s,x)=>s+(row[x][k]||0),0)
  : (row[sex][k]||0));
const total=(row,sex)=>keys.reduce((s,k)=>s+val(row,sex,k),0);
let max=0;
for(const row of P.pyramid)for(const sex of ['Gesamt',...sexes]){
 const t=total(row,sex);if(t>max)max=t;}
const rows=P.pyramid.slice().reverse();
const panel=(sex,title)=>{
 const bars=rows.map(row=>{
  const segs=keys.map(k=>{const v=val(row,sex,k);
   return v?`<i class="py-seg" style="width:${(100*v/max).toFixed(2)}%;background:${colors[k]}" `
    +`title="${esc(row.age_group)} · ${esc(title)} · ${esc(P.labels[k])}: ${integer(v)} Tsd."></i>`:'';}).join('');
  const sum=total(row,sex);
  return `<div class="py-row"><span class="py-age">${esc(row.age_group)}</span>`
   +`<span class="py-bar">${segs}</span>`
   +`<span class="py-total">${sum?integer(sum):'·'}</span></div>`;}).join('');
 return `<div class="py-panel"><h4 class="py-title">${esc(title)}</h4>${bars}</div>`;};
host.innerHTML='<div class="py-panels">'
 +panel('Gesamt','Gesamt')+panel('Männlich','Männer')+panel('Weiblich','Frauen')+'</div>';
$('pyramid-legend').innerHTML=keys.map(k=>`<span><i class="legend-swatch" style="background:${colors[k]}"></i>${esc(P.labels[k])}</span>`).join('');
const u=P.under_25;
$('pyramid-note').textContent='Unter 25 Jahre: '
 +Object.entries(u).map(([k,v])=>k+' '+pf.format(v)+' %').join(' · ')
 +'. Alle drei Felder teilen sich einen Maßstab; Zahlen in Tausend. '+P.meta.survey_note
 +' Leere Stellen sind von der Quelle geheim gehaltene Fallzahlen.';
}
// What every figure rests on. Register, projection, sample and census count different
// things; the table names the kind for each measure so they are not read as one series.
function renderBases(){
const host=$('bases-table');if(!host)return;
if(!BASES){host.innerHTML='<p class="empty-state">Keine Grundlagen geladen.</p>';return;}
$('bases-headline').textContent=BASES.headline;
$('bases-kinds').innerHTML=Object.values(BASES.kinds).map(k=>
 `<div class="kind"><strong>${esc(k.label)}</strong><span>${esc(k.note)}</span></div>`).join('');
const f=BASES.two_foreign_counts;
$('bases-foreign').innerHTML='<strong>Die ausländische Bevölkerung erscheint mit zwei Werten.</strong>'
 +`<p>Fortschreibung ${integer(f.fortschreibung_persons)} zum ${esc(f.fortschreibung_reference)}, `
 +`Register ${integer(f.register_persons)} zum ${esc(f.register_reference)}. `
 +`Unterschied ${integer(f.difference_persons)} Personen.</p><p>${esc(f.explanation)}</p>`;
host.innerHTML=table(['Größe','Art der Quelle','Stichtag','Gebiet','Wofür verwendet'],
 BASES.entries.map(e=>[esc(e.measure),
  `<span class="kind-tag kind-${esc(e.kind)}">${esc(e.kind_label)}</span>`,
  esc(e.reference),esc(e.geography),esc(e.used_for)]),
 'Zusammengestellt aus den erzeugten Datendateien; Stichtage und Quellen stammen aus der Aufbereitung selbst.');
const fx=BASES.federal_cross_check;
$('bases-denominator').innerHTML=esc(BASES.denominator_note)+' '+esc(BASES.census_revision_note||'')+(fx?'<br><br>Gegenprobe: Unsere Landessumme von '+integer(fx.our_population)+' Einwohnern weicht um '+(fx.population_difference_percent>0?'+':'')+pf.format(fx.population_difference_percent)+' % vom Bundeswert ab ('+esc(fx.source)+', '+esc(fx.reference)+'). '+esc(fx.what_it_cannot_show):'');
}
initProjection();renderContext();renderPyramid();renderBases();renderOrigins();renderSources();renderResearch();updateLayer();
// About / Impressum. Build and provenance fields are read from the shipped data,
// so the dialog cannot advertise a geometry build the page does not actually have.
function initAbout(){
const dlg=$('about');if(!dlg)return;
const set=(id,text)=>{const el=$(id);if(el)el.textContent=text;};
const day=v=>{if(!v)return null;const m=String(v).match(/^(\d{4})-(\d{2})-(\d{2})/);return m?m[3]+'.'+m[2]+'.'+m[1]:String(v);};
set('about-version',D.version||'–');
set('about-built',day(D.built_on)||'–');
set('about-input',D.input_version?D.input_version+(D.input_sha256?' · SHA-256 '+String(D.input_sha256).slice(0,16)+'…':''):'–');
set('about-geo-ref',G&&G.geometry_reference?G.geometry_reference:'Noch keine amtlichen Geometrien aufgebaut');
set('about-geo-sha',G&&G.archive_sha256?G.archive_sha256:'Kein Archiv bezogen');
let opener=null;
const open=e=>{opener=(e&&e.currentTarget)||null;if(typeof dlg.showModal==='function'){if(!dlg.open)dlg.showModal();}else{dlg.setAttribute('open','');}dlg.scrollTop=0;const c=$('close-about');if(c)c.focus();};
const close=()=>{if(typeof dlg.close==='function'){if(dlg.open)dlg.close();}else{dlg.removeAttribute('open');}if(opener&&opener.isConnected)opener.focus();};
['about-button','about-button-footer'].forEach(id=>{const b=$(id);if(b)b.addEventListener('click',open);});
const c=$('close-about');if(c)c.addEventListener('click',close);
// Clicking the backdrop closes; clicks inside the panel must not.
dlg.addEventListener('click',ev=>{if(ev.target===dlg)close();});
// Any in-page anchor inside the dialog should close it so the target is visible.
dlg.addEventListener('click',ev=>{const a=ev.target.closest&&ev.target.closest('a[href^="#"]');if(a)close();});
}
initAbout();

// Public diagnostics expose state and source availability, not hidden data.
window.Atlas={getState:()=>JSON.parse(JSON.stringify(state, (key,value)=>key==='researchRows'?undefined:value)),getData:()=>D,hasGeometry:!!G,hasEstimate:!!EST,getEstimate:()=>EST?JSON.parse(JSON.stringify(EST)):null,select:setSelected};
})();
