/**
 * Conflict Resolution - Smart Conflict Handling
 * 
 * Strategies:
 * 1. Last-write-wins (default) - Use most recent update
 * 2. Field-level merge - Merge non-conflicting fields
 * 3. Manual resolution - Store for user review
 * 
 * 2035-ready: Handles multi-device simultaneous edits
 */

export interface ConflictResolution {
  strategy: 'LOCAL' | 'REMOTE' | 'MERGED' | 'MANUAL';
  data: any;
  autoResolved: boolean;
}

export class ConflictResolver {
  /**
   * Resolve conflict between local and remote data
   */
  async resolve(
    tableName: string,
    localData: any,
    remoteData: any
  ): Promise<ConflictResolution> {
    // Strategy 1: Last-write-wins (compare timestamps)
    if (localData.updated_at && remoteData.updated_at) {
      if (localData.updated_at > remoteData.updated_at) {
        return {
          strategy: 'LOCAL',
          data: localData,
          autoResolved: true,
        };
      } else if (remoteData.updated_at > localData.updated_at) {
        return {
          strategy: 'REMOTE',
          data: remoteData,
          autoResolved: true,
        };
      }
    }

    // Strategy 2: Field-level merge
    // Try to merge non-conflicting fields
    const merged = this.mergeFields(localData, remoteData);
    
    if (merged.hasConflicts) {
      // Cannot auto-resolve - needs manual review
      return {
        strategy: 'MANUAL',
        data: remoteData, // Use remote as fallback
        autoResolved: false,
      };
    }

    return {
      strategy: 'MERGED',
      data: merged.data,
      autoResolved: true,
    };
  }

  /**
   * Merge fields intelligently
   * Returns merged data and conflict status
   */
  private mergeFields(
    local: any,
    remote: any
  ): { data: any; hasConflicts: boolean } {
    const merged = { ...remote }; // Start with remote as base
    let hasConflicts = false;

    // System fields - always take remote
    const systemFields = [
      'id',
      'created_at',
      'updated_at',
      'last_synced_at',
    ];

    // Compare each field
    for (const key of Object.keys(local)) {
      if (systemFields.includes(key)) {
        continue; // Skip system fields
      }

      // If both changed the same field to different values
      if (local[key] !== remote[key]) {
        // Check if it's a meaningful difference (not just null/undefined)
        const localHasValue = local[key] !== null && local[key] !== undefined;
        const remoteHasValue = remote[key] !== null && remote[key] !== undefined;

        if (localHasValue && remoteHasValue) {
          // Both have values but they differ - conflict!
          hasConflicts = true;
          console.log(
            `⚠️ Conflict on field "${key}": local="${local[key]}" remote="${remote[key]}"`
          );
        } else if (localHasValue && !remoteHasValue) {
          // Local has value, remote doesn't - use local
          merged[key] = local[key];
        }
        // If remote has value and local doesn't, keep remote (already in merged)
      }
    }

    return { data: merged, hasConflicts };
  }

  /**
   * Get conflict resolution suggestions for UI
   */
  getSuggestions(
    tableName: string,
    localData: any,
    remoteData: any
  ): Array<{
    field: string;
    localValue: any;
    remoteValue: any;
    suggestion: 'LOCAL' | 'REMOTE' | 'MANUAL';
    reason: string;
  }> {
    const suggestions = [];

    for (const key of Object.keys(localData)) {
      if (localData[key] !== remoteData[key]) {
        const localTimestamp = localData.updated_at || 0;
        const remoteTimestamp = remoteData.updated_at || 0;

        let suggestion: 'LOCAL' | 'REMOTE' | 'MANUAL' = 'MANUAL';
        let reason = 'Values differ, manual review recommended';

        // Suggest based on timestamp
        if (localTimestamp > remoteTimestamp) {
          suggestion = 'LOCAL';
          reason = 'Local version is newer';
        } else if (remoteTimestamp > localTimestamp) {
          suggestion = 'REMOTE';
          reason = 'Remote version is newer';
        }

        suggestions.push({
          field: key,
          localValue: localData[key],
          remoteValue: remoteData[key],
          suggestion,
          reason,
        });
      }
    }

    return suggestions;
  }
}
