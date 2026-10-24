import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const css=readFileSync(new URL('../style.css',import.meta.url),'utf8');
const luminance=hex=>{if(hex.length===4)hex='#'+[...hex.slice(1)].map(c=>c+c).join('');const channels=hex.match(/[0-9a-f]{2}/gi).map(c=>parseInt(c,16)/255).map(c=>c<=.04045?c/12.92:((c+.055)/1.055)**2.4);return channels[0]*.2126+channels[1]*.7152+channels[2]*.0722;};
const ratio=(a,b)=>{const x=[luminance(a),luminance(b)].sort((a,b)=>b-a);return(x[0]+.05)/(x[1]+.05)};
for(const [name,block]of [['dark',css.match(/:root\{([^}]+)/)[1]],['light',css.match(/body\.light\{([^}]+)/)[1]]]){
 const tokens=Object.fromEntries([...block.matchAll(/--([a-z]+):(#[0-9a-f]{6}|#[0-9a-f]{3})/gi)].map(m=>[m[1],m[2]]));
 test(name+' text and control boundaries remain legible',()=>{
 for(const [fg,bg]of [['text','bg'],['muted','surface'],['accent','bg'],['positive','surface'],['warning','raised'],['danger','surface']])assert.ok(ratio(tokens[fg],tokens[bg])>=4.5,`${name} ${fg}/${bg} ${ratio(tokens[fg],tokens[bg]).toFixed(2)}`);
 assert.ok(ratio(tokens.line,tokens.bg)>=3,`${name} input boundary ${ratio(tokens.line,tokens.bg).toFixed(2)}`);
 });
}
