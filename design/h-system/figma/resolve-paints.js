
const page=await figma.getNodeByIdAsync('13:4');await figma.setCurrentPageAsync(page);
await Promise.all([{family:'Inter',style:'Regular'},{family:'Inter',style:'Semi Bold'},{family:'Onest',style:'Bold'},{family:'JetBrains Mono',style:'Regular'}].map(f=>figma.loadFontAsync(f)));
const vars=await figma.variables.getLocalVariablesAsync('COLOR');const map=Object.fromEntries(vars.map(v=>[v.id,v]));const collections=await figma.variables.getLocalVariableCollectionsAsync();const col=collections.find(c=>c.name==='H / Semantic studies');const ids=[];
for(const n of page.children){if('setExplicitVariableModeForCollection'in n)n.setExplicitVariableModeForCollection(col,col.defaultModeId);}
for(const n of page.findAll()){for(const field of ['fills','strokes']){if(!(field in n)||!Array.isArray(n[field]))continue;let changed=false;let paints=n[field].map(p=>{const id=p.boundVariables&&p.boundVariables.color&&p.boundVariables.color.id;const v=map[id];if(p.type!=='SOLID'||!v)return p;const rgba=Object.values(v.valuesByMode)[0];changed=true;return {...p,color:{r:rgba.r,g:rgba.g,b:rgba.b}};});if(changed){n[field]=paints;ids.push(n.id);}}}
return {mutatedNodeIds:[...new Set(ids)],fallbackPaintsResolved:true};
