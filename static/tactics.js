(function () {
  'use strict';
  const field=document.querySelector('#tactics-field');
  const editors=[...document.querySelectorAll('.tactics-editor')];
  if(!field||!editors.length)return;

  let stored={};
  try{
    const parsed=JSON.parse(field.value||'{}');
    if(Array.isArray(parsed)){
      const keys=editors.length===7?['chapter_03']:['chapter_04','chapter_05','chapter_08','chapter_09','chapter_10','chapter_11','chapter_12'];
      keys.forEach(key=>{stored[key]={markers:parsed.map(marker=>({...marker})),arrows:[]};});
    }else if(parsed&&typeof parsed==='object')stored=parsed;
  }catch(_){stored={};}

  const clamp=value=>Math.max(0,Math.min(1,Number(value)||0));
  function normalizedBoard(raw){
    const board={markers:[],arrows:[]};
    const used={a:new Set(),b:new Set()};
    (Array.isArray(raw?.markers)?raw.markers:[]).slice(0,30).forEach(marker=>{
      const team=marker.team==='b'?'b':'a';
      let number=Number.parseInt(marker.number,10);
      if(!number||number<1||number>99||used[team].has(number)){
        number=1;while(used[team].has(number)&&number<99)number+=1;
      }
      used[team].add(number);
      board.markers.push({x:clamp(marker.x),y:clamp(marker.y),team,number});
    });
    (Array.isArray(raw?.arrows)?raw.arrows:[]).slice(0,40).forEach(arrow=>board.arrows.push({x1:clamp(arrow.x1),y1:clamp(arrow.y1),x2:clamp(arrow.x2),y2:clamp(arrow.y2),team:arrow.team==='b'?'b':'a'}));
    return board;
  }
  const boards={};
  editors.forEach(editor=>{boards[editor.dataset.chapter]=normalizedBoard(stored[editor.dataset.chapter]||{});});

  function persist(){
    const compact={};
    Object.entries(boards).forEach(([key,board])=>{if(board.markers.length||board.arrows.length)compact[key]={markers:board.markers,arrows:board.arrows};});
    field.value=JSON.stringify(compact);
    field.dispatchEvent(new Event('input',{bubbles:true}));
  }

  editors.forEach(editor=>{
    const key=editor.dataset.chapter,board=boards[key],canvas=editor.querySelector('canvas'),ctx=canvas.getContext('2d');
    const buttons=Object.fromEntries([...editor.querySelectorAll('[data-action]')].map(button=>[button.dataset.action,button]));
    const pad=34,inner={x:pad,y:pad,w:canvas.width-2*pad,h:canvas.height-2*pad};
    let team='a',tool='players',dragged=-1,arrowStart=null,arrowPreview=null;
    const history=[];
    const snapshot=()=>JSON.stringify({markers:board.markers,arrows:board.arrows});
    function remember(){history.push(snapshot());if(history.length>30)history.shift();}
    function restore(value){const old=JSON.parse(value);board.markers=old.markers;board.arrows=old.arrows;boards[key]=board;persist();draw();}
    function point(event){const rect=canvas.getBoundingClientRect();const x=(event.clientX-rect.left)*canvas.width/rect.width;const y=(event.clientY-rect.top)*canvas.height/rect.height;return{x:clamp((x-inner.x)/inner.w),y:clamp((y-inner.y)/inner.h)};}
    function coords(p){return{x:inner.x+p.x*inner.w,y:inner.y+p.y*inner.h};}
    function near(p){return board.markers.findIndex(marker=>{const a=coords(marker),b=coords(p);return Math.hypot(a.x-b.x,a.y-b.y)<20;});}
    function nextNumber(){const used=new Set(board.markers.filter(marker=>marker.team===team).map(marker=>marker.number));let number=1;while(used.has(number)&&number<99)number+=1;return number;}
    function arrow(from,to,color){
      const start=coords(from),end=coords(to),angle=Math.atan2(end.y-start.y,end.x-start.x),head=13;
      ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(start.x,start.y);ctx.lineTo(end.x,end.y);ctx.stroke();
      ctx.beginPath();ctx.moveTo(end.x,end.y);ctx.lineTo(end.x-head*Math.cos(angle-.55),end.y-head*Math.sin(angle-.55));ctx.lineTo(end.x-head*Math.cos(angle+.55),end.y-head*Math.sin(angle+.55));ctx.closePath();ctx.fill();
    }
    function draw(){
      const{x,y,w,h}=inner;ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#cde3c9';ctx.fillRect(0,0,canvas.width,canvas.height);
      for(let i=0;i<8;i++){ctx.fillStyle=i%2?'#b9d5b6':'#c8dfc4';ctx.fillRect(x+i*w/8,y,w/8,h);}
      ctx.strokeStyle='#5b926b';ctx.lineWidth=2;ctx.strokeRect(x,y,w,h);ctx.beginPath();ctx.moveTo(x+w/2,y);ctx.lineTo(x+w/2,y+h);ctx.stroke();ctx.beginPath();ctx.arc(x+w/2,y+h/2,Math.min(h*.16,64),0,2*Math.PI);ctx.stroke();
      ctx.strokeRect(x,y+h*.25,w*.15,h*.5);ctx.strokeRect(x+w*.85,y+h*.25,w*.15,h*.5);ctx.strokeRect(x,y+h*.37,w*.07,h*.26);ctx.strokeRect(x+w*.93,y+h*.37,w*.07,h*.26);
      board.arrows.forEach(item=>arrow({x:item.x1,y:item.y1},{x:item.x2,y:item.y2},item.team==='a'?'#78951e':'#152119'));
      if(arrowStart&&arrowPreview)arrow(arrowStart,arrowPreview,team==='a'?'#78951e':'#152119');
      board.markers.forEach(marker=>{const p=coords(marker);ctx.fillStyle=marker.team==='a'?'#d7f179':'#152119';ctx.strokeStyle=marker.team==='a'?'#152119':'#d7f179';ctx.lineWidth=3;ctx.beginPath();ctx.arc(p.x,p.y,13,0,2*Math.PI);ctx.fill();ctx.stroke();ctx.fillStyle=marker.team==='a'?'#152119':'#f4f5ee';ctx.textAlign='center';ctx.font='bold 12px system-ui';ctx.fillText(marker.number,p.x,p.y+4);});
      ctx.fillStyle='#203b2b';ctx.font='bold 12px system-ui';ctx.textAlign='left';ctx.fillText(tool==='arrows'?'PILVERKTYG · DRA FRÅN START TILL MÅL':'SPELARVERKTYG · KLICKA ELLER DRA',18,19);
    }
    function chooseTeam(next){team=next;buttons['team-a'].classList.toggle('selected',team==='a');buttons['team-b'].classList.toggle('selected',team==='b');}
    function chooseTool(next){tool=next;buttons.players.classList.toggle('selected',tool==='players');buttons.arrows.classList.toggle('selected',tool==='arrows');draw();}
    canvas.addEventListener('pointerdown',event=>{
      event.preventDefault();const p=point(event);canvas.setPointerCapture(event.pointerId);
      if(tool==='arrows'){arrowStart=p;arrowPreview=p;draw();return;}
      dragged=near(p);remember();
      if(dragged<0){if(board.markers.length>=30){history.pop();return;}board.markers.push({...p,team,number:nextNumber()});dragged=board.markers.length-1;}
      else board.markers[dragged]={...board.markers[dragged],...p};
      persist();draw();
    });
    canvas.addEventListener('pointermove',event=>{
      if(tool==='arrows'&&arrowStart){arrowPreview=point(event);draw();return;}
      if(dragged<0)return;board.markers[dragged]={...board.markers[dragged],...point(event)};persist();draw();
    });
    canvas.addEventListener('pointerup',event=>{
      if(tool==='arrows'&&arrowStart){const end=point(event);if(Math.hypot(end.x-arrowStart.x,end.y-arrowStart.y)>.015){remember();board.arrows.push({x1:arrowStart.x,y1:arrowStart.y,x2:end.x,y2:end.y,team});persist();}arrowStart=null;arrowPreview=null;draw();}
      dragged=-1;
    });
    canvas.addEventListener('pointercancel',()=>{dragged=-1;arrowStart=null;arrowPreview=null;draw();});
    buttons['team-a'].addEventListener('click',()=>chooseTeam('a'));buttons['team-b'].addEventListener('click',()=>chooseTeam('b'));buttons.players.addEventListener('click',()=>chooseTool('players'));buttons.arrows.addEventListener('click',()=>chooseTool('arrows'));
    buttons.undo.addEventListener('click',()=>{if(history.length)restore(history.pop());});
    buttons.clear.addEventListener('click',()=>{if(!board.markers.length&&!board.arrows.length)return;if(confirm('Ta bort alla spelare och pilar i detta kapitel?')){remember();board.markers=[];board.arrows=[];persist();draw();}});
    chooseTeam('a');chooseTool('players');draw();
  });
  persist();
})();
