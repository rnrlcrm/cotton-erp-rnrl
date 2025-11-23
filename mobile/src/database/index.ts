/**
 * Database Initialization - WatermelonDB Setup
 * 
 * Creates and configures the local-first database.
 * Handles migrations and adapter setup.
 */

import { Database } from '@nozbe/watermelondb';
import SQLiteAdapter from '@nozbe/watermelondb/adapters/sqlite';
import { schema } from './schema';
import {
  User,
  Partner,
  Trade,
  QualityReport,
  SyncQueueItem,
  Conflict,
} from './models';

// SQLite adapter configuration
const adapter = new SQLiteAdapter({
  schema,
  // Optional: increase performance with JSI
  jsi: true,
  // Optional: onSetUpError callback
  onSetUpError: (error) => {
    console.error('Database setup error:', error);
  },
});

// Initialize database with all models
export const database = new Database({
  adapter,
  modelClasses: [
    User,
    Partner,
    Trade,
    QualityReport,
    SyncQueueItem,
    Conflict,
  ],
});
