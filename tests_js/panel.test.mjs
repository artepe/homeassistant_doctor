import {test} from 'node:test';
import assert from 'node:assert/strict';
globalThis.HTMLElement=class{attachShadow(){this.shadowRoot={};}};
globalThis.localStorage={getItem:()=>null};
let Panel;
globalThis.customElements={get:()=>null,define:(_name,cls)=>{Panel=cls;}};
await import('../custom_components/ha_doctor/frontend/panel.js');
test('activation accepts default integration-disabled monitor sensor and preserves draft',async()=>{
 const panel=new Panel();panel.render=()=>{};
 panel.sourceDraft={cpu:'sensor.my_cpu'};const calls=[];
 panel.hass={user:{is_admin:true},callWS:async msg=>{calls.push(msg);return [{entity_id:'sensor.my_cpu',platform:'systemmonitor',disabled_by:'integration'}];}};
 await panel.enableSource('cpu');
 assert.deepEqual(calls[1],{type:'config/entity_registry/update',entity_id:'sensor.my_cpu',disabled_by:null});
 assert.equal(panel.sourceDraft.cpu,'sensor.my_cpu');assert.equal(panel.busy,false);
});
test('activation refuses another integration and non-admin user',async()=>{
 for(const admin of [true,false]){
  const panel=new Panel();panel.render=()=>{};panel.sourceDraft={cpu:'sensor.remote'};const calls=[];
  panel.hass={user:{is_admin:admin},callWS:async msg=>{calls.push(msg);return [{entity_id:'sensor.remote',platform:'other',disabled_by:'user'}];}};
  await panel.enableSource('cpu');assert.equal(calls.some(x=>x.type.endsWith('/update')),false);
  assert.match(panel.message,/epäonnistui/);
 }
});
