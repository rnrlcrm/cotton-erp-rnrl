/**
 * WatermelonDB Schema - Local-first Database Schema
 * 
 * Defines the offline-first database structure for mobile app.
 * Syncs with backend API when connected.
 * 
 * 2035-ready: Works 100% offline, syncs when online
 */

import { appSchema, tableSchema } from '@nozbe/watermelondb';

export const schema = appSchema({
  version: 1,
  tables: [
    // Users (cached for offline access)
    tableSchema({
      name: 'users',
      columns: [
        { name: 'user_id', type: 'string', isIndexed: true },
        { name: 'full_name', type: 'string' },
        { name: 'email', type: 'string', isOptional: true },
        { name: 'mobile_number', type: 'string', isIndexed: true },
        { name: 'role', type: 'string' },
        { name: 'partner_id', type: 'string', isOptional: true },
        { name: 'last_synced_at', type: 'number' },
        { name: 'created_at', type: 'number' },
        { name: 'updated_at', type: 'number' },
      ],
    }),

    // Partners (business partners cached locally)
    tableSchema({
      name: 'partners',
      columns: [
        { name: 'partner_id', type: 'string', isIndexed: true },
        { name: 'company_name', type: 'string', isIndexed: true },
        { name: 'partner_type', type: 'string', isIndexed: true }, // BUYER, SELLER, SUB_BROKER
        { name: 'contact_person', type: 'string' },
        { name: 'mobile', type: 'string' },
        { name: 'email', type: 'string', isOptional: true },
        { name: 'address', type: 'string', isOptional: true },
        { name: 'city', type: 'string', isOptional: true },
        { name: 'state', type: 'string', isOptional: true },
        { name: 'status', type: 'string' },
        { name: 'last_synced_at', type: 'number' },
        { name: 'created_at', type: 'number' },
        { name: 'updated_at', type: 'number' },
      ],
    }),

    // Trades (offline trade creation)
    tableSchema({
      name: 'trades',
      columns: [
        { name: 'trade_id', type: 'string', isIndexed: true },
        { name: 'trade_number', type: 'string', isIndexed: true },
        { name: 'trade_type', type: 'string', isIndexed: true }, // BUY, SELL
        { name: 'commodity', type: 'string', isIndexed: true },
        { name: 'quantity', type: 'number' },
        { name: 'unit', type: 'string' },
        { name: 'price_per_unit', type: 'number' },
        { name: 'total_amount', type: 'number' },
        { name: 'buyer_id', type: 'string', isIndexed: true },
        { name: 'seller_id', type: 'string', isIndexed: true },
        { name: 'status', type: 'string', isIndexed: true },
        { name: 'trade_date', type: 'number' },
        { name: 'delivery_date', type: 'number', isOptional: true },
        { name: 'notes', type: 'string', isOptional: true },
        { name: 'is_synced', type: 'boolean', isIndexed: true }, // Sync status
        { name: 'sync_error', type: 'string', isOptional: true },
        { name: 'last_synced_at', type: 'number', isOptional: true },
        { name: 'created_at', type: 'number' },
        { name: 'updated_at', type: 'number' },
      ],
    }),

    // Quality Reports (offline quality inspection)
    tableSchema({
      name: 'quality_reports',
      columns: [
        { name: 'report_id', type: 'string', isIndexed: true },
        { name: 'report_number', type: 'string', isIndexed: true },
        { name: 'trade_id', type: 'string', isIndexed: true },
        { name: 'commodity', type: 'string' },
        { name: 'grade', type: 'string' },
        { name: 'moisture_content', type: 'number', isOptional: true },
        { name: 'trash_content', type: 'number', isOptional: true },
        { name: 'staple_length', type: 'number', isOptional: true },
        { name: 'strength', type: 'number', isOptional: true },
        { name: 'inspector_name', type: 'string' },
        { name: 'inspection_date', type: 'number' },
        { name: 'status', type: 'string' },
        { name: 'remarks', type: 'string', isOptional: true },
        { name: 'photos', type: 'string', isOptional: true }, // JSON array of photo URLs
        { name: 'is_synced', type: 'boolean', isIndexed: true },
        { name: 'sync_error', type: 'string', isOptional: true },
        { name: 'last_synced_at', type: 'number', isOptional: true },
        { name: 'created_at', type: 'number' },
        { name: 'updated_at', type: 'number' },
      ],
    }),

    // Sync Queue (pending mutations to sync)
    tableSchema({
      name: 'sync_queue',
      columns: [
        { name: 'mutation_id', type: 'string', isIndexed: true },
        { name: 'table_name', type: 'string', isIndexed: true },
        { name: 'record_id', type: 'string', isIndexed: true },
        { name: 'operation', type: 'string' }, // CREATE, UPDATE, DELETE
        { name: 'data', type: 'string' }, // JSON stringified data
        { name: 'retry_count', type: 'number' },
        { name: 'last_error', type: 'string', isOptional: true },
        { name: 'status', type: 'string', isIndexed: true }, // PENDING, SYNCING, FAILED, SYNCED
        { name: 'created_at', type: 'number' },
        { name: 'updated_at', type: 'number' },
      ],
    }),

    // Conflicts (for manual resolution)
    tableSchema({
      name: 'conflicts',
      columns: [
        { name: 'conflict_id', type: 'string', isIndexed: true },
        { name: 'table_name', type: 'string' },
        { name: 'record_id', type: 'string' },
        { name: 'local_data', type: 'string' }, // JSON
        { name: 'remote_data', type: 'string' }, // JSON
        { name: 'conflict_type', type: 'string' }, // UPDATE_UPDATE, UPDATE_DELETE
        { name: 'resolved', type: 'boolean', isIndexed: true },
        { name: 'resolution', type: 'string', isOptional: true }, // LOCAL, REMOTE, MANUAL
        { name: 'created_at', type: 'number' },
        { name: 'updated_at', type: 'number' },
      ],
    }),
  ],
});
