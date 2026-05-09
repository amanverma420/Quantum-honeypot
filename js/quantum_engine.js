
/** Apply Hadamard gate to a 2-element complex state vector [[re,im],[re,im]] */
function applyH(s) {
  const k = 1 / Math.sqrt(2);
  return [
    [k * s[0][0] + k * s[1][0],  k * s[0][1] + k * s[1][1]],
    [k * s[0][0] - k * s[1][0],  k * s[0][1] - k * s[1][1]]
  ];
}

/** Apply Pauli-X (bit-flip) gate */
function applyX(s) {
  return [[...s[1]], [...s[0]]];
}

/** |⟨a|b⟩|² — probability fidelity between two pure states */
function innerProduct(a, b) {
  let re = 0, im = 0;
  for (let i = 0; i < a.length; i++) {
    re += a[i][0] * b[i][0] + a[i][1] * b[i][1];
    im += a[i][0] * b[i][1] - a[i][1] * b[i][0];
  }
  return re * re + im * im;
}

/** Computational basis |0⟩ */
const KET0 = [[1, 0], [0, 0]];

// ─── TOKEN CREATION ──────────────────────────────────────────────────────────

/**
 * Generate a fresh quantum honeypot token with N tripwire qubits.
 * Each qubit is prepared in either the '+' or '×' basis at random.
 * The basis key is held server-side and never embedded in the token.
 *
 * @param {number} n  Number of qubits
 * @returns {{ states: Array, basisKey: string[] }}
 */
function makeToken(n) {
  const states   = [];
  const basisKey = [];

  for (let i = 0; i < n; i++) {
    const basis = Math.random() < 0.5 ? '+' : 'x';
    basisKey.push(basis);

    // Start in |0⟩, apply H to get |+⟩; if '×' basis, also apply X then H
    let st = [[...KET0[0]], [...KET0[1]]];
    st = applyH(st);
    if (basis === 'x') {
      st = applyX(st);
      st = applyH(st);
    }
    states.push(st);
  }

  return { states, basisKey };
}

// ─── TOKEN MEASUREMENT ───────────────────────────────────────────────────────

/**
 * Simulate measurement of a quantum token under a given strategy.
 *
 * Strategies:
 *   'legit'  — authorised user with correct basis key
 *   'random' — random basis guess each qubit
 *   'fixed'  — always use rectilinear '+' basis
 *   'clone'  — simulate No-Cloning decoherence
 *
 * @returns {{ scores: number[], avg: number, guessKey: string[] }}
 */
function measureToken(token, strategy) {
  const { states, basisKey } = token;
  const scores   = [];
  const guessKey = [];

  for (let i = 0; i < states.length; i++) {
    let guess;
    if (strategy === 'legit')  guess = basisKey[i];
    else if (strategy === 'fixed') guess = '+';
    else guess = Math.random() < 0.5 ? '+' : 'x';

    guessKey.push(guess);

    // Decode: apply inverse of the basis transform, then H
    let st = states[i].map(r => [...r]);
    if (guess === 'x') {
      st = applyX(st);
      st = applyH(st);
    }
    st = applyH(st);

    // Fidelity with |0⟩ after decoding
    let fid = innerProduct(KET0, st);

    // Clone attacks: decoherence degrades fidelity severely (No-Cloning Theorem)
    if (strategy === 'clone') {
      fid *= (0.28 + Math.random() * 0.42);
    }

    scores.push(Math.max(0, Math.min(1, fid)));
  }

  const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
  return { scores, avg, guessKey };
}