import {publicPages,productPages} from './content.mjs';
// Browser-only consent lease; no Android capture or action authority is conferred.
export const initialState=Object.freeze({permission:'unknown',observing:false,telemetry:null,status:'unknown',executionEnabled:false,acknowledged:false,consentRequired:true});
export function transition(state,event){
 const next={...state,executionEnabled:false};
 if(event==='grant') return {...next,permission:'granted',status:'ready',observing:false,telemetry:null,consentRequired:false};
 if(event==='observe'&&state.permission==='granted'&&state.consentRequired===false&&state.status==='ready')return {...next,observing:true,status:'observing',telemetry:null};
 if(event==='revoke')return {...next,permission:'revoked',observing:false,telemetry:null,status:'revoked',consentRequired:true};
 if(event==='deny')return {...next,permission:'denied',observing:false,telemetry:null,status:'denied',consentRequired:true};
 if(['stop','offline','stale','timeout'].includes(event))return {...next,observing:false,telemetry:null,status:event==='stop'?'stopped':event,consentRequired:true};
 if(event==='recover')return {...next,observing:false,telemetry:null,status:state.consentRequired?'stopped':state.permission==='granted'?'ready':state.permission};
 if(event==='confirm')return {...next,acknowledged:true};
 return next;
}
export function resolveRoute(path,surface='site'){
 const clean=path.length>1?path.replace(/\/$/,''):path;
 const pages=surface==='site'?publicPages:(productPages[surface]||[]);
 const page=pages.find(p=>p.path===clean);
 return page?{...page,found:true}:{path:clean,found:false,title:['Страница не найдена','Page not found']};
}
export function parseSurface(value){return ['site','android','windows','control','library'].includes(value)?value:'site';}
