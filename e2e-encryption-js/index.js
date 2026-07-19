const keyExchangeOption = {
  name: "ECDH",
  namedCurve: "P-384",
}
const keyExportImportOption = "jwk"

function deriveSecretKey(privateKey, publicKey) {
  return window.crypto.subtle.deriveKey(
    {
      name: "ECDH",
      public: publicKey
    },
    privateKey,
    {
      name: "AES-GCM",
      length: 256,
    },
    false,
    ["encrypt", "decrypt"],
  );
}

async function generateKey() {
  let keyPair = await window.crypto.subtle.generateKey(
    keyExchangeOption,
    false,
    ["deriveKey"]
  );
  /*
   * { privateKey: ..., publicKey: ... }
   */
  return keyPair;
}

function getMessageEncoding(text) {
  let enc = new TextEncoder();
  return enc.encode(text);
}

async function encrypt(secretKey, text) {
  const iv = window.crypto.getRandomValues(new Uint8Array(12));
  const encoded = getMessageEncoding(text);
  const ciphertext = await window.crypto.subtle.encrypt(
    {
      name: "AES-GCM",
      iv
    },
    secretKey,
    encoded
  )
  const buffer = new Uint8Array(ciphertext);
  const base64ciphertext = buffer.toBase64();
  const base64iv = iv.toBase64();

  return { base64iv, base64ciphertext }
}

async function decrypt(secretKey, payload) {
  const { base64iv, base64ciphertext } = payload;
  const ciphertext = Uint8Array.fromBase64(base64ciphertext);
  const iv = Uint8Array.fromBase64(base64iv);
  let decrypted = await window.crypto.subtle.decrypt(
    {
      name: "AES-GCM",
      iv
    },
    secretKey,
    ciphertext
  );
  let dec = new TextDecoder();
  return dec.decode(decrypted);
}

async function exportKey(publicKey) {
  const exportedKey = await window.crypto.subtle.exportKey(
    keyExportImportOption,
    publicKey
  );
  return exportedKey
}

function importSecretKey(key) {
  return window.crypto.subtle.importKey(
    keyExportImportOption,
    key,
    keyExchangeOption,
    true,
    []
  );
}

document.querySelector("#genKey").addEventListener("click", async () => {
  window.myKey = await generateKey();
});

document.querySelector("#postPubKey").addEventListener("click", async () => {
  const name = document.querySelector("#name").value;
  const exportedKey = await exportKey(window.myKey.publicKey);
  const body = JSON.stringify({ name: name, exportedPublicKey: exportedKey })
  await fetch(`/postPubKey`, { method: "POST", body: body, headers: { "Content-Type": "application/json" }, }).then(r => r.json());
});

document.querySelector("#getPubKey").addEventListener("click", async () => {
  const oppName = document.querySelector("#opp-name").value;
  const j = await fetch(`/getPubKey?name=${oppName}`, { headers: { "Content-Type": "application/json", } }).then(r => r.json());
  const pubKey = await importSecretKey(j)
  window.secKey = await deriveSecretKey(window.myKey.privateKey, pubKey);
});

document.querySelector("#send").addEventListener("click", async () => {
  const name = document.querySelector("#name").value;
  const oppName = document.querySelector("#opp-name").value;

  const txt = document.querySelector('#input').value;
  const encrypted = await encrypt(window.secKey, txt)
  const body = JSON.stringify({ name, oppName, encrypted });
  await fetch(`/sendMessageTo`, { method: "POST", headers: { "Content-Type": "application/json", }, body })
});

document.querySelector("#fetch").addEventListener("click", async () => {
  const name = document.querySelector("#name").value;
  const oppName = document.querySelector("#opp-name").value;

  const j = await fetch(`/getMessage?name=${name}&oppName=${oppName}`, { headers: { "Content-Type": "application/json" } }).then(r => r.json());
  const text = await decrypt(window.secKey, j.encrypted)
  document.querySelector("#output").textContent = text;
});

window.onerror = (event, source, lineno, colno, error) => {
  document.querySelector("#error").textContent = `${event.toString}:${source.toString()}:${lineno}:${colno}:${error.toString()}`
}
