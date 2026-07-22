// tests/test_tax_calculator.js — calculateSingaporeTax() in static/js/tax.js
// ---------------------------------------------------------------------------
// Loads the real tax.js module into a sandboxed VM context so these tests exercise the actual
// client-side tax function instead of a reimplementation that could silently drift from it.
// (tax.js has no top-level DOM calls, but the document stub is kept as a harmless safeguard.)

const { test } = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const taxJsPath = path.join(__dirname, "..", "static", "js", "tax.js");
const src = fs.readFileSync(taxJsPath, "utf-8");

const sandbox = { document: { addEventListener: () => {} }, console };
vm.createContext(sandbox);
vm.runInContext(src, sandbox);

const { calculateSingaporeTax } = sandbox;

// Repeated floating-point rate multiplications (e.g. 40000 * 0.07) can land a cent off an
// integer (3350.0000000000005) without any bug being present — tolerate sub-cent drift rather
// than asserting exact float equality.
function assertCurrencyEqual(actual, expected, message) {
    assert.ok(Math.abs(actual - expected) < 0.01, message || `expected ~${expected}, got ${actual}`);
}

test("income at or below the S$20,000 tax-free threshold owes zero tax", () => {
    assertCurrencyEqual(calculateSingaporeTax(20000), 0);
    assertCurrencyEqual(calculateSingaporeTax(15000), 0);
});

test("S$30,000 chargeable income: 2% on the S$10,000 above S$20,000", () => {
    assertCurrencyEqual(calculateSingaporeTax(30000), 200);
});

test("S$80,000 chargeable income matches the IRAS published example of S$3,350", () => {
    assertCurrencyEqual(calculateSingaporeTax(80000), 3350);
});

test("S$120,000 chargeable income crosses into the 11.5% bracket", () => {
    assertCurrencyEqual(calculateSingaporeTax(120000), 7950);
});

test("S$1,000,000 chargeable income (top of the 23% bracket)", () => {
    assertCurrencyEqual(calculateSingaporeTax(1000000), 199150);
});

test("income above S$1,000,000 is taxed at the top 24% marginal rate on the excess", () => {
    assertCurrencyEqual(calculateSingaporeTax(1100000), 199150 + 100000 * 0.24);
});
