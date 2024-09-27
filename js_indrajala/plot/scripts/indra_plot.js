
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
//import { pl } from 'date-fns/locale';

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

    let plotData = null;

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
        // let plot_desc = `${model}/${variant}/${run_number}`;
        let rec = JSON.parse(data.data);
        let xi = rec['epoch'].toFixed(6);
        let yi = rec['loss'];
        let ymi = rec['mean_loss'];
        plotData.x.push(xi);
        plotData.y_l.push(yi);
        plotData.y_lm.push(ymi);

        // While plotData x and y is longer than 1000, remove first element
        while (plotData.x.length > 1000) {
            plotData.x.shift();
            plotData.y_l.shift();
            plotData.y_lm.shift();
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
        chart.data.labels = plotData.x;
        chart.data.datasets[0].data = plotData.y_l;
        chart.data.datasets[1].data = plotData.y_lm;
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
        if (mode == 1) {  // Real time single event
            domain = data.domain;
            console.log('Measurement event:', data);
            // split domain:
            let doms = domain.split('/');
            if (doms.length !== 5) {
                console.error(`Received invalid domain ${domain}`);
                return;
            }
            let meas_type = doms[2];
            let context = doms[3];
            let location = doms[4];
            let plot_desc = `${meas_type}, ${context}, ${location}`;
            let yi = JSON.parse(data.data);
            let xi = data.time_jd_start; // IndraTime.julianToDatetime(data.time_jd_start);
            plotData.x.push(xi);
            plotData.y.push(yi);
        } else {  // History event, bulk update
            for (let tup in data) {
                let jd = data[tup][0];
                let yi = data[tup][1];
                let xi = jd; // IndraTime.julianToDatetime(jd);
                plotData.x.push(xi);
                plotData.y.push(yi);
            }
        }

        // While plotData x and y is longer than 1000, remove random element
        while (plotData.x.length > 1000) {
            let idx = Math.floor(Math.random() * plotData.x.length);
            plotData.x.splice(idx, 1);
            plotData.y.splice(idx, 1);
        }
        // Sort by x, make copy of x and y
        let x = plotData.x.slice();  // copy
        let y = plotData.y.slice();  // copy
        let z = x.map((e, i) => [e, y[i]]);
        z.sort((a, b) => a[0] - b[0]);
        for (let i = 0; i < z.length; i++) {
            x[i] = z[i][0];
            y[i] = z[i][1];
        }
        // get average x distance
        if (x.length > 10) {
            let dx_s = 0;
            for (let i = 1; i < x.length; i++) {
                dx_s += x[i] - x[i - 1];
            }
            let dx_m = dx_s / (x.length - 1);
            // Insert NaNs for missing x values (dxi > 5 * dx), start reverse:
            let nan_cnt = 0;
            let i = x.length - 1;
            while (i > 0) {
                let dxi = x[i] - x[i - 1];
                if (dxi > 5 * dx_m) {
                    // Insert one for Y
                    x.splice(i, 0, x[i - 1] + dxi / 2);
                    y.splice(i, 0, NaN);
                    i--;
                    nan_cnt++;
                }
                i--;
            }
            console.log(`Inserted ${nan_cnt} NaNs`);
        }

        // Time conversion
        for (let i = 0; i < x.length; i++) {
            x[i] = IndraTime.julianToDatetime(x[i]);
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
        chart.data.labels = x;
        chart.data.datasets[0].data = y;
        chart.update();
        console.log(`Received measure event ${mode}`);
    }

    function measurementChart() {
        const skipped = (ctx, value) => ctx.p0.skip || ctx.p1.skip ? value : undefined;
        const down = (ctx, value) => ctx.p0.parsed.y > ctx.p1.parsed.y ? value : undefined;
        chart = new Chart(plotCanvas, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Measurement',
                    data: [],
                    borderWidth: 1,
                    pointRadius: 0,
                    borderColor: 'rgb(192, 75, 75)',
                    segment: {
                        borderColor: ctx => skipped(ctx, 'rgb(0,0,0,0.2)') || down(ctx, 'rgb(75, 192, 192)'),
                        borderDash: ctx => skipped(ctx, [6, 6]),
                    },
                    spanGaps: true,
                }
                ]
            },
            options: {
                responsive: true,
                animation: false,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time'
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

        // While plotData x and y is longer than 1000, remove first element
        while (plotData.x.length > 1000) {
            plotData.x.shift();
            plotData.y_l.shift();
            plotData.y_lm.shift();
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
        //{ value: 'none', name: 'Select Application', subscription: null, chart_init: null, msg_event: null },
        {
            value: 'aiMon', name: 'AI monitor', subscription: '$event/ml/model/train/+/+/+/record', chart_init: aiMonChart, msg_event: aiMonitorEvent,
            pData: {
                x: [],
                y_l: [],
                y_lm: []
            },

        },
        {
            value: 'servperf', name: 'Server performance', subscription: '$sys/stat/msgpersec', chart_init: serverPerfChart, msg_event: serverPerfEvent,
            pData: { x: [], y: [] }
        },
    ];

    const selectLine = document.createElement('div');
    selectLine.classList.add('button-line');

    const plotTypeSelect = document.createElement('select');
    plotTypeSelect.classList.add('selectBox');
    plotTypeSelect.classList.add('margin-bottom');

    function titleFromDomain(domain) {
        let doms = domain.split('/');
        if (doms.length !== 5) {
            return domain;
        }
        // uppercase first letter of each word
        let capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1);

        let meas_type = capitalize(doms[2]);
        let context = capitalize(doms[3]);
        let location = capitalize(doms[4]);
        return `${context}: ${meas_type} @${location}`;
    }

    getUniqueDomains("$event/measurement%", null, (result) => {
        for (let i = 0; i < plotTypes.length; i++) {
            let option = document.createElement('option');
            option.value = plotTypes[i].value;
            option.text = plotTypes[i].name;
            option.style.backgroundColor = color_scheme['light']['background'];  // Chrome just throws this away
            plotTypeSelect.appendChild(option);
        }
        // sort result by titleFromDomain()
        result.sort((a, b) => titleFromDomain(a).localeCompare(titleFromDomain(b)));

        for (let i = 0; i < result.length; i++) {
            let option = document.createElement('option');
            option.value = result[i];
            option.text = titleFromDomain(result[i]);
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
                    plotData = plotTypes[sel].pData;
                    curSubscription = plotTypes[sel].subscription;
                    subscribe(curSubscription, plotTypes[sel].msg_event);
                } else {
                    plotData = {
                        x: [],
                        y: []
                    };
                    curSubscription = plotTypeSelect.value;
                    getHistory(curSubscription, null, null, 1000, "Sample", (data) => { measurementEvent(data, 0, curSubscription); });
                    subscribe(curSubscription, (data) => { measurementEvent(data, 1); });
                }
            }
        });
        buttonLine.appendChild(plotTypeSelect);

        // Add select element for duration: all, 1h, 4h, 24h, 7d, 30d
        const durationSelect = document.createElement('select');
        durationSelect.classList.add('selectBox');
        durationSelect.classList.add('margin-bottom');
        let durations = ['All', '1h', '4h', '24h', '7d', '30d'];
        for (let i = 0; i < durations.length; i++) {
            let option = document.createElement('option');
            option.value = durations[i];
            option.text = durations[i];
            option.style.backgroundColor = color_scheme['light']['background'];  // Chrome just throws this away
            durationSelect.appendChild(option);
        }
        buttonLine.appendChild(durationSelect);
        plotDiv.appendChild(buttonLine);

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
        plotData = {
            x: [],
            y_l: [],
            y_lm: []
        };
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




