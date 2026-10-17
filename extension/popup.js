const $ = id => document.getElementById(id);
chrome.tabs.query({ active: true, currentWindow: true }, ([tab]) => {
  let h = ''; try { h = new URL(tab.url).hostname; } catch (e) {}
  const key = 'off:' + h;
  $('host').textContent = h || 'this page';
  chrome.storage.local.get(['enabled', key], v => { $('on').checked = v.enabled !== false; $('site').checked = !!v[key]; });
  $('on').onchange = () => chrome.storage.local.set({ enabled: $('on').checked });
  $('site').onchange = () => h && chrome.storage.local.set({ [key]: $('site').checked });
});
