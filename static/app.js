// small helper to apply heights to chart bars on dashboard
window.addEventListener('DOMContentLoaded', ()=>{
  try{
    document.querySelectorAll('.bar[data-h]').forEach(el=>{
      const v = parseInt(el.getAttribute('data-h'), 10) || 0;
      el.style.height = v + '%';
    });
  }catch(e){console.error(e)}
});

// existing validation code (if present) - keep minimal
(function(){
  document.addEventListener('submit', function(e){
    // preserve earlier minimal validation behaviour; do nothing here if not needed
  });
})();
