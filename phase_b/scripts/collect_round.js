(async () => {
  const id = __ID__;
  const rows=[]; const pages=[];
  for (let p=1;p<=8;p++) {
    const res=await fetch(`/member/lottery/yeekee/${id}?page=${p}`,{credentials:'same-origin',cache:'no-store'});
    if (res.status!==200) { pages.push({p,status:res.status}); break; }
    const html=await res.text();
    const doc=new DOMParser().parseFromString(html,'text/html');
    const lis=[...doc.querySelectorAll('ul.number-key-list > li')];
    pages.push({p,rows:lis.length});
    for (const li of lis) {
      const seq=parseInt(li.querySelector('.no')?.textContent.trim(),10);
      const num=(li.querySelector('.key')?.textContent||'').replace(/\s+/g,'');
      const ts=(li.innerText.match(/(\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}:\d{2})/)||[])[1]||null;
      if (seq && /^\d{5}$/.test(num)) rows.push({seq,num,ts});
    }
    if (lis.length<50) break;
  }
  return JSON.stringify({id, pages, rows});
})()
