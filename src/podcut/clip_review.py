"""Self-contained local review page. Corrections download as JSON; no server/upload."""
import base64
import json
from pathlib import Path


def build_page(data):
    safe = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    font_css = []
    for font in data["fonts"]:
        # IDs are locally derived hashes, never user-supplied CSS names.
        if len(font["id"]) != 16 or any(c not in "0123456789abcdef" for c in font["id"]):
            raise ValueError("Invalid font ID")
        encoded = base64.b64encode(Path(font["path"]).read_bytes()).decode("ascii")
        font_css.append("@font-face{font-family:f" + font["id"] + ";src:url(data:font/ttf;base64," + encoded + ")}")
    return TEMPLATE.replace("/*FONTS*/", "\n".join(font_css)).replace("/*DATA*/", safe)


TEMPLATE = r'''<!doctype html><html lang="ka"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Podcut Flow · ტექსტის და კლიპების გადამოწმება</title>
<style>
/*FONTS*/
:root{color-scheme:light;font-family:system-ui,sans-serif;color:#122438;background:#eef3f5}
*{box-sizing:border-box}body{max-width:1320px;margin:auto;padding:24px}h1{font-size:27px}h2{font-size:21px}
header,.card{background:#fff;border:1px solid #d8e4e8;border-radius:14px;padding:22px;margin-bottom:18px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.muted{color:#52677a;font-size:14px}
button,.button{background:#007e86;color:white;border:0;border-radius:8px;padding:11px 16px;cursor:pointer;font:inherit}
input,select,textarea{border:1px solid #a9bcc6;border-radius:6px;padding:8px;font:inherit;max-width:100%}
input[type=number]{width:106px}textarea{width:100%;min-height:64px;resize:vertical}label{display:inline-flex;gap:8px;align-items:center;margin:7px}
video{width:100%;max-height:330px;background:#101820;border-radius:9px}.clip{border-top:1px solid #d8e4e8;padding:15px 0}
table{width:100%;border-collapse:collapse}td,th{text-align:left;border-bottom:1px solid #d8e4e8;padding:9px;vertical-align:top}
th{position:sticky;top:0;background:white}td:first-child{width:240px}#sample{background:#183742;color:white;padding:25px;text-align:center;min-height:160px;border-radius:10px;overflow-wrap:anywhere}
.notice{background:#e5f6f4;border-left:4px solid #00878c;padding:12px}.error{color:#a62323}details{margin:12px 0}summary{cursor:pointer}
@media(max-width:800px){.grid{grid-template-columns:1fr}body{padding:10px}td:first-child{width:140px}input[type=number]{width:85px}}
</style>
<header><p class="muted">PODCUT FLOW · META → REVIEW → CLIPS</p>
<h1>ჯერ ტექსტი და არჩევანი — შემდეგ ვიდეო</h1>
<p>სრული ტრანსკრიპტი ქვემოთაა, ტაიმკოდებით. შეასწორე ტექსტი და დროები, აირჩიე ჰუკი და სუბტიტრები.
ყველა დრო წამებშია და ამავე ვიდეოს დასაწყისიდან ითვლება. / Review the full transcript before assembly.</p>
<div id="brief" class="notice"></div>
<p class="muted">ეს გვერდი ადგილობრივად მუშაობს. ტექსტი და ვიდეო არსად იტვირთება. ცვლილებები შეინახე JSON-ფაილად და დაუბრუნე აგენტს.
დადასტურებამდე ვიდეო არ აიწყობა. / Save corrections and return the file to your agent.</p></header>
<div class="grid"><section class="card"><h2>მოუსმინე და გადაამოწმე / Listen</h2>
<p>აირჩიე შესაბამისი ადგილობრივი ვიდეო მოსასმენად:</p><input id="videoFile" type="file" accept="video/*"><p id="fileNote" class="muted"></p>
<video id="player" controls></video><p class="muted">ტაიმკოდზე დაჭერით ვიდეო შესაბამის ადგილზე გადავა. ფაილის არჩევა მის ატვირთვას არ ნიშნავს.</p>
</section><section class="card"><h2>ნამდვილი შრიფტი და ფერი / Caption style</h2>
<p class="muted">გამოიყენება მხოლოდ დამატებული ორიგინალი TTF/OTF ფაილები. საკუთარი ფონტი მიეცი აგენტს დასამატებლად.</p>
<label>Font <select id="font"></select></label><label>Size <input id="size" type="number" min="24" max="110"></label>
<label>Text <input id="color" type="color"></label><label>Outline <input id="outline_color" type="color"></label>
<label>Outline size <input id="outline" type="number" min="0" max="10"></label>
<p><button type="button" data-palette="white">White</button> <button type="button" data-palette="yellow">Yellow</button> <button type="button" data-palette="mint">Mint</button></p>
<div id="sample"></div><p class="muted">შრიფტის რეალური ნიმუში. საბოლოო ზომა და განლაგება ვიდეოს კადრზეც უნდა შემოწმდეს.</p>
<label>Layout <select id="layout"><option value="blur">9:16 · სრული კადრი, დაბურული ფონი</option><option value="crop">9:16 · ცენტრალური ჭრა</option><option value="source">ორიგინალი პროპორციები</option></select></label>
</section></div>
<section class="card"><h2>კლიპები და ჰუკი / Clips &amp; opening teaser</h2>
<p>ჰუკი ვიდეოდან არჩეული რეალური მონაკვეთია. „Repeat“ დასაწყისში ტიზერს ამატებს და სრულ საუბარშიც ტოვებს.
ხანგრძლივობა ტიზერის ჩათვლით ითვლება. დასაწყისისა და დასასრულის დროები დაამთხვიე ტექსტის საზღვრებს.</p>
<div id="clips"></div><p id="errors" class="error"></p></section>
<section class="card"><h2>სრული ტრანსკრიპტი / Full timed transcript</h2>
<p class="muted">Meta-ს დროები მიახლოებითია: განსაკუთრებით გადაამოწმე სახელები, სიტყვის დასაწყისი/ბოლო და ჭრის ადგილები.
მონაკვეთის დასაყოფად ან დასამატებლად აგენტს მიეცი დრო და შესწორება.</p>
<table><thead><tr><th>დრო / Time</th><th>ტექსტი / Text</th></tr></thead><tbody id="cues"></tbody></table>
</section><section class="card"><h2>შენახვა / Save review</h2>
<label><input type="checkbox" id="confirmed"> გადავამოწმე სრული ტექსტი, ჰუკი, დროები და სუბტიტრების არჩევანი.</label>
<p><button id="save">შესწორებების შენახვა / Download corrections</button></p>
<p class="muted">JSON-ის ჩამოტვირთვა ვიდეოს რენდერს არ იწყებს. აგენტი შეიტანს ცვლილებებს და შენს დასტურს მიმდინარე ვერსიას მიაბამს.
ტექსტის გარეშე სუფთა ვიდეო ყოველთვის შენარჩუნდება; ჩაბეჭდილი სუბტიტრების მოსაშორებლად სუფთა ვერსია გამოიყენება.</p></section>
<script id="data" type="application/json">/*DATA*/</script><script>
'use strict';
const d=JSON.parse(document.getElementById('data').textContent), $=id=>document.getElementById(id);
const palettes={white:['#FFFFFF','#101820'],yellow:['#FFE55C','#111827'],mint:['#77F2CE','#10252B']};
const ts=t=>{const n=Math.round(t*1000),h=Math.floor(n/3600000),m=Math.floor(n/60000)%60,s=Math.floor(n/1000)%60;return `${h.toString().padStart(2,'0')}:${m.toString().padStart(2,'0')}:${s.toString().padStart(2,'0')}.${(n%1000).toString().padStart(3,'0')}`};
function el(tag,text){const e=document.createElement(tag);if(text!==undefined)e.textContent=text;return e}
function change(){d.approval=null;$('confirmed').checked=false}
$('brief').textContent=`შეთანხმებულია / Agreed: ${d.brief.count} ვიდეო · ${d.brief.min_seconds}–${d.brief.max_seconds} წამი თითოეული, ჰუკის ჩათვლით. რაოდენობის ან დიაპაზონის შეცვლა შეათანხმე აგენტთან.`;
$('fileNote').textContent=d.video.path;
let mediaUrl;
$('videoFile').onchange=e=>{if(mediaUrl)URL.revokeObjectURL(mediaUrl);if(e.target.files[0]){$('player').src=mediaUrl=URL.createObjectURL(e.target.files[0]);}};
$('font').add(new Option('აირჩიე ფონტი / Select font',''));
d.fonts.forEach(f=>$('font').add(new Option(f.family,f.id)));
$('font').value=d.style.font_id||'';
$('layout').value=d.layout;
$('layout').onchange=()=>{d.layout=$('layout').value;change()};
function sample(){const s=$('sample');s.textContent=d.cues[0]?.text||'ქართული · English';s.style.fontFamily=d.style.font_id?'f'+d.style.font_id:'system-ui';s.style.fontSize=(d.style.size/2)+'px';s.style.color=d.style.color;s.style.webkitTextStroke=(d.style.outline/5)+'px '+d.style.outline_color}
$('font').onchange=()=>{d.style.font_id=$('font').value||null;change();sample()};
for(const k of ['size','color','outline_color','outline']){$(k).value=d.style[k];$(k).oninput=()=>{d.style[k]=['size','outline'].includes(k)?Number($(k).value):$(k).value;change();sample()}}
document.querySelectorAll('[data-palette]').forEach(b=>b.onclick=()=>{[d.style.color,d.style.outline_color]=palettes[b.dataset.palette];$('color').value=d.style.color;$('outline_color').value=d.style.outline_color;change();sample()});
function numeric(label,value,update){const l=el('label',label),i=el('input');i.type='number';i.step='0.001';i.min='0';i.value=value??'';i.oninput=()=>{update(i.value===''?null:Number(i.value));change();timelines()};l.append(i);return l}
const timelineNodes=[];
d.clips.forEach(c=>{const box=el('div');box.className='clip';box.append(el('h3',c.id));
box.append(numeric('Start',c.start,v=>c.start=v),numeric('End',c.end,v=>c.end=v));
const originalHook=c.hook;c.hook=c.hook||{start:null,end:null,mode:'repeat'};
box.append(numeric('Hook start',c.hook.start,v=>c.hook.start=v),numeric('Hook end',c.hook.end,v=>c.hook.end=v));
const mode=el('select');mode.add(new Option('Repeat · ტიზერი და სრული საუბარი','repeat'));mode.add(new Option('Move · მხოლოდ დასაწყისში','move'));mode.value=c.hook.mode;mode.onchange=()=>{c.hook.mode=mode.value;change();timelines()};box.append(mode);
const cap=el('select');cap.add(new Option('სუბტიტრები? / Captions?',''));cap.add(new Option('ჩართული / On','on'));cap.add(new Option('გამორთული / Off','off'));cap.value=c.captions===null?'':c.captions?'on':'off';cap.onchange=()=>{c.captions=cap.value===''?null:cap.value==='on';change()};box.append(el('label','Captions'),cap);
const text=el('div');timelineNodes.push([c,text]);box.append(text);$('clips').append(box);
});
function timelines(){for(const[c,node]of timelineNodes){node.replaceChildren();if(!c.hook||c.hook.start===null||c.hook.end===null){node.append(el('p','ჰუკი ჯერ არჩეული არ არის / Choose the spoken hook.'));continue}
const h=c.hook,total=c.end-c.start+(h.mode==='repeat'?h.end-h.start:0);node.append(el('p',`Final: ${total.toFixed(3)} sec · Hook: ${ts(h.start)} → ${ts(h.end)}`));
const ranges=h.mode==='repeat'?[[h.start,h.end],[c.start,c.end]]:[[h.start,h.end],[c.start,h.start],[h.end,c.end]];
let cursor=0;for(const[a,b]of ranges){if(b<=a)continue;const details=el('details'),summary=el('summary',`${ts(cursor)} → ${ts(cursor+b-a)} | source ${ts(a)} → ${ts(b)}`);details.append(summary,el('p',d.cues.filter(q=>q.start>=a&&q.end<=b).map(q=>q.text).join(' ')));node.append(details);cursor+=b-a;}
}}
d.cues.forEach(q=>{const tr=el('tr'),t=el('td'),text=el('td');const seek=el('button',ts(q.start));seek.type='button';seek.onclick=()=>{if($('player').src){$('player').currentTime=q.start;$('player').play().catch(()=>{})}};
t.append(seek,numeric('Start',q.start,v=>{q.start=v;seek.textContent=ts(v||0)}),numeric('End',q.end,v=>q.end=v));
const area=el('textarea');area.value=q.text;area.oninput=()=>{q.text=area.value;change();timelines();sample()};text.append(area);tr.append(t,text);$('cues').append(tr)});
$('save').onclick=()=>{const out=structuredClone(d);out.approval=null;out.user_review={confirmed:$('confirmed').checked};const blob=new Blob([JSON.stringify(out,null,2)],{type:'application/json'}),u=URL.createObjectURL(blob),a=el('a');a.href=u;a.download='review-corrections.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
timelines();sample();
</script></html>'''
