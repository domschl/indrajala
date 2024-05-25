
"use strict";

import { indra_styles, color_scheme } from '../../indralib/scripts/indra_styles.js';
import {
    connection, indraLogin, indraLogout, indraKVRead, indraKVWrite, indraKVDelete
} from '../../indralib/scripts/indra_client.js';
import {
    showNotification, removeStatusLine, loginPage,
    changeMainElement, enableElement, disableElement, removeMainElement,
    showStatusLine
} from '../../indralib/scripts/indra_client_gui_lib.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
    // Code that relies on the DOM being fully loaded
    chatApp();
});

let app_data = {};

function chatApp(loggedInUser) {
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
                loginDiv = loginPage(chatPage, indraPortalApp);
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


function chatPage(currentUser) {
    const chatDiv = document.createElement('div');
    chatDiv.classList.add('pane-container');
    // create left and right pane separated by a movable splitter:
    const leftPane = document.createElement('div');
    leftPane.classList.add('pane');
    const rightPane = document.createElement('div');
    rightPane.classList.add('pane');
    const splitter = document.createElement('div');
    splitter.classList.add('splitter');

    // Add test-label to each pane:
    leftPane.textContent = 'User List';
    rightPane.textContent = 'Chat Window';

    // add to chatDiv
    chatDiv.appendChild(leftPane);
    chatDiv.appendChild(splitter);
    chatDiv.appendChild(rightPane);

    let isDragging = false;

    splitter.addEventListener('mousedown', function (e) {
        isDragging = true;
    });

    chatDiv.addEventListener('mousemove', function (e) {
        if (!isDragging) {
            return;
        }

        e.preventDefault();

        let x = e.pageX;
        leftPane.style.width = x + 'px';
        rightPane.style.width = (window.innerWidth - x - 10) + 'px';
    });

    document.addEventListener('mouseup', function (e) {
        isDragging = false;
    });
    changeMainElement(chatDiv);
}

function nonsense() {
    let startX = 0;
    let startWidth = 0;
    let leftWidth = 0;
    let rightWidth = 0;
    let dragging = false;
    splitter.addEventListener('mousedown', (e) => {
        startX = e.clientX;
        startWidth = leftPane.offsetWidth;
        dragging = true;
    });
    document.addEventListener('mousemove', (e) => {
        if (dragging) {
            leftWidth = startWidth + e.clientX - startX;
            rightWidth = chatDiv.offsetWidth - leftWidth;
            leftPane.style.width = leftWidth + 'px';
            rightPane.style.width = rightWidth + 'px';
        }
    });
    document.addEventListener('mouseup', () => {
        dragging = false;
    });
    chatDiv.appendChild(leftPane);
    chatDiv.appendChild(splitter);
    chatDiv.appendChild(rightPane);
    // create user list in left pane:
    const userListDiv = document.createElement('div');
    userListDiv.classList.add('user-list-div');
    leftPane.appendChild(userListDiv);
    const userList = document.createElement('ul');
    userList.classList.add('user-list');
    userListDiv.appendChild(userList);
    // create chat window in right pane:
    const chatWindowDiv = document.createElement('div');
    chatWindowDiv.classList.add('chat-window-div');
    rightPane.appendChild(chatWindowDiv);
    const chatWindow = document.createElement('ul');
    chatWindow.classList.add('chat-window');
    chatWindowDiv.appendChild(chatWindow);
    // create chat input in right pane:
    const chatInputDiv = document.createElement('div');
    chatInputDiv.classList.add('chat-input-div');
    rightPane.appendChild(chatInputDiv);
    const chatInput = document.createElement('input');
    chatInput.classList.add('chat-input');
    chatInputDiv.appendChild(chatInput);
    const chatButton = document.createElement('button');
    chatButton.classList.add('chat-button');
    chatButton.textContent = 'Send';
    chatInputDiv.appendChild(chatButton);
    // add event listeners:
    chatButton.addEventListener('click', () => {
        if (chatInput.value) {
            // send chat message
            const message = { from: currentUser, to: 'all', text: chatInput.value };
            // send message to server
            chatInput.value = '';
        }
    });
    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            chatButton.click();
        }
    });
    // update user list:
    const updateUserList = (userList) => {
        userList.innerHTML = '';
        for (const user in userList) {
            const userItem = document.createElement('li');
            userItem.textContent = user;
            userList.appendChild(userItem);
            userItem.addEventListener('click', () => {
                chatInput.value = '@' + user + ' ';
                chatInput.focus();
            });
        }
    };

}
