(function () {
  'use strict';
  const canvas=document.querySelector('#tactics-board');
  const field=document.querySelector('#tactics-field');
  if(!canvas||!field)return;
  const ctx=canvas.getContext('2d');
  let markers=[];
  try{const v=JSON.parse(field.value||'[]'); if(Array.isArray(v))markers=v.slice(0,30);}catch(_){markers=[];}
  let team='a', dragged=-1;
  const pad=30;
  const inner={x:pad,y:pad,w:canvas.width-2*pad,h:canvas.height-2*pad};
  function pitch(){
    const {x,y,w,h}=inner;
    ctx.fillStyle='#cde3c9';ctx.fillRect(0,0,canvas.width,canvas.height);
    for(let i=0;i<8;i++) {ctx.fillStyle=i%2?'#b9d5b6':'#c8dfc4';ctx.fillRect(x+i*w/8,y,w/8,h)}
    ctx.strokeStyle='#5b926b';ctx.lineWidth=2;
    ctx.strokeRect(x,y,w,h);
    ctx.beginPath();ctx.moveTo(x+w/2,y);ctx.lineTo(x+w/2,y+h);ctx.stroke();
    ctx.beginPath();ctx.arc(x+w/2,y+h/2,Math.min(h*.16,64),0,2*Math.PI);ctx.stroke();
    ctx.strokeRect(x,y+h*.25,w*.15,h*.5);ctx.strokeRect(x+w*.85,y+h*.25,w*.15,h*.5);
    ctx.strokeRect(x,y+h*.37,w*.07,h*.26);ctx.strokeRect(x+w*.93,y+h*.37,w*.07,h*.26);
    ctx.fillStyle='#203b2b';ctx.font='bold 12px system-ui';ctx.textAlign='left';ctx.fillText('LÄGG TILL / DRA SPELARE PÅ PLANEN',18,18);
    markers.forEach((m,i)=>{
      const cx=x+m.x*w,cy=y+m.y*h;
      ctx.fillStyle=m.team==='a'?'#d7f179':'#152119';
      ctx.strokeStyle=m.team==='a'?'#152119':'#d7f179';ctx.lineWidth=3;
      ctx.beginPath();ctx.arc(cx,cy,11,0,2*Math.PI);ctx.fill();ctx.stroke();
      ctx.fillStyle=m.team==='a'?'#152119':'#f4f5ee';ctx.textAlign='center';ctx.font='bold 11px system-ui';ctx.fillText(i+1,cx,cy+4);
    });
  }
  function save(){field.value=JSON.stringify(markers);field.dispatchEvent(new Event('input',{bubbles:true}));pitch()}
  function point(event){const r=canvas.getBoundingClientRect();const x=(event.clientX-r.left)*canvas.width/r.width;const y=(event.clientY-r.top)*canvas.height/r.height;return {x:Math.max(0,Math.min(1,(x-inner.x)/inner.w)),y:Math.max(0,Math.min(1,(y-inner.y)/inner.h))}}
  function near(p){return markers.findIndex(m=>Math.hypot((m.x-p.x)*inner.w,(m.y-p.y)*inner.h)<20)}
  canvas.addEventListener('pointerdown',ev=>{ev.preventDefault();const p=point(ev);dragged=near(p);if(dragged<0){if(markers.length>=30)return;markers.push({...p,team});dragged=markers.length-1;}canvas.setPointerCapture(ev.pointerId);save()});
  canvas.addEventListener('pointermove',ev=>{if(dragged<0)return;markers[dragged]={...markers[dragged],...point(ev)};save()});
  canvas.addEventListener('pointerup',()=>{dragged=-1});
  canvas.addEventListener('pointercancel',()=>{dragged=-1});
  const teamA=document.querySelector('#team-a'),teamB=document.querySelector('#team-b');
  function choose(next){team=next;teamA.classList.toggle('selected',team==='a');teamB.classList.toggle('selected',team==='b')}
  teamA.addEventListener('click',()=>choose('a'));teamB.addEventListener('click',()=>choose('b'));
  document.querySelector('#tactics-undo').addEventListener('click',()=>{markers.pop();save()});
  document.querySelector('#tactics-clear').addEventListener('click',()=>{if(confirm('Ta bort alla spelarpositioner?')){markers=[];save()}});
  choose('a');pitch();
})();
