import {publicPages,productPages} from './content.mjs';
export const initialState=Object.freeze({permission:'unknown',observing:false,telemetry:null,status:'unknown',executionEnabled:false,acknowledged:false});
export function transition(state,event){
 const next={...state,executionEnabled:false};
 if(event==='grant') return {...next,permission:'granted',status:'ready',observing:false,telemetry:null};
 if(event==='observe'&&state.permission==='granted'&&!['offline','stale'].includes(state.status))return {...next,observing:true,status:'observing',telemetry:null};
 if(event==='revoke')return {...next,permission:'revoked',observing:false,telemetry:null,status:'revoked'};
 if(event==='deny')return {...next,permission:'denied',observing:false,telemetry:null,status:'denied'};
 if(['stop','offline','stale','timeout'].includes(event))return {...next,observing:false,telemetry:null,status:event==='stop'?'stopped':event};
 if(event==='recover')return {...next,observing:false,telemetry:null,status:state.permission==='granted'?'ready':state.permission};
 if(event==='confirm')return {...next,acknowledged:true};
 return next;
}
export function resolveRoute(path,surface='site'){
 const clean=path.length>1?path.replace(/\/$/,''):path;
 const pages=surface==='site'?publicPages:(productPages[surface]||[]);
 const page=pages.find(p=>p.path===clean);
 return page?{...page,found:true}:{path:clean,found:false,title:['Страница не найдена','Page not found']};
}
