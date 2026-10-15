import {test} from 'node:test';
import assert from 'node:assert/strict';
import {esc,badSensors,isBad,missingRegistry,pick,read,uptime,sameRegistryIdentity,monitorCandidates} from '../custom_components/ha_doctor/frontend/metrics.mjs';
const ent=(id,state,unit='')=>({entity_id:id,state:String(state),attributes:{unit_of_measurement:unit}});
test('unavailable and unknown only on sensor.*',()=>{
 const states={'sensor.a':ent('sensor.a','unavailable'),'sensor.b':ent('sensor.b','unknown'),'sensor.c':ent('sensor.c',12),'binary_sensor.d':ent('binary_sensor.d','unavailable')};
 assert.deepEqual(badSensors(states).map(x=>x.id),['sensor.a','sensor.b']);
});
test('missing state cannot be deleted as live faulty',()=>{
 assert.equal(isBad('sensor.none',{}),false);
 assert.equal(isBad('sensor.none',{'sensor.none':ent('sensor.none','unknown')}),true);
});
test('disabled registry is identified separately',()=>{
 assert.deepEqual(missingRegistry([{entity_id:'sensor.missing',disabled_by:'user'}],{}).map(x=>x.state),['missing']);
});
test('prefers system monitor CPU',()=>{
 const s={'sensor.other_cpu_use':ent('sensor.other_cpu_use',8,'%'),'sensor.system_monitor_processor_use':ent('sensor.system_monitor_processor_use',37,'%')};
 assert.equal(pick('cpu',s).entity_id,'sensor.system_monitor_processor_use');
});
test('GPU readings never borrowed from CPU',()=>{
 assert.equal(pick('gpu',{'sensor.system_monitor_processor_use':ent('sensor.system_monitor_processor_use',22,'%')}),null);
 assert.equal(pick('gpu_temp',{'sensor.cpu_temperature':ent('sensor.cpu_temperature',40,'°C')}),null);
});
test('Fahrenheit processor to Celsius',()=>assert.equal(read('cpu_temp',ent('sensor.cpu_temperature',212,'°F')),100));
test('unknown measurement is not treated as numeric',()=>assert.equal(read('cpu',ent('sensor.processor_use','unknown','%')),null));
test('uptime placeholder and clock arithmetic',()=>{
 assert.equal(uptime(null),'—');
});
test('escapes HTML and quotes',()=>assert.equal(esc('<img x="1">'),'&lt;img x=&quot;1&quot;&gt;'));

test('bulk delete refuses replacement registry entry',()=>{
 const a={entity_id:'sensor.bad',unique_id:'one',platform:'demo',config_entry_id:'a'};
 assert.equal(sameRegistryIdentity(a,{...a,name:'new label'}),true);
 assert.equal(sameRegistryIdentity(a,{...a,unique_id:'two'}),false);
 assert.equal(sameRegistryIdentity(a,{...a,config_entry_id:'b'}),false);
});

test('registry recommendations find renamed and disabled System monitor sensors only',()=>{
 const rows=[{entity_id:'sensor.oma_cpu',platform:'systemmonitor',unique_id:'pi_processor_use',disabled_by:'integration'},{entity_id:'sensor.remote_processor_use',platform:'other',unique_id:'processor_use'}];
 assert.deepEqual(monitorCandidates('cpu',rows,{}).map(r=>r.entity_id),['sensor.oma_cpu']);
 assert.deepEqual(monitorCandidates('gpu',rows,{}),[]);
});
test('memory amount excludes percentage; network excludes counters; uptime supported',()=>{
 const rows=['memory_use','memory_use_percent','network_in_eth0','network_throughput_in_eth0','uptime'].map(key=>({entity_id:'sensor.system_monitor_'+key,platform:'systemmonitor',unique_id:key}));
 assert.deepEqual(monitorCandidates('mem_used',rows,{}).map(r=>r.unique_id),['memory_use']);
 assert.deepEqual(monitorCandidates('net_in',rows,{}).map(r=>r.unique_id),['network_throughput_in_eth0']);
 assert.equal(monitorCandidates('last_boot',rows,{}).length,1);
});
test('missing explicit override does not silently show another device',()=>{
 assert.equal(pick('cpu',{'sensor.processor_use':ent('sensor.processor_use',33,'%')},'sensor.deleted'),null);
});
