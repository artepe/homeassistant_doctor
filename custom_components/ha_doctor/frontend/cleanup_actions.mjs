/** Safely apply explicitly confirmed entity registry actions.
 * Registry removal and disabling are different operations. Never claim a
 * deletion until a new registry read proves that the entry is absent.
 */
import {isBad, sameRegistryIdentity} from './metrics.mjs';

export async function applyRegistryCleanup({mode, ids, originalRegistry, includeMissing=false, callWS, getStates}){
  if(!['remove','disable'].includes(mode))throw Error('Invalid cleanup mode');
  if(!Array.isArray(ids)||ids.length===0||ids.length>5000||new Set(ids).size!==ids.length ||
     ids.some(id=>typeof id!=='string'||!id.startsWith('sensor.')))throw Error('Invalid sensor selection');
  if(typeof callWS!=='function'||typeof getStates!=='function')throw Error('Missing Home Assistant connection');
  const original=new Map((originalRegistry||[]).map(e=>[e.entity_id,e]));
  const fresh=await callWS({type:'config/entity_registry/list'});
  if(!Array.isArray(fresh))throw Error('Rekisterin alkuvahvistus epaonnistui');
  const current=new Map(fresh.map(e=>[e.entity_id,e]));
  const sent=[],skipped=[],failed=[],alreadyDisabled=[];
  for(const id of ids){
    const before=original.get(id),entry=current.get(id);
    if(!before||!entry){skipped.push(id+': ei enaa rekisterissa');continue;}
    if(!sameRegistryIdentity(before,entry)){skipped.push(id+': tunniste vaihtunut');continue;}
    const states=getStates()||{};
    if(!(isBad(id,states)||(includeMissing&&!states[id]))){
      skipped.push(id+': anturi toimii taas');continue;
    }
    if(mode==='disable'){
      if(entry.disabled_by==='user'){alreadyDisabled.push(id);continue;}
      if(entry.disabled_by){skipped.push(id+': poistettu kaytosta jo ('+entry.disabled_by+')');continue;}
    }
    try{
      await callWS(mode==='remove'
        ? {type:'config/entity_registry/remove',entity_id:id}
        : {type:'config/entity_registry/update',entity_id:id,disabled_by:'user'});
      sent.push(id);
    }catch(error){
      failed.push(id+': '+String(error?.message||error));
    }
  }
  let after=null,verificationError='';
  try{
    after=await callWS({type:'config/entity_registry/list'});
    if(!Array.isArray(after))throw Error('Virheellinen rekisterivastaus');
  }catch(error){verificationError=String(error?.message||error);}
  const verified=[],present=[],unverified=[];
  if(after){
    const check=new Map(after.map(e=>[e.entity_id,e]));
    for(const id of sent){
      const entry=check.get(id);
      if(mode==='remove'){
        if(!entry)verified.push(id);
        else present.push(id);
      }else{
        if(entry?.disabled_by==='user'&&sameRegistryIdentity(original.get(id),entry))verified.push(id);
        else present.push(id);
      }
    }
  }else unverified.push(...sent);
  return {mode,verified,present,unverified,alreadyDisabled,skipped,failed,verificationError,registry:after};
}
