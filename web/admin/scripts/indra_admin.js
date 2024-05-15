
"use strict";
// Browser entry point for Indralib, run with:
// python -m http.server
// point browser to http://localhost:8000/

import { indra_styles } from './shared/indra_styles.js';
import { IndraEvent } from './shared/indralib.js';
import { connection, indraLoginWait } from './shared/indra_client.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
  // Code that relies on the DOM being fully loaded
  main();
});

let containerDiv;

function main() {
  // Create a new div element
  indra_styles();
  connection(indraLoginPageClose);
  loginPageOpen();
}

let passwordInput;

function showNotification(text) {
  const notification = document.createElement('div');
  notification.classList.add('notification');
  notification.textContent = text;
  document.body.appendChild(notification);

  // Fade in notification
  setTimeout(() => {
    notification.style.opacity = 1;
  }, 100);

  // Fade out and remove notification after 2 seconds
  setTimeout(() => {
    notification.style.opacity = 0;
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 500); // 0.5s for fade-out transition
  }, 2000);
}

function loginPageOpen() {
  // Create container div
  containerDiv = document.createElement('div');
  containerDiv.classList.add('container-style')
  containerDiv.classList.add('margin-top');

  // Create title heading
  const titleHeading = document.createElement('h2');
  titleHeading.textContent = 'Indrajāla Login';
  titleHeading.classList.add('margin-bottom');

  // Create input group for username
  const usernameInputGroup = document.createElement('div');
  usernameInputGroup.classList.add('margin-bottom');

  // Create label for username
  const usernameLabel = document.createElement('label');
  usernameLabel.textContent = 'Username:';
  usernameLabel.setAttribute('for', 'username'); // Add 'for' attribute
  usernameLabel.classList.add('label-style');

  // Create input field for username
  const usernameInput = document.createElement('input');
  usernameInput.setAttribute('type', 'text');
  usernameInput.setAttribute('autocapitalize', 'none');
  usernameInput.setAttribute('placeholder', 'Enter your username');
  usernameInput.classList.add('input-style');
  usernameInput.id = 'username';
  usernameInput.autocomplete = 'username';

  // Append label and input to username input group
  usernameInputGroup.appendChild(usernameLabel);
  usernameInputGroup.appendChild(usernameInput);

  // Create input group for password
  const passwordInputGroup = document.createElement('div');
  passwordInputGroup.classList.add('margin-bottom');

  // Create label for password
  const passwordLabel = document.createElement('label');
  passwordLabel.textContent = 'Password:';
  passwordLabel.setAttribute('for', 'password'); // Add 'for' attribute
  passwordLabel.classList.add('label-style');

  // Create input field for password
  passwordInput = document.createElement('input');
  passwordInput.setAttribute('type', 'password');
  passwordInput.setAttribute('placeholder', 'Enter your password');
  passwordInput.classList.add('input-style');
  passwordInput.id = 'password';
  passwordInput.autocomplete = 'current-password';

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
    //console.log('Username:', username);
    //console.log('Password:', password);
    console.log('Logging in...');
    indraLoginWait(username, password, indraLoginResult);
  }

  // Add event listener to login button
  loginButton.addEventListener('click', handleLogin);

  // Function to handle keydown event on input fields
  function handleKeyPress(event) {
    if (event.key === 'Enter') {
      // Trigger click event on the login button
      loginButton.click();
    }
  }

  // Add event listeners to input fields
  usernameInput.addEventListener('keydown', handleKeyPress);
  passwordInput.addEventListener('keydown', handleKeyPress);

  usernameInput.focus();
  usernameInput.select();
  //setTimeout(() => {
  // Select the content of the username input field
  //  usernameInput.select();
  //}, 500);
}

export function indraLoginPageClose() {
  // Remove container div
  containerDiv.remove();
}

function indraLoginResult(result) {
  console.log('Login result:', result);
  if (result === true) {
    console.log('Login successful!');
    showNotification('Login to Indrajāla successful!');
    indraLoginPageClose();
  } else {
    console.log('Login failed!');
    showNotification('Login failed. Please try again.');
    passwordInput.value = '';
    passwordInput.focus();
  }
}