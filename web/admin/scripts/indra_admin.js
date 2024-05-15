
"use strict";
// Browser entry point for Indralib, run with:
// python -m http.server
// point browser to http://localhost:8000/

import { helloWorld } from './shared/indralib.js';
import { indra_styles, indra_custom_styles } from './shared/indra_styles.js';
//import { indra_custom_styles } from './shared/indra_styles.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
  // Code that relies on the DOM being fully loaded
  main();
});

function main() {
  // Create a new div element
  indra_styles();
  const newDiv = document.createElement('div');

  // Set attributes (optional)
  indra_custom_styles();
  newDiv.id = 'myDiv';
  newDiv.classList.add('custom-class');

  // Set inner text or HTML content (optional)
  newDiv.textContent = helloWorld();

  // Append the new div element to an existing element in the DOM
  document.body.appendChild(newDiv);
}
