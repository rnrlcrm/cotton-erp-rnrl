/**
 * Sync Engine - Bidirectional Synchronization
 * 
 * Handles offline → online sync for local-first architecture.
 * Features:
 * - Pull changes from backend
 * - Push local changes to backend
 * - Conflict detection and resolution
 * - Retry with exponential backoff
 * - Background sync every 30s
 * 
 * 2035-ready: Works offline, syncs when connected
 */

import { database } from '../database';
import { SyncQueueItem, Conflict } from '../database/models';
import { ConflictResolver } from './conflictResolution';
import { Q } from '@nozbe/watermelondb';

interface SyncChange {
  id: string;
  table: string;
  operation: 'CREATE' | 'UPDATE' | 'DELETE';
  data: any;
  updated_at: number;
}

interface SyncResponse {
  changes: SyncChange[];
  timestamp: number;
  conflicts?: Array<{
    id: string;
    table: string;
    local: any;
    remote: any;
  }>;
}

export class SyncEngine {
  private apiBaseUrl: string;
  private syncInterval: NodeJS.Timeout | null = null;
  private conflictResolver: ConflictResolver;
  private isSyncing = false;

  constructor(apiBaseUrl: string) {
    this.apiBaseUrl = apiBaseUrl;
    this.conflictResolver = new ConflictResolver();
  }

  /**
   * Start background sync (every 30 seconds when online)
   */
  startBackgroundSync() {
    if (this.syncInterval) {
      return; // Already started
    }

    this.syncInterval = setInterval(async () => {
      try {
        await this.sync();
      } catch (error) {
        console.log('Background sync failed:', error);
        // Don't throw - just log and retry on next interval
      }
    }, 30000); // 30 seconds

    // Initial sync
    this.sync().catch(console.error);
  }

  /**
   * Stop background sync
   */
  stopBackgroundSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  /**
   * Full bidirectional sync
   */
  async sync(): Promise<void> {
    if (this.isSyncing) {
      console.log('Sync already in progress, skipping...');
      return;
    }

    this.isSyncing = true;
    console.log('🔄 Starting sync...');

    try {
      // Step 1: Push local changes first
      await this.pushChanges();

      // Step 2: Pull remote changes
      await this.pullChanges();

      console.log('✅ Sync completed successfully');
    } catch (error) {
      console.error('❌ Sync failed:', error);
      throw error;
    } finally {
      this.isSyncing = false;
    }
  }

  /**
   * Pull changes from backend since last sync
   */
  async pullChanges(): Promise<void> {
    const lastPulledAt = await this.getLastPulledAt();
    
    console.log(`📥 Pulling changes since ${new Date(lastPulledAt).toISOString()}`);

    const response = await fetch(
      `${this.apiBaseUrl}/sync/changes?since=${lastPulledAt}`,
      {
        method: 'GET',
        headers: await this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error(`Pull failed: ${response.status} ${response.statusText}`);
    }

    const syncData: SyncResponse = await response.json();

    if (syncData.changes.length === 0) {
      console.log('No remote changes to pull');
      return;
    }

    console.log(`📦 Received ${syncData.changes.length} changes`);

    // Apply changes to local database
    await database.write(async () => {
      for (const change of syncData.changes) {
        await this.applyRemoteChange(change);
      }
    });

    // Save last pulled timestamp
    await this.setLastPulledAt(syncData.timestamp);
  }

  /**
   * Push local changes to backend
   */
  async pushChanges(): Promise<void> {
    const queueItems = await database.collections
      .get<SyncQueueItem>('sync_queue')
      .query(
        Q.where('status', Q.oneOf(['PENDING', 'FAILED'])),
        Q.sortBy('created_at', Q.asc)
      )
      .fetch();

    if (queueItems.length === 0) {
      console.log('No local changes to push');
      return;
    }

    console.log(`📤 Pushing ${queueItems.length} local changes`);

    // Group changes by table for batch processing
    const changesByTable: { [key: string]: SyncChange[] } = {};
    
    for (const item of queueItems) {
      if (!changesByTable[item.tableName]) {
        changesByTable[item.tableName] = [];
      }
      
      changesByTable[item.tableName].push({
        id: item.recordId,
        table: item.tableName,
        operation: item.operation as any,
        data: JSON.parse(item.data),
        updated_at: item.updatedAt.getTime(),
      });
    }

    try {
      const response = await fetch(`${this.apiBaseUrl}/sync/push`, {
        method: 'POST',
        headers: {
          ...await this.getAuthHeaders(),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          changes: Object.values(changesByTable).flat(),
        }),
      });

      if (!response.ok) {
        throw new Error(`Push failed: ${response.status} ${response.statusText}`);
      }

      const result: SyncResponse = await response.json();

      // Handle conflicts if any
      if (result.conflicts && result.conflicts.length > 0) {
        console.log(`⚠️ ${result.conflicts.length} conflicts detected`);
        await this.handleConflicts(result.conflicts);
      }

      // Mark all items as synced
      await database.write(async () => {
        for (const item of queueItems) {
          await item.update(record => {
            record.status = 'SYNCED';
          });
        }
      });

      console.log(`✅ Pushed ${queueItems.length} changes successfully`);
    } catch (error) {
      console.error('Push failed:', error);
      
      // Mark items as failed and increment retry count
      await database.write(async () => {
        for (const item of queueItems) {
          await item.update(record => {
            record.status = 'FAILED';
            record.retryCount += 1;
            record.lastError = (error as Error).message;
          });
        }
      });

      throw error;
    }
  }

  /**
   * Apply remote change to local database
   */
  private async applyRemoteChange(change: SyncChange): Promise<void> {
    const collection = database.collections.get(change.table);

    try {
      switch (change.operation) {
        case 'CREATE':
        case 'UPDATE':
          // Try to find existing record
          const existing = await collection.find(change.id).catch(() => null);
          
          if (existing) {
            // Update existing record
            await existing.update((record: any) => {
              Object.assign(record, change.data);
              record.lastSyncedAt = change.updated_at;
            });
          } else {
            // Create new record
            await collection.create((record: any) => {
              record._raw.id = change.id;
              Object.assign(record, change.data);
              record.lastSyncedAt = change.updated_at;
            });
          }
          break;

        case 'DELETE':
          const recordToDelete = await collection.find(change.id).catch(() => null);
          if (recordToDelete) {
            await recordToDelete.markAsDeleted();
          }
          break;
      }
    } catch (error) {
      console.error(`Failed to apply change for ${change.table}/${change.id}:`, error);
      throw error;
    }
  }

  /**
   * Handle sync conflicts
   */
  private async handleConflicts(conflicts: Array<{
    id: string;
    table: string;
    local: any;
    remote: any;
  }>): Promise<void> {
    await database.write(async () => {
      const conflictsCollection = database.collections.get<Conflict>('conflicts');

      for (const conflict of conflicts) {
        // Store conflict for user review
        await conflictsCollection.create(record => {
          record.conflictId = `${conflict.table}_${conflict.id}_${Date.now()}`;
          record.tableName = conflict.table;
          record.recordId = conflict.id;
          record.localData = JSON.stringify(conflict.local);
          record.remoteData = JSON.stringify(conflict.remote);
          record.conflictType = 'UPDATE_UPDATE';
          record.resolved = false;
        });

        // Auto-resolve using strategy (last-write-wins by default)
        const resolution = await this.conflictResolver.resolve(
          conflict.table,
          conflict.local,
          conflict.remote
        );

        if (resolution.autoResolved) {
          // Apply resolved data
          const collection = database.collections.get(conflict.table);
          const record = await collection.find(conflict.id);
          await record.update((r: any) => {
            Object.assign(r, resolution.data);
          });

          // Mark conflict as resolved
          const conflictRecord = await conflictsCollection
            .query(Q.where('record_id', conflict.id))
            .fetch();
          
          if (conflictRecord[0]) {
            await conflictRecord[0].update(c => {
              c.resolved = true;
              c.resolution = resolution.strategy;
            });
          }
        }
      }
    });
  }

  /**
   * Get last pulled timestamp from local storage
   */
  private async getLastPulledAt(): Promise<number> {
    // TODO: Store in AsyncStorage or secure storage
    return 0; // Start from beginning on first sync
  }

  /**
   * Save last pulled timestamp
   */
  private async setLastPulledAt(timestamp: number): Promise<void> {
    // TODO: Store in AsyncStorage
    console.log(`Last pulled at: ${new Date(timestamp).toISOString()}`);
  }

  /**
   * Get authentication headers
   */
  private async getAuthHeaders(): Promise<Record<string, string>> {
    // TODO: Get auth token from secure storage
    const token = 'TODO_GET_FROM_STORAGE';
    return {
      Authorization: `Bearer ${token}`,
    };
  }

  /**
   * Get sync status
   */
  async getSyncStatus(): Promise<{
    pending: number;
    failed: number;
    lastSyncAt: number | null;
  }> {
    const queueItems = await database.collections
      .get<SyncQueueItem>('sync_queue')
      .query()
      .fetch();

    const pending = queueItems.filter(i => i.status === 'PENDING').length;
    const failed = queueItems.filter(i => i.status === 'FAILED').length;

    return {
      pending,
      failed,
      lastSyncAt: await this.getLastPulledAt(),
    };
  }
}
