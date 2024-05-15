
"use strict";
// Browser entry point for Indralib, run with:
// python -m http.server
// point browser to http://localhost:8000/

import { IndraEvent, uuidv4 } from './shared/indralib.js';
import { indra_styles } from './shared/indra_styles.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
  // Code that relies on the DOM being fully loaded
  main();
});

let containerDiv;

function main() {
  // Create a new div element
  indra_styles();
  connection();
  login();
}

let socket;

function connection() {
  const serverHost = window.location.hostname;
  const serverPort = window.location.port;

  const websocketUrl = `wss://${serverHost}:${serverPort}/ws`;
  console.log('WebSocket URL:', websocketUrl);

  socket = new WebSocket(websocketUrl);

  socket.addEventListener('open', function (event) {
    console.log('Connected to WebSocket server');
  });

  socket.addEventListener('message', function (event) {
    console.log('Message from server:', event.data);
    // convert event.data from JSON-string to object
    let status = JSON.parse(JSON.parse(event.data).data);
    console.log('Status:', status);
    if (status === 'OK') {
      console.log('Login successful!');
      if (containerDiv) {
        containerDiv.remove();
      }
    } else {
      console.log('Login failed!');
    }
  });

  socket.addEventListener('close', function (event) {
    console.log('Disconnected from WebSocket server');
  });

  socket.addEventListener('error', function (event) {
    console.error('WebSocket error:', event);
  });
}

function login() {
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
  const passwordInput = document.createElement('input');
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

    const cmd = {
      key: `entity/indrajala/user/${username}/password`,
      value: password,
    };

    // For demonstration purposes, just alert that login is successful
    //alert('Login successful!');
    let ie = new IndraEvent();
    ie.domain = "$trx/kv/req/login";
    ie.form_id = "ws/js";
    ie.data_type = "kvverify";
    ie.auth_hash = "";
    ie.data = JSON.stringify(cmd);
    socket.send(ie.to_json());
    console.log('Sent message to server:', ie.to_json());
    //return containerDiv;
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
  //setTimeout(() => {
  // Select the content of the username input field
  //  usernameInput.select();
  //}, 500);

}