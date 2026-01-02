// ====== ITEM AUTOFILL & LOCK FROM EXCEL MASTER ======

document.addEventListener("input", function(e){
  let t = e.target;
  if(t.tagName !== "INPUT") return;

  let nm = (t.name || "").toLowerCase();
  if(!nm.includes("code") && !nm.includes("name") && !nm.includes("category")) return;

  let scope = t.closest("tr") || t.closest("form") || document;

  scope._itemValid = false;   // typing makes it invalid

  let by = "code";
  if(nm.includes("name")) by = "name";
  if(nm.includes("category")) by = "category";

  let q = t.value.trim();
  removeBox();

  if(!q){
    clearScope(scope, t);
    return;
  }

  let pageCat = document.getElementById("pageCategory");
  let cat = pageCat ? pageCat.value : "";

  fetch(`/api/item_lookup?by=${by}&q=${encodeURIComponent(q)}&cat=${encodeURIComponent(cat)}`)

    .then(r=>r.json())
    .then(d=>{
      if(d.ok && d.results && d.results.length){
        showBox(t, scope, d.results);
      } else {
        clearScope(scope, t);
      }
    })
    .catch(()=>{});
});

function showBox(inp, scope, results){
  removeBox();

  let box = document.createElement("div");
  box.id = "autoBox";
  box.style.position = "absolute";
  box.style.background = "#fff";
  box.style.border = "1px solid #999";
  box.style.zIndex = 9999;
  box.style.maxHeight = "180px";
  box.style.overflowY = "auto";
  box.style.width = inp.offsetWidth + "px";
  box.style.fontSize = "13px";

  let r = inp.getBoundingClientRect();
  box.style.left = r.left + window.scrollX + "px";
  box.style.top = r.bottom + window.scrollY + "px";

  results.forEach(it=>{
    let d = document.createElement("div");
    d.style.padding = "4px 6px";
    d.style.cursor = "pointer";
    d.onmouseover = ()=>d.style.background="#eef";
    d.onmouseout = ()=>d.style.background="#fff";

    // 🔹 Display in CAPITAL
    d.innerHTML = `<b>${it.category.toUpperCase()}</b> | ${it.code.toUpperCase()} - ${it.name.toUpperCase()}`;

    d.onclick = ()=>{
      fillScope(scope, it);
      scope._itemValid = true;   // ✅ selected from list
      removeBox();
    };
    box.appendChild(d);
  });

  document.body.appendChild(box);
}

function fillScope(scope, it){
  let cat = scope.querySelector("input[name*='category']");
  let code = scope.querySelector("input[name*='code']");
  let name = scope.querySelector("input[name*='name']");

  if(cat) cat.value = it.category.toUpperCase();
  if(code) code.value = it.code.toUpperCase();
  if(name) name.value = it.name.toUpperCase();
}

function clearScope(scope, active){
  let cat = scope.querySelector("input[name*='category']");
  let code = scope.querySelector("input[name*='code']");
  let name = scope.querySelector("input[name*='name']");

  if(cat && cat !== active) cat.value = "";
  if(code && code !== active) code.value = "";
  if(name && name !== active) name.value = "";
}

function removeBox(){
  let b = document.getElementById("autoBox");
  if(b) b.remove();
}

// 🔒 Block submit if not selected from list
document.addEventListener("submit", function(e){
  let form = e.target;
  if(form._itemValid === false){
    alert("❌ Sirf Excel master se select kiya hua item hi allowed hai.");
    e.preventDefault();
  }
});
