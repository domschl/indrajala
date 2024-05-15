
"use strict";
// Browser entry point for Indralib, run with:
// python -m http.server
// point browser to http://localhost:8000/

import { helloWorld } from './shared/indralib.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function() {
    // Code that relies on the DOM being fully loaded
    console.log(helloWorld());
  });
