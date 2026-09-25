/* Small shared helpers for the map and the search box. The modelled estimates are
 * computed in the build pipeline, not here, so that the published figures cannot
 * depend on anything a browser does at runtime. */
(function (root) {
  'use strict';
  function bucket(value, thresholds) {
    if (value === null || value === undefined || !Number.isFinite(value)) return -1;
    const i=thresholds.findIndex(t=>value<t);
    return i<0?thresholds.length:i;
  }
  function normalize(value) {
    return String(value).toLocaleLowerCase('de-DE').replace(/ß/g,'ss').normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim();
  }
  const api={bucket,normalize};
  root.AtlasModel=api;
  if (typeof module!=='undefined' && module.exports) module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
