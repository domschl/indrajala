"use strict";

import { IndraEvent } from './indralib.js';

let socket;
let trx = {};
var session_id = '';

export var server_state = false;
export var websocketUrl = '';

let statusLine = null;

let subscriptions = {};

let currentMainElement = null;
let loginSessionGUI = null;
let startSessionGUI = null;
let abortSessionGUI = null;

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

export function connection(loginGUI = null, startGUI = null, abortGUI = null) {
    const serverHost = window.location.hostname;
    const serverPort = window.location.port;

    if (loginGUI !== null) {
        loginSessionGUI = loginGUI;
        startSessionGUI = startGUI;
        abortSessionGUI = abortGUI;
    }

    websocketUrl = `wss://${serverHost}:${serverPort}/ws`;
    console.log('WebSocket URL:', websocketUrl);

    socket = new WebSocket(websocketUrl);

    socket.addEventListener('open', function (event) {
        console.log('Connected to WebSocket server at', websocketUrl);
        removeStatusLine();
        server_state = true;
        if (loginSessionGUI !== null) {
            let loginDiv = loginSessionGUI(startSessionGUI, abortSessionGUI);
            changeMainElement(loginDiv);
            enableElement(currentMainElement);
        }
        showNotification('Connected to server at ' + websocketUrl);
    });

    socket.addEventListener('message', function (event) {
        let ie;
        try {
            ie = JSON.parse(event.data);
        } catch (error) {
            console.error('Error parsing received JSON ', event.data, error);
            return;
        }
        console.log('Message from server:', ie);
        for (const [key, value] of Object.entries(trx)) {
            if (key === ie.uuid4) {
                value.resolve(ie);
                delete trx[key];
                return;
            }
        }
        for (sub in subscriptions) {
            if (IndraEvent.mqcmp(ie.domain, sub)) {
                subscriptions[sub](ie);
            }
        }
    });

    socket.addEventListener('close', function (event) {
        console.log('Disconnected from WebSocket server');
        server_state = false;
        if (loginSessionGUI !== null) {
            let loginDiv = loginSessionGUI(startSessionGUI, abortSessionGUI);
            changeMainElement(loginDiv);
            disableElement(currentMainElement);
        }
        // retry connect
        showStatusLine('Reconnecting to server at ' + websocketUrl + '...', 0);
        setTimeout(connection, 1000);
    });

    socket.addEventListener('error', function (event) {
        console.error('WebSocket error:', event);
        // disconnect
        socket.close();
    });
}


function sendTransaction(ie) {
    // check if ie.domain starts with '$trx/'
    if (ie.domain.startsWith('$trx/')) {
        console.log('Sending transaction:', ie.to_json());
        // generate a future / promise:
        // return a promise that resolves when the transaction is committed
        trx[ie.uuid4] = {};
        trx[ie.uuid4].prom = new Promise((resolve, reject) => {
            trx[ie.uuid4].resolve = resolve;
            trx[ie.uuid4].reject = reject;
        }
        );
        socket.send(ie.to_json());
        return trx[ie.uuid4].prom;
    } else {
        socket.send(ie.to_json());
        return null;
    }
}

export function indraLogin(username, password, loginResult) {
    const cmd = {
        key: `entity/indrajala/user/${username}/password`,
        value: password,
    };
    let ie = new IndraEvent();
    ie.domain = "$trx/kv/req/login";
    ie.from_id = "ws/js";
    ie.data_type = "kvverify";
    ie.auth_hash = "";
    ie.data = JSON.stringify(cmd);
    let pr = sendTransaction(ie);
    if (pr === null) {
        console.log('Didn\'t get promise!');
        return false;
    }
    console.log('Sent message to server:', ie.to_json());
    // Wait for the promise to resolve
    pr.then((ie) => {
        console.log('Promise: Received response from server:', ie);
        let value = JSON.parse(ie.data);
        if (value === 'OK') {
            session_id = ie.auth_hash;
            console.log('Login successful:', value, session_id);
            loginResult(true);
        } else {
            console.log('Login failed:', value);
            loginResult(false);
        }
    },
        (error) => {
            console.log('Promise: Error:', error);
            loginResult(false);
        }
    );
}

export function indraLogout(logoutResult) {
    let ie = new IndraEvent();
    ie.domain = "$trx/kv/req/logout";
    ie.from_id = "ws/js";
    ie.auth_hash = session_id;
    ie.data_type = "";
    ie.data = "";
    let pr = sendTransaction(ie);
    if (pr === null) {
        console.log('Didn\'t get promise!');
        return false;
    }
    console.log('Sent message to server:', ie.to_json());
    // Wait for the promise to resolve
    pr.then((ie) => {
        console.log('Promise: Received response from server:', ie);
        let value = JSON.parse(ie.data);
        if (value === 'OK') {
            session_id = '';
            console.log('Logout successful:', value, session_id);
            logoutResult(true);
        } else {
            session_id = '';  // XXX?
            console.log('Logout failed:', value);
            logoutResult(false);
        }
    },
        (error) => {
            console.log('Promise: Error:', error);
            session_id = '';  // XXX?
            logoutResult(false);
        }
    );
}

export function indraKVRead(key, readResult) {
    let cmd = {
        key: key,
    };
    let ie = new IndraEvent();
    ie.domain = "$trx/kv/req/read";
    ie.from_id = "ws/js";
    ie.auth_hash = session_id;
    ie.data_type = "kvread";
    ie.data = JSON.stringify(cmd);
    let pr = sendTransaction(ie);
    if (pr === null) {
        console.log('Didn\'t get promise!');
        return null;
    }
    console.log('Sent message to server:', ie.to_json());
    // Wait for the promise to resolve
    pr.then((ie) => {
        console.log('Promise: Received response from server:', ie);
        let value = JSON.parse(ie.data);
        console.log('Value:', value);
        readResult(value);
    },
        (error) => {
            console.log('Promise: Error:', error);
            readResult(null);
        }
    );

}

export function indraKVWrite(key, value, writeResult) {
    let cmd = {
        key: key,
        value: value,
    };
    let ie = new IndraEvent();
    ie.domain = "$trx/kv/req/write";
    ie.from_id = "ws/js";
    ie.auth_hash = session_id;
    ie.data_type = "kvwrite";
    ie.data = JSON.stringify(cmd);
    let pr = sendTransaction(ie);
    if (pr === null) {
        console.log('Didn\'t get promise!');
        return null;
    }
    console.log('Sent message to server:', ie.to_json());
    // Wait for the promise to resolve
    pr.then((ie) => {
        console.log('Promise: Received response from server:', ie);
        let value = JSON.parse(ie.data);
        console.log('Value:', value);
        writeResult(value);
    },
        (error) => {
            console.log('Promise: Error:', error);
            writeResult(null);
        }
    );

}

export function indraKVDelete(key, deleteResult) {
    let cmd = {
        key: key,
    };
    let ie = new IndraEvent();
    ie.domain = "$trx/kv/req/delete";
    ie.from_id = "ws/js";
    ie.auth_hash = session_id;
    ie.data_type = "kvdelete";
    ie.data = JSON.stringify(cmd);
    let pr = sendTransaction(ie);
    if (pr === null) {
        console.log('Didn\'t get promise!');
        return null;
    }
    console.log('Sent message to server:', ie.to_json());
    // Wait for the promise to resolve
    pr.then((ie) => {
        console.log('Promise: Received response from server:', ie);
        let value = JSON.parse(ie.data);
        console.log('Value:', value);
        deleteResult(value);
    },
        (error) => {
            console.log('Promise: Error:', error);
            deleteResult(null);
        }
    );
}

export function subscribe(domain, eventHandler) {
    let ie = new IndraEvent();
    ie.domain = "$cmd/subs";
    ie.from_id = "ws/js";
    ie.auth_hash = session_id;
    ie.data_type = "vector/string";
    ie.data = JSON.stringify([domain]);
    subscriptions[domain] = eventHandler;
    socket.send(ie.to_json());
    console.log('Sent message to server:', ie.to_json());
}

export function unsubscribe(domain) {
    let ie = new IndraEvent();
    ie.domain = "$cmd/unsubs";
    ie.from_id = "ws/js";
    ie.auth_hash = session_id;
    ie.data_type = "vector/string";
    ie.data = JSON.stringify([domain]);
    delete subscriptions[domain];
    socket.send(ie.to_json());
    console.log('Sent message to server:', ie.to_json());
}


// -------- GUI Stuff
import { color_scheme } from './../../indralib/scripts/indra_styles.js';

export function loginPageOpen(appPageOpen, abortPageOpen) {
    // Create container div
    let containerDiv = document.createElement('div');
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
                indraKVRead(`entity/indrajala/user/${username}/roles`, function (result) {
                    if (result !== null) {
                        let roles = JSON.parse(result[0][1]);
                        console.log('Roles:', roles);
                        if (roles.includes('admin')) {
                            console.log('Login successful!');
                            showNotification('Login to Indrajāla successful!');
                            appPageOpen();
                        } else {
                            console.log('Login failed!');
                            showNotification('Login failed. User not authorized as role admin.');
                            passwordInput.value = '';
                            usernameInput.focus();
                            enableElement(containerDiv);
                        }
                    } else {
                        console.log('Login failed!');
                        showNotification('Login failed. User not authorized, roles not defined, admin role required.');
                        passwordInput.value = '';
                        usernameInput.focus();
                        enableElement(containerDiv);
                    }
                });
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
