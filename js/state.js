/**
 * state.js
 * Centralised mutable application state.
 * All modules read/write through this object.
 */

const State = {
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
      qlayerEl:    'db-qlayer'
    },
    api: {
      name:        'Honeypot API Master Key',
      label:       'API_MASTER_KEY',
      panelTitle:  'API Master Key — vault/prod/api_root',
      rotatedEl:   'api-rotated',
      qlayerEl:    'api-qlayer'
    },
    s3: {
      name:        'Honeypot S3 Credentials',
      label:       'S3_BACKUP_BUCKET',
      panelTitle:  'S3 Backup Credentials — prod-backup-2024',
      rotatedEl:   's3-rotated',
      qlayerEl:    's3-qlayer'
    }
  }
};