"use strict";

import { IndraEvent } from './indralib.js';

let socket;
let trx = {};
var session_id = '';


export function connection() {
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
        //let status = JSON.parse(JSON.parse(event.data).data);
        //console.log('Status:', status);
        // enumerate trx and search for uuid4 matching event.data.uuid4
        for (const [key, value] of Object.entries(trx)) {
            if (key === JSON.parse(event.data).uuid4) {
                value.resolve(JSON.parse(event.data));
                delete trx[key];
            }
        }
        //if (status === 'OK') {
        //    console.log('Login successful!');
        //    tempResult();
        //} else {
        //    console.log('Login failed!');
        //}
    });

    socket.addEventListener('close', function (event) {
        console.log('Disconnected from WebSocket server');
    });

    socket.addEventListener('error', function (event) {
        console.error('WebSocket error:', event);
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

export function indraLoginWait(username, password, loginResult) {
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

export function indraLogoutWait(logoutResult) {
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