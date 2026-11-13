// Autonomio backport (GHSA-gcqx-w48m-w2h4): entry shim. Upstream index.js
// required the unpublished-at-runtime 'is-mergeable-object' helper; the
// self-contained patched dist/cjs.js below is the single implementation, so
// this entry forwards to it. Local version 4.3.1-autonomio.1.
module.exports = require('./dist/cjs.js');
