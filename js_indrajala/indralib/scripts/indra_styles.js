
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

const white_std = '#fff';
const gray_std = '#ccc';

export const color_scheme = {
    'light': {
        'button-bg': '#007bff', 'button-fg': white_std, 'button-hover': '#0056b3', 'button-disabled': gray_std,
        'status-bg': '#0056b3', 'status-fg': white_std, 'status-hover': '#007bff', 'status-error': '#dc3545', 'status-success': '#28a745',
        'edit-mouse-enter': '#0056b3', 'edit-mouse-leave': '#007bff',
        'notification-bg': '#333', 'notification-fg': white_std, 'notification-hover': '#007bff',
        'background': white_std, 'foreground': '#333', 'border': gray_std,
    },
}


const indraStyleDict = {
    '.container-style': {
        'max-width': '400px',
        'margin': '0 auto',
        'padding': '20px',
        'border': '1px solid ' + gray_std,
        'border-radius': '5px',
        'box-shadow': '0 0 10px rgba(0, 0, 0, 0.1)'
    },
    '.margin-top': {
        'margin-top': '20px'
    },
    '.margin-bottom': {
        'margin-bottom': '20px'
    },
    '.margin-bottom-40': {
        'margin-bottom': '40px'
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
        'font-size': '16px',  // This prevents iOS from zooming in on input fields 
        'border': '1px solid ' + gray_std,
        'box-sizing': 'border-box'
    },
    '.button-style': {
        'display': 'block',
        'width': '100%',
        'padding': '10px',
        'border': 'none',
        'border-radius': '3px',
        'background-color': color_scheme['light']['button-bg'],
        'color': color_scheme['light']['button-fg'],
        'font-size': '16px',
        'cursor': 'pointer',
        'transition': 'background-color 0.3s'
    },
    '.half-button-style': {
        'display': 'block',
        'width': '47.5%',
        'padding': '10px',
        'border': 'none',
        'border-radius': '3px',
        'background-color': color_scheme['light']['button-bg'],
        'color': color_scheme['light']['button-fg'],
        'font-size': '16px',
        'cursor': 'pointer',
        'transition': 'background-color 0.3s'
    },
    '.icon-button-style': {
        'display': 'block',
        'padding': '10px',
        'width': '70px',
        'border': 'none',
        'border-radius': '3px',
        'background-color': color_scheme['light']['button-bg'],
        'color': color_scheme['light']['button-fg'],
        'cursor': 'pointer',
        'transition': 'background-color 0.3s',

        'font-family': 'Material Icons',
        'font-weight': 'normal',
        'font-style': 'normal',
        'font-size': '24px',  // Preferred icon size
        'display': 'inline-block',
        'line-height': '1',
        'text-transform': 'none',
        'letter-spacing': 'normal',
        'word-wrap': 'normal',
        'white-space': 'nowrap',
        'direction': 'ltr',
        'font-feature-settings': 'liga'
    },
    '.button-line': {
        'display': 'flex',
        'justify-content': 'space-between' /* Adjust as needed */
    },
    'button:hover': {
        'background-color': color_scheme['light']['button-hover']
    },
    '.notification': {
        'position': 'fixed',
        'bottom': '10px',  /* Adjust bottom distance as needed */
        'left': '50%',
        'transform': 'translateX(-50%)',
        'background-color': color_scheme['light']['notification-bg'],
        'color': color_scheme['light']['notification-fg'],
        'padding': '10px 20px',
        'border-radius': '5px',
        'opacity': '0',
        'transition': 'opacity 0.5s ease-in-out'
    },
    '.status-line': {
        'position': 'fixed',
        'bottom': '10px',
        'width': '100%',
        //'left': '50%',
        //'transform': 'translateX(-50%)',
        'background-color': color_scheme['light']['status-bg'],
        'color': color_scheme['light']['status-fg'],
        'padding': '10px 20px',
        //'border-radius': '5px',
        'opacity': '0',
        'transition': 'opacity 0.5s ease-in-out'
    },
    '.overlay': {
        'position': 'relative',
        'pointer-events': 'none'
    },
    '.overlay::before': {
        'content': '""',
        'position': 'absolute',
        'top': '0',
        'left': '0',
        'width': '100%',
        'height': '100%',
        'background-color': 'rgba(0, 0, 0, 0.3)',
        'z-index': '999'
    },
    '.portal-container': {
        'display': 'flex',
        'flex-direction': 'column',
        'align-items': 'center'
    },
    '.portal-link': {
        'display': 'flex',
        'align-items': 'center',
        'width': '90%',
        'padding': '10px 10px',
        'margin': '10px 10px',
        'background-color': color_scheme['light']['button-bg'],
        'color': color_scheme['light']['button-fg'],
        'text-decoration': 'none',
        'border-radius': '5px',
        'transition': 'background-color 0.3s ease'
    },
    '.portal-link i': {
        'margin-right': '10px' /* Spacing between icon and text */
    },
    '.portal-link:hover': {
        'background-color': color_scheme['light']['button-hover']
    },
    '.material-icons': {
        'font-family': 'Material Icons',
        'font-weight': 'normal',
        'font-style': 'normal',
        'font-size': '24px',  // Preferred icon size
        'display': 'inline-block',
        'line-height': '1',
        'text-transform': 'none',
        'letter-spacing': 'normal',
        'word-wrap': 'normal',
        'white-space': 'nowrap',
        'direction': 'ltr',
        'font-feature-settings': 'liga'
    },
    '.userList': {
        'list-style-type': 'none',
        'width': '100%',
        'padding': '0',
        'margin': '0',
        'max-height': '300px', /* Adjust the maximum height as needed */
        'overflow-y': 'auto' /* Enable vertical scrolling */
    },
    '.userListItem': {
        'display': 'flex',
        'align-items': 'center',
        'margin-bottom': '-1px',
        'border': '1px solid ' + gray_std, /* Add a light gray border */
        'padding': '10px', /* Add padding for spacing */
        'cursor': 'pointer', /* Change cursor to pointer on hover */
    },
    '.userListItem:hover': {
        'background-color': '#f9f9f9' /* Change background color on hover */
    },
    '.userListItem.selected': {
        'background-color': '#f0f0f0' /* Change background color when selected */
    },
    '.iconContainer': {
        'margin-right': '10px'
    },
    '.textContainer': {
        'display': 'flex',
        'flex-direction': 'column'
    },
    '.userIcon': {
        'margin-right': '10px'
    },
    '.username': {
        'font-weight': 'bold'
    },
    '.fullname': {
        'font-size': 'smaller',
        'color': 'gray'
    },
    '.selectBox': {
        'display': 'flex',
        'align-items': 'center',
        'justify-content': 'space-between',
        'padding': '10px',
        'border': '1px solid ' + gray_std,
        'border-radius': '3px',
        'cursor': 'pointer',
        'height': '40px',
        'width': '100%',
        'font-size': '16px',  // This prevents iOS from zooming in on input fields 
        'appearance': 'none', // No fancy 3D gradient
    },
    'select option': {
        'background-color': white_std,
    },
    '.selectBoxRight': {
        'display': 'bock',
        'align-items': 'center',
        'justify-content': 'space-between',
        'padding': '10px',
        'margin-left': '10px',
        'border': '1px solid ' + gray_std,
        'border-radius': '3px',
        'cursor': 'pointer',
        'height': '40px',
        'width': '80px',
        'font-size': '16px',  // This prevents iOS from zooming in on input fields 
        'appearance': 'none', // No fancy 3D gradient
    },
    '.separator': {
        'width': '100%',
        'height': '1px',
        'background-color': gray_std, /* Gray color */
        'margin-top': '10px',
        'margin-bottom': '10px'
    },
    '.pane-container': {
        'display': 'flex',
        'width': '100%',
        'height': '100%',
    },
    '.pane': {
        'display': 'flex',
        'flex-grow': '1',
        'overflow': 'auto',
        'border': '1px solid ' + gray_std,
        'width': '100%',
        'height': '100%',
    },
    '.plot-pane': {
        'display': 'flex',
        'flex-grow': '1',
        'overflow': 'auto',
        'width': '100%',
        'height': '100%',
    },
    '.plot-canvas': {
        'display': 'flex',
        'flex-grow': '1',
        'overflow': 'auto',
        'width': '100%',
        'height': '100%',
        'min-height': '300px',
    },
    '.splitter': {
        'width': '5px',
        'cursor': 'col-resize',
        'background-color': gray_std
    },
};

function loadMaterialIcons() {
    // Define font file path (replace '/fonts/material-icons.woff2' with the actual path)
    const fontUrl = '/fonts/MaterialIcons-Regular.ttf';

    // Create @font-face rule
    const fontFaceRule = `
      @font-face {
        font-family: 'Material Icons';
        font-style: normal;
        font-weight: 400;
        src: local('Material Icons'), local('MaterialIcons-Regular'), url(${fontUrl}) format('truetype');
      }
    `;

    // Create a style element
    const styleElement = document.createElement('style');
    styleElement.textContent = fontFaceRule;

    // Append the style element to the document head
    document.head.appendChild(styleElement);
}

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

    loadMaterialIcons();
    console.log('Styles appended to the document head.');
}
