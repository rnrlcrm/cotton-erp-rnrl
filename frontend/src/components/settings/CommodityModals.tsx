/**
 * Commodity CRUD Modals
 * All modal components for Commodities settings
 */

import { useState, useEffect } from 'react';
import { SparklesIcon } from '@heroicons/react/24/outline';
import Modal from '@/components/common/Modal';
import { useToast } from '@/contexts/ToastContext';
import commodityService from '@/services/api/commodityService';
import type {
  Commodity,
  CommodityCreate,
  TradeType,
  BargainType,
  PassingTerm,
  WeightmentTerm,
  DeliveryTerm,
  PaymentTerm,
} from '@/types/settings';

// ==================== Commodity Modal ====================

interface CommodityModalProps {
  isOpen: boolean;
  onClose: () => void;
  commodity?: Commodity;
  onSuccess: () => void;
}

export function CommodityModal({ isOpen, onClose, commodity, onSuccess }: CommodityModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [formData, setFormData] = useState<CommodityCreate>({
    name: '',
    category: '',
    base_unit: 'kg',
    default_currency: 'INR',
  });

  useEffect(() => {
    if (commodity) {
      setFormData({
        name: commodity.name,
        category: commodity.category,
        hsn_code: commodity.hsn_code,
        gst_rate: commodity.gst_rate,
        description: commodity.description,
        uom: commodity.uom,
        base_unit: commodity.base_unit,
        trade_unit: commodity.trade_unit,
        rate_unit: commodity.rate_unit,
        standard_weight_per_unit: commodity.standard_weight_per_unit,
        default_currency: commodity.default_currency,
        supported_currencies: commodity.supported_currencies,
        international_pricing_unit: commodity.international_pricing_unit,
        hs_code_6digit: commodity.hs_code_6digit,
        quality_standards: commodity.quality_standards,
        major_producing_countries: commodity.major_producing_countries,
        major_consuming_countries: commodity.major_consuming_countries,
        trading_hubs: commodity.trading_hubs,
        traded_on_exchanges: commodity.traded_on_exchanges,
        price_volatility: commodity.price_volatility,
        phytosanitary_required: commodity.phytosanitary_required,
        fumigation_required: commodity.fumigation_required,
        seasonal_commodity: commodity.seasonal_commodity,
        shelf_life_days: commodity.shelf_life_days,
        delivery_tolerance_pct: commodity.delivery_tolerance_pct,
        weight_tolerance_pct: commodity.weight_tolerance_pct,
        is_active: commodity.is_active,
      });
    } else {
      setFormData({
        name: '',
        category: '',
        base_unit: 'kg',
        default_currency: 'INR',
      });
    }
  }, [commodity, isOpen]);

  const handleAISuggestCategory = async () => {
    if (!formData.name) {
      toast.warning('Please enter commodity name first');
      return;
    }

    try {
      setAiLoading(true);
      const result = await commodityService.detectCategory(formData.name, formData.description || '');
      setFormData(prev => ({ ...prev, category: result.category }));
      toast.success('AI suggested category');
    } catch (error: any) {
      toast.error(error.message || 'Failed to detect category');
    } finally {
      setAiLoading(false);
    }
  };

  const handleAISuggestHSN = async () => {
    if (!formData.name) {
      toast.warning('Please enter commodity name first');
      return;
    }

    try {
      setAiLoading(true);
      const result = await commodityService.suggestHSN(formData.name, formData.category);
      setFormData(prev => ({
        ...prev,
        hsn_code: result.hsn_code,
        gst_rate: result.gst_rate,
      }));
      toast.success('AI suggested HSN code and GST rate');
    } catch (error: any) {
      toast.error(error.message || 'Failed to suggest HSN');
    } finally {
      setAiLoading(false);
    }
  };

  const handleAISuggestInternational = async () => {
    if (!formData.name) {
      toast.warning('Please enter commodity name first');
      return;
    }

    try {
      setAiLoading(true);
      const result = await commodityService.suggestInternationalFields(formData.name, formData.category);
      setFormData(prev => ({
        ...prev,
        hs_code_6digit: result.hs_code_6digit,
        international_pricing_unit: result.international_pricing_unit,
        quality_standards: result.quality_standards,
        major_producing_countries: result.major_producing_countries,
        major_consuming_countries: result.major_consuming_countries,
        trading_hubs: result.trading_hubs,
        traded_on_exchanges: result.traded_on_exchanges,
        price_volatility: result.price_volatility,
        phytosanitary_required: result.phytosanitary_required,
        fumigation_required: result.fumigation_required,
        seasonal_commodity: result.seasonal_commodity,
      }));
      toast.success('AI populated international fields (90% of data)');
    } catch (error: any) {
      toast.error(error.message || 'Failed to suggest international fields');
    } finally {
      setAiLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name || !formData.category) {
      toast.error('Please fill in all required fields');
      return;
    }

    try {
      setLoading(true);
      if (commodity) {
        await commodityService.updateCommodity(commodity.id, formData);
        toast.success('Commodity updated successfully');
      } else {
        await commodityService.createCommodity(formData);
        toast.success('Commodity created successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save commodity');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={commodity ? 'Edit Commodity' : 'Add Commodity'} size="xl">
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* AI Helper Buttons */}
        <div className="flex flex-wrap gap-2 p-3 bg-gradient-to-r from-sun-500/10 to-saturn-500/10 border border-sun-500/20 rounded-lg">
          <button
            type="button"
            onClick={handleAISuggestCategory}
            disabled={aiLoading || !formData.name}
            className="flex items-center space-x-1 px-3 py-1.5 bg-sun-500/20 hover:bg-sun-500/30 text-sun-300 text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <SparklesIcon className="w-4 h-4" />
            <span>AI Detect Category</span>
          </button>
          <button
            type="button"
            onClick={handleAISuggestHSN}
            disabled={aiLoading || !formData.name}
            className="flex items-center space-x-1 px-3 py-1.5 bg-sun-500/20 hover:bg-sun-500/30 text-sun-300 text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <SparklesIcon className="w-4 h-4" />
            <span>AI Suggest HSN/GST</span>
          </button>
          <button
            type="button"
            onClick={handleAISuggestInternational}
            disabled={aiLoading || !formData.name}
            className="flex items-center space-x-1 px-3 py-1.5 bg-sun-500/20 hover:bg-sun-500/30 text-sun-300 text-sm rounded disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <SparklesIcon className="w-4 h-4" />
            <span>AI Populate International (90%)</span>
          </button>
        </div>

        {/* Basic Information */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">
              Commodity Name <span className="text-mars-400">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">
              Category <span className="text-mars-400">*</span>
            </label>
            <input
              type="text"
              value={formData.category}
              onChange={(e) => setFormData({ ...formData, category: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
              required
            />
          </div>
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">Description</label>
          <textarea
            value={formData.description || ''}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={2}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
          />
        </div>

        {/* Tax Information */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">HSN Code</label>
            <input
              type="text"
              value={formData.hsn_code || ''}
              onChange={(e) => setFormData({ ...formData, hsn_code: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">GST Rate (%)</label>
            <input
              type="number"
              step="0.01"
              value={formData.gst_rate || ''}
              onChange={(e) => setFormData({ ...formData, gst_rate: e.target.value ? parseFloat(e.target.value) : null })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">HS Code (6-digit)</label>
            <input
              type="text"
              maxLength={6}
              value={formData.hs_code_6digit || ''}
              onChange={(e) => setFormData({ ...formData, hs_code_6digit: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
        </div>

        {/* Units */}
        <div className="grid grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Base Unit</label>
            <select
              value={formData.base_unit}
              onChange={(e) => setFormData({ ...formData, base_unit: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            >
              <option value="kg">Kilogram (kg)</option>
              <option value="quintal">Quintal</option>
              <option value="ton">Ton</option>
              <option value="bale">Bale</option>
              <option value="bag">Bag</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Trade Unit</label>
            <input
              type="text"
              value={formData.trade_unit || ''}
              onChange={(e) => setFormData({ ...formData, trade_unit: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Rate Unit</label>
            <input
              type="text"
              value={formData.rate_unit || ''}
              onChange={(e) => setFormData({ ...formData, rate_unit: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Std Weight/Unit</label>
            <input
              type="number"
              step="0.01"
              value={formData.standard_weight_per_unit || ''}
              onChange={(e) => setFormData({ ...formData, standard_weight_per_unit: e.target.value ? parseFloat(e.target.value) : null })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
        </div>

        {/* International Trading */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Default Currency</label>
            <select
              value={formData.default_currency}
              onChange={(e) => setFormData({ ...formData, default_currency: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            >
              <option value="INR">INR</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Intl Pricing Unit</label>
            <input
              type="text"
              value={formData.international_pricing_unit || ''}
              onChange={(e) => setFormData({ ...formData, international_pricing_unit: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Price Volatility</label>
            <select
              value={formData.price_volatility || ''}
              onChange={(e) => setFormData({ ...formData, price_volatility: e.target.value })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            >
              <option value="">Select...</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>

        {/* Checkboxes */}
        <div className="grid grid-cols-3 gap-4">
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.phytosanitary_required || false}
              onChange={(e) => setFormData({ ...formData, phytosanitary_required: e.target.checked })}
              className="w-4 h-4 text-sun-500 bg-pearl-900 border-pearl-700 rounded focus:ring-sun-500"
            />
            <span className="text-sm text-pearl-200">Phytosanitary Required</span>
          </label>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.fumigation_required || false}
              onChange={(e) => setFormData({ ...formData, fumigation_required: e.target.checked })}
              className="w-4 h-4 text-sun-500 bg-pearl-900 border-pearl-700 rounded focus:ring-sun-500"
            />
            <span className="text-sm text-pearl-200">Fumigation Required</span>
          </label>
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.seasonal_commodity || false}
              onChange={(e) => setFormData({ ...formData, seasonal_commodity: e.target.checked })}
              className="w-4 h-4 text-sun-500 bg-pearl-900 border-pearl-700 rounded focus:ring-sun-500"
            />
            <span className="text-sm text-pearl-200">Seasonal Commodity</span>
          </label>
        </div>

        {/* Tolerances */}
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Delivery Tolerance (%)</label>
            <input
              type="number"
              step="0.01"
              value={formData.delivery_tolerance_pct || ''}
              onChange={(e) => setFormData({ ...formData, delivery_tolerance_pct: e.target.value ? parseFloat(e.target.value) : null })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Weight Tolerance (%)</label>
            <input
              type="number"
              step="0.01"
              value={formData.weight_tolerance_pct || ''}
              onChange={(e) => setFormData({ ...formData, weight_tolerance_pct: e.target.value ? parseFloat(e.target.value) : null })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-pearl-200 mb-1">Shelf Life (days)</label>
            <input
              type="number"
              value={formData.shelf_life_days || ''}
              onChange={(e) => setFormData({ ...formData, shelf_life_days: e.target.value ? parseInt(e.target.value) : null })}
              className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            />
          </div>
        </div>

        {/* Active Status */}
        {commodity && (
          <label className="flex items-center space-x-2 cursor-pointer">
            <input
              type="checkbox"
              checked={formData.is_active !== false}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 text-sun-500 bg-pearl-900 border-pearl-700 rounded focus:ring-sun-500"
            />
            <span className="text-sm text-pearl-200">Active</span>
          </label>
        )}

        {/* Buttons */}
        <div className="flex justify-end space-x-3 pt-4 border-t border-pearl-700/30">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800 hover:bg-pearl-700 text-pearl-200 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded hover:from-saturn-600 hover:to-sun-600 transition-all disabled:opacity-50"
          >
            {loading ? 'Saving...' : commodity ? 'Update Commodity' : 'Create Commodity'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ==================== Trade Type Modal ====================

interface TradeTypeModalProps {
  isOpen: boolean;
  onClose: () => void;
  tradeType?: TradeType;
  onSuccess: () => void;
}

export function TradeTypeModal({ isOpen, onClose, tradeType, onSuccess }: TradeTypeModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '' });

  useEffect(() => {
    if (tradeType) {
      setFormData({
        name: tradeType.name,
        description: tradeType.description || '',
      });
    } else {
      setFormData({ name: '', description: '' });
    }
  }, [tradeType, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name) {
      toast.error('Please enter trade type name');
      return;
    }

    try {
      setLoading(true);
      if (tradeType) {
        await commodityService.updateTradeType(tradeType.id, formData);
        toast.success('Trade type updated successfully');
      } else {
        await commodityService.createTradeType(formData);
        toast.success('Trade type created successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save trade type');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={tradeType ? 'Edit Trade Type' : 'Add Trade Type'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">
            Name <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
          />
        </div>

        <div className="flex justify-end space-x-3 pt-4 border-t border-pearl-700/30">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800 hover:bg-pearl-700 text-pearl-200 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded hover:from-saturn-600 hover:to-sun-600 transition-all disabled:opacity-50"
          >
            {loading ? 'Saving...' : tradeType ? 'Update' : 'Create'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ==================== Bargain Type Modal ====================

interface BargainTypeModalProps {
  isOpen: boolean;
  onClose: () => void;
  bargainType?: BargainType;
  onSuccess: () => void;
}

export function BargainTypeModal({ isOpen, onClose, bargainType, onSuccess }: BargainTypeModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '' });

  useEffect(() => {
    if (bargainType) {
      setFormData({
        name: bargainType.name,
        description: bargainType.description || '',
      });
    } else {
      setFormData({ name: '', description: '' });
    }
  }, [bargainType, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name) {
      toast.error('Please enter bargain type name');
      return;
    }

    try {
      setLoading(true);
      if (bargainType) {
        await commodityService.updateBargainType(bargainType.id, formData);
        toast.success('Bargain type updated successfully');
      } else {
        await commodityService.createBargainType(formData);
        toast.success('Bargain type created successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save bargain type');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={bargainType ? 'Edit Bargain Type' : 'Add Bargain Type'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">
            Name <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
          />
        </div>

        <div className="flex justify-end space-x-3 pt-4 border-t border-pearl-700/30">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800 hover:bg-pearl-700 text-pearl-200 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded hover:from-saturn-600 hover:to-sun-600 transition-all disabled:opacity-50"
          >
            {loading ? 'Saving...' : bargainType ? 'Update' : 'Create'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ==================== Generic Term Modal ====================

interface TermModalProps {
  isOpen: boolean;
  onClose: () => void;
  term?: PassingTerm | WeightmentTerm | DeliveryTerm;
  termType: 'passing' | 'weightment' | 'delivery';
  onSuccess: () => void;
}

export function TermModal({ isOpen, onClose, term, termType, onSuccess }: TermModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '' });

  const termTypeLabel = termType.charAt(0).toUpperCase() + termType.slice(1);

  useEffect(() => {
    if (term) {
      setFormData({
        name: term.name,
        description: term.description || '',
      });
    } else {
      setFormData({ name: '', description: '' });
    }
  }, [term, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name) {
      toast.error('Please enter term name');
      return;
    }

    try {
      setLoading(true);
      
      if (term) {
        // Update
        if (termType === 'passing') {
          await commodityService.updatePassingTerm(term.id, formData);
        } else if (termType === 'weightment') {
          await commodityService.updateWeightmentTerm(term.id, formData);
        } else {
          await commodityService.updateDeliveryTerm(term.id, formData);
        }
        toast.success(`${termTypeLabel} term updated successfully`);
      } else {
        // Create
        if (termType === 'passing') {
          await commodityService.createPassingTerm(formData);
        } else if (termType === 'weightment') {
          await commodityService.createWeightmentTerm(formData);
        } else {
          await commodityService.createDeliveryTerm(formData);
        }
        toast.success(`${termTypeLabel} term created successfully`);
      }
      
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || `Failed to save ${termType} term`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={term ? `Edit ${termTypeLabel} Term` : `Add ${termTypeLabel} Term`} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">
            Name <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
          />
        </div>

        <div className="flex justify-end space-x-3 pt-4 border-t border-pearl-700/30">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800 hover:bg-pearl-700 text-pearl-200 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded hover:from-saturn-600 hover:to-sun-600 transition-all disabled:opacity-50"
          >
            {loading ? 'Saving...' : term ? 'Update' : 'Create'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

// ==================== Payment Term Modal ====================

interface PaymentTermModalProps {
  isOpen: boolean;
  onClose: () => void;
  paymentTerm?: PaymentTerm;
  onSuccess: () => void;
}

export function PaymentTermModal({ isOpen, onClose, paymentTerm, onSuccess }: PaymentTermModalProps) {
  const toast = useToast();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '', days: 0 });

  useEffect(() => {
    if (paymentTerm) {
      setFormData({
        name: paymentTerm.name,
        description: paymentTerm.description || '',
        days: paymentTerm.days || 0,
      });
    } else {
      setFormData({ name: '', description: '', days: 0 });
    }
  }, [paymentTerm, isOpen]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name) {
      toast.error('Please enter payment term name');
      return;
    }

    try {
      setLoading(true);
      if (paymentTerm) {
        await commodityService.updatePaymentTerm(paymentTerm.id, formData);
        toast.success('Payment term updated successfully');
      } else {
        await commodityService.createPaymentTerm(formData);
        toast.success('Payment term created successfully');
      }
      onSuccess();
      onClose();
    } catch (error: any) {
      toast.error(error.message || 'Failed to save payment term');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={paymentTerm ? 'Edit Payment Term' : 'Add Payment Term'} size="md">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">
            Name <span className="text-mars-400">*</span>
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            rows={3}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-pearl-200 mb-1">Payment Days</label>
          <input
            type="number"
            value={formData.days}
            onChange={(e) => setFormData({ ...formData, days: parseInt(e.target.value) || 0 })}
            className="w-full px-3 py-2 bg-pearl-900/50 border border-pearl-700/50 rounded text-pearl-100 focus:outline-none focus:border-sun-500"
          />
        </div>

        <div className="flex justify-end space-x-3 pt-4 border-t border-pearl-700/30">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-pearl-800 hover:bg-pearl-700 text-pearl-200 rounded transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded hover:from-saturn-600 hover:to-sun-600 transition-all disabled:opacity-50"
          >
            {loading ? 'Saving...' : paymentTerm ? 'Update' : 'Create'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
