/**
 * state.js
 * Centralised mutable application state.
 * All modules read/write through this object.
 */

export const AppState = {
  // Quantum config
  N_QUBITS:  6,
  THRESHOLD: 0.85,

  // Active resource
  activeResource: 'db',

  // Session counters
  session: {
    legitFids:    [],
    attackFids:   [],
    fp:           0,
    totalAttacks: 0
  },

  // Logs & results
  logEntries: [],
  simResults: [],
  charts:     {},
  lastAnalyticsData: null,

  // Resource metadata lookup
  RESOURCE_META: {
    db: {
      name:        'Honeypot DB Credential',
      label:       'DB_PROD_ADMIN',
      panelTitle:  'PostgreSQL Admin Credential',
      rotatedEl:   'db-rotated',
      qlayerEl:    'db-qlayer',
      nodeId:      'node-db'
    },
    api: {
      name:        'Honeypot API Master Key',
      label:       'API_MASTER_KEY',
      panelTitle:  'API Master Key — vault/prod/api_root',
      rotatedEl:   'api-rotated',
      qlayerEl:    'api-qlayer',
      nodeId:      'node-vault'
    },
    s3: {
      name:        'Honeypot S3 Credentials',
      label:       'S3_BACKUP_BUCKET',
      panelTitle:  'S3 Backup Credentials — prod-backup-2024',
      rotatedEl:   's3-rotated',
      qlayerEl:    's3-qlayer',
      nodeId:      'node-s3'
    }
  },

  BB84_STEPS_META: [
    {
      title: "Step 1: Alice Prepares Qubits",
      desc: "Alice prepares a random sequence of classical bits. She encodes them into quantum states using randomly chosen bases (Rectilinear '+' or Diagonal 'x') and sends them over the quantum channel."
    },
    {
      title: "Step 2: Eve's Intercept (Optional)",
      desc: "If Eve (the attacker) tries to intercept the qubits, she must measure them. Since she doesn't know Alice's bases, she guesses. This measurement collapses the superposition states, introducing noise and altering the information."
    },
    {
      title: "Step 3: Bob Measures Qubits",
      desc: "Bob receives the qubits and measures them in randomly selected bases. If Eve did not interfere, Bob gets 100% accurate results whenever his basis matches Alice's. If Eve eavesdropped, Bob's results will be corrupted."
    },
    {
      title: "Step 4: Public Discussion & Sifting",
      desc: "Alice and Bob publicly disclose the bases they used for preparation and measurement. They discard all bits where their bases did not match. The remaining bits form the 'Sifted Key'."
    },
    {
      title: "Step 5: Error Reconciliation & Key Verification",
      desc: "Alice and Bob compare a small public subset of their sifted keys to estimate the error rate. If the error is 0%, the channel is secure. If the error rate is ~25%, it proves Eve was eavesdropping, alerting the honeypot system!"
    }
  ]
};