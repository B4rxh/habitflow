(function(){
const NK="habitflow-notes",$=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],uid=()=>Math.random().toString(36).slice(2,9);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const ico=c=>String.fromCodePoint(c),ICONS=[128196,128218,127919,128161,9989,128170,128564,128167,128221,11088,128640,129504,127793,128295,127775,128214];
const T={p:"Text",h1:"Heading 1",h2:"Heading 2",h3:"Heading 3",todo:"To-do list",ul:"Bulleted list",ol:"Numbered list",quote:"Quote",callout:"Callout",code:"Code",hr:"Divider",page:"Link to page",habits:"Today's habits"};
const LIST=["todo","ul","ol"],RESET=["todo","ul","ol","quote","callout"],FIXED=["hr","page","habits"],FONTS=["serif","sans","mono"],FONTN={serif:"Serif",sans:"Sans",mono:"Mono"};
const DROP=["SCRIPT","STYLE","TEMPLATE","NOSCRIPT","IFRAME","OBJECT","EMBED"];
const OK={B:"b",STRONG:"b",I:"i",EM:"i",U:"u",S:"s",STRIKE:"s",DEL:"s",CODE:"code",MARK:"mark"};
const mk=(t,x="")=>({id:uid(),t,x,c:0});
const blocksOf=a=>a.map(([t,x])=>mk(t,esc(x)));
const TPL={Blank:[["p",""]],
"Daily journal":[["h2","Today"],["habits",""],["h2","Top priorities"],["todo",""],["todo",""],["todo",""],["h2","Notes"],["p",""],["h2","Grateful for"],["ul",""]],
"Study notes":[["h2","Topic"],["p",""],["h2","Key ideas"],["ul",""],["h2","Questions"],["ul",""],["callout","Summary in one sentence"]],
"Weekly review":[["h2","Wins"],["ul",""],["h2","To improve"],["ul",""],["h2","Next week"],["todo",""],["quote","Small habits, big change."]]};
const WELCOME=[["p","Type a slash at the start of a line to pick a block. Select any text to make it bold, highlighted or a link."],["todo","Tick this to-do"],["ul","Type a dash and a space for a bullet list"],["ol","Type 1. and a space for a numbered list"],["quote","Drag the :: handle on the left to reorder blocks."],["habits",""],["callout","Press Ctrl K to search pages or jump anywhere. Everything saves in this browser, so use Backup to keep a copy."]];

let N={pages:[],cur:null,col:{},v:2},q="",sm=null,timer=0,iconOpen=false,drag=null;
try{const r=JSON.parse(localStorage.getItem(NK)||"{}");N=Object.assign(N,r);if(!r.v){N.pages.forEach(p=>p.blocks.forEach(b=>{b.x=esc(b.x||"")}));N.v=2}}catch(e){}
const cur=()=>N.pages.find(p=>p.id===N.cur),blk=id=>cur().blocks.find(b=>b.id===id);

const parse=h=>new DOMParser().parseFromString(h,"text/html").body;
function clean(html){
 const walk=n=>{let o="";n.childNodes.forEach(c=>{
  if(c.nodeType===3)o+=esc(c.nodeValue.replace(/\u00a0/g," "));
  else if(c.nodeType===1){
   if(c.nodeName==="BR")o+="<br>";
   else if(DROP.includes(c.nodeName)){}
   else if(c.nodeName==="A"){const h=(c.getAttribute("href")||"").trim();o+=/^(https?:|mailto:)/i.test(h)?`<a href="${esc(h)}" target="_blank" rel="noopener">${walk(c)}</a>`:walk(c)}
   else if(OK[c.nodeName])o+=`<${OK[c.nodeName]}>${walk(c)}</${OK[c.nodeName]}>`;
   else o+=walk(c)}});return o};
 return walk(parse(html)).replace(/(<br>)+$/,"")}
const plain=h=>parse(clean(h).replace(/<br>/g,"\n")).textContent;
const strip=h=>h.replace(/<br>/g," ").replace(/<[^>]*>/g,"").replace(/&(amp|lt|gt|quot);/g,(m,k)=>({amp:"&",lt:"<",gt:">",quot:'"'}[k]));
const tx=n=>{let s="";n.childNodes.forEach(c=>{s+=c.nodeType===3?c.nodeValue.replace(/\u00a0/g," "):c.nodeName==="BR"?"\n":tx(c)});return s};
const txt=el=>tx(el).replace(/\n$/,"");
function off(el){const s=getSelection();if(!s.rangeCount)return 0;const r=document.createRange();r.selectNodeContents(el);r.setEnd(s.anchorNode,s.anchorOffset);return tx(r.cloneContents()).length}
function split(el){const s=getSelection(),r=s.getRangeAt(0),a=document.createRange(),b=document.createRange();
 a.selectNodeContents(el);a.setEnd(r.startContainer,r.startOffset);b.selectNodeContents(el);b.setStart(r.endContainer,r.endOffset);
 const h=g=>{const d=document.createElement("div");d.append(g.cloneContents());return clean(d.innerHTML)};return[h(a),h(b)]}
function setCaret(el,pos){const r=document.createRange();let left=pos,placed=false;
 (function w(n){n.childNodes.forEach(c=>{if(placed)return;
  if(c.nodeType===3){if(left<=c.nodeValue.length){r.setStart(c,left);placed=true}else left-=c.nodeValue.length}
  else if(c.nodeName==="BR"){if(left===0){r.setStartBefore(c);placed=true}else left-=1}
  else w(c)})})(el);
 if(!placed){r.selectNodeContents(el);r.collapse(false)}
 r.collapse(true);const s=getSelection();s.removeAllRanges();s.addRange(r)}

const st=document.createElement("style");
st.textContent=`#Notes.on{display:grid;grid-template-columns:262px minmax(0,1fr);gap:24px;position:relative}
#nside{background:var(--card);border-radius:16px;padding:12px;align-self:start;position:sticky;top:12px;max-height:84vh;overflow:auto;display:grid;grid-template-columns:minmax(0,1fr);gap:10px}
#nq{width:100%}.r2{display:flex;gap:8px;align-items:center}.r2 select{flex:1;min-width:0}
#nlist h4{font-size:12px;color:var(--mut);margin:12px 8px 4px;font-weight:600}
.ni{display:flex;align-items:center;gap:6px;padding:6px 8px;border-radius:10px;cursor:pointer;transition:background .15s}
.ni:hover{background:var(--hov)}.ni.cur{background:var(--sel)}
.ni b{flex:1;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cv{background:none;border:0;color:var(--mut);width:18px;padding:0;cursor:pointer;font-size:11px}
.np{opacity:0;background:none;border:0;color:var(--mut);font-size:18px;cursor:pointer}.ni:hover .np{opacity:1}
.nbar{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:20px}#npg{display:none}
#nsv{margin-left:auto;font-size:12px}#nmain{min-width:0}
#nhead,#ned{max-width:740px;margin-inline:auto}
.nic{font-size:46px;background:none;border:0;cursor:pointer;line-height:1;padding:0 0 6px;transition:transform .2s}.nic:hover{transform:scale(1.12)}
.picker{display:flex;flex-wrap:wrap;gap:4px;background:var(--card);padding:8px;border-radius:12px;width:max-content;max-width:100%;animation:in .25s}
.picker button{background:none;border:0;font-size:22px;cursor:pointer;border-radius:8px;padding:4px 6px}.picker button:hover{background:var(--hov)}
#ntitle{font:800 clamp(30px,5vw,40px)/1.15 var(--ui);outline:none;margin:6px 0 18px}
#ntitle:empty::before{content:attr(data-ph);color:var(--trk)}
.blk{position:relative;display:flex;align-items:flex-start;gap:4px;padding:2px 0;border-radius:6px}.blk.over{box-shadow:0 -2px 0 var(--acc)}
.hd{position:absolute;left:-26px;top:6px;width:22px;text-align:center;opacity:0;cursor:grab;color:var(--mut);user-select:none;font-size:12px;line-height:26px;transition:opacity .15s}.blk:hover .hd{opacity:1}
.mk{flex:none;min-width:22px;color:var(--mut);padding-top:4px;text-align:center}
.mk input{width:18px;height:18px;accent-color:var(--acc);margin:5px 0 0;cursor:pointer}
.bx{flex:1;min-width:0;outline:none;padding:3px 4px;white-space:pre-wrap;word-break:break-word}
.bx:empty:focus::before{content:attr(data-ph);color:var(--trk)}
.f-serif .bx{font:400 18px/1.7 var(--serif)}.f-sans .bx{font:400 16px/1.65 var(--ui)}.f-mono .bx{font:400 14.5px/1.7 ui-monospace,Consolas,monospace}
.t-h1 .bx,.t-h2 .bx,.t-h3 .bx{font-family:var(--ui);font-weight:800;line-height:1.3}
.t-h1 .bx{font-size:30px;margin-top:14px}.t-h2 .bx{font-size:23px;margin-top:10px;font-weight:700}.t-h3 .bx{font-size:18px;font-weight:700}
.t-quote .bx{border-left:3px solid var(--acc);padding-left:16px;color:var(--mut);font-style:italic}
.t-callout .bx{background:var(--card);border-radius:12px;padding:12px 16px;border-left:3px solid var(--amb)}
.t-code .bx{background:var(--code);border-radius:10px;padding:12px 16px;font:14px/1.6 ui-monospace,Consolas,monospace}
.t-hr hr{flex:1;border:0;border-top:1px solid var(--trk);margin:16px 0}
.done .bx{text-decoration:line-through;color:var(--mut)}
.bx b{font-weight:700}.bx a{color:var(--acc);text-decoration:underline;cursor:pointer}
.bx mark{background:#fbbf2459;color:inherit;border-radius:4px;padding:0 3px}
.bx code{background:var(--code);border-radius:6px;padding:1px 6px;font:.88em ui-monospace,Consolas,monospace}
.pl{flex:1;padding:8px 12px;border-radius:10px;background:var(--card);cursor:pointer;color:var(--txt);font-weight:600;transition:background .15s}.pl:hover{background:var(--hov)}
.hb{flex:1;display:flex;flex-wrap:wrap;gap:8px;padding:4px 0}
.chip{background:var(--card);border-radius:12px;padding:8px 14px;border-left:3px solid var(--c);min-width:96px}
.chip small{display:block;color:var(--mut);font-size:11px}.chip b{font-size:16px}
.bd{opacity:0;background:none;border:0;color:var(--mut);font-size:20px;cursor:pointer;padding:0 6px;align-self:center}.blk:hover .bd{opacity:1}
#nsm{position:absolute;z-index:5;width:240px;max-height:300px;overflow:auto;background:var(--card);border:1px solid var(--trk);border-radius:12px;padding:6px;box-shadow:var(--shadow);animation:in .15s}
#nsm[hidden]{display:none}.smi{padding:7px 10px;border-radius:8px;cursor:pointer}.smi.act,.smi:hover{background:var(--hov)}
#ntb{position:absolute;z-index:6;display:flex;gap:2px;background:var(--card);border:1px solid var(--trk);border-radius:10px;padding:4px;box-shadow:var(--shadow);animation:in .12s}
#ntb[hidden]{display:none}
#ntb button{background:none;border:0;color:var(--txt);min-width:32px;height:30px;padding:0 6px;border-radius:7px;cursor:pointer;font:700 13px var(--ui)}#ntb button:hover{background:var(--hov)}
@media(max-width:900px){#Notes.on{grid-template-columns:minmax(0,1fr);gap:12px}#nside{display:none;position:static;max-height:320px}#Notes.pg #nside{display:grid}#npg{display:inline-flex}.hd{display:none}}`;
document.head.append(st);

const sec=document.createElement("section");sec.id="Notes";
sec.innerHTML=`<aside id="nside"><input id="nq" placeholder="Search notes"><button class="btn" id="ntoday">Today's journal</button><div class="r2"><select id="nt">${Object.keys(TPL).map(k=>`<option>${k}`).join("")}</select><button class="gb" id="nnew">New page</button></div><div id="nlist"></div><div class="r2"><button class="gb" id="nbk">Backup</button><label class="gb">Restore<input type="file" id="nrs" accept=".json" hidden></label></div></aside><article id="nmain"><div class="nbar"><button class="gb" id="npg">Pages</button><button class="gb" id="nfav"></button><button class="gb" id="nsub">Add sub-page</button><button class="gb" id="nfont"></button><button class="gb" id="ndup">Duplicate</button><button class="gb" id="nmd">Export .md</button><button class="gb" id="ndel">Delete</button><span id="nsv" class="mut"></span></div><div id="nhead"></div><div id="ned"></div><div id="nsm" hidden></div></article><div id="ntb" hidden><button data-f="bold" title="Bold"><b>B</b></button><button data-f="italic" title="Italic"><i>I</i></button><button data-f="underline" title="Underline"><u>U</u></button><button data-f="strikeThrough" title="Strikethrough"><s>S</s></button><button data-f="code" title="Inline code">&lt;/&gt;</button><button data-f="mark" title="Highlight">Hi</button><button data-f="link" title="Link">Link</button></div>`;
$("main").append(sec);

const words=()=>cur().blocks.reduce((n,b)=>n+(FIXED.includes(b.t)?0:strip(b.x).split(/\s+/).filter(Boolean).length),0);
function save(){const p=cur();if(p)p.upd=Date.now();try{localStorage.setItem(NK,JSON.stringify({v:2,pages:N.pages,cur:N.cur,col:N.col}))}catch(e){}$("#nsv").textContent=p?"Saved \u00b7 "+words()+" words":"Saved"}
function later(){$("#nsv").textContent="Saving...";clearTimeout(timer);timer=setTimeout(save,300)}
function mkPage(o){const p=Object.assign({id:uid(),title:"",icon:128196,parent:null,fav:0,font:"serif",upd:Date.now(),blocks:[]},o);N.pages.push(p);return p}
function addPage(parent=null,name="Blank"){sec.classList.remove("pg");const w=name==="Welcome",p=mkPage({parent,title:w?"Welcome to your notebook":"",icon:w?127775:128196,blocks:blocksOf(w?WELCOME:TPL[name])});if(parent)delete N.col[parent];N.cur=p.id;iconOpen=false;save();all();$("#ntitle").focus()}
function delPage(){const p=cur();if(!confirm(`Delete "${p.title||"Untitled"}" and its sub-pages?`))return;const gone=new Set([p.id]);let grow=true;
 while(grow){grow=false;N.pages.forEach(x=>{if(x.parent&&gone.has(x.parent)&&!gone.has(x.id)){gone.add(x.id);grow=true}})}
 N.pages=N.pages.filter(x=>!gone.has(x.id));if(!N.pages.length)return addPage(null,"Welcome");N.cur=N.pages[0].id;save();all()}
function dupPage(){const p=cur(),c=JSON.parse(JSON.stringify(p));c.id=uid();c.title=(p.title||"Untitled")+" copy";c.blocks.forEach(b=>{b.id=uid()});c.fav=0;c.upd=Date.now();delete c.journal;delete c.jroot;N.pages.push(c);N.cur=c.id;save();all()}
function openToday(){sec.classList.remove("pg");const H=window.HT,d=H?H.day():new Date().toLocaleDateString("sv");let p=N.pages.find(x=>x.journal===d);
 if(!p){let root=N.pages.find(x=>x.jroot);
  if(!root)root=mkPage({title:"Journal",icon:128212,jroot:1,blocks:blocksOf([["p","Your daily pages live here, one for each day."]])});
  const title=new Date(d+"T00:00:00").toLocaleDateString("en-GB",{weekday:"short",day:"numeric",month:"short",year:"numeric"});
  p=mkPage({title,icon:128197,parent:root.id,journal:d,blocks:blocksOf(TPL["Daily journal"])});delete N.col[root.id]}
 N.cur=p.id;iconOpen=false;save();window.show("Notes")}

function side(){const L=$("#nlist"),s=q.trim().toLowerCase(),kids=id=>N.pages.filter(p=>(p.parent||null)===id);
 const row=(p,d,tree)=>{const has=tree&&kids(p.id).length;return`<div class="ni${p.id===N.cur?" cur":""}" data-id="${p.id}" style="padding-left:${6+d*14}px"><button class="cv" data-cv="${p.id}" style="visibility:${has?"visible":"hidden"}" aria-label="Expand or collapse">${N.col[p.id]?"&#9656;":"&#9662;"}</button><span>${ico(p.icon)}</span><b>${esc(p.title||"Untitled")}</b><button class="np" title="Add sub-page">+</button></div>`};
 if(s){const m=N.pages.filter(p=>(p.title+" "+p.blocks.map(b=>strip(b.x)).join(" ")).toLowerCase().includes(s));L.innerHTML=m.map(p=>row(p,0,false)).join("")||`<p class="mut">No pages match.</p>`;return}
 const walk=(par,d)=>kids(par).map(p=>row(p,d,true)+(N.col[p.id]?"":walk(p.id,d+1))).join(""),fv=N.pages.filter(p=>p.fav);
 L.innerHTML=(fv.length?`<h4>Favorites</h4>${fv.map(p=>row(p,0,false)).join("")}`:"")+`<h4>Pages</h4>`+walk(null,0)}
function head(){const p=cur();$("#nhead").innerHTML=`<button class="nic" id="nico">${ico(p.icon)}</button>${iconOpen?`<div class="picker">${ICONS.map(c=>`<button data-ic="${c}">${ico(c)}</button>`).join("")}</div>`:""}<h1 id="ntitle" contenteditable="true" data-ph="Untitled"></h1>`;
 $("#ntitle").textContent=p.title;$("#nfav").textContent=p.fav?"Unfavorite":"Favorite";$("#nfont").textContent="Font: "+FONTN[p.font||"serif"];$("#nmain").className="f-"+(p.font||"serif")}

function habitData(){const H=window.HT;if(!H)return[];const d=H.day(),D=H.D,tk=D.tasks.filter(t=>t.d===d),sl=(D.sleep[d]||{}).hours||0;
 return[["Water",D.water.filter(x=>x.d===d).length+" / "+H.G.water,"blu"],["Focus",H.sum(D.focus,d)+" min","acc"],["Study",H.sum(D.study,d)+" min","pnk"],["Fitness",H.sum(D.fit,d)+" min","grn"],["Sleep",sl?sl.toFixed(1)+" h":"not logged","amb"],["Tasks",tk.filter(t=>t.done).length+" / "+tk.length,"ros"]]}
function blocksR(fid,pos){const p=cur();let n=0;
 $("#ned").innerHTML=p.blocks.map(b=>{n=b.t==="ol"?n+1:0;const hd=`<span class="hd" draggable="true">::</span>`;
  if(b.t==="hr")return`<div class="blk t-hr" data-id="${b.id}">${hd}<hr></div>`;
  if(b.t==="page"){const g=N.pages.find(x=>x.id===b.ref);return`<div class="blk t-page" data-id="${b.id}">${hd}<a class="pl" data-ref="${b.ref}">${g?ico(g.icon)+" "+esc(g.title||"Untitled"):"Page not found"}</a><button class="bd" title="Remove">&times;</button></div>`}
  if(b.t==="habits")return`<div class="blk t-habits" data-id="${b.id}">${hd}<div class="hb">${habitData().map(([a,v,c])=>`<div class="chip" style="--c:var(--${c})"><small>${a}</small><b>${v}</b></div>`).join("")}</div><button class="bd" title="Remove">&times;</button></div>`;
  const m=b.t==="todo"?`<input type="checkbox" ${b.c?"checked":""}>`:b.t==="ul"?"&bull;":b.t==="ol"?n+".":"",mkh=m?`<span class="mk">${m}</span>`:"";
  return`<div class="blk t-${b.t}${b.c&&b.t==="todo"?" done":""}" data-id="${b.id}">${hd}${mkh}<div class="bx" contenteditable="true" data-ph="${b.t==="p"?"Type / for blocks":T[b.t]}"></div></div>`}).join("");
 p.blocks.forEach(b=>{if(!FIXED.includes(b.t))$(`#ned [data-id="${b.id}"] .bx`).innerHTML=clean(b.x)});if(fid)focusB(fid,pos)}
function all(){side();head();blocksR();$("#nsv").textContent=cur()?"Saved \u00b7 "+words()+" words":""}
function focusB(id,pos){const el=$(`#ned [data-id="${id}"] .bx`);if(!el)return;el.focus();
 if(typeof pos==="number"&&pos>0)setCaret(el,pos);else{const r=document.createRange(),s=getSelection();r.selectNodeContents(el);r.collapse(pos===0);s.removeAllRanges();s.addRange(r)}}
function near(i,d){const bs=cur().blocks;for(let j=i+d;j>=0&&j<bs.length;j+=d)if(!FIXED.includes(bs[j].t))return bs[j]}

function menu(row,s){const items=Object.entries(T).filter(([k,v])=>v.toLowerCase().includes(s.toLowerCase())||k.startsWith(s.toLowerCase()));if(!items.length)return closeMenu();
 sm={id:row.dataset.id,items,i:0};const m=$("#nsm"),a=sec.getBoundingClientRect(),r=row.getBoundingClientRect();m.style.top=r.bottom-a.top+4+"px";m.style.left=Math.max(0,r.left-a.left)+"px";m.hidden=false;drawMenu()}
function drawMenu(){$("#nsm").innerHTML=sm.items.map(([k,v],i)=>`<div class="smi${i===sm.i?" act":""}" data-t="${k}">${v}</div>`).join("")}
function closeMenu(){sm=null;$("#nsm").hidden=true}
function pick(t){if(!sm)return;const b=blk(sm.id),bs=cur().blocks,i=bs.indexOf(b);
 if(t==="page"){const ps=N.pages.filter(p=>p.id!==N.cur).slice(0,40);sm.items=ps.length?ps.map(p=>["pg:"+p.id,ico(p.icon)+" "+esc(p.title||"Untitled")]):[["none","No other pages yet"]];sm.i=0;drawMenu();return}
 closeMenu();if(t==="none")return;b.x="";
 if(t.startsWith("pg:")){b.t="page";b.ref=t.slice(3)}else b.t=t;
 if(FIXED.includes(b.t)){const nb=mk("p");bs.splice(i+1,0,nb);save();blocksR(nb.id);return}
 save();blocksR(b.id)}

function onType(el){const row=el.closest(".blk"),b=blk(row.dataset.id),x=txt(el);b.x=clean(el.innerHTML);
 const rules=[[/^# $/,"h1"],[/^## $/,"h2"],[/^### $/,"h3"],[/^[-*] $/,"ul"],[/^1\. $/,"ol"],[/^\[\] $/,"todo"],[/^> $/,"quote"],[/^```$/,"code"]];
 if(b.t==="p"){const hit=rules.find(([r])=>r.test(x));if(hit){b.t=hit[1];b.x="";save();blocksR(b.id);return}
  if(x==="---"){b.t="hr";b.x="";const nb=mk("p");cur().blocks.splice(cur().blocks.indexOf(b)+1,0,nb);save();blocksR(nb.id);return}}
 if(x.startsWith("/")&&b.t==="p")menu(row,x.slice(1));else closeMenu();later()}

const activeBx=()=>{const s=getSelection(),n=s.anchorNode,e=n&&(n.nodeType===3?n.parentElement:n);return e&&e.closest?e.closest(".bx"):null};
function sync(el){const row=el.closest(".blk");if(!row)return;blk(row.dataset.id).x=clean(el.innerHTML);later()}
function wrap(tag){const s=getSelection();if(!s.rangeCount)return;const r=s.getRangeAt(0);let n=r.commonAncestorContainer;n=n.nodeType===3?n.parentNode:n;
 const host=n.closest(tag);
 if(host&&host.closest(".bx")){const p=host.parentNode;while(host.firstChild)p.insertBefore(host.firstChild,host);p.removeChild(host);return}
 const w=document.createElement(tag);w.append(r.extractContents());r.insertNode(w);s.removeAllRanges();const nr=document.createRange();nr.selectNodeContents(w);s.addRange(nr)}
function fmt(cmd){const el=activeBx();if(!el||!document.execCommand)return;
 if(cmd==="code"||cmd==="mark")wrap(cmd);
 else if(cmd==="link"){const s=getSelection(),n=s.anchorNode,p=n&&(n.nodeType===3?n.parentElement:n);
  if(p&&p.closest("a"))document.execCommand("unlink");
  else{const r=s.rangeCount?s.getRangeAt(0).cloneRange():null,u=prompt("Link address");if(!u||!r)return;s.removeAllRanges();s.addRange(r);
   const v=u.trim();document.execCommand("createLink",false,/^(https?:|mailto:)/i.test(v)?v:"https://"+v)}}
 else document.execCommand(cmd);
 sync(el)}
document.addEventListener("selectionchange",()=>{const tb=$("#ntb"),s=getSelection();
 if(!sec.classList.contains("on")||!s.rangeCount||s.isCollapsed){tb.hidden=true;return}
 const el=activeBx();if(!el||!sec.contains(el)||el.closest(".t-code")){tb.hidden=true;return}
 const rc=s.getRangeAt(0).getBoundingClientRect(),a=sec.getBoundingClientRect();
 tb.hidden=false;const top=rc.top-a.top-44;tb.style.top=(top<0?rc.bottom-a.top+8:top)+"px";tb.style.left=Math.max(0,Math.min(rc.left-a.left,a.width-270))+"px"});
sec.addEventListener("mousedown",e=>{if(e.target.closest("#ntb"))e.preventDefault()});

const fromLine=line=>{let m;
 if(m=line.match(/^(#{1,3}) (.*)/))return["h"+m[1].length,m[2]];
 if(m=line.match(/^\s*[-*] \[( |x)\] (.*)/i))return["todo",m[2],m[1].toLowerCase()==="x"];
 if(m=line.match(/^\s*[-*+] (.*)/))return["ul",m[1]];
 if(m=line.match(/^\s*\d+[.)] (.*)/))return["ol",m[1]];
 if(m=line.match(/^> (.*)/))return["quote",m[1]];
 if(/^---+$/.test(line.trim()))return["hr",""];
 return["p",line]};
function pasteBlocks(el,text){const b=blk(el.closest(".blk").dataset.id),bs=cur().blocks,i=bs.indexOf(b),[h,t]=split(el);
 const made=text.replace(/\r/g,"").split("\n").filter(l=>l.trim()!=="").map(fromLine).map(([ty,x,c])=>{const nb=mk(ty,esc(x));if(c)nb.c=1;return nb});
 if(!made.length)return;
 if(!plain(h)&&b.t==="p")bs.splice(i,1,...made);else{b.x=h;bs.splice(i+1,0,...made)}
 const last=made[made.length-1];
 if(plain(t))bs.splice(bs.indexOf(last)+1,0,mk("p",t));
 save();blocksR(FIXED.includes(last.t)?null:last.id)}
function insertPlain(text){if(!document.execCommand)return;text.split("\n").forEach((l,i)=>{if(i)document.execCommand("insertLineBreak");if(l)document.execCommand("insertText",false,l)})}
sec.addEventListener("paste",e=>{const el=e.target.closest&&(e.target.closest(".bx")||e.target.closest("#ntitle"));if(!el)return;
 e.preventDefault();const text=(e.clipboardData||window.clipboardData).getData("text/plain");if(!text)return;
 if(el.id==="ntitle"){insertPlain(text.replace(/\s*\n\s*/g," "));return}
 if(!text.includes("\n")||blk(el.closest(".blk").dataset.id).t==="code"){insertPlain(text);return}
 pasteBlocks(el,text)});

sec.addEventListener("input",e=>{const t=e.target;
 if(t.id==="nq"){q=t.value;side();return}
 if(t.id==="ntitle"){cur().title=txt(t).replace(/\n/g," ").trim();side();later();return}
 if(t.classList.contains("bx"))onType(t)});
sec.addEventListener("keydown",e=>{const el=e.target;
 if(el.id==="ntitle"&&e.key==="Enter"){e.preventDefault();const f=cur().blocks.find(b=>!FIXED.includes(b.t));if(f)focusB(f.id,0);return}
 if(!el.classList||!el.classList.contains("bx"))return;
 const meta=e.ctrlKey||e.metaKey,k=(e.key||"").toLowerCase();
 if(meta&&k==="k"&&!getSelection().isCollapsed){e.preventDefault();e.stopPropagation();fmt("link");return}
 if(meta&&k==="e"){e.preventDefault();fmt("code");return}
 if(meta&&e.shiftKey&&k==="h"){e.preventDefault();fmt("mark");return}
 const b=blk(el.closest(".blk").dataset.id),bs=cur().blocks,i=bs.indexOf(b),x=txt(el);
 if(sm){if(e.key==="ArrowDown"||e.key==="ArrowUp"){e.preventDefault();sm.i=(sm.i+(e.key==="ArrowDown"?1:sm.items.length-1))%sm.items.length;drawMenu();return}
  if(e.key==="Enter"){e.preventDefault();pick(sm.items[sm.i][0]);return}
  if(e.key==="Escape"){closeMenu();return}}
 if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();
  if(b.t==="code"){if(document.execCommand)document.execCommand("insertLineBreak");return}
  if(!x&&RESET.includes(b.t)){b.t="p";save();blocksR(b.id);return}
  const[h,t]=split(el),nb=mk(LIST.includes(b.t)?b.t:"p",t);b.x=h;bs.splice(i+1,0,nb);save();blocksR(nb.id,0)}
 else if(e.key==="Backspace"&&getSelection().isCollapsed&&off(el)===0){
  if(b.t!=="p"){e.preventDefault();b.t="p";save();blocksR(b.id,0);return}
  if(i>0){e.preventDefault();const pv=bs[i-1];if(FIXED.includes(pv.t)){bs.splice(i-1,1);save();blocksR(b.id,0);return}const len=plain(pv.x).length;pv.x+=b.x;bs.splice(i,1);save();blocksR(pv.id,len)}}
 else if(e.key==="Tab"&&b.t==="code"){e.preventDefault();if(document.execCommand)document.execCommand("insertText",false,"  ")}
 else if(e.key==="ArrowUp"&&off(el)===0){const pv=near(i,-1);if(pv){e.preventDefault();focusB(pv.id)}}
 else if(e.key==="ArrowDown"&&off(el)===x.length){const nx=near(i,1);if(nx){e.preventDefault();focusB(nx.id,0)}}});
sec.addEventListener("change",e=>{const t=e.target;
 if(t.type==="checkbox"){const row=t.closest(".blk"),b=blk(row.dataset.id);b.c=t.checked?1:0;row.classList.toggle("done",!!b.c);save()}
 if(t.id==="nrs"&&t.files[0])restore(t.files[0])});
sec.addEventListener("click",e=>{const t=e.target,ni=t.closest(".ni"),id=t.id,f=t.closest("[data-f]");
 if(!t.closest(".smi"))closeMenu();
 if(f){fmt(f.dataset.f);return}
 if(t.closest(".cv")){const c=t.closest(".cv").dataset.cv;N.col[c]=N.col[c]?0:1;save();side();return}
 if(t.classList.contains("np")){addPage(ni.dataset.id);return}
 if(ni){N.cur=ni.dataset.id;iconOpen=false;sec.classList.remove("pg");save();all();return}
 const pl=t.closest(".pl");
 if(pl){if(N.pages.some(p=>p.id===pl.dataset.ref)){N.cur=pl.dataset.ref;iconOpen=false;save();all()}return}
 if(t.classList.contains("bd")){const row=t.closest(".blk"),bs=cur().blocks;bs.splice(bs.findIndex(b=>b.id===row.dataset.id),1);if(!bs.length)bs.push(mk("p"));save();blocksR();return}
 const link=t.closest(".bx a");
 if(link&&(e.ctrlKey||e.metaKey)){window.open(link.getAttribute("href"),"_blank","noopener");return}
 if(id==="npg")sec.classList.toggle("pg");
 else if(id==="ntoday")openToday();
 else if(id==="nnew")addPage(null,$("#nt").value);
 else if(id==="nsub")addPage(cur().id);
 else if(id==="nfav"){cur().fav=cur().fav?0:1;save();head();side()}
 else if(id==="nfont"){const p=cur();p.font=FONTS[(FONTS.indexOf(p.font||"serif")+1)%FONTS.length];save();head()}
 else if(id==="ndup")dupPage();
 else if(id==="nico"){iconOpen=!iconOpen;head()}
 else if(t.dataset.ic){cur().icon=+t.dataset.ic;iconOpen=false;save();head();side()}
 else if(id==="nmd")exportMd();
 else if(id==="ndel")delPage();
 else if(id==="nbk")backup();
 else if(t.closest(".smi"))pick(t.closest(".smi").dataset.t)});
sec.addEventListener("dragstart",e=>{const h=e.target.closest&&e.target.closest(".hd");if(!h)return;drag=h.closest(".blk").dataset.id;e.dataTransfer.effectAllowed="move";e.dataTransfer.setData("text/plain",drag)});
sec.addEventListener("dragover",e=>{const r=e.target.closest(".blk");if(!drag||!r)return;e.preventDefault();$$(".blk.over").forEach(x=>x.classList.remove("over"));r.classList.add("over")});
sec.addEventListener("drop",e=>{const r=e.target.closest(".blk");if(!drag||!r)return;e.preventDefault();const bs=cur().blocks,a=bs.findIndex(b=>b.id===drag),t=bs.findIndex(b=>b.id===r.dataset.id);
 if(a!==t){const[m]=bs.splice(a,1);bs.splice(t,0,m);save();blocksR()}drag=null});
sec.addEventListener("dragend",()=>{drag=null;$$(".blk.over").forEach(x=>x.classList.remove("over"))});
window.addEventListener("beforeunload",()=>{clearTimeout(timer);if(cur())save()});

function dl(name,text,type){const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function md(h){const w=n=>[...n.childNodes].map(c=>{if(c.nodeType===3)return c.nodeValue;const i=w(c);
 switch(c.nodeName){case"B":return"**"+i+"**";case"I":return"*"+i+"*";case"S":return"~~"+i+"~~";case"CODE":return"`"+i+"`";case"MARK":return"=="+i+"==";case"U":return"<u>"+i+"</u>";case"A":return"["+i+"]("+c.getAttribute("href")+")";case"BR":return"\n";default:return i}}).join("");
 return w(parse(clean(h)))}
function exportMd(){const p=cur();let n=0;
 const body=p.blocks.map(b=>{n=b.t==="ol"?n+1:0;
  if(b.t==="hr")return"---";
  if(b.t==="page"){const g=N.pages.find(x=>x.id===b.ref);return"[["+(g?g.title||"Untitled":"Page not found")+"]]"}
  if(b.t==="habits")return"Today's habits: "+habitData().map(([a,v])=>a+" "+v).join(", ");
  if(b.t==="code")return"```\n"+plain(b.x)+"\n```";
  return({h1:"# ",h2:"## ",h3:"### ",todo:b.c?"- [x] ":"- [ ] ",ul:"- ",ol:n+". ",quote:"> ",callout:"> Note: "}[b.t]||"")+md(b.x)}).join("\n\n");
 dl((p.title||"untitled").replace(/[^\w-]+/g,"-")+".md",`# ${p.title||"Untitled"}\n\n${body}\n`,"text/markdown")}
function backup(){const o={};["habitflow",NK].forEach(k=>o[k]=localStorage.getItem(k));dl("habit-tracker-backup.json",JSON.stringify(o),"application/json")}
function restore(f){const r=new FileReader();r.onload=()=>{try{const o=JSON.parse(r.result);["habitflow",NK].forEach(k=>{if(typeof o[k]==="string")localStorage.setItem(k,o[k])});location.reload()}catch(e){alert("That file is not a valid backup.")}};r.readAsText(f)}

window.notesR=()=>{if(!N.pages.length)return addPage(null,"Welcome");if(!cur())N.cur=N.pages[0].id;all()};
window.NB={
 pages:()=>N.pages,
 open:id=>{if(N.pages.some(p=>p.id===id)){N.cur=id;iconOpen=false;save();window.show("Notes")}},
 today:openToday,
 newPage:()=>{window.show("Notes");addPage(null,"Blank")},
 backup,
 find:s=>{const k=s.trim().toLowerCase(),list=k?N.pages.filter(p=>(p.title+" "+p.blocks.map(b=>strip(b.x)).join(" ")).toLowerCase().includes(k)):[...N.pages].sort((a,b)=>b.upd-a.upd).slice(0,4);
  return list.map(p=>({id:p.id,ic:ico(p.icon),title:p.title,snippet:strip((p.blocks.find(b=>!FIXED.includes(b.t)&&strip(b.x).trim())||{x:""}).x).slice(0,70)}))}
};
})();
