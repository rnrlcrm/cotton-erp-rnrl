/**
 * Trade Creation - Optimistic UI Example
 * 
 * Demonstrates offline-first pattern:
 * 1. Create trade locally (instant feedback)
 * 2. Queue for sync
 * 3. Sync when online
 * 4. Handle conflicts if needed
 * 
 * 2035-ready: Zero perceived latency, works offline
 */

import React, { useState } from 'react';
import { View, Text, TextInput, Button, Alert } from 'react-native';
import { database } from '../../database';
import { Trade } from '../../database/models';
import { MutationQueue } from '../../services/sync/queue';
import withObservables from '@nozbe/with-observables';

const mutationQueue = new MutationQueue();

export const TradeCreationScreen: React.FC = () => {
  const [commodity, setCommodity] = useState('');
  const [quantity, setQuantity] = useState('');
  const [price, setPrice] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const handleCreateTrade = async () => {
    setIsCreating(true);

    try {
      const tradeId = `trade_${Date.now()}`;
      const now = Date.now();

      const tradeData = {
        trade_id: tradeId,
        trade_number: `T-${now}`,
        trade_type: 'BUY',
        commodity,
        quantity: parseFloat(quantity),
        unit: 'QUINTALS',
        price_per_unit: parseFloat(price),
        total_amount: parseFloat(quantity) * parseFloat(price),
        buyer_id: 'current_user_partner_id', // TODO: Get from auth
        seller_id: 'selected_seller_id', // TODO: Get from form
        status: 'DRAFT',
        trade_date: now,
        is_synced: false,
      };

      // Step 1: Create locally (optimistic - instant UI update)
      await database.write(async () => {
        await database.collections.get<Trade>('trades').create(trade => {
          trade._raw.id = tradeId;
          Object.assign(trade, tradeData);
        });
      });

      // Step 2: Queue for sync
      await mutationQueue.enqueue('trades', tradeId, 'CREATE', tradeData);

      // User sees success immediately (even if offline!)
      Alert.alert('Success', 'Trade created successfully!');
      
      // Clear form
      setCommodity('');
      setQuantity('');
      setPrice('');
    } catch (error) {
      Alert.alert('Error', 'Failed to create trade');
      console.error(error);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <View style={{ padding: 20 }}>
      <Text style={{ fontSize: 24, marginBottom: 20 }}>Create Trade</Text>

      <TextInput
        placeholder="Commodity (e.g., Cotton)"
        value={commodity}
        onChangeText={setCommodity}
        style={styles.input}
      />

      <TextInput
        placeholder="Quantity (Quintals)"
        value={quantity}
        onChangeText={setQuantity}
        keyboardType="numeric"
        style={styles.input}
      />

      <TextInput
        placeholder="Price per Quintal"
        value={price}
        onChangeText={setPrice}
        keyboardType="numeric"
        style={styles.input}
      />

      <Button
        title={isCreating ? 'Creating...' : 'Create Trade'}
        onPress={handleCreateTrade}
        disabled={isCreating || !commodity || !quantity || !price}
      />

      <SyncStatusIndicator />
    </View>
  );
};

/**
 * Sync Status Indicator
 * Shows pending sync count and last sync time
 */
const SyncStatusIndicatorBase: React.FC<{ pending: number }> = ({ pending }) => {
  if (pending === 0) {
    return (
      <View style={styles.syncStatus}>
        <Text style={{ color: 'green' }}>✅ All synced</Text>
      </View>
    );
  }

  return (
    <View style={styles.syncStatus}>
      <Text style={{ color: 'orange' }}>
        ⏳ {pending} changes pending sync
      </Text>
    </View>
  );
};

// Make it reactive - automatically updates when queue changes
const SyncStatusIndicator = withObservables([], () => ({
  pending: database.collections
    .get('sync_queue')
    .query(Q.where('status', 'PENDING'))
    .observeCount(),
}))(SyncStatusIndicatorBase);

const styles = {
  input: {
    borderWidth: 1,
    borderColor: '#ccc',
    padding: 10,
    marginBottom: 10,
    borderRadius: 5,
  },
  syncStatus: {
    marginTop: 20,
    padding: 10,
    backgroundColor: '#f0f0f0',
    borderRadius: 5,
  },
};

// Missing import
import { Q } from '@nozbe/watermelondb';
