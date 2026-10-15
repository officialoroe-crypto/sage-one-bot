const views=[...document.querySelectorAll('.view')],nav=[...document.querySelectorAll('.nav')];
function show(id){views.forEach(v=>v.classList.toggle('active',v.id===id));nav.forEach(n=>n.classList.toggle('active',n.dataset.view===id));history.replaceState(null,'','#'+id);window.scrollTo(0,0)}
nav.forEach(n=>n.onclick=()=>show(n.dataset.view));
document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>show(b.dataset.open));
document.querySelector('#menu').onclick=()=>document.querySelector('.sidebar').classList.toggle('open');
const initial=location.hash.slice(1); if(initial && document.getElementById(initial)) show(initial);
