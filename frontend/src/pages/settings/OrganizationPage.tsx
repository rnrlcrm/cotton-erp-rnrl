/**
 * Organization Settings Page
 * Manage company details, GST, bank accounts, financial years, and document series
 */

import { useState, useEffect } from 'react';
import { 
  BuildingOfficeIcon, 
  BanknotesIcon, 
  CalendarIcon, 
  DocumentTextIcon,
  PlusIcon,
  PencilIcon,
  TrashIcon,
  CheckCircleIcon,
} from '@heroicons/react/24/outline';
import organizationService from '@/services/api/organizationService';
import { useToast } from '@/contexts/ToastContext';
import { 
  GSTModal, 
  BankAccountModal, 
  FinancialYearModal, 
  DocumentSeriesModal 
} from '@/components/settings/OrganizationModals';
import type { 
  Organization, 
  OrganizationGST, 
  OrganizationBankAccount,
  OrganizationFinancialYear,
  OrganizationDocumentSeries,
} from '@/types/settings';

export default function OrganizationPage() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState<'company' | 'gst' | 'banks' | 'fy' | 'docs'>('company');
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [gstList, setGstList] = useState<OrganizationGST[]>([]);
  const [bankAccounts, setBankAccounts] = useState<OrganizationBankAccount[]>([]);
  const [financialYears, setFinancialYears] = useState<OrganizationFinancialYear[]>([]);
  const [documentSeries, setDocumentSeries] = useState<OrganizationDocumentSeries[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal states
  const [gstModal, setGstModal] = useState<{ open: boolean; data?: OrganizationGST }>({ open: false });
  const [bankModal, setBankModal] = useState<{ open: boolean; data?: OrganizationBankAccount }>({ open: false });
  const [fyModal, setFyModal] = useState<{ open: boolean; data?: OrganizationFinancialYear }>({ open: false });
  const [docModal, setDocModal] = useState<{ open: boolean; data?: OrganizationDocumentSeries }>({ open: false });

  useEffect(() => {
    loadOrganizationData();
  }, []);

  const loadOrganizationData = async () => {
    try {
      setLoading(true);
      const orgs = await organizationService.listOrganizations();
      if (orgs.length > 0) {
        const org = orgs[0];
        setOrganization(org);
        
        // Load related data
        const [gst, banks, fy, docs] = await Promise.all([
          organizationService.listGST(org.id),
          organizationService.listBankAccounts(org.id),
          organizationService.listFinancialYears(org.id),
          organizationService.listDocumentSeries(org.id),
        ]);
        
        setGstList(gst);
        setBankAccounts(banks);
        setFinancialYears(fy);
        setDocumentSeries(docs);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load organization data');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteGST = async (id: string) => {
    if (!confirm('Are you sure you want to delete this GST detail?')) return;
    try {
      await organizationService.deleteGST(id);
      toast.success('GST deleted successfully');
      loadOrganizationData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete GST');
    }
  };

  const handleDeleteBank = async (id: string) => {
    if (!confirm('Are you sure you want to delete this bank account?')) return;
    try {
      await organizationService.deleteBankAccount(id);
      toast.success('Bank account deleted successfully');
      loadOrganizationData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete bank account');
    }
  };

  const handleDeleteFY = async (id: string) => {
    if (!confirm('Are you sure you want to delete this financial year?')) return;
    try {
      await organizationService.deleteFinancialYear(id);
      toast.success('Financial year deleted successfully');
      loadOrganizationData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete financial year');
    }
  };

  const handleDeleteDocSeries = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document series?')) return;
    try {
      await organizationService.deleteDocumentSeries(id);
      toast.success('Document series deleted successfully');
      loadOrganizationData();
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete document series');
    }
  };

  const tabs = [
    { id: 'company' as const, label: 'Company Details', icon: BuildingOfficeIcon },
    { id: 'gst' as const, label: 'GST', icon: DocumentTextIcon },
    { id: 'banks' as const, label: 'Bank Accounts', icon: BanknotesIcon },
    { id: 'fy' as const, label: 'Financial Years', icon: CalendarIcon },
    { id: 'docs' as const, label: 'Document Series', icon: DocumentTextIcon },
  ];

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-space-900 via-space-800 to-saturn-900 p-6">
        <div className="flex items-center justify-center h-96">
          <div className="text-pearl-100">Loading organization data...</div>
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
          Organization Settings
        </h1>
        <p className="text-pearl-300 mt-2">Manage your company information and configurations</p>
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
        {activeTab === 'company' && organization && (
          <CompanyDetails organization={organization} onUpdate={loadOrganizationData} />
        )}
        
        {activeTab === 'gst' && (
          <GSTManagement 
            gstList={gstList} 
            organizationId={organization?.id || ''}
            onAdd={() => setGstModal({ open: true })}
            onEdit={(gst) => setGstModal({ open: true, data: gst })}
            onDelete={handleDeleteGST}
          />
        )}
        
        {activeTab === 'banks' && (
          <BankAccountsManagement 
            accounts={bankAccounts} 
            organizationId={organization?.id || ''}
            onAdd={() => setBankModal({ open: true })}
            onEdit={(account) => setBankModal({ open: true, data: account })}
            onDelete={handleDeleteBank}
          />
        )}
        
        {activeTab === 'fy' && (
          <FinancialYearsManagement 
            years={financialYears} 
            organizationId={organization?.id || ''}
            onAdd={() => setFyModal({ open: true })}
            onEdit={(year) => setFyModal({ open: true, data: year })}
            onDelete={handleDeleteFY}
          />
        )}
        
        {activeTab === 'docs' && (
          <DocumentSeriesManagement 
            series={documentSeries} 
            organizationId={organization?.id || ''}
            onAdd={() => setDocModal({ open: true })}
            onEdit={(doc) => setDocModal({ open: true, data: doc })}
            onDelete={handleDeleteDocSeries}
          />
        )}
      </div>

      {/* Modals */}
      {organization && (
        <>
          <GSTModal
            isOpen={gstModal.open}
            onClose={() => setGstModal({ open: false })}
            organizationId={organization.id}
            gst={gstModal.data}
            onSuccess={loadOrganizationData}
          />
          <BankAccountModal
            isOpen={bankModal.open}
            onClose={() => setBankModal({ open: false })}
            organizationId={organization.id}
            account={bankModal.data}
            onSuccess={loadOrganizationData}
          />
          <FinancialYearModal
            isOpen={fyModal.open}
            onClose={() => setFyModal({ open: false })}
            organizationId={organization.id}
            year={fyModal.data}
            onSuccess={loadOrganizationData}
          />
          <DocumentSeriesModal
            isOpen={docModal.open}
            onClose={() => setDocModal({ open: false })}
            organizationId={organization.id}
            series={docModal.data}
            onSuccess={loadOrganizationData}
          />
        </>
      )}
    </div>
  );
}

// Component for Company Details tab
function CompanyDetails({ organization }: { organization: Organization; onUpdate?: () => void }) {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-pearl-100">Company Information</h2>
        <button className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2">
          <PencilIcon className="w-4 h-4" />
          <span>Edit Details</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="text-pearl-400 text-sm">Company Name</label>
          <p className="text-pearl-100 font-medium mt-1">{organization.name}</p>
        </div>
        <div>
          <label className="text-pearl-400 text-sm">Legal Name</label>
          <p className="text-pearl-100 font-medium mt-1">{organization.legal_name || 'N/A'}</p>
        </div>
        <div>
          <label className="text-pearl-400 text-sm">PAN</label>
          <p className="text-pearl-100 font-medium mt-1">{organization.PAN || 'N/A'}</p>
        </div>
        <div>
          <label className="text-pearl-400 text-sm">CIN</label>
          <p className="text-pearl-100 font-medium mt-1">{organization.CIN || 'N/A'}</p>
        </div>
        <div>
          <label className="text-pearl-400 text-sm">Contact Email</label>
          <p className="text-pearl-100 font-medium mt-1">{organization.contact_email || 'N/A'}</p>
        </div>
        <div>
          <label className="text-pearl-400 text-sm">Contact Phone</label>
          <p className="text-pearl-100 font-medium mt-1">{organization.contact_phone || 'N/A'}</p>
        </div>
        <div className="md:col-span-2">
          <label className="text-pearl-400 text-sm">Address</label>
          <p className="text-pearl-100 font-medium mt-1">
            {organization.address_line1 || 'N/A'}
            {organization.address_line2 && <>, {organization.address_line2}</>}
            {organization.city && <>, {organization.city}</>}
            {organization.state && <>, {organization.state}</>}
            {organization.pincode && <> - {organization.pincode}</>}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-6 border-t border-pearl-700/30">
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${organization.einvoice_required ? 'bg-emerald-500' : 'bg-pearl-600'}`}></div>
          <span className="text-pearl-300 text-sm">E-Invoice Required</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${organization.fx_enabled ? 'bg-emerald-500' : 'bg-pearl-600'}`}></div>
          <span className="text-pearl-300 text-sm">FX Enabled</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${organization.auto_invoice ? 'bg-emerald-500' : 'bg-pearl-600'}`}></div>
          <span className="text-pearl-300 text-sm">Auto Invoice</span>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`w-3 h-3 rounded-full ${organization.auto_contract_number ? 'bg-emerald-500' : 'bg-pearl-600'}`}></div>
          <span className="text-pearl-300 text-sm">Auto Contract Number</span>
        </div>
      </div>
    </div>
  );
}

// Component for GST Management tab
function GSTManagement({ gstList, onAdd, onEdit, onDelete }: {
  gstList: OrganizationGST[];
  organizationId?: string;
  onAdd: () => void;
  onEdit: (gst: OrganizationGST) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-pearl-100">GST Details</h2>
        <button 
          onClick={onAdd}
          className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
        >
          <PlusIcon className="w-4 h-4" />
          <span>Add GST</span>
        </button>
      </div>

      {gstList.length === 0 ? (
        <div className="text-center py-12 text-pearl-400">
          No GST details added yet
        </div>
      ) : (
        <div className="grid gap-4">
          {gstList.map((gst) => (
            <div key={gst.id} className="bg-pearl-800/30 rounded-lg p-4 border border-pearl-700/30">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-pearl-100 font-medium">{gst.gstin}</h3>
                    {gst.is_primary && (
                      <span className="px-2 py-1 bg-sun-500/20 text-sun-400 text-xs rounded">Primary</span>
                    )}
                    {!gst.is_active && (
                      <span className="px-2 py-1 bg-mars-500/20 text-mars-400 text-xs rounded">Inactive</span>
                    )}
                  </div>
                  <p className="text-pearl-400 text-sm mt-1">{gst.legal_name}</p>
                  <p className="text-pearl-500 text-sm mt-1">{gst.address} - {gst.state}</p>
                </div>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => onEdit(gst)}
                    className="p-2 hover:bg-pearl-700/30 rounded transition-colors"
                  >
                    <PencilIcon className="w-4 h-4 text-pearl-400" />
                  </button>
                  <button 
                    onClick={() => onDelete(gst.id)}
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

// Component for Bank Accounts Management tab
function BankAccountsManagement({ accounts, onAdd, onEdit, onDelete }: {
  accounts: OrganizationBankAccount[];
  organizationId?: string;
  onAdd: () => void;
  onEdit: (account: OrganizationBankAccount) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-pearl-100">Bank Accounts</h2>
        <button 
          onClick={onAdd}
          className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
        >
          <PlusIcon className="w-4 h-4" />
          <span>Add Account</span>
        </button>
      </div>

      {accounts.length === 0 ? (
        <div className="text-center py-12 text-pearl-400">
          No bank accounts added yet
        </div>
      ) : (
        <div className="grid gap-4">
          {accounts.map((account) => (
            <div key={account.id} className="bg-pearl-800/30 rounded-lg p-4 border border-pearl-700/30">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-pearl-100 font-medium">{account.bank_name}</h3>
                    {account.is_primary && (
                      <span className="px-2 py-1 bg-sun-500/20 text-sun-400 text-xs rounded">Primary</span>
                    )}
                  </div>
                  <p className="text-pearl-400 text-sm mt-1">
                    {account.account_holder_name} • {account.account_number}
                  </p>
                  <p className="text-pearl-500 text-sm mt-1">
                    IFSC: {account.ifsc_code} • {account.branch_name}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => onEdit(account)}
                    className="p-2 hover:bg-pearl-700/30 rounded transition-colors"
                  >
                    <PencilIcon className="w-4 h-4 text-pearl-400" />
                  </button>
                  <button 
                    onClick={() => onDelete(account.id)}
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

// Component for Financial Years Management tab
function FinancialYearsManagement({ years, onAdd, onEdit, onDelete }: {
  years: OrganizationFinancialYear[];
  organizationId?: string;
  onAdd: () => void;
  onEdit: (year: OrganizationFinancialYear) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-pearl-100">Financial Years</h2>
        <button 
          onClick={onAdd}
          className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
        >
          <PlusIcon className="w-4 h-4" />
          <span>Add Financial Year</span>
        </button>
      </div>

      {years.length === 0 ? (
        <div className="text-center py-12 text-pearl-400">
          No financial years configured yet
        </div>
      ) : (
        <div className="grid gap-4">
          {years.map((fy) => (
            <div key={fy.id} className="bg-pearl-800/30 rounded-lg p-4 border border-pearl-700/30">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-pearl-100 font-medium">{fy.year_name}</h3>
                    {fy.is_current && (
                      <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded flex items-center space-x-1">
                        <CheckCircleIcon className="w-3 h-3" />
                        <span>Current</span>
                      </span>
                    )}
                  </div>
                  <p className="text-pearl-400 text-sm mt-1">
                    {new Date(fy.start_date).toLocaleDateString()} - {new Date(fy.end_date).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => onEdit(fy)}
                    className="p-2 hover:bg-pearl-700/30 rounded transition-colors"
                  >
                    <PencilIcon className="w-4 h-4 text-pearl-400" />
                  </button>
                  <button 
                    onClick={() => onDelete(fy.id)}
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

// Component for Document Series Management tab
function DocumentSeriesManagement({ series, onAdd, onEdit, onDelete }: {
  series: OrganizationDocumentSeries[];
  organizationId?: string;
  onAdd: () => void;
  onEdit: (doc: OrganizationDocumentSeries) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold text-pearl-100">Document Series</h2>
        <button 
          onClick={onAdd}
          className="px-4 py-2 bg-gradient-to-r from-saturn-500 to-sun-500 text-white rounded-lg hover:from-saturn-600 hover:to-sun-600 transition-all flex items-center space-x-2"
        >
          <PlusIcon className="w-4 h-4" />
          <span>Add Series</span>
        </button>
      </div>

      {series.length === 0 ? (
        <div className="text-center py-12 text-pearl-400">
          No document series configured yet
        </div>
      ) : (
        <div className="grid gap-4">
          {series.map((doc) => (
            <div key={doc.id} className="bg-pearl-800/30 rounded-lg p-4 border border-pearl-700/30">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h3 className="text-pearl-100 font-medium">{doc.document_type}</h3>
                  <p className="text-pearl-400 text-sm mt-1">
                    Format: {doc.prefix}{String(doc.current_number).padStart(doc.padding_length, '0')}{doc.suffix || ''}
                  </p>
                  <p className="text-pearl-500 text-sm mt-1">
                    Current Number: {doc.current_number} • Padding: {doc.padding_length} digits
                  </p>
                </div>
                <div className="flex space-x-2">
                  <button 
                    onClick={() => onEdit(doc)}
                    className="p-2 hover:bg-pearl-700/30 rounded transition-colors"
                  >
                    <PencilIcon className="w-4 h-4 text-pearl-400" />
                  </button>
                  <button 
                    onClick={() => onDelete(doc.id)}
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
