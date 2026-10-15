import {test} from 'node:test';
import assert from 'node:assert/strict';
import {applyRegistryCleanup} from '../custom_components/ha_doctor/frontend/cleanup_actions.mjs';
const ent=(id,unique_id)=>({entity_id:id,unique_id,platform:'demo',config_entry_id:'demo_config',disabled_by:null});
const state=(id,s)=>({entity_id:id,state:s,attributes:{}});
function fixture({recreate=false,failRemove=false,afterFail=false,changed=false,disabled=false}={}){
 const orig=ent('sensor.old','original'),registry=new Map([[orig.entity_id,{...orig}]]);
 if(changed)registry.get(orig.entity_id).unique_id='replacement';
 if(disabled)registry.get(orig.entity_id).disabled_by='user';
 let count=0;const commands=[];
 const callWS=async msg=>{
  commands.push(msg);
  if(msg.type==='config/entity_registry/list'){
    count++;if(afterFail&&count===2)throw Error('connection lost');
    return [...registry.values()].map(e=>({...e}));
  }
  if(msg.type==='config/entity_registry/remove'){
    if(failRemove)throw Error('permission denied');
    registry.delete(msg.entity_id);
    if(recreate)registry.set(msg.entity_id,{...orig});
  }else if(msg.type==='config/entity_registry/update')registry.get(msg.entity_id).disabled_by=msg.disabled_by;
 };
 return {orig,registry,commands,callWS};
}
const run=(f,mode='remove',states={'sensor.old':state('sensor.old','unavailable')})=>
 applyRegistryCleanup({mode,ids:['sensor.old'],originalRegistry:[f.orig],
   callWS:f.callWS,getStates:()=>states});
test('deletion is verified missing, not merely accepted',async()=>{
 const f=fixture();const r=await run(f);
 assert.deepEqual(r.verified,['sensor.old']);assert.deepEqual(r.present,[]);
 assert.equal(f.commands[1].type,'config/entity_registry/remove');
});
test('recreated entity is NEVER counted as deleted',async()=>{
 const f=fixture({recreate:true});const r=await run(f);
 assert.deepEqual(r.verified,[]);assert.deepEqual(r.present,['sensor.old']);
});
test('disable persists in registry as disabled_by user',async()=>{
 const f=fixture();const r=await run(f,'disable');
 assert.deepEqual(r.verified,['sensor.old']);
 assert.equal(f.registry.get('sensor.old').disabled_by,'user');
 assert.equal(f.commands[1].type,'config/entity_registry/update');
});
test('already disabled sensor is skipped without API write',async()=>{
 const f=fixture({disabled:true});const r=await run(f,'disable');
 assert.deepEqual(r.alreadyDisabled,['sensor.old']);assert.equal(f.commands.length,2);
});
test('never edit replacement with changed registry identity',async()=>{
 const f=fixture({changed:true});const r=await run(f);
 assert.equal(r.skipped.length,1);assert.equal(f.commands.length,2);
});
test('never edit sensor that recovered',async()=>{
 const f=fixture();const r=await run(f,'remove',{'sensor.old':state('sensor.old','24.8')});
 assert.equal(r.skipped.length,1);assert.equal(f.commands.length,2);
});
test('API error is reported rather than claiming deletion',async()=>{
 const f=fixture({failRemove:true});const r=await run(f);
 assert.equal(r.failed.length,1);assert.deepEqual(r.verified,[]);
});
test('failed verification is reported as unverified',async()=>{
 const f=fixture({afterFail:true});const r=await run(f);
 assert.deepEqual(r.unverified,['sensor.old']);assert.deepEqual(r.verified,[]);
});
test('reject invalid or duplicate selection before any API call',async()=>{
 const f=fixture();
 await assert.rejects(applyRegistryCleanup({mode:'remove',ids:['sensor.old','sensor.old'],
   originalRegistry:[f.orig],callWS:f.callWS,getStates:()=>({})}));
 assert.equal(f.commands.length,0);
});
