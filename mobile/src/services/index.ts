/**
 * Sync Service Initialization
 * 
 * Initialize and configure the offline-first sync system.
 * Call this once when app starts.
 */

import { SyncEngine } from './sync/engine';
import { MutationQueue } from './sync/queue';

let syncEngine: SyncEngine | null = null;
let mutationQueue: MutationQueue | null = null;

/**
 * Initialize sync service
 * Call this in App.tsx on startup
 */
export async function initializeSync(apiBaseUrl: string): Promise<void> {
  console.log('🔄 Initializing sync service...');

  // Create sync engine
  syncEngine = new SyncEngine(apiBaseUrl);

  // Create mutation queue
  mutationQueue = new MutationQueue();

  // Start background sync (every 30s when online)
  syncEngine.startBackgroundSync();

  // Clean up old synced items (older than 7 days)
  await mutationQueue.cleanup(7);

  console.log('✅ Sync service initialized');
}

/**
 * Stop sync service
 * Call this when app is closing
 */
export function stopSync(): void {
  if (syncEngine) {
    syncEngine.stopBackgroundSync();
    syncEngine = null;
  }
  mutationQueue = null;

  console.log('🛑 Sync service stopped');
}

/**
 * Get sync engine instance
 */
export function getSyncEngine(): SyncEngine {
  if (!syncEngine) {
    throw new Error('Sync engine not initialized. Call initializeSync() first.');
  }
  return syncEngine;
}

/**
 * Get mutation queue instance
 */
export function getMutationQueue(): MutationQueue {
  if (!mutationQueue) {
    throw new Error('Mutation queue not initialized. Call initializeSync() first.');
  }
  return mutationQueue;
}

/**
 * Force sync now (manual trigger)
 */
export async function forceSyncNow(): Promise<void> {
  const engine = getSyncEngine();
  await engine.sync();
}

/**
 * Get sync status
 */
export async function getSyncStatus(): Promise<{
  pending: number;
  failed: number;
  lastSyncAt: number | null;
}> {
  const engine = getSyncEngine();
  return await engine.getSyncStatus();
}
