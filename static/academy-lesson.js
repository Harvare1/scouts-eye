(function(){
  'use strict';
  const canvas=document.querySelector('#academy-phase-board');
  if(canvas){
    const ctx=canvas.getContext('2d'),buttons=[...document.querySelectorAll('[data-phase]')],caption=document.querySelector('#phase-caption');
    const formations={
      with:{caption:'Med boll: vänsterbacken flyttar in och sexan sjunker mellan mittbackarna.',players:[[.08,.5],[.25,.18],[.24,.5],[.25,.82],[.43,.34],[.43,.66],[.63,.12],[.67,.35],[.67,.65],[.63,.88],[.86,.5]],arrows:[[.25,.18,.43,.34],[.43,.5,.25,.5],[.63,.12,.82,.12]]},
      without:{caption:'Utan boll: laget faller ned i 4-5-1 med kortare avstånd mellan lagdelarna.',players:[[.08,.5],[.27,.16],[.27,.39],[.27,.61],[.27,.84],[.52,.1],[.5,.3],[.48,.5],[.5,.7],[.52,.9],[.78,.5]],arrows:[]}
    };
    function arrow(a,b,c,d){const x1=34+a*(canvas.width-68),y1=34+b*(canvas.height-68),x2=34+c*(canvas.width-68),y2=34+d*(canvas.height-68),angle=Math.atan2(y2-y1,x2-x1);ctx.strokeStyle='#78951e';ctx.fillStyle='#78951e';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();ctx.beginPath();ctx.moveTo(x2,y2);ctx.lineTo(x2-13*Math.cos(angle-.55),y2-13*Math.sin(angle-.55));ctx.lineTo(x2-13*Math.cos(angle+.55),y2-13*Math.sin(angle+.55));ctx.fill();}
    function draw(name){const f=formations[name],x=34,y=34,w=canvas.width-68,h=canvas.height-68;ctx.fillStyle='#cde3c9';ctx.fillRect(0,0,canvas.width,canvas.height);for(let i=0;i<8;i++){ctx.fillStyle=i%2?'#b9d5b6':'#c8dfc4';ctx.fillRect(x+i*w/8,y,w/8,h);}ctx.strokeStyle='#5b926b';ctx.lineWidth=2;ctx.strokeRect(x,y,w,h);ctx.beginPath();ctx.moveTo(x+w/2,y);ctx.lineTo(x+w/2,y+h);ctx.stroke();ctx.beginPath();ctx.arc(x+w/2,y+h/2,62,0,Math.PI*2);ctx.stroke();ctx.strokeRect(x,y+h*.25,w*.15,h*.5);ctx.strokeRect(x+w*.85,y+h*.25,w*.15,h*.5);f.arrows.forEach(item=>arrow(...item));f.players.forEach((p,index)=>{const px=x+p[0]*w,py=y+p[1]*h;ctx.fillStyle='#d7f179';ctx.strokeStyle='#152119';ctx.lineWidth=3;ctx.beginPath();ctx.arc(px,py,13,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle='#152119';ctx.font='bold 11px system-ui';ctx.textAlign='center';ctx.fillText(index+1,px,py+4);});caption.textContent=f.caption;buttons.forEach(button=>button.classList.toggle('selected',button.dataset.phase===name));}
    buttons.forEach(button=>button.addEventListener('click',()=>draw(button.dataset.phase)));draw('with');
  }

  const form=document.querySelector('#lesson-progress-form');if(!form)return;
  const reflection=document.querySelector('#lesson-reflection'),status=document.querySelector('#autosave-status'),feedback=document.querySelector('#lesson-feedback');let timer;
  async function save(showResult){
    const selected=form.querySelector('[name="lesson-answer"]:checked');
    if(showResult&&!selected){status.textContent='Välj ett svar innan du kontrollerar.';return;}
    status.textContent='Sparar…';
    const response=await fetch(form.dataset.endpoint,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':form.dataset.csrf},body:JSON.stringify({reflection:reflection.value,answer_index:selected?Number(selected.value):null})});
    if(!response.ok){status.textContent='Kunde inte spara. Försök igen.';return;}
    const result=await response.json();status.textContent=result.completed?'Sparat · lektionen är genomförd.':'Sparat automatiskt.';
    if(showResult){feedback.hidden=false;feedback.textContent=(result.correct?'Rätt. ':'Inte rätt ännu. ')+result.explanation;if(result.completed)feedback.classList.add('success');}
  }
  reflection.addEventListener('input',()=>{clearTimeout(timer);timer=setTimeout(()=>save(false),700);});
  form.addEventListener('submit',event=>{event.preventDefault();clearTimeout(timer);save(true);});
})();
