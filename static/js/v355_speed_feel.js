
(function(){
function isClient(){return location.pathname.startsWith('/cliente')}
function animate(){
 if(!isClient()) return;
 document.querySelectorAll('.v355-card').forEach((el,i)=>{
   el.style.opacity='0';el.style.transform='translateY(8px)';
   setTimeout(()=>{el.style.opacity='1';el.style.transform='';},90+i*70);
 });
}
function instantFeedback(){
 document.querySelectorAll('a,button').forEach(el=>{
   el.addEventListener('click',()=>{
     el.style.filter='brightness(1.18)';
     setTimeout(()=>el.style.filter='',160);
   },{passive:true});
 });
}
document.addEventListener('DOMContentLoaded',()=>{animate();instantFeedback();});
})();
