
const page=await figma.getNodeByIdAsync('13:4');await figma.setCurrentPageAsync(page);
await Promise.all([{family:'Inter',style:'Regular'},{family:'Inter',style:'Semi Bold'},{family:'Onest',style:'Bold'},{family:'JetBrains Mono',style:'Regular'}].map(f=>figma.loadFontAsync(f)));
const ids=[page.id];const varIds={"canvas":"VariableID:13:7","surface":"VariableID:13:9","raised":"VariableID:13:11","text":"VariableID:13:13","muted":"VariableID:13:15","accent":"VariableID:13:17","positive":"VariableID:13:19","warning":"VariableID:13:21","danger":"VariableID:13:23","border":"VariableID:13:25"};const vars={};for(const [k,id]of Object.entries(varIds))vars[k]=await figma.variables.getVariableByIdAsync(id);
const rgb=h=>({r:parseInt(h.slice(1,3),16)/255,g:parseInt(h.slice(3,5),16)/255,b:parseInt(h.slice(5,7),16)/255});
const paint=(key)=>figma.variables.setBoundVariableForPaint({type:'SOLID',color:rgb('#19222E')},'color',vars[key]);
function fills(n,key){n.fills=[paint(key)];}
function txt(p,s,size=14,key='text',style='Regular',width=260){let t=figma.createText();ids.push(t.id);t.fontName={family:'Inter',style};t.fontSize=size;t.lineHeight={unit:'PERCENT',value:145};t.characters=s;t.textAutoResize='HEIGHT';t.resize(width,t.height);fills(t,key);p.appendChild(t);return t;}
const iconMap={"home":"13:217","games":"13:222","assistant":"13:227","intelligence":"13:232","activity":"13:237","account":"13:242","devices":"13:248","settings":"13:253","support":"13:258","battle":"13:263","pve":"13:268","pvp":"13:273","character":"13:279","builds":"13:284","talents":"13:289","quests":"13:294","professions":"13:299","resources":"13:304","auction":"13:310","trade":"13:315","inventory":"13:320","leveling":"13:325","rotation":"13:330","capture":"13:335","observe":"13:341","recommendation":"13:346","automation":"13:351","confirmation":"13:356","start":"13:361","pause":"13:366","stop":"13:372","emergency-stop":"13:377","overlay":"13:382","voice":"13:387","diagnostics":"13:392","security":"13:397","connection":"13:403","server":"13:408","updates":"13:413","download":"13:418","upload":"13:423","progress":"13:428","subscription":"13:434","billing":"13:439","notifications":"13:444","history":"13:449","search":"13:454","filters":"13:459","errors":"13:465","chevron-right":"13:470","close":"13:475","menu":"13:480","back":"13:485","unknown":"13:490","offline":"13:496"};const icons={};for(const k of ['stop','unknown','confirmation','observe','search','capture','updates','chevron-right'])icons[k]=await figma.getNodeByIdAsync(iconMap[k]);
let title=figma.createAutoLayout('VERTICAL',{itemSpacing:16,paddingLeft:32,paddingTop:32,paddingRight:32,paddingBottom:32});page.appendChild(title);ids.push(title.id);title.x=3700;title.y=120;title.resize(1200,100);title.primaryAxisSizingMode='AUTO';fills(title,'canvas');txt(title,'H / REUSABLE COMPONENT LIBRARY',32,'text','Semi Bold',1100);txt(title,'Editable variants · semantic variable bindings · text and icon properties\n48px study controls · native target 48dp Android / 44px desktop\nHover 120ms · feedback 180ms · panel 240ms · reduced motion 0ms\nEach state carries visible text and geometry; color is never the only signal.',16,'muted','Regular',1100);
const families=[
['Button',['default','hover','pressed','focus-visible','disabled','loading','success','error'], 'button'],
['IconButton',['default','hover','pressed','focus-visible','disabled'],'icon'],
['Stop',['default','hover','pressed','focus-visible','stopped'],'stop'],
['TextField',['default','hover','focus-visible','disabled','error','success'],'field'],
['Switch',['off','on','focus-visible','disabled'],'switch'],
['Checkbox',['off','on','focus-visible','disabled','error'],'check'],
['Radio',['off','on','focus-visible','disabled'],'radio'],
['Tabs',['default','selected','focus-visible','disabled'],'tab'],
['MenuItem',['default','hover','selected','disabled','denied'],'menu'],
['Status',['success','warning','error','offline','timeout','stale','unknown','unavailable','denied','revoked','stopped'],'status'],
['SourceCard',['loading','empty','unknown','unverified','stale','offline','revoked'],'source'],
['Recommendation',['default','loading','unknown','stale','acknowledged','unavailable'],'recommendation'],
['Progress',['default','loading','success','error','stopped'],'progress'],
['Skeleton',['loading'],'skeleton'],
['EmptyState',['empty','error','offline','timeout','unavailable','denied'],'empty'],
['Dialog',['default','warning','denied'],'dialog'],
['Navigation',['default','selected','focus-visible','disabled'],'nav'],
['DataRow',['default','selected','loading','unknown','stale'],'row'],
['Notification',['success','warning','error','offline'],'notice'],
['Tooltip',['default','unavailable'],'tooltip'],
['Breadcrumb',['default','focus-visible'],'breadcrumb'],
['Pagination',['default','selected','disabled'],'pagination'],
['Filter',['default','selected','focus-visible'],'filter']
];
const sets={};let ypos=420;
for(const [family,states,kind]of families){
 let comps=[];const wide=['source','recommendation','empty','dialog'].includes(kind);let maxH=0;
 for(const state of states){
 let c=figma.createComponent();ids.push(c.id);c.name='state='+state;c.description='H study '+family+' / '+state+'. '+(kind==='stop'?'Stop immediately ends local observation; never blocked by confirmation.':'Keyboard focus visible; Escape closes transient UI; errors preserve input.');c.layoutMode='VERTICAL';c.itemSpacing=12;c.paddingLeft=16;c.paddingRight=16;c.paddingTop=16;c.paddingBottom=16;c.resize(wide?340:280,48);c.primaryAxisSizingMode='AUTO';c.counterAxisSizingMode='FIXED';c.cornerRadius=8;fills(c,kind==='button'&&state==='default'?'accent':'surface');c.strokes=[paint(state==='focus-visible'?'accent':state==='error'||state==='revoked'?'danger':'border')];c.strokeWeight=state==='focus-visible'?3:1;
 const color=kind==='button'&&state==='default'?'canvas':state==='error'||state==='revoked'?'danger':'text';
 const label=kind==='stop'?(state==='stopped'?'Остановлено / Stopped':'Остановить / Stop'):kind==='field'?'Название устройства / Device name':kind==='status'?state.toUpperCase():kind==='source'?'Игровой источник / Game source':kind==='recommendation'?'Проверить источник / Review source':kind==='empty'?'Данные недоступны / Data unavailable':kind==='dialog'?'Подтвердить прочтение / Acknowledge':family+' / '+state;
 if(['button','icon','stop','tab','menu','nav','filter','breadcrumb','pagination'].includes(kind)){
 c.layoutMode='HORIZONTAL';c.counterAxisAlignItems='CENTER';c.primaryAxisAlignItems='CENTER';
 let master=icons[kind==='stop'?'stop':kind==='icon'?'search':kind==='breadcrumb'?'chevron-right':'confirmation'];let i=master.createInstance();ids.push(i.id);c.appendChild(i);const swap=c.addComponentProperty('Icon','INSTANCE_SWAP',master.id);i.componentPropertyReferences={mainComponent:swap};
 if(kind!=='icon'){let t=txt(c,label,14,color,'Semi Bold',220);let prop=c.addComponentProperty('Label','TEXT',label);t.componentPropertyReferences={characters:prop};}
 }else if(['switch','check','radio'].includes(kind)){
 c.layoutMode='HORIZONTAL';c.counterAxisAlignItems='CENTER';
 let shape=kind==='radio'?figma.createEllipse():figma.createRectangle();ids.push(shape.id);shape.resize(kind==='switch'?40:24,24);if('cornerRadius'in shape)shape.cornerRadius=kind==='switch'?12:4;fills(shape,state==='on'?'accent':'raised');shape.strokes=[paint('border')];c.appendChild(shape);
 if(state==='on'&&kind!=='switch'){let i=icons.confirmation.createInstance();ids.push(i.id);c.appendChild(i);}
 txt(c,family,14,'text','Regular',160);
 }else if(kind==='progress'||kind==='skeleton'){
 txt(c,kind==='progress'?'Загрузка / Download · '+state:'Загрузка / Loading',14,'muted');
 let track=figma.createAutoLayout('HORIZONTAL');ids.push(track.id);track.resize(248,8);track.primaryAxisSizingMode='FIXED';track.counterAxisSizingMode='FIXED';track.cornerRadius=4;fills(track,'raised');c.appendChild(track);
 let bar=figma.createRectangle();ids.push(bar.id);bar.resize(state==='success'?248:state==='error'?100:80,8);fills(bar,state==='error'?'danger':'accent');bar.cornerRadius=4;track.appendChild(bar);
 if(kind==='skeleton')for(let width of [200,140]){let b=figma.createRectangle();b.resize(width,12);fills(b,'raised');c.appendChild(b);ids.push(b.id);}
 }else{
 let t=txt(c,label,kind==='dialog'?20:16,color,'Semi Bold',wide?308:248);let prop=c.addComponentProperty('Title','TEXT',label);t.componentPropertyReferences={characters:prop};
 if(kind==='field'){let t=txt(c,state==='error'?'Проверьте значение / Check value':'Companion',14,state==='error'?'danger':'muted', 'Regular',248);let prop=c.addComponentProperty('Value','TEXT',t.characters);t.componentPropertyReferences={characters:prop};}
 if(['source','recommendation','empty','dialog','notice','row'].includes(kind)){
 let body=kind==='source'?'World of Warcraft · 3.3.5a\nSource: UNVERIFIED · Freshness: UNKNOWN':kind==='recommendation'?'RECOMMENDATION · DEMO\nReason: environment unverified\nConfidence: UNKNOWN · source: —':kind==='dialog'?'Прочтение не выполняет действие в игре.\nReading does not execute a game action.':'Нет подтверждённых данных.\nNo verified data available.';
 let b=txt(c,body,14,'muted','Regular',wide?308:248);let bodyProp=c.addComponentProperty('Body','TEXT',body);b.componentPropertyReferences={characters:bodyProp};
 }
 }
 if(state==='disabled')c.opacity=.5;
 comps.push(c);maxH=Math.max(maxH,c.height);
 }
 const set=figma.combineAsVariants(comps,page);ids.push(set.id);set.name='H/'+family;set.x=3700;set.y=ypos;set.fills=[];comps.forEach((c,i)=>{c.x=24+(i%4)*(wide?372:312);c.y=24+Math.floor(i/4)*(maxH+32);});let maxX=Math.max(...comps.map(c=>c.x+c.width)),maxY=Math.max(...comps.map(c=>c.y+c.height));set.resizeWithoutConstraints(maxX+24,maxY+24);sets[family]={id:set.id,variants:comps.map(c=>({id:c.id,name:c.name})),w:set.width,h:set.height};ypos+=set.height+100;
}
return {createdNodeIds:ids,pageId:page.id,sets,totalVariants:families.reduce((s,f)=>s+f[1].length,0)};
