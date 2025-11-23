/**
 * WatermelonDB Models - Reactive Local-first Models
 * 
 * Type-safe model definitions for offline-first database.
 * Uses decorators for fields and relationships.
 */

import { Model } from '@nozbe/watermelondb';
import { field, date, readonly, text } from '@nozbe/watermelondb/decorators';

export class User extends Model {
  static table = 'users';

  @text('user_id') userId!: string;
  @text('full_name') fullName!: string;
  @text('email') email?: string;
  @text('mobile_number') mobileNumber!: string;
  @text('role') role!: string;
  @text('partner_id') partnerId?: string;
  @field('last_synced_at') lastSyncedAt!: number;
  @readonly @date('created_at') createdAt!: Date;
  @readonly @date('updated_at') updatedAt!: Date;
}

export class Partner extends Model {
  static table = 'partners';

  @text('partner_id') partnerId!: string;
  @text('company_name') companyName!: string;
  @text('partner_type') partnerType!: string; // BUYER, SELLER, SUB_BROKER
  @text('contact_person') contactPerson!: string;
  @text('mobile') mobile!: string;
  @text('email') email?: string;
  @text('address') address?: string;
  @text('city') city?: string;
  @text('state') state?: string;
  @text('status') status!: string;
  @field('last_synced_at') lastSyncedAt!: number;
  @readonly @date('created_at') createdAt!: Date;
  @readonly @date('updated_at') updatedAt!: Date;
}

export class Trade extends Model {
  static table = 'trades';

  @text('trade_id') tradeId!: string;
  @text('trade_number') tradeNumber!: string;
  @text('trade_type') tradeType!: string; // BUY, SELL
  @text('commodity') commodity!: string;
  @field('quantity') quantity!: number;
  @text('unit') unit!: string;
  @field('price_per_unit') pricePerUnit!: number;
  @field('total_amount') totalAmount!: number;
  @text('buyer_id') buyerId!: string;
  @text('seller_id') sellerId!: string;
  @text('status') status!: string;
  @field('trade_date') tradeDate!: number;
  @field('delivery_date') deliveryDate?: number;
  @text('notes') notes?: string;
  @field('is_synced') isSynced!: boolean;
  @text('sync_error') syncError?: string;
  @field('last_synced_at') lastSyncedAt?: number;
  @readonly @date('created_at') createdAt!: Date;
  @readonly @date('updated_at') updatedAt!: Date;
}

export class QualityReport extends Model {
  static table = 'quality_reports';

  @text('report_id') reportId!: string;
  @text('report_number') reportNumber!: string;
  @text('trade_id') tradeId!: string;
  @text('commodity') commodity!: string;
  @text('grade') grade!: string;
  @field('moisture_content') moistureContent?: number;
  @field('trash_content') trashContent?: number;
  @field('staple_length') stapleLength?: number;
  @field('strength') strength?: number;
  @text('inspector_name') inspectorName!: string;
  @field('inspection_date') inspectionDate!: number;
  @text('status') status!: string;
  @text('remarks') remarks?: string;
  @text('photos') photos?: string; // JSON array of photo URLs
  @field('is_synced') isSynced!: boolean;
  @text('sync_error') syncError?: string;
  @field('last_synced_at') lastSyncedAt?: number;
  @readonly @date('created_at') createdAt!: Date;
  @readonly @date('updated_at') updatedAt!: Date;
}

export class SyncQueueItem extends Model {
  static table = 'sync_queue';

  @text('mutation_id') mutationId!: string;
  @text('table_name') tableName!: string;
  @text('record_id') recordId!: string;
  @text('operation') operation!: string; // CREATE, UPDATE, DELETE
  @text('data') data!: string; // JSON stringified
  @field('retry_count') retryCount!: number;
  @text('last_error') lastError?: string;
  @text('status') status!: string; // PENDING, SYNCING, FAILED, SYNCED
  @readonly @date('created_at') createdAt!: Date;
  @readonly @date('updated_at') updatedAt!: Date;
}

export class Conflict extends Model {
  static table = 'conflicts';

  @text('conflict_id') conflictId!: string;
  @text('table_name') tableName!: string;
  @text('record_id') recordId!: string;
  @text('local_data') localData!: string; // JSON
  @text('remote_data') remoteData!: string; // JSON
  @text('conflict_type') conflictType!: string; // UPDATE_UPDATE, UPDATE_DELETE
  @field('resolved') resolved!: boolean;
  @text('resolution') resolution?: string; // LOCAL, REMOTE, MANUAL
  @readonly @date('created_at') createdAt!: Date;
  @readonly @date('updated_at') updatedAt!: Date;
}
