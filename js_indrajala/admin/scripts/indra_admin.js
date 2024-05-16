
"use strict";
// Browser entry point for Indralib, run with:
// python -m http.server
// point browser to http://localhost:8000/

import { indra_styles, color_scheme } from './../../indralib/scripts/indra_styles.js';
import { IndraEvent } from './../../indralib/scripts/indralib.js';
import {
  connection, indraLogin, indraLogout, showNotification,
  changeMainElement, enableElement, disableElement, removeMainElement,
  indraKVRead, indraKVWrite, indraKVDelete
} from './../../indralib/scripts/indra_client.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
  // Code that relies on the DOM being fully loaded
  main();
});

let containerDiv = null;
let logoutButton;

function main() {
  // Create a new div element
  indra_styles();
  connection(indraLoginPageClose);
  loginPageOpen();
}

let passwordInput;

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

  // Create button line
  const buttonLine = document.createElement('div');
  buttonLine.classList.add('button-line');

  // Create Exit button
  const exitButton = document.createElement('button');
  exitButton.textContent = 'Exit';
  exitButton.classList.add('half-button-style');

  // Create login button
  const loginButton = document.createElement('button');
  loginButton.textContent = 'Login';
  loginButton.classList.add('half-button-style');

  // Add hover effect to login button
  loginButton.addEventListener('mouseenter', function () {
    this.style.backgroundColor = color_scheme['light']['edit-mouse-enter'];
  });
  loginButton.addEventListener('mouseleave', function () {
    this.style.backgroundColor = color_scheme['light']['edit-mouse-leave'];
  });
  exitButton.addEventListener('mouseenter', function () {
    this.style.backgroundColor = color_scheme['light']['edit-mouse-enter'];
  });
  exitButton.addEventListener('mouseleave', function () {
    this.style.backgroundColor = color_scheme['light']['edit-mouse-leave'];
  });

  // Append all elements to container div
  containerDiv.appendChild(titleHeading);
  containerDiv.appendChild(usernameInputGroup);
  containerDiv.appendChild(passwordInputGroup);
  buttonLine.appendChild(exitButton);
  buttonLine.appendChild(loginButton);
  containerDiv.appendChild(buttonLine);

  // Append container div to body
  changeMainElement(containerDiv);
  //document.body.appendChild(containerDiv);

  // Function to handle login button click
  function handleLogin() {
    const username = usernameInput.value;
    const password = passwordInput.value;

    // You can perform authentication logic here
    //console.log('Username:', username);
    //console.log('Password:', password);
    console.log('Logging in...');
    disableElement(containerDiv);
    indraLogin(username, password, indraLoginResult);
  }

  // Add event listener to login button
  loginButton.addEventListener('click', handleLogin);
  exitButton.addEventListener('click', indraPortal);

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

let userList;

function userGui() {
  // Create container div
  let usersDiv = document.createElement('div');
  usersDiv.classList.add('margin-top');
  usersDiv.classList.add('margin-bottom');

  // Create title heading
  const titleHeading = document.createElement('h2');
  titleHeading.textContent = 'Indrajāla Users';
  titleHeading.classList.add('margin-bottom');

  userList = document.createElement('ul');
  userList.classList.add('userList');

  usersDiv.appendChild(titleHeading);
  usersDiv.appendChild(userList);
  return usersDiv;
}

let selectedUser = null;

let editButton = null;
let deleteButton = null;


function addUser() {
  console.log('Adding user...');
  // Create a new user
}

function editUser() {
  if (selectedUser === null) {
    console.log('No user selected.');
    showNotification('No user selected.');
  } else {
    console.log('Editing user:', selectedUser);
    // Edit the selected user
  }
}

function deleteUser() {
  if (selectedUser === null) {
    console.log('No user selected.');
    showNotification('No user selected.');
  } else {
    console.log('Deleting user:', selectedUser);
    const confirmDelete = confirm(`Are you sure you want to delete user ${selectedUser}?`);

    // Check user response
    if (confirmDelete) {
      // User confirmed deletion, proceed with deletion action
      indraKVDelete(`entity/indrajala/user/${selectedUser}/%`, function (result) {
        if (result.startsWith('OK')) {
          console.log(`Deletion of user ${selectedUser} successful!`);
          showNotification(`User ${selectedUser} deleted successfully.`);
          // remove selectedUser from list .userListItem list
          const allItems = document.querySelectorAll('.userListItem');
          allItems.forEach(item => {
            if (item.getAttribute('data-id') === selectedUser) {
              item.remove();
            }
          });
          //const userItem = document.querySelector(`[data-id="${selectedUser}"]`);
          //if (userItem) {
          //  userItem.remove();
          //  console.log(`User item ${selectedUser} removed from list.`);
          //} else {
          //  console.log(`User item ${selectedUser} not found in list.`);
          //}
          selectedUser = null;
        } else {
          console.log(`Deletion of user ${selectedUser} failed!`);
          showNotification(`User ${selectedUser} deletion failed.`);
        }
      });
    } else {
      // User canceled deletion, do nothing
      console.log('Deletion canceled');
      showNotification(`User ${selectedUser} deletion canceled.`)
    }
  }
}

// Function to handle item selection
function handleUserSelection(event) {
  const selectedItem = event.currentTarget;

  // Check if the clicked item is already selected
  const isSelected = selectedItem.classList.contains('selected');

  // Remove 'selected' class from all items
  const allItems = document.querySelectorAll('.userListItem');
  allItems.forEach(item => item.classList.remove('selected'));

  // If the clicked item was not already selected, select it
  if (!isSelected) {
    selectedItem.classList.add('selected');
    // get username
    let username = selectedItem.querySelector('.username').textContent;
    console.log('Selected user:', username);
    selectedUser = username;
  } else {
    console.log('Deselected user:', selectedUser);
    selectedUser = null;
  }
}

function userListReadResult(result) {
  // format: [['entity/indrajala/user/<username>/<attribute>', 'value'], ...]
  // convert into dictionaries of dicts {'<username>' : {'<attribute>': 'value', ...}, ...}
  let users = {};
  for (let i = 0; i < result.length; i++) {
    let parts = result[i][0].split('/');
    let username = parts[3];
    let attribute = parts[4];
    let value = result[i][1];
    if (username in users) {
      users[username][attribute] = value;
    } else {
      users[username] = {};
      users[username][attribute] = value;
    }
    if (attribute === 'roles') {
      // json string to array of strings, is string of type '["role1", "role2", ...]'
      // save-guard against JSON.parse error:
      try {
        users[username][attribute] = JSON.parse(value);
      } catch (error) {
        console.log('Error parsing JSON: ' + value, error);
      }
    }
  }

  for (let username in users) {
    // Create list item for user
    let userItem = document.createElement('div');
    userItem.classList.add('userListItem');
    userItem.setAttribute('data-id', username);

    // Add event listener for item selection
    userItem.addEventListener('click', handleUserSelection);

    // Create container for icon
    const iconContainer = document.createElement('div');
    iconContainer.classList.add('iconContainer');

    let accountIcon = 'e7fd'; // 'person' icon
    if ('roles' in users[username]) {
      if (users[username]['roles'].includes('admin')) {
        accountIcon = 'ef3d'; // 'admin' icon
      } else {
        if (users[username]['roles'].includes('app')) {
          // cog icon
          accountIcon = 'e8b8'; // cog icon
        }
      }
    }

    const iconElement = document.createElement('i');
    // Set the HTML content to the Unicode code point
    iconElement.innerHTML = `&#x${accountIcon};`;
    iconElement.classList.add('material-icons');

    // Create container for text
    const textContainer = document.createElement('div');
    textContainer.classList.add('textContainer');

    // Create username element
    const usernameElement = document.createElement('div');
    usernameElement.classList.add('username');
    usernameElement.textContent = username;

    // Create fullname element
    const fullnameElement = document.createElement('div');
    fullnameElement.classList.add('fullname');
    fullnameElement.textContent = users[username]['fullname'];

    // Append elements to list item
    iconContainer.appendChild(iconElement);
    userItem.appendChild(iconContainer);

    // Append text elements to text container
    textContainer.appendChild(usernameElement);
    textContainer.appendChild(fullnameElement);
    userItem.appendChild(textContainer);

    userList.appendChild(userItem);
  }

  console.log('Users:', users);
}

function mainGui() {
  indraKVRead('entity/indrajala/user/%', userListReadResult);
  // Create login button
  let main_div = document.createElement('div');
  main_div.classList.add('container-style');

  let usersDiv = userGui();
  main_div.appendChild(usersDiv);

  let button_line = document.createElement('div');
  button_line.classList.add('button-line');

  let addButton = document.createElement('button');
  addButton.classList.add('icon-button-style');
  let addIcon = 'e7fe'; // 'add person' icon
  addButton.innerHTML = `&#x${addIcon};`;

  editButton = document.createElement('button');
  editButton.classList.add('icon-button-style');
  let editIcon = 'e3c9'; // 'edit' icon
  editButton.innerHTML = `&#x${editIcon};`;

  deleteButton = document.createElement('button');
  deleteButton.classList.add('icon-button-style');
  let deleteIcon = 'e872'; // 'delete' icon
  deleteButton.innerHTML = `&#x${deleteIcon};`;

  let logoutButton = document.createElement('button');
  logoutButton.classList.add('icon-button-style');
  let accountIcon = 'e9ba'; // 'logout' icon
  logoutButton.innerHTML = `&#x${accountIcon};`;

  let exitButton = document.createElement('button');
  exitButton.classList.add('icon-button-style');
  let exitIcon = 'e5cd'; // 'exit' icon
  exitButton.innerHTML = `&#x${exitIcon};`;

  let sep1 = document.createElement('div');
  sep1.classList.add('separator');
  main_div.appendChild(sep1);

  button_line.appendChild(addButton);
  button_line.appendChild(editButton);
  button_line.appendChild(deleteButton);
  button_line.appendChild(logoutButton);
  button_line.appendChild(exitButton);

  let buttons = [addButton, editButton, deleteButton, logoutButton, exitButton];
  for (let i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('mouseenter', function () {
      this.style.backgroundColor = color_scheme['light']['edit-mouse-enter'];
    });
    buttons[i].addEventListener('mouseleave', function () {
      this.style.backgroundColor = color_scheme['light']['edit-mouse-leave'];
    });
  }

  changeMainElement(main_div);
  //document.body.appendChild(logoutButton);

  // Function to handle login button click
  function handleLogout() {
    console.log('Logging out...');
    indraLogout(indraLogoutResult);
  }

  // Add event listeners
  addButton.addEventListener('click', addUser);
  editButton.addEventListener('click', editUser);
  deleteButton.addEventListener('click', deleteUser);

  logoutButton.addEventListener('click', handleLogout);
  // Exit button, got to main page
  exitButton.addEventListener('click', indraPortal);

  // Function to handle keydown event on input fields
  //function handleKeyPress(event) {
  //  if (event.key === 'Enter') {
  //    // Trigger click event on the login button
  //    logoutButton.click();
  //  }
  //}


  // Append all elements to container div
  main_div.appendChild(button_line);
}

export function indraLoginPageClose() {
  // Remove container div
  containerDiv.remove();
  containerDiv = null;
  mainGui();
}

function indraLoginResult(result) {
  console.log('Login result:', result);
  enableElement(containerDiv);
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

function indraMainGuiClose() {
  // Remove container div
  removeMainElement();
  loginPageOpen();
}

function indraPortal() {
  // go to portal at /index.html
  removeMainElement();
  window.location.href = '/index.html';
}

function indraLogoutResult(result) {
  console.log('Logout result:', result);
  if (result === true) {
    console.log('Logout successful!');
    showNotification('Logout successful!');
    indraMainGuiClose();
  } else {
    console.log('Logout failed!');
    showNotification('Logout failed.');
    indraMainGuiClose();
  }
}