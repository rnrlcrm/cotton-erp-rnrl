/**
 * Commodities Settings Page
 * Manage commodities, varieties, parameters, and trading terms
 */

import { useState, useEffect } from 'react';
import {
  CubeIcon,
  SparklesIcon,
  Cog6ToothIcon,
  DocumentDuplicateIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  MagnifyingGlassIcon,
} from '@heroicons/react/24/outline';
import { useToast } from '@/contexts/ToastContext';
import {
  CommodityModal,
  TradeTypeModal,
  BargainTypeModal,
  TermModal,
  PaymentTermModal,
} from '@/components/settings/CommodityModals';
import commodityService from '@/services/api/commodityService';
import type {
  Commodity,
  TradeType,
  BargainType,
  PassingTerm,
  WeightmentTerm,
  DeliveryTerm,
  PaymentTerm,
} from '@/types/settings';

export default function CommoditiesPage() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'commodities' | 'trade-types' | 'bargain-types' | 'terms'>('commodities');
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [tradeTypes, setTradeTypes] = useState<TradeType[]>([]);
  const [bargainTypes, setBargainTypes] = useState<BargainType[]>([]);
  const [passingTerms, setPassingTerms] = useState<PassingTerm[]>([]);
  const [weightmentTerms, setWeightmentTerms] = useState<WeightmentTerm[]>([]);
  const [deliveryTerms, setDeliveryTerms] = useState<DeliveryTerm[]>([]);
  const [paymentTerms, setPaymentTerms] = useState<PaymentTerm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [commodityModal, setCommodityModal] = useState<{ open: boolean; data?: Commodity }>({ open: false });
  const [tradeTypeModal, setTradeTypeModal] = useState<{ open: boolean; data?: TradeType }>({ open: false });
  const [bargainTypeModal, setBargainTypeModal] = useState<{ open: boolean; data?: BargainType }>({ open: false });
  const [passingTermModal, setPassingTermModal] = useState<{ open: boolean; data?: PassingTerm }>({ open: false });
  const [weightmentTermModal, setWeightmentTermModal] = useState<{ open: boolean; data?: WeightmentTerm }>({ open: false });
  const [deliveryTermModal, setDeliveryTermModal] = useState<{ open: boolean; data?: DeliveryTerm }>({ open: false });
  const [paymentTermModal, setPaymentTermModal] = useState<{ open: boolean; data?: PaymentTerm }>({ open: false });

  useEffect(() => {
    loadCommodityData();
  }, []);

  const loadCommodityData = async () => {
    try {
      setLoading(true);
      const [
        comms,
        trade,
        bargain,
        passing,
        weightment,
        delivery,
        payment,
      ] = await Promise.all([
        commodityService.listCommodities(),
        commodityService.listTradeTypes(),
        commodityService.listBargainTypes(),
        commodityService.listPassingTerms(),
        commodityService.listWeightmentTerms(),
        commodityService.listDeliveryTerms(),
        commodityService.listPaymentTerms(),
      ]);

      setCommodities(comms);
      setTradeTypes(trade);
      setBargainTypes(bargain);
      setPassingTerms(passing);
      setWeightmentTerms(weightment);
      setDeliveryTerms(delivery);
      setPaymentTerms(payment);
    } catch (err: any) {
      setError(err.message || 'Failed to load commodity data');
    } finally {
      setLoading(false);
    }
  };

  // Delete handlers
  const handleDeleteCommodity = async (id: string) => {
    if (!confirm('Are you sure you want to delete this commodity?')) return;
    try {
      await commodityService.deleteCommodity(id);
      toast.success('Commodity deleted successfully');
      loadCommodityData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete commodity');
    }
  };

  const tabs = [
    { id: 'commodities' as const, label: 'Commodities', icon: CubeIcon },
    { id: 'trade-types' as const, label: 'Trade Types', icon: Cog6ToothIcon },
    { id: 'bargain-types' as const, label: 'Bargain Types', icon: SparklesIcon },
    { id: 'terms' as const, label: 'Trading Terms', icon: DocumentDuplicateIcon },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-space-900 via-space-800 to-saturn-900 p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-pearl-100">Loading commodity data...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-space-900 via-space-800 to-saturn-900 p-6">
        <div className="bg-mars-500/20 border border-mars-500/30 rounded-lg p-4">
          <p className="text-mars-200">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-space-900 via-space-800 to-saturn-900 p-6">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold bg-gradient-to-r from-sun-400 to-saturn-400 bg-clip-text text-transparent">
          Commodity Settings
        </h1>
        <p className="text-pearl-300 mt-2">Manage commodities, trading types, and terms</p>
      </div>

      {/* Tabs */}
      <div className="mb-6 border-b border-pearl-700/30">
        <div className="flex space-x-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-3 font-medium rounded-t-lg transition-all ${
                  activeTab === tab.id
                    ? 'bg-gradient-to-r from-saturn-500/20 to-sun-500/20 text-sun-400 border-b-2 border-sun-400'
                    : 'text-pearl-400 hover:text-pearl-100 hover:bg-pearl-700/10'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Icon className="w-5 h-5" />
                  <span>{tab.label}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Content */}
      <div className="bg-pearl-900/20 backdrop-blur-sm border border-pearl-700/30 rounded-xl p-6">
        {activeTab === 'commodities' && (
          <CommoditiesList 
            commodities={commodities} 
            onAdd={() => setCommodityModal({ open: true })}
            onEdit={(commodity) => setCommodityModal({ open: true, data: commodity })}
            onDelete={handleDeleteCommodity}
          />
        )}
        
        {activeTab === 'trade-types' && (
          <TradeTypesList 
            tradeTypes={tradeTypes} 
            onAdd={() => setTradeTypeModal({ open: true })}
            onEdit={(type) => setTradeTypeModal({ open: true, data: type })}
          />
        )}
        
        {activeTab === 'bargain-types' && (
          <BargainTypesList 
            bargainTypes={bargainTypes} 
            onAdd={() => setBargainTypeModal({ open: true })}
            onEdit={(type) => setBargainTypeModal({ open: true, data: type })}
          />
        )}
        
        {activeTab === 'terms' && (
          <TradingTerms
            passingTerms={passingTerms}
            weightmentTerms={weightmentTerms}
            deliveryTerms={deliveryTerms}
            paymentTerms={paymentTerms}
            onAddPassing={() => setPassingTermModal({ open: true })}
            onEditPassing={(term) => setPassingTermModal({ open: true, data: term })}
            onAddWeightment={() => setWeightmentTermModal({ open: true })}
            onEditWeightment={(term) => setWeightmentTermModal({ open: true, data: term })}
            onAddDelivery={() => setDeliveryTermModal({ open: true })}
            onEditDelivery={(term) => setDeliveryTermModal({ open: true, data: term })}
            onAddPayment={() => setPaymentTermModal({ open: true })}
            onEditPayment={(term) => setPaymentTermModal({ open: true, data: term })}
          />
        )}
      </div>

      {/* Modals */}
      <CommodityModal
        isOpen={commodityModal.open}
        onClose={() => setCommodityModal({ open: false })}
        commodity={commodityModal.data}
        onSuccess={loadCommodityData}
      />
      <TradeTypeModal
        isOpen={tradeTypeModal.open}
        onClose={() => setTradeTypeModal({ open: false })}
        tradeType={tradeTypeModal.data}
        onSuccess={loadCommodityData}
      />
      <BargainTypeModal
        isOpen={bargainTypeModal.open}
        onClose={() => setBargainTypeModal({ open: false })}
        bargainType={bargainTypeModal.data}
        onSuccess={loadCommodityData}
      />
      <TermModal
        isOpen={passingTermModal.open}
        onClose={() => setPassingTermModal({ open: false })}
        term={passingTermModal.data}
        termType="passing"
        onSuccess={loadCommodityData}
      />
      <TermModal
        isOpen={weightmentTermModal.open}
        onClose={() => setWeightmentTermModal({ open: false })}
        term={weightmentTermModal.data}
        termType="weightment"
        onSuccess={loadCommodityData}
      />
      <TermModal
        isOpen={deliveryTermModal.open}
        onClose={() => setDeliveryTermModal({ open: false })}
        term={deliveryTermModal.data}
        termType="delivery"
        onSuccess={loadCommodityData}
      />
      <PaymentTermModal
        isOpen={paymentTermModal.open}
        onClose={() => setPaymentTermModal({ open: false })}
        paymentTerm={paymentTermModal.data}
        onSuccess={loadCommodityData}
      />
    </div>
  );
}

// Component for Commodities List
function CommoditiesList({ 
  commodities, 
  onAdd, 
  onEdit, 
  onDelete 
}: { 
  commodities: Commodity[]; 
  onAdd: () => void;
  onEdit: (commodity: Commodity) => void;
  onDelete: (id: string) => void;
}) {
  const [searchTerm, setSearchTerm] = useState('');
  
  const filteredCommodities = commodities.filter(c =>
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.category.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-pearl-100">Commodities Catalog</h2>
        <div className="flex items-center space-x-4">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-pearl-400" />
            <input
              type="text"
              placeholder="Search commodities..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 pr-4 py-2 bg-pearl-800/50 border border-pearl-700/30 rounded-lg text-pearl-100 placeholder-pearl-500 focus:outline-none focus:ring-2 focus:ring-sun-500"
            />
          </div>
          <button 
            onClick={onAdd}
            className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
          >
            <PlusIcon className="w-4 h-4" />
            <span>Add Commodity</span>
          </button>
        </div>
      </div>

      {filteredCommodities.length === 0 ? (
        <div className="text-center py-12 text-pearl-400">
          {searchTerm ? 'No commodities found matching your search' : 'No commodities added yet'}
        </div>
      ) : (
        <div className="grid gap-4">
          {filteredCommodities.map((commodity) => (
            <div key={commodity.id} className="bg-pearl-800/30 rounded-lg p-4 border border-pearl-700/30 hover:border-sun-500/30 transition-colors">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-pearl-100 font-medium">{commodity.name}</h3>
                    <span className="px-2 py-1 bg-saturn-500/20 text-saturn-400 text-xs rounded">{commodity.category}</span>
                    {!commodity.is_active && (
                      <span className="px-2 py-1 bg-mars-500/20 text-mars-400 text-xs rounded">Inactive</span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
                    <div>
                      <p className="text-pearl-500 text-xs">HSN Code</p>
                      <p className="text-pearl-300 text-sm">{commodity.hsn_code || 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-pearl-500 text-xs">GST Rate</p>
                      <p className="text-pearl-300 text-sm">{commodity.gst_rate ? `${commodity.gst_rate}%` : 'N/A'}</p>
                    </div>
                    <div>
                      <p className="text-pearl-500 text-xs">Base Unit</p>
                      <p className="text-pearl-300 text-sm">{commodity.base_unit}</p>
                    </div>
                    <div>
                      <p className="text-pearl-500 text-xs">Trade Unit</p>
                      <p className="text-pearl-300 text-sm">{commodity.trade_unit || 'N/A'}</p>
                    </div>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => onEdit(commodity)}
                    className="p-2 hover:bg-pearl-700/30 rounded transition-colors"
                  >
                    <PencilIcon className="w-4 h-4 text-pearl-400" />
                  </button>
                  <button 
                    onClick={() => onDelete(commodity.id)}
                    className="p-2 hover:bg-mars-500/20 rounded transition-colors"
                  >
                    <TrashIcon className="w-4 h-4 text-mars-400" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Component for Trade Types List
function TradeTypesList({ 
  tradeTypes, 
  onAdd, 
  onEdit 
}: { 
  tradeTypes: TradeType[]; 
  onAdd: () => void;
  onEdit: (type: TradeType) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-pearl-100">Trade Types</h2>
        <button 
          onClick={onAdd}
          className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
        >
          <PlusIcon className="w-4 h-4" />
          <span>Add Trade Type</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tradeTypes.map((type) => (
          <div key={type.id} className="bg-pearl-800/30 rounded-lg p-4 border border-pearl-700/30">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-pearl-100 font-medium">{type.name}</h3>
                <p className="text-pearl-400 text-sm mt-1">{type.description}</p>
              </div>
              <div className="flex space-x-1">
                <button 
                  onClick={() => onEdit(type)}
                  className="p-1.5 hover:bg-pearl-700/30 rounded transition-colors"
                >
                  <PencilIcon className="w-3.5 h-3.5 text-pearl-400" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Component for Bargain Types List
function BargainTypesList({ 
  bargainTypes, 
  onAdd, 
  onEdit 
}: { 
  bargainTypes: BargainType[]; 
  onAdd: () => void;
  onEdit: (type: BargainType) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-pearl-100">Bargain Types</h2>
        <button 
          onClick={onAdd}
          className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
        >
          <PlusIcon className="w-4 h-4" />
          <span>Add Bargain Type</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {bargainTypes.map((type) => (
          <div key={type.id} className="bg-pearl-800/30 rounded-lg p-4 border border-pearl-700/30">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="text-pearl-100 font-medium">{type.name}</h3>
                <p className="text-pearl-400 text-sm mt-1">{type.description}</p>
              </div>
              <div className="flex space-x-1">
                <button 
                  onClick={() => onEdit(type)}
                  className="p-1.5 hover:bg-pearl-700/30 rounded transition-colors"
                >
                  <PencilIcon className="w-3.5 h-3.5 text-pearl-400" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Component for Trading Terms
function TradingTerms({
  passingTerms,
  weightmentTerms,
  deliveryTerms,
  paymentTerms,
  onAddPassing,
  onEditPassing,
  onAddWeightment,
  onEditWeightment,
  onAddDelivery,
  onEditDelivery,
  onAddPayment,
  onEditPayment,
}: {
  passingTerms: PassingTerm[];
  weightmentTerms: WeightmentTerm[];
  deliveryTerms: DeliveryTerm[];
  paymentTerms: PaymentTerm[];
  onAddPassing: () => void;
  onEditPassing: (term: PassingTerm) => void;
  onAddWeightment: () => void;
  onEditWeightment: (term: WeightmentTerm) => void;
  onAddDelivery: () => void;
  onEditDelivery: (term: DeliveryTerm) => void;
  onAddPayment: () => void;
  onEditPayment: (term: PaymentTerm) => void;
}) {
  const [activeTermTab, setActiveTermTab] = useState<'passing' | 'weightment' | 'delivery' | 'payment'>('passing');

  const termTabs = [
    { id: 'passing' as const, label: 'Passing Terms' },
    { id: 'weightment' as const, label: 'Weightment Terms' },
    { id: 'delivery' as const, label: 'Delivery Terms' },
    { id: 'payment' as const, label: 'Payment Terms' },
  ];

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold text-pearl-100">Trading Terms</h2>

      {/* Sub-tabs for different term types */}
      <div className="flex space-x-2 border-b border-pearl-700/30">
        {termTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTermTab(tab.id)}
            className={`px-4 py-2 font-medium rounded-t transition-all ${
              activeTermTab === tab.id
                ? 'bg-pearl-800/50 text-sun-400 border-b-2 border-sun-400'
                : 'text-pearl-400 hover:text-pearl-100'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="pt-4">
        {activeTermTab === 'passing' && (
          <TermsList 
            terms={passingTerms} 
            type="Passing" 
            onAdd={onAddPassing}
            onEdit={onEditPassing}
          />
        )}
        {activeTermTab === 'weightment' && (
          <TermsList 
            terms={weightmentTerms} 
            type="Weightment" 
            onAdd={onAddWeightment}
            onEdit={onEditWeightment}
          />
        )}
        {activeTermTab === 'delivery' && (
          <TermsList 
            terms={deliveryTerms} 
            type="Delivery" 
            onAdd={onAddDelivery}
            onEdit={onEditDelivery}
          />
        )}
        {activeTermTab === 'payment' && (
          <PaymentTermsList 
            terms={paymentTerms} 
            onAdd={onAddPayment}
            onEdit={onEditPayment}
          />
        )}
      </div>
    </div>
  );
}

// Generic Terms List Component
function TermsList({ 
  terms, 
  type, 
  onAdd, 
  onEdit 
}: { 
  terms: any[]; 
  type: string;
  onAdd: () => void;
  onEdit: (term: any) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-pearl-200">{type} Terms</h3>
        <button 
          onClick={onAdd}
          className="px-3 py-1.5 bg-gradient-to-r from-saturn-500 to-sun-500 text-white text-sm rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
        >
          <PlusIcon className="w-3.5 h-3.5" />
          <span>Add {type} Term</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {terms.map((term) => (
          <div key={term.id} className="bg-pearl-800/30 rounded-lg p-3 border border-pearl-700/30">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="text-pearl-100 font-medium text-sm">{term.name}</h4>
                {term.description && (
                  <p className="text-pearl-400 text-xs mt-1">{term.description}</p>
                )}
              </div>
              <div className="flex space-x-1">
                <button 
                  onClick={() => onEdit(term)}
                  className="p-1 hover:bg-pearl-700/30 rounded transition-colors"
                >
                  <PencilIcon className="w-3 h-3 text-pearl-400" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Payment Terms List Component (with days)
function PaymentTermsList({ 
  terms, 
  onAdd, 
  onEdit 
}: { 
  terms: PaymentTerm[];
  onAdd: () => void;
  onEdit: (term: PaymentTerm) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-pearl-200">Payment Terms</h3>
        <button 
          onClick={onAdd}
          className="px-3 py-1.5 bg-gradient-to-r from-saturn-500 to-sun-500 text-white text-sm rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
        >
          <PlusIcon className="w-3.5 h-3.5" />
          <span>Add Payment Term</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {terms.map((term) => (
          <div key={term.id} className="bg-pearl-800/30 rounded-lg p-3 border border-pearl-700/30">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="text-pearl-100 font-medium text-sm">{term.name}</h4>
                {term.description && (
                  <p className="text-pearl-400 text-xs mt-1">{term.description}</p>
                )}
                {term.days !== null && (
                  <p className="text-sun-400 text-xs mt-1">{term.days} days</p>
                )}
              </div>
              <div className="flex space-x-1">
                <button 
                  onClick={() => onEdit(term)}
                  className="p-1 hover:bg-pearl-700/30 rounded transition-colors"
                >
                  <PencilIcon className="w-3 h-3 text-pearl-400" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
