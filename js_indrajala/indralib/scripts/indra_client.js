"use strict";

import { IndraEvent } from './indralib.js';

var socket = null;
let trx = {};
var session_id = '';

export var server_state = false;
export var websocketUrl = '';

let subscriptions = {};


export function connection(connectionEvent = null) {
    const serverHost = window.location.hostname;
    const serverPort = window.location.port;

    websocketUrl = `wss://${serverHost}:${serverPort}/ws`;
    console.log('WebSocket URL:', websocketUrl);

    socket = new WebSocket(websocketUrl);
    if (connectionEvent !== null) {
        connectionEvent("connecting", { connectionState: false, indraServerUrl: websocketUrl });
    }

    socket.addEventListener('open', function (event) {
        console.log('Connected to WebSocket server at', websocketUrl);
        if (connectionEvent !== null) {
            connectionEvent("connected", { connectionState: true, indraServerUrl: websocketUrl });
        }
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
        for (let sub in subscriptions) {
            if (IndraEvent.mqcmp(ie.domain, sub)) {
                subscriptions[sub](ie);
            }
        }
    });

    socket.addEventListener('error', function (event) {
        console.error('WebSocket error:', event);
        // disconnect
        socket.close();
    });

    socket.addEventListener('close', function (event) {
        console.log('Disconnected from WebSocket server');
        server_state = false;
        if (connectionEvent !== null) {
            connectionEvent("disconnected", { connectionState: false, indraServerUrl: websocketUrl });
        }
        setTimeout(() => connection(connectionEvent), 1000);
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

export function getUserSessionList(listHandler) {
    let ie = new IndraEvent();
    ie.domain = "$trx/cs/session";
    ie.from_id = "ws/js";
    ie.auth_hash = session_id;
    ie.data_type = "list_request";
    cmd = {
        cmd: "list_user_sessions",
    }
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
        listHandler(value);
    },
        (error) => {
            console.log('Promise: Error:', error);
            listHandler(null);
        }
    );
}
