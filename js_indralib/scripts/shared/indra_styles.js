
"use strict";

export function generateCssText(styles, selector) {
    let cssText = '';
    if (styles.hasOwnProperty(selector)) {
        cssText += `${selector} {`;
        for (const property in styles[selector]) {
            if (styles[selector].hasOwnProperty(property)) {
                const value = styles[selector][property];
                cssText += `${property}: ${value};`;
            }
        }
        cssText += `}`;
    }
    return cssText;
}

const indraStyleDict = {
    '.container-style': {
        'max-width': '400px',
        'margin': '0 auto',
        'padding': '20px',
        'border': '1px solid #ccc',
        'border-radius': '5px',
        'box-shadow': '0 0 10px rgba(0, 0, 0, 0.1)'
    },
    '.margin-bottom': {
        'margin-bottom': '20px'
    },
    '.label-style': {
        'display': 'block',
        'font-weight': 'bold',
        'margin-bottom': '5px'
    },
    '.input-style': {
        'width': '100%',
        'padding': '10px',
        'border-radius': '3px',
        'border': '1px solid #ccc',
        'box-sizing': 'border-box'
    },
    '.button-style': {
        'display': 'block',
        'width': '100%',
        'padding': '10px',
        'border': 'none',
        'border-radius': '3px',
        'background-color': '#007bff',
        'color': '#fff',
        'font-size': '16px',
        'cursor': 'pointer',
        'transition': 'background-color 0.3s'
    },
    'button:hover': {
        'background-color': '#0056b3'
    }
};

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

    // Generate styles from dictionary and append to the document head
    for (const selector in indraStyleDict) {
        const cssText = generateCssText(indraStyleDict, selector);
        const styleElement = document.createElement('style');
        styleElement.textContent = cssText;
        document.head.appendChild(styleElement);
    }
    console.log('Styles appended to the document head.');
}