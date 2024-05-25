
"use strict";

import { indra_styles, color_scheme } from './../../indralib/scripts/indra_styles.js';
import {
  connection, indraLogin, indraLogout, indraKVRead, indraKVWrite, indraKVDelete
} from './../../indralib/scripts/indra_client.js';
import {
  showNotification, removeStatusLine, loginPage,
  changeMainElement, enableElement, disableElement, removeMainElement,
  showStatusLine
} from './../../indralib/scripts/indra_client_gui_lib.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
  // Code that relies on the DOM being fully loaded
  adminApp();
});

let app_data = {};

function adminApp(loggedInUser) {
  indra_styles();
  app_data = { connectionState: false, indraServerUrl: '', userList: {}, loginState: false, loggedInUser: '' };
  app_data.userList = null;
  app_data.loggedInUser = loggedInUser;
  app_data.loginState = true;
  connection((state, data) => {
    app_data.connectionState = data.connectionState;
    app_data.indraServerUrl = data.indraServerUrl;
    let loginDiv;
    switch (state) {
      case 'connecting':
        showStatusLine('Connecting to server at ' + app_data.indraServerUrl);
        app_data.userList = null;
        app_data.loginState = false;
        break;
      case 'connected':
        removeStatusLine();
        app_data
        loginDiv = loginPage(userListPage, indraPortalApp);
        changeMainElement(loginDiv);
        enableElement(loginDiv);
        showNotification('Connected to server at ' + app_data.indraServerUrl);
        break;
      case 'disconnected':
        app_data.userList = null;
        app_data.loginState = false;
        loginDiv = loginPage(userListPage, indraPortalApp);
        changeMainElement(loginDiv);
        disableElement(loginDiv);
        break;
      default:
        self.log.error("Unknown connection state: " + state);
        break;
    }
  });
}

function indraPortalApp() {
  // go to portal at /index.html
  removeMainElement();
  window.location.href = '/index.html';
}

function userEditorPage(isNew = true, currentUser = null) {
  // Create container div
  let containerDiv = document.createElement('div');
  containerDiv.classList.add('container-style')
  containerDiv.classList.add('margin-top');

  const anti_chrome_autofill = 'one-time-code'
  // Create title heading
  const titleHeading = document.createElement('h2');
  if (isNew) {
    titleHeading.textContent = 'Indrajāla User Creator';
  } else {
    titleHeading.textContent = 'Indrajāla User Editor';
  }
  titleHeading.classList.add('margin-bottom');

  // --- Username input group ---
  // Create input group for username, make it read-only if not new
  const usernameInputGroup = document.createElement('div');
  usernameInputGroup.classList.add('margin-bottom');

  // Create label for username
  const usernameLabel = document.createElement('label');
  if (isNew) {
    usernameLabel.textContent = 'New Username:';
  } else {
    usernameLabel.textContent = 'Existing Username:';
  }
  usernameLabel.setAttribute('for', 'username'); // Add 'for' attribute
  usernameLabel.classList.add('label-style');

  // Create input field for username
  const usernameInput = document.createElement('input');
  usernameInput.setAttribute('type', 'text');
  usernameInput.setAttribute('autocapitalize', 'none');
  if (isNew) {
    usernameInput.setAttribute('placeholder', 'Enter new username');
  }
  usernameInput.classList.add('input-style');
  usernameInput.id = 'username';
  usernameInput.autocomplete = anti_chrome_autofill;
  let existingUser = currentUser.username;
  if (!isNew) {
    usernameInput.readOnly = true;
    usernameInput.value = existingUser;
    // Make background color light gray
    usernameInput.style.backgroundColor = color_scheme['light']['button-disabled'];
  }

  // Append label and input to username input group
  usernameInputGroup.appendChild(usernameLabel);
  usernameInputGroup.appendChild(usernameInput);

  // --- Fullname input group ---
  // Create input group for fullname
  const fullnameInputGroup = document.createElement('div');
  fullnameInputGroup.classList.add('margin-bottom');

  // Create label for fullname
  const fullnameLabel = document.createElement('label');
  fullnameLabel.textContent = 'User\'s fullname:';
  fullnameLabel.setAttribute('for', 'user_fullname'); // Add 'for' attribute
  fullnameLabel.classList.add('label-style');

  // Create input field for fullname
  const fullnameInput = document.createElement('input');
  fullnameInput.setAttribute('type', 'text');
  fullnameInput.setAttribute('autocapitalize', 'none');
  fullnameInput.setAttribute('placeholder', 'User\'s fullname');
  fullnameInput.classList.add('input-style');
  fullnameInput.id = 'user_fullname';
  fullnameInput.autocomplete = anti_chrome_autofill;
  if (!isNew) {
    // set value to currentUser.fullname
    fullnameInput.value = currentUser.fullname;
  } else {
    fullnameInput.value = '';
  }

  // Append label and input to fullname input group
  fullnameInputGroup.appendChild(fullnameLabel);
  fullnameInputGroup.appendChild(fullnameInput);

  // --- Password1 input group ---
  // Create input group for password1
  const password1InputGroup = document.createElement('div');
  password1InputGroup.classList.add('margin-bottom');

  // Create label for password
  const password1Label = document.createElement('label');
  password1Label.textContent = 'New Password:';
  password1Label.setAttribute('for', 'password1'); // Add 'for' attribute
  password1Label.classList.add('label-style');

  // Create input field for password
  const password1Input = document.createElement('input');
  password1Input.setAttribute('type', 'password');
  password1Input.setAttribute('placeholder', 'User\'s password');
  password1Input.classList.add('input-style');
  password1Input.id = 'new_password1';
  password1Input.autocomplete = anti_chrome_autofill;
  password1Input.value = '';

  // Append label and input to password input group
  password1InputGroup.appendChild(password1Label);
  password1InputGroup.appendChild(password1Input);

  // --- Password2 input group ---
  // Create input group for password2
  const password2InputGroup = document.createElement('div');
  password2InputGroup.classList.add('margin-bottom');

  // Create label for password
  const password2Label = document.createElement('label');
  password2Label.textContent = 'New Password (rep.):';
  password2Label.setAttribute('for', 'password2'); // Add 'for' attribute
  password2Label.classList.add('label-style');

  // Create input field for password
  const password2Input = document.createElement('input');
  password2Input.setAttribute('type', 'password');
  password2Input.setAttribute('placeholder', 'User\'s password');
  password2Input.classList.add('input-style');
  password2Input.id = 'password2';
  password2Input.autocomplete = anti_chrome_autofill;
  password2Input.value = '';

  // Append label and input to password input group
  password2InputGroup.appendChild(password2Label);
  password2InputGroup.appendChild(password2Input);

  // --- Roles input group ---
  // Create input group for roles
  const rolesInputGroup = document.createElement('div');
  rolesInputGroup.classList.add('margin-bottom');

  // Create label for roles
  const rolesLabel = document.createElement('label');
  rolesLabel.textContent = 'Account roles:';
  rolesLabel.setAttribute('for', 'roles'); // Add 'for' attribute
  rolesLabel.classList.add('label-style');

  // Create input field for roles
  const rolesInput = document.createElement('input');
  rolesInput.setAttribute('type', 'text');
  rolesInput.setAttribute('autocapitalize', 'none');
  rolesInput.setAttribute('placeholder', 'Enter User\'s roles');
  rolesInput.classList.add('input-style');
  rolesInput.id = 'roles';
  rolesInput.autocomplete = anti_chrome_autofill;
  if (!isNew) {
    // set value to currentUser.roles
    rolesInput.value = currentUser.roles.join(', ');
  }

  // Append label and input to roles input group
  rolesInputGroup.appendChild(rolesLabel);
  rolesInputGroup.appendChild(rolesInput);

  // Create button line
  const buttonLine = document.createElement('div');
  buttonLine.classList.add('button-line');

  // Create Cancel button
  const cancelButton = document.createElement('button');
  cancelButton.textContent = 'Cancel';
  cancelButton.classList.add('half-button-style');

  // Create Save button
  const saveButton = document.createElement('button');
  saveButton.textContent = 'Save';
  saveButton.classList.add('half-button-style');

  // Add hover effect to buttons
  saveButton.addEventListener('mouseenter', function () {
    this.style.backgroundColor = color_scheme['light']['edit-mouse-enter'];
  });
  saveButton.addEventListener('mouseleave', function () {
    this.style.backgroundColor = color_scheme['light']['edit-mouse-leave'];
  });
  cancelButton.addEventListener('mouseenter', function () {
    this.style.backgroundColor = color_scheme['light']['edit-mouse-enter'];
  });
  cancelButton.addEventListener('mouseleave', function () {
    this.style.backgroundColor = color_scheme['light']['edit-mouse-leave'];
  });

  // Append all elements to container div
  containerDiv.appendChild(titleHeading);
  containerDiv.appendChild(usernameInputGroup);
  containerDiv.appendChild(fullnameInputGroup);
  containerDiv.appendChild(password1InputGroup);
  containerDiv.appendChild(password2InputGroup);
  containerDiv.appendChild(rolesInputGroup);
  buttonLine.appendChild(cancelButton);
  buttonLine.appendChild(saveButton);
  containerDiv.appendChild(buttonLine);

  // Append container div to body
  changeMainElement(containerDiv);
  //document.body.appendChild(containerDiv);

  // Function to handle save button click
  function handleSave() {
    const username = usernameInput.value;
    const password = passwordInput.value;

    // You can perform authentication logic here
    //console.log('Username:', username);
    //console.log('Password:', password);
    console.log('Saving...');
    //disableElement(containerDiv);
    //indraLogin(username, password, indraLoginResult);
  }

  // Add event listener to login button
  saveButton.addEventListener('click', (event) => {
    let username;
    if (isNew) {
      username = usernameInput.value;
      if (username === '') {
        showNotification('Username cannot be empty.');
        usernameInput.focus();
        return;
      }
      if (username in app_data.userList) {
        showNotification(`Username ${username} already exists.`);
        usernameInput.focus();
        return;
      }
    } else {
      username = existingUser;
    }
    let password = '';
    let password1 = password1Input.value;
    let password2 = password2Input.value;
    if (password1 != '' || password2 != '') {
      if (password1 != password2) {
        showNotification('Passwords do not match.');
        password1.value = '';
        password2.value = '';
        password1Input.focus();
        return;
      } else {
        password = password1;
      }
    }
    let fullname = fullnameInput.value;
    let roles = rolesInput.value.split(',').map(role => role.trim());
    console.log('Roles:', roles);
    let valid_roles = ['admin', 'app', 'user'];
    let valid_found = false;
    for (let role of roles) {
      if (valid_roles.includes(role)) {
        valid_found = true;
        break;
      } else {
        console.log('Invalid or user-defined role:', role);
      }
    }
    if (!valid_found) {
      showNotification('Roles must be one of admin, app, user, with other roles separated by commas.');
      rolesInput.focus();
      return;
    }
    if (isNew) {
      if (password === '') {
        showNotification('Password cannot be empty.');
        password1Input.focus();
        return;
      }
      if (roles.length === 0) {
        showNotification('Roles cannot be empty.');
        rolesInput.focus();
        return;
      }
    }

    if (isNew) {
      // write new user to KV store
      let domain_root = `entity/indrajala/user/${username}/`;
      indraKVWrite(`${domain_root}password`, password, function (result) {
        if (result.startsWith('OK')) {
          console.log(`Password for user ${username} written successfully.`);
          showNotification(`User ${username} data saved.`);
        } else {
          console.log(`Password for user ${username} write failed.`);
        }
      });
      if (fullname != '') {
        indraKVWrite(`${domain_root}fullname`, fullname, function (result) {
          if (result.startsWith('OK')) {
            console.log(`Fullname for user ${username} written successfully.`);
            showNotification(`User ${username} data saved.`);
          } else {
            console.log(`Fullname for user ${username} write failed.`);
          }
        });
      }
      let roles_str = JSON.stringify(roles);
      indraKVWrite(`${domain_root}roles`, roles_str, function (result) {
        if (result.startsWith('OK')) {
          console.log(`Roles for user ${username} written successfully.`);
          showNotification(`User ${username} data saved.`);
        } else {
          console.log(`Roles for user ${username} write failed.`);
        }
      });
    } else {
      if (password != '') {
        indraKVWrite(`entity/indrajala/user/${username}/password`, password, function (result) {
          if (result.startsWith('OK')) {
            console.log(`Password for user ${username} written successfully.`);
            showNotification(`User ${username} data saved.`);
          } else {
            console.log(`Password for user ${username} write failed.`);
          }
        });
      }
      if (fullname != currentUser.fullname) {
        if (fullname === '') {
          indraKVDelete(`entity/indrajala/user/${username}/fullname`, function (result) {
            if (result.startsWith('OK')) {
              console.log(`Fullname for user ${username} deleted successfully.`);
              showNotification(`User ${username} data saved.`);
            } else {
              console.log(`Fullname for user ${username} delete failed.`);
            }
          });
        } else {
          indraKVWrite(`entity/indrajala/user/${username}/fullname`, fullname, function (result) {
            if (result.startsWith('OK')) {
              console.log(`Fullname for user ${username} written successfully.`);
              showNotification(`User ${username} data saved.`);
            } else {
              console.log(`Fullname for user ${username} write failed.`);
            }
          });

        }
      }
      let roles_str = JSON.stringify(roles);
      if (roles_str != JSON.stringify(currentUser.roles)) {
        indraKVWrite(`entity/indrajala/user/${username}/roles`, roles_str, function (result) {
          if (result.startsWith('OK')) {
            console.log(`Roles for user ${username} written successfully.`);
            showNotification(`User ${username} data saved.`);
          } else {
            console.log(`Roles for user ${username} write failed.`);
          }
        });
      }
    }
    userListPage();
  });

  cancelButton.addEventListener('click', (event) => {
    if (isNew) {
      showNotification('User creation canceled.');
    } else {
      showNotification('User editing canceled.');
    }
    userListPage();
  });

  // Function to handle keydown event on input fields
  function handleKeyPress(event) {
    if (event.key === 'Enter') {
      // Trigger click event on the login button
      saveButton.click();
    }
  }

  // Add event listeners to input fields
  usernameInput.addEventListener('keydown', handleKeyPress);
  fullnameInput.addEventListener('keydown', handleKeyPress);
  password1Input.addEventListener('keydown', handleKeyPress);
  password2Input.addEventListener('keydown', handleKeyPress);
  rolesInput.addEventListener('keydown', handleKeyPress);

  usernameInput.focus();
  usernameInput.select();
  //setTimeout(() => {
  // Select the content of the username input field
  //  usernameInput.select();
  //}, 500);
  return containerDiv;
}


function userListPage() {
  app_data.userList = null;

  let userList;

  let selectedUser = null;
  let selectedUserData = null;

  let editButton = null;
  let deleteButton = null;

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

  function deleteUser() {
    if (selectedUser === null) {
      console.log('No user selected.');
      showNotification('No user selected.');
    } else {
      if (selectedUser === 'admin') {
        console.log('Cannot delete admin user.');
        showNotification('Cannot delete admin user.');
        return;
      }

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
            selectedUserData = null;
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

  indraKVRead('entity/indrajala/user/%', (result) => {
    // format: [['entity/indrajala/user/<username>/<attribute>', 'value'], ...]
    // convert into dictionaries of dicts {'<username>' : {'<attribute>': 'value', ...}, ...}
    app_data.userList = {};
    for (let i = 0; i < result.length; i++) {
      let parts = result[i][0].split('/');
      let username = parts[3];
      let attribute = parts[4];
      let value = result[i][1];
      if (username in app_data.userList) {
        app_data.userList[username][attribute] = value;
      } else {
        app_data.userList[username] = {};
        app_data.userList[username][attribute] = value;
      }
      if (attribute === 'roles') {
        // json string to array of strings, is string of type '["role1", "role2", ...]'
        // save-guard against JSON.parse error:
        try {
          app_data.userList[username][attribute] = JSON.parse(value);
        } catch (error) {
          console.log('Error parsing JSON: ' + value, error);
        }
      }
    }

    for (let username in app_data.userList) {
      // Create list item for user
      let userItem = document.createElement('div');
      userItem.classList.add('userListItem');
      userItem.setAttribute('data-id', username);

      // Add event listener for item selection, lambda to pass event and users list
      userItem.addEventListener('click', (event) => {
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
          selectedUserData = app_data.userList[username];
        } else {
          console.log('Deselected user:', selectedUser);
          selectedUser = null;
          selectedUserData = null;
        }

      });
      //handleUserSelection);

      // Create container for icon
      const iconContainer = document.createElement('div');
      iconContainer.classList.add('iconContainer');

      let accountIcon = 'e7fd'; // 'person' icon
      if ('roles' in app_data.userList[username]) {
        if (app_data.userList[username]['roles'].includes('admin')) {
          accountIcon = 'ef3d'; // 'admin' icon
        } else {
          if (app_data.userList[username]['roles'].includes('app')) {
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
      fullnameElement.textContent = app_data.userList[username]['fullname'];

      // Append elements to list item
      iconContainer.appendChild(iconElement);
      userItem.appendChild(iconContainer);

      // Append text elements to text container
      textContainer.appendChild(usernameElement);
      textContainer.appendChild(fullnameElement);
      userItem.appendChild(textContainer);

      userList.appendChild(userItem);
    }
    selectedUser = null;
    selectedUserData = null;

    console.log('Users:', app_data.userList);
  });
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

  function handleLogout() {
    console.log('Logging out...');
    app_data.userList = null;
    app_data.loggedInUser = '';
    app_data.loginState = false;
    selectedUser = null;
    selectedUserData = null;
    indraLogout((result) => {
      console.log('Logout result:', result);
      if (result === true) {
        console.log('Logout successful!');
        showNotification('Logout successful!');
      } else {
        console.log('Logout failed!');
        showNotification('Logout failed.');
      }
      removeMainElement();
      loginPage(userListPage, indraPortalApp);
    });
  }

  function addEditUser(isNew = true) {
    if (isNew) {
      console.log('Adding user...');
    } else {
      if (selectedUser === null) {
        console.log('No user selected.');
        showNotification('No user selected.');
        return;
      }
    }
    let currentUser = {
      'username': '',
      'fullname': '',
      'password1': '',
      'password1': '',
      'roles': []
    }
    if (!isNew) {
      currentUser = selectedUserData;
      currentUser['username'] = selectedUser;
      currentUser['password1'] = '';
      currentUser['password2'] = '';
    }
    console.log('Current user:', currentUser);
    let curDiv = userEditorPage(isNew, currentUser);
    changeMainElement(curDiv);
  }

  // Add event listeners
  addButton.addEventListener('click', () => addEditUser(true));
  editButton.addEventListener('click', () => addEditUser(false));
  deleteButton.addEventListener('click', deleteUser);

  logoutButton.addEventListener('click', handleLogout);
  // Exit button, got to main page
  exitButton.addEventListener('click', indraPortalApp);
  // Append all elements to container div
  main_div.appendChild(button_line);
  changeMainElement(main_div);
}
