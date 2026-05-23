
(function(){
  document.addEventListener('click',function(e){
    var a=e.target.closest&&e.target.closest('a[href]');
    if(!a||a.target||a.href.indexOf('#')>-1)return;
    document.documentElement.classList.add('v490-navigating');
  },{passive:true});
})();
