
"use strict";

export function indra_styles() {
    // Select the elements to normalize
    const elementsToNormalize = ['html', 'body', 'div', 'span', 'iframe'];

    // Loop through each element and apply normalization styles
    elementsToNormalize.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
            element.style.margin = '0';
            element.style.padding = '0';
            element.style.border = '0';
            element.style.fontSize = '100%';
            element.style.fontFamily = 'Arial, Helvetica, sans-serif';
            element.style.verticalAlign = 'baseline';
        });
    });
}

export function indra_custom_styles() {
    const cssText = `
  .custom-class {
    background-color: blue;
    color: white;
    padding: 10px;
    border: 1px solid black;
  }
  `;

    // Create a new style element
    const styleElement = document.createElement('style');

    // Set the CSS text content of the style element
    styleElement.textContent = cssText;

    // Append the style element to the head of the document
    document.head.appendChild(styleElement);
    console.log('Styles appended to the document head.');
}
