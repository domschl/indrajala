"use strict";
// Node.js entry point for Indralib, run with:
// node scripts/browser_indralib.js

import { helloWorld } from './shared/indralib.js';

let greeting = helloWorld();
console.log(greeting);
