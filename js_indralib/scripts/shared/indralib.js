"use strict";
// Indralib shared ES6 module

export function helloWorld() {
    if (typeof window === 'undefined') {
      console.log('Shared module is running in node');
      return 'Hello, world in Node.js';
    } else {
      console.log('Shared module is running in a browser');
      return 'Hello, world in a browser';
    }
  }
  