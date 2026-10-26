import test from 'node:test';
import assert from 'node:assert/strict';
import postcss from 'postcss';
import {parse,format,claro,escuro,ehVerde,TOM} from '../tema/paleta.js';
import tema,{prefixar} from '../tema/postcss-tema.js';

const perto=(a,b,tol=.02)=>Math.abs(a-b)<=tol;

test('hex <-> HSL round-trips and keeps the alpha suffix',()=>{
 for(const h of ['#1b6654','#f3f6f3','#c62828','#ffffff','#000000'])assert.equal(format(parse(h)),h);
 assert.equal(format(parse('#28472b04')).slice(7),'04');
 assert.equal(format(parse('#fff')),'#ffffff');
});

test('light theme: greens become orange, non-greens are untouched',()=>{
 assert.equal(claro('#c62828'),'#c62828');assert.equal(claro('#1565c0'),'#1565c0');assert.equal(claro('#ffffff'),'#ffffff');
 const btn=parse(claro('#1b6654',{prop:'background'}));assert.ok(perto(btn.h,TOM,2)&&btn.s>.6&&btn.l>.35&&btn.l<.45,'primary button becomes the orange accent, dark enough for white text');
 const cinza=parse(claro('#7c8881',{prop:'color'}));assert.ok(perto(cinza.h,TOM,2)&&cinza.l<=.42,'muted gray text gets warm and readable (4.5:1)');
 const tinta=parse(claro('#f3f6f3',{prop:'background'})),orig=parse('#f3f6f3');assert.ok(perto(tinta.l,orig.l,.01),'light tints keep their lightness');assert.ok(!ehVerde(tinta));
 const lateral=parse(claro('#163d32',{prop:'background',cromo:true}));assert.ok(lateral.s<=.11&&lateral.l<.2,'sidebar becomes warm graphite');
 const link=parse(claro('#3b6e57',{prop:'color'}));assert.ok(perto(link.h,TOM,2)&&link.l<=.4,'colored text stays dark enough to read on white');
});

test('dark theme: light surfaces turn dark, dark text turns light, accents stay',()=>{
 const sup=parse(escuro('#ffffff',{prop:'background'}));assert.ok(sup.l<.15);
 const txt=parse(escuro('#2a2420',{prop:'color'}));assert.ok(txt.l>.7);
 assert.equal(escuro('#ffffff',{prop:'color'}),'#ffffff');
 const acc=parse(escuro('#e2702b',{prop:'background'}));assert.ok(acc.s>.5&&acc.l>=.5);
 const borda=parse(escuro('#e3e7e1',{prop:'border'}));assert.ok(borda.l<.3);
 assert.equal(escuro('#102a1510',{prop:'box-shadow'}),'#00000010');
 assert.equal(escuro('#b8553e',{prop:'box-shadow'}),'#b8553e');
});

test('plugin rewrites colors and adds a dark sibling rule, sparing manual and vendor CSS',async()=>{
 const css='.primary{background:#1b6654;color:white;padding:4px}:root{--x:#246958}@media (max-width:5px){.a,.b{border:1px solid #e3e7e1}}@keyframes k{0%{color:#000}}';
 const out=(await postcss([tema()]).process(css,{from:'src/style.css'})).css;
 assert.match(out,/\.primary\{background:#[0-9a-f]{6};color:white;padding:4px\}/);
 assert.match(out,/:root\[data-theme="dark"\] \.primary\{background:#[0-9a-f]{6};color:#ffffff\}/);
 assert.match(out,/:root\[data-theme="dark"\] \.a,:root\[data-theme="dark"\] \.b\{border:1px solid #/);
 assert.ok(!/data-theme="dark"\] 0%/.test(out),'keyframes are not prefixed');
 const vendor=(await postcss([tema()]).process(css,{from:'node_modules/leaflet/leaflet.css'})).css;assert.equal(vendor,css);
 const manual='/* tema: manual */ .x{color:#1b6654}';assert.equal((await postcss([tema()]).process(manual,{from:'src/tema.css'})).css,manual);
 assert.equal(prefixar(':root'),':root[data-theme="dark"]');assert.equal(prefixar('a:is(.x,.y), b'),':root[data-theme="dark"] a:is(.x,.y),:root[data-theme="dark"] b');
});
