
"use strict";
// Browser entry point for Indralib, run with:
// python -m http.server
// point browser to http://localhost:8000/

import { indra_styles } from './../indralib/scripts/indra_styles.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
  // Code that relies on the DOM being fully loaded
  main();
});

function createPortal(links) {
  // Create a container for the portal
  const portalContainer = document.createElement('div');
  portalContainer.classList.add('portal-container');

  // Iterate over the array of links
  links.forEach(link => {
    // Create a link element
    const linkElement = document.createElement('a');
    linkElement.href = link.url;
    linkElement.textContent = link.description;
    linkElement.classList.add('portal-link');

    // Create an icon element
    const iconElement = document.createElement('i');
    iconElement.classList.add('fas', link.icon); // Assuming link.icon contains the Font Awesome icon class

    // Append the icon to the link
    linkElement.prepend(iconElement);

    // Append the link to the portal container
    portalContainer.appendChild(linkElement);
  });

  // Return the portal container
  return portalContainer;
}

function main() {
  const links = [
    { url: 'https://www.google.com', description: 'Google', icon: 'search' },
    { url: 'admin/index.html', description: 'Admin Portal', icon: 'admin_panel_settings' },
  ];
  indra_styles();
  const portal = createPortal(links);
  document.body.appendChild(portal);
}

