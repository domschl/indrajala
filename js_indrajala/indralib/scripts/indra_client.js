"use strict";

import { IndraEvent } from './indralib.js';

let socket;
let trx = {};
var session_id = '';

export var server_state = false;
export var websocketUrl = '';

let statusLine = null;

export let currentMainElement = null;

export function removeMainElement() {
    if (currentMainElement !== null) {
        document.body.removeChild(currentMainElement);
        currentMainElement = null;
    }
}

export function changeMainElement(newMainElement) {
    removeMainElement
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

export function connection() {
    const serverHost = window.location.hostname;
    const serverPort = window.location.port;

    websocketUrl = `wss://${serverHost}:${serverPort}/ws`;
    console.log('WebSocket URL:', websocketUrl);

    socket = new WebSocket(websocketUrl);

    socket.addEventListener('open', function (event) {
        console.log('Connected to WebSocket server at', websocketUrl);
        removeStatusLine();
        server_state = true;
        enableElement(currentMainElement);
        showNotification('Connected to server at ' + websocketUrl);
    });

    socket.addEventListener('message', function (event) {
        console.log('Message from server:', event.data);
        for (const [key, value] of Object.entries(trx)) {
            if (key === JSON.parse(event.data).uuid4) {
                value.resolve(JSON.parse(event.data));
                delete trx[key];
            }
        }
    });

    socket.addEventListener('close', function (event) {
        console.log('Disconnected from WebSocket server');
        server_state = false;
        // retry connect
        disableElement(currentMainElement);
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