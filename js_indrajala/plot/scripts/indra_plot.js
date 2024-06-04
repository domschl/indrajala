
"use strict";

import { indra_styles, color_scheme } from '../../indralib/scripts/indra_styles.js';
import {
    connection, subscribe, indraLogin, indraLogout, indraKVRead, indraKVWrite, indraKVDelete
} from '../../indralib/scripts/indra_client.js';
import {
    showNotification, removeStatusLine, loginPage,
    changeMainElement, enableElement, disableElement, removeMainElement,
    showStatusLine
} from '../../indralib/scripts/indra_client_gui_lib.js';
import './chart.umd.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
    // Code that relies on the DOM being fully loaded
    plotApp();
});

let app_data = {};

function plotApp(loggedInUser) {
    indra_styles();
    app_data = { connectionState: false, indraServerUrl: '', userList: {}, loginState: false, loggedInUser: '' };
    app_data.userList = null;
    app_data.loggedInUser = loggedInUser;
    app_data.loginState = true;
    app_data.plotData = {
    }

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
                loginDiv = loginPage(plotPage, indraPortalApp, "Indrajāla plot login", ['user']);
                changeMainElement(loginDiv);
                enableElement(loginDiv);
                showNotification('Connected to server at ' + app_data.indraServerUrl);
                break;
            case 'disconnected':
                app_data.userList = null;
                app_data.loginState = false;
                loginDiv = loginPage(userListPage, indraPortalApp, "Indrajāla plot login", ['user', 'plot']);
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


function plotPage(currentUser) {
    let plotCanvas = null;
    subscribe('$event/ml/model/train/+/+/+/record', (data) => {
        // split domain:
        let doms = data.domain.split('/');
        if (doms.length !== 8) {
            console.error(`Received invalid domain ${data.domain}`);
            return;
        }
        let model = doms[4];
        let variant = doms[5];
        let run_number = doms[6];
        let plot_desc = `${model}/${variant}/${run_number}`;
        if (!(plot_desc in app_data.plotData)) {
            app_data.plotData[plot_desc] = {
                x: [],
                y_l: [],
                y_lm: []
            };
        }
        let rec = JSON.parse(data.data);
        let xi = rec['epoch'].toFixed(6);
        let yi = rec['loss'];
        let ymi = rec['mean_loss'];
        app_data.plotData[plot_desc].x.push(xi);
        app_data.plotData[plot_desc].y_l.push(yi);
        app_data.plotData[plot_desc].y_lm.push(ymi);
        // update chart
        if (plotCanvas === null) {
            console.error('Plot canvas not found');
            return;
        }
        let chart = Chart.getChart(plotCanvas);
        chart.data.labels = app_data.plotData[plot_desc].x;
        chart.data.datasets[0].data = app_data.plotData[plot_desc].y_l;
        chart.data.datasets[1].data = app_data.plotData[plot_desc].y_lm;
        chart.update();
        console.log(`Received model train event ${data.data}`);
    });

    let mainDiv = document.createElement('div');
    mainDiv.classList.add('container-style');

    const plotDiv = document.createElement('div');
    plotDiv.classList.add('margin-top');
    plotDiv.classList.add('margin-bottom');
    mainDiv.appendChild(plotDiv);

    // Create title heading
    const titleHeading = document.createElement('h2');
    titleHeading.textContent = 'Indrajāla Plots';
    titleHeading.classList.add('margin-bottom');
    plotDiv.appendChild(titleHeading);

    const plotPane = document.createElement('div');
    plotPane.classList.add('pane');
    plotPane.classList.add('plot-pane');
    plotDiv.appendChild(plotPane);

    // add canvas
    plotCanvas = document.createElement('canvas');
    plotCanvas.classList.add('plot-canvas');
    plotPane.appendChild(plotCanvas);
    const chart = new Chart(plotCanvas, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Loss',
                data: [],
                borderWidth: 1,
                pointRadius: 0,
            }
                , {
                label: 'Mean Loss',
                data: [],
                borderWidth: 1,
                pointRadius: 0,
            }]
        },
        options: {
            responsive: true,
            animation: false,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false
                }
            }
        }
    }
    );

    let buttonLine = document.createElement('div');
    buttonLine.classList.add('button-line');

    function handleLogout() {
        console.log('Logging out...');
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
            loginPage(plotPage, indraPortalApp, "Indrajāla Plots login", ['admin']);
        });
    }

    function deletePlot() {
        for (let plot_desc in app_data.plotData) {
            app_data.plotData[plot_desc] = {
                x: [],
                y_l: [],
                y_lm: []
            };
        }
        let chart = Chart.getChart(plotCanvas);
        chart.data.labels = [];
        chart.data.datasets[0].data = [];
        chart.data.datasets[1].data = [];
        chart.update();
    }

    function editPlot() {
        console.log('Edit plot');
    }

    let buttons = [{ name: 'delete', icon: 'e872', action: deletePlot },
    { name: 'logout', icon: 'e9ba', action: handleLogout },
    { name: 'exit', icon: 'e5cd', action: indraPortalApp },
    { name: 'edit', icon: 'e3c9', action: editPlot }
    ];

    for (let i = 0; i < buttons.length; i++) {
        let button = document.createElement('button');
        button.classList.add('icon-button-style');
        button.innerHTML = `&#x${buttons[i].icon};`;
        button.addEventListener('mouseenter', function () {
            this.style.backgroundColor = color_scheme['light']['edit-mouse-enter'];
        });
        button.addEventListener('mouseleave', function () {
            this.style.backgroundColor = color_scheme['light']['edit-mouse-leave'];
        });
        button.addEventListener('click', buttons[i].action);
        buttonLine.appendChild(button);
    }

    mainDiv.appendChild(buttonLine);

    changeMainElement(mainDiv);
}




