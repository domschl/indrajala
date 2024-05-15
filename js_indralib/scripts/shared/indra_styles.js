
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
    //    const cssText = `
    //  .custom-class {
    //    background-color: blue;
    //    color: white;
    //    padding: 10px;
    //    border: 1px solid black;
    //  }
    //  `;

    // Create a new style element
    //const styleElement = document.createElement('style');

    // Set the CSS text content of the style element
    //styleElement.textContent = cssText;

    // Append the style element to the head of the document
    //document.head.appendChild(styleElement);

    const containerStyle = document.createElement('style');
    containerStyle.textContent = `
  .container-style {
    max-width: 400px;
    margin: 50px auto;
    padding: 20px;
    border: 1px solid #ccc;
    borderRadius: 5px;
    boxShadow: 0 0 10px rgba(0, 0, 0, 0.1);
  }
`;
    document.head.appendChild(containerStyle);

    const marginBottomStyle = document.createElement('style');
    marginBottomStyle.textContent = `
    .margin-bottom {
        margin-bottom: 20px;
        }
    `;
    document.head.appendChild(marginBottomStyle);

    const labelStyle = document.createElement('style');
    labelStyle.textContent = `
    .label-style {
        display: block;
        font-weight: bold;
        margin-bottom: 5px;
    }
    `;
    document.head.appendChild(labelStyle);

    const inputStyle = document.createElement('style');
    inputStyle.textContent = `
    .input-style {
        width: 100%;
        padding: 10px;
        border-radius: 3px;
        border: 1px solid #ccc;
        box-sizing: border-box;
    }
    `;
    document.head.appendChild(inputStyle);

    const buttonStyle = document.createElement('style');
    buttonStyle.textContent = `
    .button-style {
        display: block;
        width: 100%;
        padding: 10px;
        border: none;
        border-radius: 3px;
        background-color: #007bff;
        color: #fff;
        font-size: 16px;
        cursor: pointer;
        transition: background-color 0.3s;
    }
    `;
    document.head.appendChild(buttonStyle);

    console.log('Styles appended to the document head.');
}
