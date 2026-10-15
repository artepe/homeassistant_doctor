import {METRICS,esc,badSensors,isBad,missingRegistry,pick,read,uptime,monitorCandidates} from './metrics.mjs?v=0.4.1';
import {applyRegistryCleanup} from './cleanup_actions.mjs?v=0.4.1';
const LABELS={
 cpu:['CPU-kuorma','%','#60a5fa'],ram:['RAM-muisti','%','#a78bfa'],disk:['Tallennustila','%','#34d399'],
 cpu_temp:['CPU-lämpötila','°C','#fb923c'],gpu:['GPU-kuorma','%','#67e8f9'],gpu_temp:['GPU-lämpötila','°C','#f472b6'],
 swap:['Swap','%','#c4b5fd'],mem_free:['RAM vapaana','','#34d399'],mem_used:['RAM käytössä','','#60a5fa'],
 last_boot:['Käyttöaika','','#60a5fa'],net_in:['Verkko sisään','','#22d3ee'],net_out:['Verkko ulos','','#22d3ee']
};
const CSS=':host{display:block;min-height:100%;color:var(--primary-text-color,#e5edf8);font:14px system-ui,-apple-system,sans-serif}*{box-sizing:border-box}main{max-width:1290px;margin:0 auto;padding:24px 22px 60px}.top{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:22px}.brand{display:flex;gap:13px;align-items:center}.logo{background:linear-gradient(135deg,#0891b2,#2563eb);color:white;font-size:24px;font-weight:900;border-radius:14px;padding:11px 14px}h1{font-size:25px;letter-spacing:-.7px;margin:0}.sub,.hint,small{color:var(--secondary-text-color,#a8b6c7);font-size:12px}.live{font-size:12px;color:#22c55e}.tabs{display:flex;gap:8px;border-bottom:1px solid var(--divider-color,#384358);margin-bottom:23px;overflow:auto}.tab{border:0;background:transparent;color:var(--secondary-text-color,#a8b6c7);padding:13px 15px;white-space:nowrap;font-weight:700}.tab.active{color:var(--primary-text-color,#fff);border-bottom:3px solid #60a5fa}.surface,.card,.smallcard{border:1px solid var(--divider-color,#364257);border-radius:14px;background:var(--card-background-color,#1a2533)}.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:14px}.welcome{padding:23px;color:white;background:linear-gradient(125deg,#123044,#1c4164)}h2{font-size:18px;margin:0 0 10px}.welcome h2{font-size:25px}.welcome p{color:#bdcce1;line-height:1.5}.score{font-size:39px;font-weight:800}.summary{padding:20px;display:flex;justify-content:space-around;align-items:center;gap:10px}.summary b{display:block;font-size:28px;margin:10px 0}.section{display:flex;justify-content:space-between;align-items:center;margin:24px 0 12px;gap:10px}.section h2{margin:0}.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.card{padding:17px;min-height:160px;display:flex;flex-direction:column;gap:14px;justify-content:space-between}.card .value{font-size:31px;font-weight:800}.card .value small{font-size:14px}.card code,.smallcard code{font-size:10px;color:var(--secondary-text-color,#a8b6c7);overflow-wrap:anywhere}.bar{height:5px;background:var(--divider-color,#384358);border-radius:6px;overflow:hidden}.bar span{height:100%;display:block}.little{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.smallcard{padding:14px}.smallcard strong{display:block;font-size:19px;margin:8px 0}.box{padding:19px;margin-bottom:15px}.box p{line-height:1.6;color:var(--secondary-text-color,#a8b6c7)}.controls{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin:14px 0}select,input[type=search],input[type=text]{border:1px solid var(--divider-color,#384358);background:var(--primary-background-color,#111a28);color:var(--primary-text-color,#fff);border-radius:8px;padding:10px 12px;min-width:180px}input[type=search]{flex:1}.btn{padding:10px 13px;border-radius:9px;border:1px solid var(--divider-color,#435169);background:var(--primary-background-color,#121e30);color:var(--primary-text-color,#fff);font-weight:700;cursor:pointer}.btn.blue{background:#2563eb;color:#fff}.btn.danger{background:#9f1239;color:white}.btn:disabled{opacity:.35;cursor:default}input[type=checkbox]{accent-color:#2563eb}table{width:100%;border-collapse:collapse;text-align:left;min-width:520px}td,th{padding:11px;border-bottom:1px solid var(--divider-color,#384358);font-size:12px}th{color:var(--secondary-text-color,#a8b6c7)}td code{font-size:11px;color:var(--secondary-text-color,#a8b6c7)}.scroll{overflow:auto}.tag{font-size:11px;border:1px solid var(--divider-color,#555);border-radius:30px;padding:4px 8px;color:#fbbf24}.red{color:#fb7185}.green{color:#34d399}.warning{border:1px solid #be123c;border-radius:12px;padding:16px;margin-top:18px}.notice{padding:12px;border:1px solid var(--divider-color,#435169);border-radius:9px;white-space:pre-wrap;font-size:12px;margin:12px 0}.config{display:grid;grid-template-columns:160px minmax(0,1fr);gap:10px;align-items:center;margin:10px 0}.config input,.config select{width:100%;max-width:100%}.config>div{min-width:0}.config .btn{margin-top:8px}a{color:#60a5fa} @media(max-width:820px){.hero{grid-template-columns:1fr}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.little{grid-template-columns:repeat(2,minmax(0,1fr))}}@media(max-width:540px){main{padding:16px 10px}.cards{gap:8px}.card{padding:12px}.card .value{font-size:25px}.summary b{font-size:22px}.config{grid-template-columns:1fr}}';
class HADoctorPanel extends HTMLElement{
 constructor(){super();this.attachShadow({mode:'open'});this._hass=null;this.tab='overview';this.search='';this.selected=new Set();this.includeMissing=false;this.registry=null;this.registryError='';this.loading=false;this.pending=[];this.backupReady=false;this.confirmText='';this.operation='remove';this.message='';this.busy=false;this.timer=null;this.lastRender=0;this.sources={};this.sourceDraft=null;try{this.sources=JSON.parse(localStorage.getItem('ha_doctor_sources')||'{}')||{};}catch(_){}}
 connectedCallback(){this.shadowRoot.addEventListener('click',e=>this.clicked(e));this.shadowRoot.addEventListener('change',e=>this.changed(e));this.shadowRoot.addEventListener('input',e=>this.typed(e));this.render();}
 disconnectedCallback(){clearTimeout(this.timer);}
 set hass(value){this._hass=value;if(!this.isConnected)return;if((this.tab==='settings'||(this.tab==='cleanup'&&this.pending.length))&&!this.busy)return;if(Date.now()-this.lastRender>4500)this.render();else if(!this.timer)this.timer=setTimeout(()=>{this.timer=null;this.render();},4500);}
 get hass(){return this._hass;}
 set panel(value){this._panel=value;}
 get panel(){return this._panel;}
 measurement(key){const ent=pick(key,this._hass?.states||{},this.sources[key]);return{ent,value:read(key,ent)};}
 tile(key){const [label,unit,color]=LABELS[key];const r=this.measurement(key);const display=r.value===null?'—':r.value.toFixed(1);const pct=unit==='%'?r.value:unit==='°C'&&r.value!==null?r.value/90*100:null;const width=Math.min(100,Math.max(0,pct||0));return '<div class="card"><div><b>'+esc(label)+'</b><span style="float:right;color:'+color+'">●</span></div><div class="value">'+display+' <small>'+(r.value===null?'':unit)+'</small></div>'+(pct===null?'':'<div class="bar"><span style="width:'+width+'%;background:'+color+'"></span></div>')+'<code>'+esc(r.ent?.entity_id||'Anturia ei löytynyt – valitse lähde')+'</code></div>';}
 additional(key){const r=this.measurement(key);let v=r.value===null?'—':key==='last_boot'?uptime(r.value):r.value.toFixed(1);const unit=key==='last_boot'?'':r.ent?.attributes?.unit_of_measurement||LABELS[key][1];return '<div class="smallcard"><small>'+esc(LABELS[key][0])+'</small><strong>'+esc(v)+' <small>'+esc(unit)+'</small></strong><code>'+esc(r.ent?.entity_id||'Ei anturia')+'</code></div>';}
 overview(bad){const states=this._hass?.states||{},total=Object.keys(states).filter(id=>id.startsWith('sensor.')).length,unavailable=bad.filter(x=>x.state==='unavailable').length;const score=total?Math.round((total-bad.length)*100/total)+'%':'—';return '<div class="hero"><section class="surface welcome"><h2>System Lab</h2><p>Raspberry Pi 5:n ja Home Assistantin laitteistomittarit sekä anturien saatavuus. Näytetään vain oikeiden HA-sensorien arvot.</p><div class="score">'+score+'</div><small>Anturien saatavuus juuri nyt</small></section><section class="surface summary"><div><small>ANTUREITA</small><b>'+total+'</b></div><div><small>UNAVAILABLE</small><b class="red">'+unavailable+'</b></div><div><small>MUUT VIAT</small><b>'+Math.max(0,bad.length-unavailable)+'</b></div></section></div><div class="section"><h2>🖥 Tekniikkataulu</h2><small>Live • Home Assistant -sensorit</small></div><div class="cards">'+['cpu','ram','disk','cpu_temp','gpu','gpu_temp'].map(k=>this.tile(k)).join('')+'</div><div class="section"><h2>Lisätiedot</h2></div><div class="little">'+['swap','mem_free','mem_used','last_boot','net_in','net_out'].map(k=>this.additional(k)).join('')+'</div><p class="hint">Lisää Home Assistantin System Monitor -integraatio ja ota sen mittarit käyttöön. GPU-kuormaa ja GPU-lämpöä ei voi luotettavasti lukea HA OS:ssa ilman niitä tarjoavaa erillistä sensoria. Puuttuvat mittarit näkyvät viivana. Levyn käyttö voi koskea HA:n käytettävissä olevaa tiedostojärjestelmää, ei koko host-levyä.</p><section class="surface box"><h2>Anturihäiriöt ('+bad.length+')</h2>'+(!bad.length?'<p class="green">Kaikki aktiiviset anturit raportoivat kelvollisen tilan.</p>':'<p>'+bad.slice(0,7).map(x=>esc(x.id)+' ('+esc(x.state)+')').join('<br>')+'</p>')+'<button class="btn" data-tab="cleanup">Avaa anturien siivous →</button></section>';}
 allCandidates(bad){const missing=this.includeMissing?missingRegistry(this.registry,this._hass?.states||{}):[];return bad.concat(missing).filter(x=>(x.id+' '+x.name+' '+x.state).toLowerCase().includes(this.search.toLowerCase()));}
 cleanup(bad){const rows=this.allCandidates(bad),registered=new Set((this.registry||[]).map(x=>x.entity_id)),count=[...this.selected].filter(x=>registered.has(x)).length;const list=rows.map(x=>'<tr><td><input type="checkbox" data-select="'+esc(x.id)+'" '+(this.selected.has(x.id)?'checked ':'')+(!registered.has(x.id)?'disabled ':'')+'></td><td>'+esc(x.name)+'<br><code>'+esc(x.id)+'</code>'+(x.disabled_by?'<br><small>Disabled: '+esc(x.disabled_by)+'</small>':'')+'</td><td><span class="tag">'+esc(x.state)+'</span></td><td>'+esc(x.changed?new Date(x.changed).toLocaleString('fi-FI'):'—')+'</td></tr>').join('');return '<section class="surface box"><h2>⚠ Sensor Cleanup</h2><p>Valitse vikatilaiset anturit, jotka todella haluat poistaa <b>entiteettirekisteristä</b>. Pelkkä unavailable ei tarkoita pysyvää vikaa. Integraatio voi luoda anturin myöhemmin uudelleen. Toiminto ei poista historiaa eikä tee muutoksia automaattisesti.</p><div class="controls"><input type="search" id="search" placeholder="Hae anturia" value="'+esc(this.search)+'"><button class="btn" data-action="refresh">Päivitä rekisteri</button><button class="btn" data-action="all">Valitse kaikki näkyvät</button><button class="btn" data-action="clear">Tyhjennä</button></div><label><input type="checkbox" id="missing" '+(this.includeMissing?'checked':'')+'> Näytä myös rekisterissä olevat, mutta tiloista puuttuvat (voivat olla tarkoituksella pois käytöstä!)</label><div class="controls"><small>'+rows.length+' näkyvissä · '+this.selected.size+' valittu · '+count+' rekisterissä</small><button class="btn blue" data-action="prepare" '+(count&&!this.busy?'':'disabled')+'>Tarkista poistettavat ('+count+')</button></div>'+(this.registryError?'<div class="notice red">'+esc(this.registryError)+'</div>':'')+(!this.registry?'<div class="notice">Lataa entity registry ennen poistoa.</div>':'')+'<div class="scroll"><table><thead><tr><th>Valinta</th><th>Anturi</th><th>Tila</th><th>Muutos</th></tr></thead><tbody>'+list+'</tbody></table></div>'+(!rows.length?'<p>Ei osumia.</p>':'')+(this.pending.length?'<div class="warning"><b class="red">⚠ Poistaminen vaatii vahvistuksen</b><p>'+this.pending.length+' rekisterimerkintää valittu. Ota ensin täydellinen Home Assistant -varmuuskopio. Alla ladattava JSON on vain metadataa, ei palautettava HA-varmuuskopio.</p><p><code>'+esc(this.pending.join(', '))+'</code></p><div class="controls"><button class="btn" data-action="backup">⬇ Lataa valinnan metatiedot</button><button class="btn '+(this.operation==='remove'?'blue':'')+'" data-action="mode-remove">Poista rekisteristä</button><button class="btn '+(this.operation==='disable'?'blue':'')+'" data-action="mode-disable">Poista käytöstä</button><input type="text" id="phrase" placeholder="'+(this.operation==='disable'?'DISABLE ':'DELETE ')+this.pending.length+'" value="'+esc(this.confirmText)+'" autocomplete="off" spellcheck="false"><button class="btn danger" data-action="apply" '+(!this.backupReady||this.busy?'disabled':'')+'>'+((this.operation==='disable')?'Poista käytöstä ':'Poista rekisteristä ')+this.pending.length+' valittua</button><button class="btn" data-action="cancel">Peruuta</button></div><small>Syötä '+(this.operation==='disable'?'DISABLE ':'DELETE ')+this.pending.length+'. Poisto voi olla tilapäinen, jos integraatio luo anturin uudelleen. Käytöstä poisto säilyttää rekisterimerkinnän, mutta estää normaalisti anturin lataamisen. Jokainen anturi tarkistetaan uudelleen.</small></div>':'')+(this.message?'<div class="notice">'+esc(this.message)+'</div>':'')+'</section>';}
 settings(){
 const states=this._hass?.states||{},draft=this.sourceDraft||this.sources;
 const rows=Object.keys(METRICS).map(k=>{
  const recommended=monitorCandidates(k,this.registry,states),recommendedIds=new Set(recommended.map(r=>r.entity_id));
  const ids=[...recommended.map(r=>r.entity_id),...Object.keys(states).filter(id=>id.startsWith('sensor.')&&!recommendedIds.has(id)).sort()];
  if(draft[k]&&!ids.includes(draft[k]))ids.unshift(draft[k]);
  const current=pick(k,states,draft[k]);
  const options=ids.map(id=>{const r=recommended.find(r=>r.entity_id===id),e=states[id];return '<option value="'+esc(id)+'" '+(draft[k]===id?'selected':'')+'>'+esc((r?'★ ':'')+(e?.attributes?.friendly_name||r?.name||r?.original_name||id)+' — '+id+' — '+(r?.disabled_by?'Pois käytöstä':e?e.state+' '+(e.attributes?.unit_of_measurement||''):'Ei saatavilla'))+'</option>';}).join('');
  const entry=(this.registry||[]).find(r=>r.entity_id===draft[k]);
  return '<div class="config"><label for="source-'+k+'">'+esc(LABELS[k][0])+'</label><div><select id="source-'+k+'" data-source="'+k+'"><option value="">Automaattinen'+(current?' — '+esc(current.entity_id):' — ei anturia')+'</option>'+options+'</select>'+(entry?.platform==='systemmonitor'&&entry.disabled_by?'<button class="btn" data-action="enable-source" data-metric="'+k+'" '+(this.busy?'disabled':'')+'>Ota valittu anturi käyttöön</button>':'')+'</div></div>';
 }).join('');
 return '<section class="surface box"><h2>⚙ Mittarien lähteet</h2><p>Valitse anturi nimen, entity-tunnuksen ja nykyarvon perusteella. ★ merkitsee tämän mittarin System monitor -ehdokasta. Valinnat tallennetaan tämän selaimen muistiin.</p><div class="controls"><a class="btn" href="/config/integrations/dashboard/add?domain=systemmonitor">Lisää System monitor</a><button class="btn" data-action="refresh" '+(this.loading?'disabled':'')+'>Hae anturit uudelleen</button><button class="btn" data-action="detect" '+(!this.registry?'disabled':'')+'>Etsi Raspberry Pi:n mittarit</button></div><p>System monitorin anturit ovat aluksi pois käytöstä. Valitse tähdellä merkitty anturi ja paina tarvittaessa ”Ota valittu anturi käyttöön”. Arvon ilmestymisessä voi kestää hetki. Jos ehdokkaita on useita, tarkista oikea levy ja verkkoliitäntä. GPU vaatii erilliset anturit.</p>'+(this.registryError?'<div class="notice red">'+esc(this.registryError)+'</div>':'')+(this.loading?'<p>Haetaan entiteettirekisteriä…</p>':'')+rows+'<div class="controls"><button class="btn blue" data-action="save">Tallenna</button><button class="btn" data-action="reset">Palauta automaattinen</button></div>'+(this.message?'<div class="notice" role="status">'+esc(this.message)+'</div>':'')+'</section>';
 }

 render(){if(!this.isConnected)return;this.lastRender=Date.now();const bad=badSensors(this._hass?.states||{});this.shadowRoot.innerHTML='<style>'+CSS+'</style><main><header class="top"><div class="brand"><span class="logo">✚</span><div><h1>HA Doctor / System Lab</h1><div class="sub">Raspberry Pi · Diagnostics · v0.4.1</div></div></div><span class="live">● '+(this._hass?'Home Assistant yhdistetty':'Odotetaan yhteyttä')+'</span></header><nav class="tabs">'+[['overview','Yleiskuva'],['cleanup','Anturien siivous ('+bad.length+')'],['settings','Mittarilähteet']].map(x=>'<button class="tab '+(this.tab===x[0]?'active':'')+'" data-tab="'+x[0]+'">'+x[1]+'</button>').join('')+'</nav>'+(this.tab==='overview'?this.overview(bad):this.tab==='cleanup'?this.cleanup(bad):this.settings())+'</main>';}
 typed(ev){if(ev.target?.id==='phrase'){this.confirmText=ev.target.value;return;}if(ev.target?.id==='search'){this.search=ev.target.value;const p=ev.target.selectionStart;this.render();const input=this.shadowRoot.getElementById('search');input?.focus();try{input?.setSelectionRange(p,p)}catch(_){}}}
 changed(ev){if(ev.target?.dataset?.source){this.sourceDraft={...(this.sourceDraft||this.sources),[ev.target.dataset.source]:ev.target.value};this.render();return;}if(ev.target?.id==='missing'){this.includeMissing=ev.target.checked;this.pending=[];this.render();}if(ev.target?.dataset?.select){const id=ev.target.dataset.select;ev.target.checked?this.selected.add(id):this.selected.delete(id);this.pending=[];this.render();}}
 async clicked(ev){const b=ev.target.closest('button');if(!b)return;if(b.dataset.tab){this.tab=b.dataset.tab;this.pending=[];this.message='';this.render();if(['cleanup','settings'].includes(this.tab)&&!this.registry)await this.fetchRegistry();return;}
 const a=b.dataset.action;if(!a)return;
 if(a==='refresh')return this.fetchRegistry();
 if(a==='detect'){
  this.sourceDraft={...(this.sourceDraft||this.sources)};let count=0;
  for(const key of Object.keys(METRICS)){const rows=monitorCandidates(key,this.registry,this._hass?.states);if(rows.length){this.sourceDraft[key]=rows[0].entity_id;count++;}}
  this.message=count+' mittaria löytyi. Tarkista valinnat, aktivoi tarvittaessa anturit ja paina Tallenna.';this.render();return;
 }
 if(a==='enable-source')return this.enableSource(b.dataset.metric);

 if(a==='all'){const ok=new Set((this.registry||[]).map(x=>x.entity_id));this.allCandidates(badSensors(this._hass?.states||{})).forEach(x=>{if(ok.has(x.id))this.selected.add(x.id)});this.pending=[];this.render();return;}
 if(a==='clear'){this.selected.clear();this.pending=[];this.render();return;}
 if(a==='cancel'){this.pending=[];this.backupReady=false;this.confirmText='';this.render();return;}
 if(a==='prepare'){const registered=new Set((this.registry||[]).map(x=>x.entity_id));this.pending=[...this.selected].filter(id=>registered.has(id)&&(isBad(id,this._hass?.states)||(this.includeMissing&&!this._hass?.states?.[id]))).sort();this.backupReady=false;this.confirmText='';this.render();return;}
 if(a==='backup'){if(!this.pending.length||!this.registry)return;const ids=new Set(this.pending),blob=new Blob([JSON.stringify({warning:'Metadata export, NOT a restorable Home Assistant backup',created:new Date().toISOString(),entries:this.registry.filter(x=>ids.has(x.entity_id))},null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='ha-doctor-registry-'+new Date().toISOString().slice(0,10)+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),2000);this.backupReady=true;this.render();return;}
 if(a==='mode-remove'||a==='mode-disable'){this.operation=a==='mode-disable'?'disable':'remove';this.confirmText='';this.message='';this.render();return;}
 if(a==='apply')return this.removeSelected();
 if(a==='save'){const data={};this.shadowRoot.querySelectorAll('[data-source]').forEach(x=>{if(x.value.trim())data[x.dataset.source]=x.value.trim()});this.sources=data;this.sourceDraft=null;try{localStorage.setItem('ha_doctor_sources',JSON.stringify(data))}catch(_){}this.message='Lähteet tallennettu.';this.render();return;}
 if(a==='reset'){this.sources={};this.sourceDraft=null;this.sourceDraft=null;try{localStorage.removeItem('ha_doctor_sources')}catch(_){}this.message='Automaattinen tunnistus käytössä.';this.render();}
 }
 async enableSource(metric){
  if(this.busy)return;
  const id=(this.sourceDraft||this.sources)[metric];
  this.busy=true;this.message='Otetaan anturi käyttöön…';this.render();
  try{
   if(this._hass?.user?.is_admin!==true)throw Error('Toiminto vaatii ylläpitäjän oikeudet.');
   const rows=await this._hass.callWS({type:'config/entity_registry/list'});
   const entry=rows.find(r=>r.entity_id===id);
   if(!entry||entry.platform!=='systemmonitor')throw Error('Valitse System monitor -anturi.');
   if(['device','config_entry','system'].includes(entry.disabled_by))throw Error('Ota ensin integraatio käyttöön Asetukset → Laitteet ja palvelut -sivulla.');
   await this._hass.callWS({type:'config/entity_registry/update',entity_id:id,disabled_by:null});
   this.registry=await this._hass.callWS({type:'config/entity_registry/list'});
   this.message=id+' otettu käyttöön. Odota hetki, hae anturit uudelleen ja tallenna valinnat.';
  }catch(err){this.message='Käyttöönotto epäonnistui: '+String(err?.message||err);}
  finally{this.busy=false;this.render();}
 }
 async fetchRegistry(){if(!this._hass?.callWS)return;this.loading=true;this.registryError='';this.render();try{const r=await this._hass.callWS({type:'config/entity_registry/list'});if(!Array.isArray(r))throw Error('Virheellinen rekisterivastaus');this.registry=r;}catch(err){this.registry=null;this.registryError=String(err?.message||err)}finally{this.loading=false;this.render()}}
 async removeSelected(){
  if(this.busy)return;
  if(this._hass?.user?.is_admin!==true){
   this.message='Toiminto estetty: kirjaudu Home Assistantin yllapitajana.';
   this.render();return;
  }
  if(!this.backupReady||!this.pending.length){
   this.message='Valitse anturit, tarkista valinta ja lataa metatietoraportti ensin.';
   this.render();return;
  }
  const expected=(this.operation==='disable'?'DISABLE ':'DELETE ')+this.pending.length;
  if(this.confirmText.trim()!==expected){
   this.message='Kirjoita tasan '+expected;this.render();return;
  }
  this.busy=true;this.message='Tarkistetaan entiteettirekisteria…';this.render();
  try{
   const result=await applyRegistryCleanup({
    mode:this.operation,ids:[...this.pending],originalRegistry:this.registry,
    includeMissing:this.includeMissing,
    callWS:message=>this._hass.callWS(message),
    getStates:()=>this._hass?.states||{}
   });
   this.registry=result.registry;
   for(const id of result.verified)this.selected.delete(id);
   const description=this.operation==='disable'?'Poistettu kaytosta':'Vahvistetusti poistettu rekisterista';
   const secondary=this.operation==='disable'?'Ei vahvistetusti poistettu kaytosta':'Yha rekisterissa / luotu uudelleen';
   this.message=description+': '+result.verified.length+
    ' | '+secondary+': '+result.present.length+
    ' | ei voitu varmistaa: '+result.unverified.length+
    ' | ohitettu: '+(result.skipped.length+result.alreadyDisabled.length)+
    ' | virheita: '+result.failed.length+
    (result.present.length?'\n'+result.present.join('\n'):'')+
    (result.unverified.length?'\nVarmistus epaonnistui: '+result.verificationError+'\n'+result.unverified.join('\n'):'')+
    (result.skipped.length||result.failed.length?'\n'+result.skipped.concat(result.failed).join('\n'):'')+
    (result.alreadyDisabled.length?'\nJo poistettu kaytosta: '+result.alreadyDisabled.join(', '):'')+
    (this.operation==='remove'&&result.present.length?'\nIntegraatio voi luoda anturit uudelleen. Valitse ne ja kayta erillista Poista kaytosta -toimintoa.':'')+
    (this.operation==='disable'&&result.verified.length?'\nKestava kaytostapoisto voi vaatia integraation uudelleenlatauksen tai HA:n kaynnistyksen.':'');
  }catch(error){
   this.message='Muutoksia ei voitu vahvistaa: '+String(error?.message||error);
  }finally{
   this.busy=false;this.pending=[];this.backupReady=false;this.confirmText='';this.render();
  }
 }

}
if(!customElements.get('ha-doctor-panel'))customElements.define('ha-doctor-panel',HADoctorPanel);
