/** Pure frontend helpers. Never assume a missing entity is broken. */
export const METRICS={
 cpu:['processor_use','cpu_usage','cpu_use'],ram:['memory_usage','memory_use_percent','ram_usage'],
 disk:['disk_use_percent','disk_usage_percent','disk_usage'],
 cpu_temp:['processor_temperature','cpu_temperature','cpu_temp','soc_temperature'],
 gpu:['gpu_usage','gpu_utilization','gpu_load'],gpu_temp:['gpu_temperature','gpu_temp'],
 swap:['swap_use_percent','swap_usage_percent'],mem_free:['memory_free'],mem_used:['memory_use','memory_used'],
 last_boot:['last_boot','system_uptime'],net_in:['network_throughput_in','download_speed'],
 net_out:['network_throughput_out','upload_speed']
};
export const BAD=new Set(['unavailable','unknown','']);
export function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
export function badSensors(states){
 return Object.entries(states||{}).filter(([id,e])=>id.startsWith('sensor.')&&e&&BAD.has(String(e.state??'').trim().toLowerCase()))
 .map(([id,e])=>({id,name:String(e.attributes?.friendly_name||id),state:String(e.state??'').trim().toLowerCase()||'empty',changed:e.last_changed||''}))
 .sort((a,b)=>a.id.localeCompare(b.id));
}
export function isBad(id,states){return !!states?.[id]&&badSensors({[id]:states[id]}).length>0;}
export function missingRegistry(registry,states){return (registry||[]).filter(r=>r.entity_id?.startsWith('sensor.')&&!states?.[r.entity_id])
 .map(r=>({id:r.entity_id,name:r.name||r.original_name||r.entity_id,state:'missing',changed:'',disabled_by:r.disabled_by}));}
export function pick(metric,states,override){
 if(override&&states?.[override]?.entity_id?.startsWith('sensor.'))return states[override];
 let best=null,bestScore=0;
 for(const e of Object.values(states||{})){
  if(!e?.entity_id?.startsWith('sensor.'))continue;
  const key=e.entity_id.slice(7).toLowerCase(),unit=String(e.attributes?.unit_of_measurement||'').toLowerCase();
  const candidates=METRICS[metric]||[];
  if(['cpu','ram','disk','gpu','swap'].includes(metric)&&unit&&unit!=='%')continue;
  if(['cpu_temp','gpu_temp'].includes(metric)&&unit&&!['°c','°f','c','f'].includes(unit))continue;
  const exact=candidates.some(k=>key===k||key.endsWith('_'+k));
  const matches=candidates.some(k=>key.includes(k));
  if(!exact && !matches)continue;
  const score=(exact?100:matches?45:0)+(key.startsWith('system_monitor_')?20:0);
  if(score>bestScore){best=e;bestScore=score;}
 }
 return best;
}
export function read(metric,ent){
 if(!ent||BAD.has(String(ent.state??'').trim().toLowerCase()))return null;
 if(metric==='last_boot'){let d=Date.parse(ent.state);return Number.isFinite(d)?d:null;}
 const n=Number(ent.state);
 if(!Number.isFinite(n))return null;
 const unit=String(ent.attributes?.unit_of_measurement||'').toLowerCase();
 return (metric==='cpu_temp'||metric==='gpu_temp')&&['°f','f'].includes(unit)?(n-32)*5/9:n;
}
export function uptime(ms){if(!Number.isFinite(ms))return '—';let s=Math.max(0,Math.floor((Date.now()-ms)/1000));return Math.floor(s/86400)+'d '+Math.floor((s%86400)/3600)+'h '+Math.floor((s%3600)/60)+'m';}

/** Avoid removing a replacement which reused an existing entity_id. */
export function sameRegistryIdentity(before, after){
 if(!before||!after||before.entity_id!==after.entity_id)return false;
 return ['unique_id','platform','config_entry_id','device_id'].every(k=>(before[k]??null)===(after[k]??null));
}
