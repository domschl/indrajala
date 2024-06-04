
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
    portalContainer.classList.add('container-style')
    portalContainer.classList.add('margin-top');

    // Create title heading
    const titleHeading = document.createElement('h2');
    titleHeading.textContent = 'Indrajāla Portal';
    titleHeading.classList.add('margin-bottom');

    // Create Subtitle
    const appLabel = document.createElement('label');
    appLabel.textContent = 'Applications:';
    appLabel.classList.add('label-style');
    //appLabel.classList.add('margin-bottom-40');

    // Append the title to the portal container
    portalContainer.appendChild(titleHeading);
    portalContainer.appendChild(appLabel);

    // Iterate over the array of links
    links.forEach(link => {
        // Create a link element
        const linkElement = document.createElement('a');
        linkElement.href = link.url;
        linkElement.textContent = link.description;
        linkElement.classList.add('portal-link');

        const iconElement = document.createElement('i');
        // Set the HTML content to the Unicode code point
        iconElement.innerHTML = `&#x${link.iconCodePoint};`;
        iconElement.classList.add('material-icons');

        // Create an icon element
        //const iconElement = document.createElement('i');
        //iconElement.classList.add('material-icons');
        //iconElement.textContent = link.icon;

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
        { url: 'admin/index.html', description: 'Indrajāla Administrator', iconCodePoint: 'ef3d' },  // 'admin_panel_settings'
        { url: 'chat/index.html', description: 'Indrajāla Chat', iconCodePoint: 'e0b7' },  // 'chat'
        { url: 'plot/index.html', description: 'Indrajāla Plot', iconCodePoint: 'e4fc' },  // 'query_stats'
    ];
    indra_styles();
    // load more links from a JSON file at /config/portal_apps.json:
    // format: [{url: '...', description: '...', iconCodePoint: '...'}, ...]
    // get iconCodePoints from https://fonts.google.com/icons (click on icon, then look for 'codepoint')

    fetch('/config/portal_apps.json')
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Data contains the parsed JSON
            console.log(data);

            // Here you can process the data as needed
            // For example, iterate over the array of dictionaries
            // appending the links to the links array
            data.forEach(item => {
                links.push(item);
            });

            // Create the portal with the links
            const portal = createPortal(links);
            document.body.appendChild(portal);
        })
        .catch(error => {
            console.error('There was a problem fetching /config/portal_apps.json:', error);
        });
}

