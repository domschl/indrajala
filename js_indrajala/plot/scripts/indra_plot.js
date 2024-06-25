
"use strict";

import { indra_styles, color_scheme } from '../../indralib/scripts/indra_styles.js';
import {
    connection, subscribe, unsubscribe, indraLogin, indraLogout,
    indraKVRead, indraKVWrite, indraKVDelete,
    getUniqueDomains, getHistory
} from '../../indralib/scripts/indra_client.js';
import {
    showNotification, removeStatusLine, loginPage,
    changeMainElement, enableElement, disableElement, removeMainElement,
    showStatusLine
} from '../../indralib/scripts/indra_client_gui_lib.js';
import { IndraTime } from '../../indralib/scripts/indra_time.js';
//import './chart.umd.js';
import "./node_modules/chart.js/dist/chart.umd.js";
//import "./node_modules/moment/dist/moment.js";
import './node_modules/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.bundle.js';

// Wait for DOMContentLoaded event (frickel, frickel)
document.addEventListener('DOMContentLoaded', function () {
    // Code that relies on the DOM being fully loaded
    plotApp();
});

let app_data = {};

function plotApp(loggedInUser) {
    indra_styles();
    app_data = { connectionState: false, indraServerUrl: '', loginState: false, loggedInUser: '' };
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
                loginDiv = loginPage(plotPage, indraPortalApp, "Indrajāla plot login", ['user', 'plot']);
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
    let plotApp = null;

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

    let chart = null;
    let curSubscription = null;

    function aiMonitorEvent(data) {
        console.log('AI Monitor event:', data);
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
        if (chart === null) {
            console.error('Chart not found');
            return;
        }
        //let chart = Chart.getChart(plotCanvas);
        chart.data.labels = app_data.plotData[plot_desc].x;
        chart.data.datasets[0].data = app_data.plotData[plot_desc].y_l;
        chart.data.datasets[1].data = app_data.plotData[plot_desc].y_lm;
        chart.update();
        console.log(`Received model train event ${data.data}`);
    }

    function aiMonChart() {
        chart = new Chart(plotCanvas, {
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
    }

    function measurementEvent(data, mode, domain = null) {
        if (mode == 1) {
            domain = data.domain;
            console.log('Measurement event:', data);
            // split domain:
            let doms = data.domain.split('/');
            if (doms.length !== 5) {
                console.error(`Received invalid domain ${data.domain}`);
                return;
            }
            let meas_type = doms[2];
            let context = doms[3];
            let location = doms[4];
            let plot_desc = `${meas_type}, ${context}, ${location}`;
            if (!(domain in app_data.plotData)) {
                app_data.plotData[domain] = {
                    x: [],
                    y: [],
                };
            }
            let yi = JSON.parse(data.data);
            let xi = IndraTime.julianToDatetime(data.time_jd_start);
            app_data.plotData[domain].x.push(xi);
            app_data.plotData[domain].y.push(yi);
        } else {
            console.log('getHistory Measurement event:', data);
            if (!(domain in app_data.plotData)) {
                app_data.plotData[domain] = {
                    x: [],
                    y: [],
                };
            }
            for (let tup in data) {
                let jd = data[tup][0];
                let yi = data[tup][1];
                let xi = IndraTime.julianToDatetime(jd);
                console.log(`Measurement event: ${tup}, ${jd}, ${xi}, ${yi}`);
                app_data.plotData[domain].x.push(xi);
                app_data.plotData[domain].y.push(yi);
            }
        }

        // While plotData x and y is longer than 1000, remove random element
        for (let domain in app_data.plotData) {
            while (app_data.plotData[domain].x.length > 1000) {
                let idx = Math.floor(Math.random() * app_data.plotData[domain].x.length);
                app_data.plotData[domain].x.splice(idx, 1);
                app_data.plotData[domain].y.splice(idx, 1);
            }
        }
        // update chart
        if (plotCanvas === null) {
            console.error('Plot canvas not found');
            return;
        }
        if (chart === null) {
            console.error('Chart not found');
            return;
        }
        //let chart = Chart.getChart(plotCanvas);
        chart.data.labels = app_data.plotData[domain].x;
        chart.data.datasets[0].data = app_data.plotData[domain].y;
        chart.update();
        console.log(`Received model train event ${data.data}`);
    }

    function measurementChart() {
        chart = new Chart(plotCanvas, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Measurement',
                    data: [],
                    borderWidth: 1,
                    pointRadius: 0,
                }
                ]
            },
            options: {
                responsive: true,
                animation: false,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'second'
                        }
                    },
                    y: {
                        beginAtZero: false
                    }
                }
            }
        }
        );
    }

    function serverPerfEvent(data) {
        console.log('Server performance event:', data);
        let msgpersec = JSON.parse(data.data);
        let jd_time = data.time_jd_start;
        console.log(data);
        let dt = IndraTime.julianToDatetime(jd_time);
        console.log(`Server performance event time: ${dt}, ${jd_time}`);
        // hh:mm:ss, make sure to include leading zeros
        let h = dt.getHours(); let m = dt.getMinutes(); let s = dt.getSeconds();
        if (h < 10) { h = '0' + h; }
        if (m < 10) { m = '0' + m; }
        if (s < 10) { s = '0' + s; }
        let time_str = `${h}:${m}:${s}`;
        let x = time_str;
        let y = msgpersec;
        let plotDesc = '$sys/stat/msgpersec';
        if (!(plotDesc in app_data.plotData)) {
            app_data.plotData[plotDesc] = {
                x: [],
                y: []
            };
        }
        app_data.plotData[plotDesc].x.push(x);
        app_data.plotData[plotDesc].y.push(y);
        // update chart
        if (plotCanvas === null) {
            console.error('Plot canvas not found');
            return;
        }
        if (chart === null) {
            console.error('Chart not found');
            return;
        }
        //let chart = Chart.getChart(plotCanvas);
        chart.data.labels = app_data.plotData[plotDesc].x;
        chart.data.datasets[0].data = app_data.plotData[plotDesc].y;
        chart.update();
        console.log(`Received server performance event ${data.data}`);
    }

    function serverPerfChart() {
        chart = new Chart(plotCanvas, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Messages per second',
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
    }

    let plotTypes = [
        { value: 'none', name: 'Select Application', subscription: null, chart_init: null, msg_event: null },
        {
            value: 'aiMon', name: 'AI monitor', subscription: '$event/ml/model/train/+/+/+/record', chart_init: aiMonChart, msg_event: aiMonitorEvent
        },
        { value: 'servperf', name: 'Server performance', subscription: '$sys/stat/msgpersec', chart_init: serverPerfChart, msg_event: serverPerfEvent },
        { value: 'sensordata', name: 'Sensor data', subscription: null, chart_init: null, msg_event: null },];

    const plotTypeSelect = document.createElement('select');
    plotTypeSelect.classList.add('selectBox');
    plotTypeSelect.classList.add('margin-bottom');

    getUniqueDomains("$event/measurement%", "%", (result) => {
        for (let i = 0; i < plotTypes.length; i++) {
            let option = document.createElement('option');
            option.value = plotTypes[i].value;
            option.text = plotTypes[i].name;
            option.style.backgroundColor = color_scheme['light']['background'];  // Chrome just throws this away
            plotTypeSelect.appendChild(option);
        }
        for (let i = 0; i < result.length; i++) {
            let option = document.createElement('option');
            option.value = result[i];
            option.text = result[i];
            option.style.backgroundColor = color_scheme['light']['background'];  // Chrome just throws this away
            plotTypeSelect.appendChild(option);
        }
        plotTypeSelect.addEventListener('change', function () {
            console.log('Selected plot type:', plotTypeSelect.value);
            let sel = plotTypeSelect.selectedIndex;
            if (curSubscription !== null) {
                unsubscribe(curSubscription);
            }
            if (chart !== null) {
                chart.destroy();
                chart = null;
            }
            if (sel < plotTypes.length && plotTypes[sel].chart_init !== null) {
                plotTypes[sel].chart_init();
            } else {
                measurementChart();
            }
            if (sel > 0) {
                if (sel < plotTypes.length) {
                    curSubscription = plotTypes[sel].subscription;
                    subscribe(curSubscription, plotTypes[sel].msg_event);
                } else {
                    curSubscription = plotTypeSelect.value;
                    getHistory(curSubscription, null, null, 1000, "Sample", (data) => { measurementEvent(data, 0, curSubscription); });
                    subscribe(curSubscription, (data) => { measurementEvent(data, 1); });
                }
            }
        });
        plotDiv.appendChild(plotTypeSelect);

        const plotPane = document.createElement('div');
        plotPane.classList.add('pane');
        plotPane.classList.add('plot-pane');
        plotDiv.appendChild(plotPane);

        // add canvas
        plotCanvas = document.createElement('canvas');
        plotCanvas.classList.add('plot-canvas');
        plotPane.appendChild(plotCanvas);

        let buttonLine = document.createElement('div');
        buttonLine.classList.add('button-line');
        let buttons = [
            { name: 'edit', icon: 'e3c9', action: editPlot },
            { name: 'delete', icon: 'e872', action: deletePlot },
            { name: 'logout', icon: 'e9ba', action: handleLogout },
            { name: 'exit', icon: 'e5cd', action: indraPortalApp },
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
    });

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
            loginPage(plotPage, indraPortalApp, "Indrajāla Plots login", ['app']);
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


}




