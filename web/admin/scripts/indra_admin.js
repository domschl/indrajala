
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
  //const newDiv = document.createElement('div');

  // Set attributes (optional)
  indra_custom_styles();
  //newDiv.id = 'myDiv';
  //newDiv.classList.add('custom-class');

  // Set inner text or HTML content (optional)
  //newDiv.textContent = helloWorld();

  // Append the new div element to an existing element in the DOM
  //document.body.appendChild(newDiv);
  login();
}

function login() {
  // Create container div
  const containerDiv = document.createElement('div');
  containerDiv.classList.add('container-style');

  // Create title heading
  const titleHeading = document.createElement('h2');
  titleHeading.textContent = 'Login';
  titleHeading.classList.add('margin-bottom');

  // Create input group for username
  const usernameInputGroup = document.createElement('div');
  usernameInputGroup.classList.add('margin-bottom');

  // Create label for username
  const usernameLabel = document.createElement('label');
  usernameLabel.textContent = 'Username:';
  usernameLabel.classList.add('label-style');

  // Create input field for username
  const usernameInput = document.createElement('input');
  usernameInput.setAttribute('type', 'text');
  usernameInput.setAttribute('placeholder', 'Enter your username');
  usernameInput.classList.add('input-style');

  // Append label and input to username input group
  usernameInputGroup.appendChild(usernameLabel);
  usernameInputGroup.appendChild(usernameInput);

  // Create input group for password
  const passwordInputGroup = document.createElement('div');
  passwordInputGroup.classList.add('margin-bottom');

  // Create label for password
  const passwordLabel = document.createElement('label');
  passwordLabel.textContent = 'Password:';
  passwordLabel.classList.add('label-style');

  // Create input field for password
  const passwordInput = document.createElement('input');
  passwordInput.setAttribute('type', 'password');
  passwordInput.setAttribute('placeholder', 'Enter your password');
  passwordInput.classList.add('input-style');

  // Append label and input to password input group
  passwordInputGroup.appendChild(passwordLabel);
  passwordInputGroup.appendChild(passwordInput);

  // Create login button
  const loginButton = document.createElement('button');
  loginButton.textContent = 'Login';
  loginButton.classList.add('button-style');

  // Add hover effect to login button
  loginButton.addEventListener('mouseenter', function () {
    this.style.backgroundColor = '#0056b3';
  });
  loginButton.addEventListener('mouseleave', function () {
    this.style.backgroundColor = '#007bff';
  });

  // Append all elements to container div
  containerDiv.appendChild(titleHeading);
  containerDiv.appendChild(usernameInputGroup);
  containerDiv.appendChild(passwordInputGroup);
  containerDiv.appendChild(loginButton);

  // Append container div to body
  document.body.appendChild(containerDiv);

  // Function to handle login button click
  function handleLogin() {
    const username = usernameInput.value;
    const password = passwordInput.value;

    // You can perform authentication logic here
    console.log('Username:', username);
    console.log('Password:', password);

    // For demonstration purposes, just alert that login is successful
    alert('Login successful!');
  }

  // Add event listener to login button
  loginButton.addEventListener('click', handleLogin);
}