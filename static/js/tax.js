// tax.js — Singapore YA2026 progressive income-tax brackets + calculator, used by
// the IRAS Tax & Wealth pane in hub.js.

// --- Singapore Progressive Tax Brackets (YA2026) ---
const TAX_BRACKETS = [
    { limit: 20000, rate: 0.00 },  // First S$20,000 (tax-free)
    { limit: 10000, rate: 0.02 },  // 20,001 to 30,000
    { limit: 10000, rate: 0.035 }, // 30,001 to 40,000
    { limit: 40000, rate: 0.07 },  // 40,001 to 80,000
    { limit: 40000, rate: 0.115 }, // 80,001 to 120,000
    { limit: 40000, rate: 0.15 },  // 120,001 to 160,000
    { limit: 40000, rate: 0.18 },  // 160,001 to 200,000
    { limit: 40000, rate: 0.19 },  // 200,001 to 240,000
    { limit: 40000, rate: 0.195 }, // 240,001 to 280,000
    { limit: 40000, rate: 0.20 },  // 280,001 to 320,000
    { limit: 180000, rate: 0.22 }, // 320,001 to 500,000
    { limit: 500000, rate: 0.23 }, // 500,001 to 1,000,000
    { limit: Infinity, rate: 0.24 } // Above 1,000,000
];

// --- Tax Calculation Helper ---
function calculateSingaporeTax(chargeableIncome) {
    if (chargeableIncome <= 20000) return 0;
    const brackets = TAX_BRACKETS;
    let tax = 0;
    let tempIncome = chargeableIncome - 20000;

    for (let i = 1; i < brackets.length; i++) {
        const b = brackets[i];
        if (tempIncome <= 0) break;
        const taxableAmount = Math.min(tempIncome, b.limit);
        tax += taxableAmount * b.rate;
        tempIncome -= taxableAmount;
    }
    return tax;
}

