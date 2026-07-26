function getOrCreate(id, tag, parent) {
  let elm = document.getElementById(id)
  if (!elm) {
    elm = document.createElement(tag)
    elm.id = id;
    if (parent === undefined) {
      document.body.append(elm);
    } else {
      parent.append(elm)
    }
  }
  return elm;
}

const setupLoadingDialog = (message = null) => {
  const loadingDialog = getOrCreate("loadingDialog", "dialog")
  loadingDialog.closedBy = "none";
  loadingDialog.innerHTML = "";
  const p = document.createElement("p");
  p.textContent = message ?? "loading...";
  loadingDialog.append(p);
  return loadingDialog;
}

async function runFetch(url, options) {
  const urlObj = new URL(url, window.location.origin)
  urlObj.searchParams.append('screenCd', window.screenCd)
  const method = options?.method ?? "GET";
  const body = method == "GET" ? undefined : JSON.stringify({ ...options?.body })
  return await fetch(urlObj, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
    body
  }).then(r => {
    if (!r.ok) {
      throw new Error(r.body)
    }
    return r
  }).then(r => r.json())
}


const url = new URL(document.location.href)
window.screenCd = url.searchParams.get("screenCd")
