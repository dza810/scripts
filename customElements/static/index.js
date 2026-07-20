function getOrCreate(id, tag, parent) {
  let elm = document.getElementById(id)
  if(!elm) {
    elm = document.createElement(tag)
    elm.id = id;
    if(parent === undefined) {
      document.body.append(elm);
    } else {
      parent.append(elm)
    }
  }
  return elm;
}

const setupLoadingDialog = (message=null) => {
  const loadingDialog = getOrCreate("loadingDialog", "dialog")
  loadingDialog.closedBy = "none";
  loadingDialog.innerHTML = "";
  const p = document.createElement("p");
  p.textContent = message ?? "loading...";
  loadingDialog.append(p);
  return loadingDialog;
}

