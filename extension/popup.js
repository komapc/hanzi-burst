const $ = id => document.getElementById(id);
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  let h = ''; try { h = new URL(tab.url).hostname; } catch (e) {}
  const key = 'off:' + h;
  $('host').textContent = h || 'this page';
  chrome.storage.local.get(['enabled', 'mode', key], v => { $('on').checked = v.enabled !== false; $('mode').value = v.mode === 'hover' ? 'hover' : 'select'; $('site').checked = !!v[key]; });
  $('on').onchange = () => chrome.storage.local.set({ enabled: $('on').checked });
  $('mode').onchange = () => chrome.storage.local.set({ mode: $('mode').value });
  $('site').onchange = () => h && chrome.storage.local.set({ [key]: $('site').checked });
});
