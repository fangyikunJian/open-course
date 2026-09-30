# -*- coding: utf-8 -*-
"""CS234 放映厅 · 公共装配层

沿用 ML 放映厅的做法：内容与引擎分离，引擎来自 eng.txt，用 Python 生成 *.html。
本文件在原引擎之上做两件事，都是**加法**，不改动 eng.txt 本身：

  1. 引擎补丁 —— 把 gS / gN / DUR / isFast 也挂到 window.__engine 上。
     原引擎只导出高层绘图函数，RL 图元需要直接往画布加元素，所以要拿到图层句柄。
     gS/gN 在 clearScene 里只被清空、从不重新赋值，所以直接传选择集是安全的。

  2. RL 图元包 —— 原工具箱是为 ML 做的（散点+拟合线+矩阵），RL 要画的东西不一样：

     arrow(x1,y1,x2,y2,cls,bend)    带箭头的线（bend 给弧度）
     mdpChain(o)                    一维状态链（Mars rover 那种）
     bars(o)                        每状态一根值条（值函数可视化）
     gridworld(o)                   二维格子世界：值 / 策略箭头 / 高亮 / 墙
     backup(o)                      Sutton&Barto 回溯图：状态圆 + 动作点
     tree(o)                        搜索树，支持只画前 k 个节点（增长动画）
     errbar(o)                      误差棒 / 置信区间（UCB 那类）
     lamps(o)                       指示灯排（范式对比用）

  配色语义与 ML 版严格一致，学习者的条件反射不能打断：
     蓝 b = 模型/输入   黄 y = 注意力/结论   绿 g = 正确/答案
     珊瑚 r = 误差/错误  紫 v = 强调
"""
import io
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))

import _paths

# ── 1. 引擎补丁：导出图层句柄 ──────────────────────────────────────────────
_EXPORT_OLD = "window.__engine={clearScene:clearScene,"
_EXPORT_NEW = ("window.__engine={gS:gS,gN:gN,DUR:DUR,"
               "isFast:function(){return FAST;},clearScene:clearScene,")

# ── 2. RL 图元包（CSS） ────────────────────────────────────────────────────
RL_CSS = r"""
/* ══ RL 图元包 ══ */

/* #quiz 缺容器兜底。引擎里 #sum 有 max-height:90vh + overflow:auto，而 #quiz 两者都没有；
   又因为 #quizL 是 align-items:center，一旦内容超高就**上下对称裁切** ——
   最先看不见的是最底部的 .why，也就是那一拍的全部教学载荷（解析）。
   这比 SUM 卡溢出更隐蔽：SUM 至少还能滚，QUIZ 是直接两头切掉。
   选择器同为 (1,0,0)，本段注入在引擎样式之后，靠顺序取胜。 */
#quiz{max-height:88vh;overflow:auto}
.pt.b{fill:var(--coral)} .pt.c{fill:var(--green)} .pt.y{fill:var(--yellow)} .pt.v{fill:var(--violet)}
.box.y{stroke:var(--yellow)} .box.v{stroke:var(--violet)} .box.b{stroke:var(--blue)}
/* 层级只用颜色区分，字号一律沿用引擎的 .slbl 14px —— ML 版就是这么做的，
   混用字号会让画面每次切换都「跳」一下。sm / big 是**兜底色**，不是字号。

   顺序至关重要：sm/big/ink 必须排在语义色**之前**。三者特异度相同（0,2,0），
   靠先后决胜 —— 上一版把它们写在后面，于是 note(txt,x,y,cls+" sm") 这类调用
   （bars 第 187 行、errbar 第 303 行等，全片 15 处）的语义色被静默压成 --dim，
   而深底上的暗灰标签看起来像正常标签，所以没人反馈。
   「层级只靠颜色」这个正解，被为兼容它而保留的别名从内部取消掉了。
   现在的顺序下：class="slbl y sm" → 黄（语义色在后，赢）；class="slbl sm" → 暗色。 */
.slbl.ink{fill:var(--ink)} .slbl.sm{fill:var(--dim)} .slbl.big{fill:var(--ink)}
/* 五个语义色必须**全部**在别名之后重新声明 —— 包括 g 与 r。
   它们原本定义在 eng.txt 的基础样式里，而本段整体注入在基础样式之后，
   所以只在本段内部调顺序是不够的：第一次修完，slbl.y.sm 变对了，
   而 slbl.g.sm 仍被压成暗灰（实测 rgb(147,161,181)）—— 因为 .slbl.g 来自上游。 */
.slbl.y{fill:var(--yellow)} .slbl.b{fill:var(--blue)} .slbl.v{fill:var(--violet)}
.slbl.g{fill:var(--green)} .slbl.r{fill:var(--coral)}

/* ── 动画铁律 ──────────────────────────────────────────────────────────
   动画必须演示机制。看完一段动画，观众应当明白一件<b>之前不明白的事</b>。
   不解释任何东西的动画（呼吸、脉冲环、无限循环的小车、行进虚线）一律不要——
   它们只是视觉噪音，会盖过真正要看的东西。

   因此这里没有 infinite 动画。每个动画都：
     · 播一次就停在正确的终态；
     · 终态本身携带完整信息（后台标签页暂停也不丢内容）；
     · 有明确的「它在演示什么」的答案。
   ──────────────────────────────────────────────────────────────────── */
@keyframes rl-slide{to{offset-distance:100%}}
.tracer{animation:rl-slide var(--walk-dur,2.4s) ease-in-out 1 forwards;offset-rotate:0deg}
.trail{stroke-dasharray:none}

.arw{stroke:#3A4759;stroke-width:1.8;fill:none;marker-end:url(#ah)}
.arw.g{stroke:var(--green);marker-end:url(#ah-g)}
.arw.y{stroke:var(--yellow);marker-end:url(#ah-y)}
.arw.r{stroke:var(--coral);marker-end:url(#ah-r)}
.arw.b{stroke:var(--blue);marker-end:url(#ah-b)}
.arw.v{stroke:var(--violet);marker-end:url(#ah-v)}
.arw.dash{stroke-dasharray:5 4}

.snode{fill:#101724;stroke:#2B3646;stroke-width:1.8}
.snode.g{stroke:var(--green)} .snode.y{stroke:var(--yellow)}
.snode.r{stroke:var(--coral)} .snode.b{stroke:var(--blue)} .snode.v{stroke:var(--violet)}
.anode{fill:var(--dim);stroke:none}
.anode.y{fill:var(--yellow)} .anode.g{fill:var(--green)} .anode.r{fill:var(--coral)}

.gcell{fill:#0E1420;stroke:#1E2836;stroke-width:1.2}
.gcell.wall{fill:#1B2230;stroke:#243044}
.gcell.hl{fill:#2A2410;stroke:var(--yellow);stroke-width:2}
.gcell.g{fill:#0E2A24;stroke:var(--green);stroke-width:2}
.gcell.r{fill:#3A1A1E;stroke:var(--coral);stroke-width:2}
.gcell.b{fill:#0E1F33;stroke:var(--blue);stroke-width:2}

.vbar{fill:var(--blue);opacity:.85}
.vbar.g{fill:var(--green)} .vbar.y{fill:var(--yellow)}
.vbar.r{fill:var(--coral)} .vbar.v{fill:var(--violet)}

.ebar{stroke:var(--dim);stroke-width:1.7;fill:none}
.ebar.y{stroke:var(--yellow)} .ebar.g{stroke:var(--green)} .ebar.r{stroke:var(--coral)}

.lamp{fill:#141B27;stroke:#28323F;stroke-width:1.6}
.lamp.on{fill:#2A2410;stroke:var(--yellow);stroke-width:2.2}
.lamp.off{fill:#141B27;stroke:#28323F;opacity:.45}
.lamp.dead{fill:#2A1418;stroke:var(--coral);stroke-width:2}

.tnode{fill:#101724;stroke:#2B3646;stroke-width:1.6}
.tnode.hl{stroke:var(--yellow);stroke-width:2.2}
.tnode.g{stroke:var(--green);stroke-width:2.2}
.tedge{stroke:#2A3546;stroke-width:1.5;fill:none}
.tedge.hl{stroke:var(--yellow);stroke-width:2.2}
"""

# ── 3. RL 图元包（JS） ─────────────────────────────────────────────────────
RL_JS = r"""
/* ══════════════ RL 图元包（在 __engine 之上扩展，不改原引擎） ══════════════ */
(function(){
var E=window.__engine, gS=E.gS, gN=E.gN, DUR=E.DUR, W=E.W, H=E.H;
var note=E.note;
function fast(){return E.isFast();}
function fadeIn(sel,delay){
  if(fast()){sel.attr("opacity",1);return sel;}
  return sel.attr("opacity",0).transition().duration(420).delay(delay||0).attr("opacity",1);
}

/* 箭头标记（各色一份），只建一次 */
(function(){
  var svg=d3.select("#scene");
  if(!svg.select("defs#rlmk").empty())return;
  var defs=svg.append("defs").attr("id","rlmk");
  var cols={"ah":"#3A4759","ah-g":"#5BDDA8","ah-y":"#FFD36E",
            "ah-r":"#FF7C87","ah-b":"#54A9F7","ah-v":"#B48BF5"};
  Object.keys(cols).forEach(function(id){
    defs.append("marker").attr("id",id).attr("viewBox","0 0 10 10")
      .attr("refX",9).attr("refY",5).attr("markerWidth",6).attr("markerHeight",6)
      .attr("orient","auto")
      .append("path").attr("d","M0,0.6L10,5L0,9.4z").attr("fill",cols[id]);
  });
})();

/* ── arrow ── */
function arrow(x1,y1,x2,y2,cls,bend){
  var d;
  if(bend){
    var mx=(x1+x2)/2,my=(y1+y2)/2,dx=x2-x1,dy=y2-y1,L=Math.sqrt(dx*dx+dy*dy)||1;
    d="M"+x1+","+y1+"Q"+(mx-dy/L*bend)+","+(my+dx/L*bend)+" "+x2+","+y2;
  } else d="M"+x1+","+y1+"L"+x2+","+y2;
  var p=gS.append("path").attr("class","arw "+(cls||"")).attr("d",d);
  if(!fast()&&p.node().getTotalLength){
    var L2=p.node().getTotalLength();
    p.attr("stroke-dasharray",L2+" "+L2).attr("stroke-dashoffset",L2)
     .transition().duration(520).attr("stroke-dashoffset",0);
  }
  return p;
}

/* ── mdpChain ──
   o={n,x,y,r,gap,w, label:fn(i), lcls:fn(i), cls:fn(i), rew:fn(i),
      arcs:[[from,to,label,cls,bend]]} */
function mdpChain(o){
  var n=o.n, r=o.r||30, gap=o.gap||((o.w||900)/(n-1)),
      x0=o.x!=null?o.x:(W-(n-1)*gap)/2, y=o.y||300, pos=[];
  for(var i=0;i<n;i++){
    var cx=x0+i*gap; pos.push([cx,y]);
    var c=gS.append("circle").attr("class","snode "+((o.cls&&o.cls(i))||""))
      .attr("cx",cx).attr("cy",y).attr("r",r);
    fadeIn(c,i*55);
    if(o.label)note(o.label(i),cx,y+5,(o.lcls&&o.lcls(i))||"ink");
    if(o.rew&&o.rew(i)!=null)note(o.rew(i),cx,y-r-14,"y");
  }
  (o.arcs||[]).forEach(function(a){
    var A=pos[a[0]],B=pos[a[1]],sgn=B[0]>=A[0]?1:-1,bend=a[4]||0;
    arrow(A[0]+sgn*r,A[1],B[0]-sgn*r,B[1],a[3]||"",bend);
    /* 事故实录：这里原来是 Math.abs(bend)，把弧的方向丢掉了。两个后果都实测到过：
       (1) L02 KP1 的 A⇄B 来回弧，两个「1.0」标签落在同一个像素框 (627,255)-(653,273)；
       (2) L02 KP2 的 bend=-84 让弧向下弯，标签却仍算在上方，离自己的弧 100px。
       arrow 的控制点 y = my+(dx/L)*bend，故弧顶 y = A[1]+sgn*bend/2；标签跟着弧顶走。 */
    if(a[2]){
      var eff=sgn*bend, ay=A[1]+eff/2;
      note(a[2],(A[0]+B[0])/2, bend?(eff<0?ay-12:ay+20):A[1]-16, a[3]||"");
    }
  });
  return pos;
}

/* ── bars ──
   o={vals:[],x,y,w,h,max, label:fn(i), cls:fn(i), fmt:fn(v)} */
function bars(o){
  var v=o.vals,n=v.length,
      x0=o.x!=null?o.x:200, y0=o.y!=null?o.y:460,
      w=o.w||880, h=o.h||210, gap=w/n, bw=gap*0.62, mx=o.max;
  if(mx==null){
    mx=0; for(var q=0;q<n;q++) if(Math.abs(v[q])>mx) mx=Math.abs(v[q]);
  }
  if(!mx)mx=1;
  gS.append("line").attr("class","axline")
    .attr("x1",x0).attr("x2",x0+w).attr("y1",y0).attr("y2",y0);
  for(var i=0;i<n;i++){
    var hh=Math.abs(v[i])/mx*h, cx=x0+i*gap+gap/2;
    var b=gS.append("rect").attr("class","vbar "+((o.cls&&o.cls(i))||""))
      .attr("x",cx-bw/2).attr("width",bw).attr("rx",3);
    if(fast())b.attr("y",y0-hh).attr("height",hh);
    else b.attr("y",y0).attr("height",0).transition().duration(DUR).delay(i*45)
          .attr("y",y0-hh).attr("height",hh);
    if(o.label)note(o.label(i),cx,y0+22,"sm");
    note(o.fmt?o.fmt(v[i]):(Math.round(v[i]*100)/100),
         cx,y0-hh-9,((o.cls&&o.cls(i))||"")+" sm");
  }
}

/* ── gridworld ──
   o={rows,cols,x,y,cs, val:fn(i,j), pol:fn(i,j)->"u|d|l|r",
      cls:fn(i,j), wall:fn(i,j), tag:fn(i,j)} */
function gridworld(o){
  var R=o.rows,C=o.cols,cs=o.cs||88,
      x0=o.x!=null?o.x:(W-C*cs)/2, y0=o.y!=null?o.y:150;
  for(var i=0;i<R;i++)for(var j=0;j<C;j++){
    var isW=o.wall&&o.wall(i,j);
    var cl=isW?"wall":((o.cls&&o.cls(i,j))||"");
    var rc=gS.append("rect").attr("class","gcell "+cl)
      .attr("x",x0+j*cs).attr("y",y0+i*cs)
      .attr("width",cs-4).attr("height",cs-4).attr("rx",5);
    fadeIn(rc,(i*C+j)*16);
    if(isW)continue;
    var cx=x0+j*cs+(cs-4)/2, cy=y0+i*cs+(cs-4)/2;
    if(o.val&&o.val(i,j)!=null)note(o.val(i,j),cx,cy+5,((o.cls&&o.cls(i,j))||"ink"));
    if(o.tag&&o.tag(i,j))note(o.tag(i,j),x0+j*cs+7,y0+i*cs+15,"sm","start");
    if(o.pol&&o.pol(i,j)){
      var d=o.pol(i,j),L=cs*0.26,
          dx=d==="l"?-L:d==="r"?L:0, dy=d==="u"?-L:d==="d"?L:0,
          off=o.val?16:0;
      arrow(cx-dx*0.5,cy-dy*0.5+off,cx+dx*0.9,cy+dy*0.9+off,"y");
    }
  }
  return {x0:x0,y0:y0,cs:cs,
          cx:function(j){return x0+j*cs+(cs-4)/2;},
          cy:function(i){return y0+i*cs+(cs-4)/2;}};
}

/* ── backup：Sutton&Barto 回溯图 ──
   o={x,y,dy,spread,r, levels:["s","a","s"], branch:[1,2], labels:[], hl:[]} */
function backup(o){
  var x=o.x!=null?o.x:W/2, y=o.y!=null?o.y:150, dy=o.dy||105, r=o.r||20,
      lv=o.levels, br=o.branch||[], hl=o.hl||[], lab=o.labels||[], cur=[[x,y]];
  for(var k=0;k<lv.length;k++){
    var kind=lv[k], isHL=hl.indexOf(k)>=0, next=[];
    (function(kind,isHL,k){
      cur.forEach(function(p,pi){
        var c;
        if(kind==="s")
          c=gS.append("circle").attr("class","snode "+(isHL?"y":""))
             .attr("cx",p[0]).attr("cy",p[1]).attr("r",r);
        else
          c=gS.append("circle").attr("class","anode "+(isHL?"y":""))
             .attr("cx",p[0]).attr("cy",p[1]).attr("r",r*0.42);
        fadeIn(c,k*90);
        if(lab[k]&&pi===0)note(lab[k],p[0]-r-12,p[1]+5,isHL?"y":"","end");
      });
    })(kind,isHL,k);
    if(k<lv.length-1){
      var b=br[k]||1, spread=(o.spread||150)/Math.pow(1.7,k);
      cur.forEach(function(p){
        for(var m=0;m<b;m++){
          var nx=p[0]+(b===1?0:(m-(b-1)/2)*spread), ny=p[1]+dy;
          gS.append("path").attr("class","tedge").attr("d","M"+p[0]+","+p[1]+"L"+nx+","+ny);
          next.push([nx,ny]);
        }
      });
      cur=next;
    }
  }
}

/* ── tree：upto 控制画到第几个节点 ──
   o={nodes:[{id,parent,x,y,label,sub,cls}], upto, r} */
function tree(o){
  var r=o.r||24, N=o.nodes, up=o.upto!=null?o.upto:N.length, pos={};
  N.forEach(function(nd){ pos[nd.id]=[nd.x,nd.y]; });
  N.forEach(function(nd,i){
    if(i>=up)return;
    if(nd.parent!=null&&pos[nd.parent]){
      var p=pos[nd.parent];
      var e=gS.append("path").attr("class","tedge "+(nd.cls==="hl"?"hl":""))
        .attr("d","M"+p[0]+","+p[1]+"L"+nd.x+","+nd.y);
      if(!fast()&&e.node().getTotalLength){
        var L=e.node().getTotalLength();
        e.attr("stroke-dasharray",L+" "+L).attr("stroke-dashoffset",L)
         .transition().duration(380).delay(i*70).attr("stroke-dashoffset",0);
      }
    }
    var c=gS.append("circle").attr("class","tnode "+(nd.cls||""))
      .attr("cx",nd.x).attr("cy",nd.y).attr("r",r);
    fadeIn(c,i*70);
    if(nd.label)note(nd.label,nd.x,nd.y+5,"ink");
    if(nd.sub)note(nd.sub,nd.x,nd.y+r+15,"sm");
  });
}

/* ── errbar ──
   o={items:[{label,mean,lo,hi,cls,tag}], x,y,w,h, ymin,ymax} */
function errbar(o){
  var it=o.items,n=it.length,
      x0=o.x!=null?o.x:240, y0=o.y!=null?o.y:180,
      w=o.w||800, h=o.h||300, gap=w/n, lo=o.ymin, hi=o.ymax;
  if(lo==null){lo=it[0].lo; it.forEach(function(d){if(d.lo<lo)lo=d.lo;});}
  if(hi==null){hi=it[0].hi; it.forEach(function(d){if(d.hi>hi)hi=d.hi;});}
  var span=(hi-lo)||1, Y=function(v){return y0+h-(v-lo)/span*h;};
  gS.append("line").attr("class","axline")
    .attr("x1",x0).attr("x2",x0+w).attr("y1",y0+h).attr("y2",y0+h);
  gS.append("line").attr("class","axline")
    .attr("x1",x0).attr("x2",x0).attr("y1",y0).attr("y2",y0+h);
  it.forEach(function(d,i){
    var cx=x0+i*gap+gap/2, cl=d.cls||"", cap=13;
    var g=gS.append("g"); fadeIn(g,i*90);
    g.append("path").attr("class","ebar "+cl).attr("d",
      "M"+(cx-cap)+","+Y(d.hi)+"H"+(cx+cap)+
      "M"+cx+","+Y(d.hi)+"V"+Y(d.lo)+
      "M"+(cx-cap)+","+Y(d.lo)+"H"+(cx+cap));
    g.append("circle")
      .attr("class","pt "+(cl==="y"?"y":cl==="g"?"c":cl==="r"?"b":"a"))
      .attr("cx",cx).attr("cy",Y(d.mean)).attr("r",6);
    note(d.label,cx,y0+h+22,"sm");
    if(d.tag)note(d.tag,cx,Y(d.hi)-12,cl+" sm");
  });
  return {Y:Y,x0:x0,w:w};
}

/* ── lamps ──
   o={items:[{label,sub,state:"on|off|dead"}], x,y,r,gap, caption} */
function lamps(o){
  var it=o.items,n=it.length,gap=o.gap||210,
      x0=o.x!=null?o.x:(W-(n-1)*gap)/2, y=o.y||210, r=o.r||34;
  it.forEach(function(d,i){
    var cx=x0+i*gap, st=d.state||"off";
    var c=gS.append("circle").attr("class","lamp "+st).attr("cx",cx).attr("cy",y).attr("r",r);
    fadeIn(c,i*80);
    note(st==="dead"?"✕":(st==="on"?"✓":"—"),cx,y+7,
         st==="dead"?"r":(st==="on"?"y":""));
    note(d.label,cx,y+r+22,st==="on"?"y":(st==="dead"?"r":"sm"));
    if(d.sub)note(d.sub,cx,y+r+40,"sm");
  });
  if(o.caption)note(o.caption,W/2,y+r+82,"ink big");
}

/* ═══════════ 演示机制的动画 ═══════════
   每个函数下面都写了「它在演示什么」。写不出这一句的动画不要写。
   全部播一次即停在正确终态，不循环。 */

/* ── trace ──
   演示什么：智能体<b>沿这条路走了一趟</b>，走过的地方留下痕迹。
   用于：策略的轨迹、示范轨迹与偏移轨迹的对比。
   o={pts:[[x,y]..], dur, cls, r, label, trail:true} */
function trace(o){
  var pts=o.pts, d="M"+pts[0][0]+","+pts[0][1];
  for(var i=1;i<pts.length;i++)d+="L"+pts[i][0]+","+pts[i][1];
  if(o.trail!==false){
    var tp=gS.append("path").attr("class","arw "+(o.cls||"y")+" trail")
      .attr("d",d).attr("marker-end",null);
    if(!fast()&&tp.node().getTotalLength){
      var L=tp.node().getTotalLength();
      tp.attr("stroke-dasharray",L+" "+L).attr("stroke-dashoffset",L)
        .transition().duration((o.dur||2.4)*1000).ease(d3.easeSinInOut)
        .attr("stroke-dashoffset",0);
    }
  }
  var g=gS.append("g").attr("class","tracer")
    .style("offset-path",'path("'+d+'")')
    .style("--walk-dur",(o.dur||2.4)+"s");
  g.append("circle").attr("class","snode "+(o.cls||"y"))
    .attr("cx",0).attr("cy",0).attr("r",o.r||13);
  if(o.label)g.append("text").attr("class","slbl ink")
    .attr("x",0).attr("y",4).attr("text-anchor","middle").text(o.label);
  return g;
}

/* ── morphBars ──
   演示什么：参数一变，<b>每根柱子怎么随之变化</b>——谁涨谁跌、谁反超谁。
   用于：γ 从一个值变到另一个值时值函数的重排。柱子从 from 高度<b>过渡到</b> to 高度，
   数字同步滚动，所以「反超」这件事是看得见的，而不是两张静态图。
   o={from:[], to:[], x,y,w,h,max, label:fn(i), cls:fn(i), fmt:fn(v), dur} */
function morphBars(o){
  var A=o.from, B=o.to, n=B.length,
      x0=o.x!=null?o.x:200, y0=o.y!=null?o.y:460,
      w=o.w||880, h=o.h||210, gap=w/n, bw=gap*0.62,
      mx=o.max, dur=(o.dur||1400);
  if(mx==null){mx=0;B.forEach(function(v){if(Math.abs(v)>mx)mx=Math.abs(v);});}
  if(!mx)mx=1;
  var fmt=o.fmt||function(v){return (Math.round(v*100)/100).toString();};
  gS.append("line").attr("class","axline")
    .attr("x1",x0).attr("x2",x0+w).attr("y1",y0).attr("y2",y0);
  for(var i=0;i<n;i++){
    (function(i){
      var cx=x0+i*gap+gap/2,
          hA=Math.abs(A[i])/mx*h, hB=Math.abs(B[i])/mx*h;
      var bar=gS.append("rect").attr("class","vbar "+((o.cls&&o.cls(i))||""))
        .attr("x",cx-bw/2).attr("width",bw).attr("rx",3)
        .attr("y",y0-hA).attr("height",hA);
      var txt=gN.append("text").attr("class","slbl "+((o.cls&&o.cls(i))||""))
        .attr("x",cx).attr("text-anchor","middle").attr("y",y0-hA-9).text(fmt(A[i]));
      if(o.label)note(o.label(i),cx,y0+22,"sm");
      if(fast()){bar.attr("y",y0-hB).attr("height",hB);txt.attr("y",y0-hB-9).text(fmt(B[i]));return;}
      bar.transition().duration(dur).ease(d3.easeCubicInOut)
         .attr("y",y0-hB).attr("height",hB);
      txt.transition().duration(dur).ease(d3.easeCubicInOut)
         .attr("y",y0-hB-9)
         .tween("t",function(){var iv=d3.interpolateNumber(A[i],B[i]),self=this;
           return function(t){self.textContent=fmt(iv(t));};});
    })(i);
  }
}

/* ── fillBars ──
   演示什么：动态规划的<b>回代顺序</b>——每个值都要等它右边那个算完才能算。
   用于：Bellman 一致性方程从终点向起点回代。柱子按 order 依次出现，一次。
   o={vals:[], order:[下标顺序], x,y,w,h,max, label, cls, fmt, step:每步毫秒} */
function fillBars(o){
  var v=o.vals,n=v.length,
      x0=o.x!=null?o.x:200, y0=o.y!=null?o.y:460,
      w=o.w||880, h=o.h||210, gap=w/n, bw=gap*0.62,
      mx=o.max, step=o.step||260;
  if(mx==null){mx=0;v.forEach(function(q){if(Math.abs(q)>mx)mx=Math.abs(q);});}
  if(!mx)mx=1;
  var fmt=o.fmt||function(q){return (Math.round(q*100)/100).toString();};
  var order=o.order;
  if(!order){order=[];for(var k=n-1;k>=0;k--)order.push(k);}  // 默认从右往左
  gS.append("line").attr("class","axline")
    .attr("x1",x0).attr("x2",x0+w).attr("y1",y0).attr("y2",y0);
  for(var i=0;i<n;i++){
    var cx=x0+i*gap+gap/2;
    gS.append("rect").attr("class","gcell")
      .attr("x",cx-bw/2).attr("y",y0-h).attr("width",bw).attr("height",h)
      .attr("rx",3).attr("opacity",.16);
    if(o.label)note(o.label(i),cx,y0+22,"sm");
  }
  order.forEach(function(idx,rank){
    var cx=x0+idx*gap+gap/2, hh=Math.abs(v[idx])/mx*h,
        delay=fast()?0:rank*step;
    var bar=gS.append("rect").attr("class","vbar "+((o.cls&&o.cls(idx))||""))
      .attr("x",cx-bw/2).attr("width",bw).attr("rx",3);
    var txt=gN.append("text").attr("class","slbl "+((o.cls&&o.cls(idx))||""))
      .attr("x",cx).attr("y",y0-hh-9).attr("text-anchor","middle").text(fmt(v[idx]));
    if(fast()){bar.attr("y",y0-hh).attr("height",hh);return;}
    bar.attr("y",y0).attr("height",0).transition().duration(320).delay(delay)
       .attr("y",y0-hh).attr("height",hh);
    txt.attr("opacity",0).transition().duration(320).delay(delay).attr("opacity",1);
  });
}

/* ── sweepGrid ──
   演示什么：值迭代时信息<b>从目标格向外一圈圈扩散</b>的顺序。
   用于：格子世界的一轮扫描。格子按 order 依次点亮并写入值，一次。
   o={rows,cols,x,y,cs, val:fn(i,j), order:[[i,j]..], cls:fn(i,j), step} */
function sweepGrid(o){
  var R=o.rows,C=o.cols,cs=o.cs||88,
      x0=o.x!=null?o.x:(W-C*cs)/2, y0=o.y!=null?o.y:150, step=o.step||190;
  for(var i=0;i<R;i++)for(var j=0;j<C;j++){
    gS.append("rect").attr("class","gcell")
      .attr("x",x0+j*cs).attr("y",y0+i*cs)
      .attr("width",cs-4).attr("height",cs-4).attr("rx",5);
  }
  (o.order||[]).forEach(function(ij,rank){
    var i=ij[0], j=ij[1],
        cx=x0+j*cs+(cs-4)/2, cy=y0+i*cs+(cs-4)/2,
        delay=fast()?0:rank*step;
    var rc=gS.append("rect").attr("class","gcell "+((o.cls&&o.cls(i,j))||"hl"))
      .attr("x",x0+j*cs).attr("y",y0+i*cs)
      .attr("width",cs-4).attr("height",cs-4).attr("rx",5);
    var tx=gN.append("text").attr("class","slbl ink")
      .attr("x",cx).attr("y",cy+5).attr("text-anchor","middle")
      .text(o.val?o.val(i,j):"");
    if(fast())return;
    rc.attr("opacity",0).transition().duration(300).delay(delay).attr("opacity",1);
    tx.attr("opacity",0).transition().duration(300).delay(delay).attr("opacity",1);
  });
  return {x0:x0,y0:y0,cs:cs,
          cx:function(j){return x0+j*cs+(cs-4)/2;},
          cy:function(i){return y0+i*cs+(cs-4)/2;}};
}

/* ── reveal ──
   演示什么：一组元素之间的<b>因果或时间顺序</b>（先有这个，才有那个）。
   用于：信用分配里奖励回传的路径、推导步骤的先后。
   sel 是 d3 选择集，按数据顺序依次淡入，一次。 */
function reveal(sel,step){
  if(fast())return sel.attr("opacity",1);
  return sel.attr("opacity",0).transition().duration(340)
            .delay(function(d,i){return i*(step||240);}).attr("opacity",1);
}

E.arrow=arrow; E.mdpChain=mdpChain; E.bars=bars; E.gridworld=gridworld;
E.backup=backup; E.tree=tree; E.errbar=errbar; E.lamps=lamps;
E.trace=trace; E.morphBars=morphBars; E.fillBars=fillBars;
E.sweepGrid=sweepGrid; E.reveal=reveal;
})();
"""


def engine():
    """读 eng.txt，打上补丁并注入 RL 图元包。幂等。"""
    src = io.open(os.path.join(HERE, "eng.txt"), encoding="utf-8").read()

    if _EXPORT_NEW not in src:
        if _EXPORT_OLD not in src:
            raise RuntimeError("eng.txt 的 __engine 导出行找不到，引擎结构变了，补丁需要重新对齐")
        src = src.replace(_EXPORT_OLD, _EXPORT_NEW, 1)

    if "RL 图元包" not in src:
        i = src.rfind("</style>")
        if i < 0:
            raise RuntimeError("eng.txt 里找不到 </style>")
        src = src[:i] + RL_CSS + "\n" + src[i:]
        src = src + "\n<script>\n" + RL_JS + "\n</script>\n"

    return src


HEADER = r'''(function(){
var E=window.__engine;
var S=E.S,KP=E.KP,SUM=E.SUM,QUIZ=E.QUIZ,W=E.W,H=E.H,rng=E.rng;
var clearScene=E.clearScene,setTitle=E.setTitle,setBig=E.setBig,setCap=E.setCap,
    setEq=E.setEq,flip=E.flip,T=E.T,note=E.note,dots=E.dots,curve=E.curve,fn=E.fn,
    boxNode=E.boxNode,link=E.link,matrix=E.matrix,axes=E.axes,noTitle=E.noTitle;
var arrow=E.arrow,mdpChain=E.mdpChain,bars=E.bars,gridworld=E.gridworld,
    backup=E.backup,tree=E.tree,errbar=E.errbar,lamps=E.lamps;
var trace=E.trace,morphBars=E.morphBars,fillBars=E.fillBars,
    sweepGrid=E.sweepGrid,reveal=E.reveal;
'''


def write(name, title, body):
    """把内容体装配成完整 HTML 并写出到 ../影片/。"""
    full = (engine() + "<script>\n" + HEADER + body
            + "\nwindow.__startProjector(CFG);\n})();\n</script>\n")
    full = full.replace("<title>放映厅模板</title>", "<title>" + title + "</title>", 1)
    outdir = _paths.out_dir()
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    out = os.path.join(outdir, name)
    io.open(out, "w", encoding="utf-8").write(full)
    print("%s  %d KB  |  %d KP  %d 镜  %d 总结卡  %d 测验" % (
        name, len(full.encode("utf-8")) // 1024,
        len(re.findall(r"\bKP\(", body)), len(re.findall(r"\bS\(\d", body)),
        len(re.findall(r"\bSUM\(", body)), len(re.findall(r"\bQUIZ\(", body))))
    return out
