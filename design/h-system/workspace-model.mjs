const buildIds=['balanced','reserve','mobility'];
export const talentIds=['focus','reserve','momentum','guard','insight','recovery'];
export function createWorkspace(){return {sample:false,executionEnabled:false,compare:[],talents:{},quantity:1,quests:[],phase:'prepare',rotationStep:0,arenaPlan:'balanced',tables:{auction:{query:'',sort:'price',page:0,selectedItem:null},economy:{query:'',sort:'name',page:0,selectedItem:null}}};}
export function reduceWorkspace(state,action){
 const s={...state,executionEnabled:false};
 if(action.type==='reset')return createWorkspace();
 if(action.type==='sample')return action.value===true?{...s,sample:true}:createWorkspace();
 if(action.type==='compare'&&s.sample&&buildIds.includes(action.id))return {...s,compare:s.compare.includes(action.id)?s.compare.filter(id=>id!==action.id):s.compare.length<2?[...s.compare,action.id]:s.compare};
 if(action.type==='talent'&&s.sample&&talentIds.includes(action.id)){
  const current=s.talents[action.id]||0,total=Object.values(s.talents).reduce((a,b)=>a+b,0),delta=action.delta===-1?-1:1;
  if(delta>0&&total>=8)return s;
  return {...s,talents:{...s.talents,[action.id]:Math.max(0,Math.min(3,current+delta))}};
 }
 if(action.type==='quantity'&&s.sample){const value=Number(action.value);return {...s,quantity:Number.isFinite(value)?Math.max(1,Math.min(99,Math.trunc(value))):s.quantity};}
 if(action.type==='quest'&&s.sample&&['survey','collect','return'].includes(action.id))return {...s,quests:s.quests.includes(action.id)?s.quests.filter(id=>id!==action.id):[...s.quests,action.id]};
 if(action.type==='phase'&&s.sample&&['prepare','react','recover'].includes(action.id))return {...s,phase:action.id};
 if(action.type==='rotation'&&s.sample)return {...s,rotationStep:Math.max(0,Math.min(3,s.rotationStep+(action.delta===-1?-1:1)))};
 if(action.type==='arena'&&s.sample&&buildIds.includes(action.id))return {...s,arenaPlan:action.id};
 if(action.type==='item'&&s.sample&&['auction','economy'].includes(action.module)&&['ore','cloth','herb','crystal','leather','ink'].includes(action.id))return {...s,tables:{...s.tables,[action.module]:{...s.tables[action.module],selectedItem:action.id}}};
 if(action.type==='table'&&['auction','economy'].includes(action.module)){
  const old=s.tables[action.module];const next={...old};
  if(action.field==='query'){next.query=String(action.value).slice(0,80);next.page=0;next.selectedItem=null;}
  if(action.field==='sort'&&['price','price-desc','name'].includes(action.value)){next.sort=action.value;next.page=0;}
  if(action.field==='page')next.page=Math.max(0,Math.trunc(Number(action.value)||0));
  return {...s,tables:{...s.tables,[action.module]:next}};
 }
 return s;
}
export function selectRows(rows,options,lang='en'){
 const index=lang==='ru'?0:1,query=(options.query||'').trim().toLocaleLowerCase();
 const list=rows.filter(row=>row.name[index].toLocaleLowerCase().includes(query));
 list.sort((a,b)=>options.sort==='name'?a.name[index].localeCompare(b.name[index]):options.sort==='price-desc'?b.price-a.price:a.price-b.price);
 const pageSize=Math.max(1,Math.min(25,options.pageSize||3)),pages=Math.max(1,Math.ceil(list.length/pageSize)),page=Math.min(pages-1,Math.max(0,options.page||0));
 return {rows:list.slice(page*pageSize,(page+1)*pageSize),total:list.length,page,pages};
}
