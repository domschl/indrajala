import { color_scheme } from './../../indralib/scripts/indra_styles.js';
import { indraLogin, indraKVRead } from './../../indralib/scripts/indra_client.js';

let currentMainElement = null;
let loginSessionGUI = null;
let startSessionGUI = null;
let abortSessionGUI = null;
let statusLine = null;

export function removeMainElement() {
    if (currentMainElement !== null) {
        document.body.removeChild(currentMainElement);
        currentMainElement = null;
    }
}

export function changeMainElement(newMainElement) {
    removeMainElement();
    currentMainElement = newMainElement;
    document.body.appendChild(currentMainElement);
}

export function disableElement(element = null) {
    let curElement;
    if (element === null) {
        curElement = currentMainElement;
    } else {
        curElement = element;
    }
    if (curElement === null) {
        return;
    }
    curElement.classList.add('overlay');
}

export function enableElement(element = null) {
    let curElement;
    if (element === null) {
        curElement = currentMainElement;
    } else {
        curElement = element;
    }
    if (curElement === null) {
        return;
    }
    curElement.classList.remove('overlay');
}

export function showNotification(text) {
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

export function showStatusLine(statusText, timeout = 0) {
    removeStatusLine(); // Remove any existing status line
    statusLine = document.createElement('div');
    statusLine.classList.add('status-line');
    statusLine.textContent = statusText;
    document.body.appendChild(statusLine);
    console.log('Showing status line:', statusLine);

    // Fade in status line
    setTimeout(() => {
        statusLine.style.opacity = 1;
    }, 500);

    if (timeout > 0) {
        // Remove status line after timeout
        setTimeout(() => {
            statusLine.style.opacity = 0;
            setTimeout(() => {
                document.body.removeChild(statusLine);
                statusLine = null;
            }, 500); // 0.5s for fade-out transition
        }, timeout);
    }
}

export function removeStatusLine() {
    if (statusLine !== null) {
        console.log('Removing status line', statusLine);
        // Fade out status line
        statusLine.style.opacity = 0;
        setTimeout(() => {
            document.body.removeChild(statusLine);
            statusLine = null;
        }, 500); // 0.5s for fade-out transition
    } else {
        console.log('No status line to remove!');
    }
}

export function loginPage(appPageOpen, abortPageOpen, loginTitle = null, requiredRoles = []) {
    // Create container div
    let containerDiv = document.createElement('div');
    containerDiv.classList.add('container-style')
    containerDiv.classList.add('margin-top');

    // Create title heading
    const titleHeading = document.createElement('h2');
    if (loginTitle !== null) {
        titleHeading.textContent = loginTitle;
    } else {
        titleHeading.textContent = 'Indrajāla Login';
    }
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
    const passwordInput = document.createElement('input');
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

    // Function to handle login button click
    function handleLogin() {
        const username = usernameInput.value;
        const password = passwordInput.value;

        // You can perform authentication logic here
        //console.log('Username:', username);
        //console.log('Password:', password);
        console.log('Logging in...');
        disableElement(containerDiv);
        indraLogin(username, password, (result) => {
            //function indraLoginResult(result) {
            console.log('Login result:', result);
            //enableElement(containerDiv);
            if (result === true) {
                // check roles contain admin
                if (requiredRoles.length > 0) {
                    indraKVRead(`entity/indrajala/user/${username}/roles`, function (result) {
                        if (result !== null) {
                            let roles = JSON.parse(result[0][1]);
                            console.log('Roles:', roles);
                            let role_check = true;
                            for (let role of requiredRoles) {
                                if (roles.includes(role)) {
                                    console.log(`User has role ${role}.`);
                                } else {
                                    console.log('Login failed!');
                                    showNotification(`Login failed. User not authorized as role ${role}.`);
                                    passwordInput.value = '';
                                    usernameInput.focus();
                                    enableElement(containerDiv);
                                    role_check = false;
                                    break;
                                }
                            }
                            if (role_check) {
                                console.log('Login successful!');
                                showNotification(`Login to Indrajāla as ${username} successful!`);
                                appPageOpen(username);
                            }
                        } else {
                            console.log('Login failed!');
                            showNotification('Login failed. User not authorized, roles not defined, admin role required.');
                            passwordInput.value = '';
                            usernameInput.focus();
                            enableElement(containerDiv);
                        }
                    }
                    );
                } else {
                    console.log('Login successful!');
                    showNotification(`Login to Indrajāla as ${username} successful!`);
                    appPageOpen(username);
                }
            } else {
                console.log('Login failed!');
                showNotification('Login failed. Please try again.');
                passwordInput.value = '';
                passwordInput.focus();
                enableElement(containerDiv);
            }
        });
    }

    // Add event listener to login button
    loginButton.addEventListener('click', handleLogin);
    exitButton.addEventListener('click', abortPageOpen);

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

    changeMainElement(containerDiv);
    return containerDiv;
}
